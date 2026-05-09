from pathlib import Path

import pytest
from typer.testing import CliRunner

from sbx_agents import Agent, Runner, RunResult
from sbx_agents.backends import Codex
from sbx_agents.cli import _check_docker_sbx_local_provider, _cli_run_config, app
from sbx_agents.errors import SandboxError
from sbx_agents.sandboxes import DockerSbxSandbox


def _fake_result() -> RunResult:
    return RunResult(
        output="ok",
        stdout="ok",
        stderr="",
        returncode=0,
        agent_name="cli",
        agent_backend="codex",
        sandbox_backend="docker_sbx",
        command=["codex", "exec", "fix"],
    )


def _write_runner_file(path: Path) -> None:
    path.write_text(
        """
from pathlib import Path

from sbx_agents import Agent, CommandResult, RunArtifacts, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes.base import SandboxSession


class CliSandbox:
    id = "cli-fake"

    def prepare(self, agent, run_config):
        return SandboxSession(workspace=Path("."), sandbox_name="cli-fake")

    def run(self, session, command):
        return CommandResult(stdout="cli output", stderr="", returncode=0, command=command)

    def collect(self, session):
        return RunArtifacts(diff="diff --git a/file b/file")

    def cleanup(self, session):
        return None


runner = Runner(
    Agent(name="cli", backend=Shell()),
    sandbox=CliSandbox(),
    default_prompt="echo default",
)
""".strip(),
        encoding="utf-8",
    )


def test_cli_run_file_target_default_prompt(tmp_path: Path) -> None:
    target = tmp_path / "main.py"
    _write_runner_file(target)
    result = CliRunner().invoke(app, ["run", str(target)])

    assert result.exit_code == 0, result.output
    assert "cli output" in result.output
    assert "Running cli with shell in cli-fake" in result.output


def test_cli_run_file_target_with_diff(tmp_path: Path) -> None:
    target = tmp_path / "main.py"
    _write_runner_file(target)
    result = CliRunner().invoke(app, ["run", f"{target}:runner", "override", "--diff"])

    assert result.exit_code == 0, result.output
    assert "cli output" in result.output
    assert "--- diff ---" in result.output
    assert "diff --git" in result.output


def test_cli_run_json_output(tmp_path: Path) -> None:
    target = tmp_path / "main.py"
    _write_runner_file(target)
    result = CliRunner().invoke(app, ["run", str(target), "--json"])

    assert result.exit_code == 0, result.output
    assert '"output": "cli output"' in result.output
    assert '"sandbox_backend": "cli-fake"' in result.output


def test_cli_run_rejects_non_runner(tmp_path: Path) -> None:
    target = tmp_path / "main.py"
    target.write_text("runner = object()\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["run", str(target)])

    assert result.exit_code != 0
    assert "Target must be a sbx_agents.Runner instance" in result.output


def test_cli_doctor() -> None:
    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "sbx-agents: ok" in result.output
    assert "docker:" in result.output
    assert "docker-sbx:" in result.output
    assert "docker-sbx auth:" in result.output


def test_cli_preflights_docker_sbx_binary_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def check_ready() -> None:
        calls.append("ready")

    monkeypatch.setattr(DockerSbxSandbox, "check_ready", check_ready)
    monkeypatch.setattr(
        DockerSbxSandbox,
        "ensure_agent_auth",
        lambda self, agent, run_config=None, **kwargs: None,
    )
    sandbox = DockerSbxSandbox(workspace=Path("."))
    runner = Runner(Agent(name="cli", backend=Codex()), sandbox=sandbox, default_prompt="fix")
    monkeypatch.setattr("sbx_agents.cli._load_target", lambda target: runner)
    monkeypatch.setattr(Runner, "_run_sync", lambda *args, **kwargs: _fake_result())

    result = CliRunner().invoke(app, ["run", "main:runner"])

    assert result.exit_code == 0, result.output
    assert calls == ["ready"]
    assert "Docker SBX ready" in result.output


def test_cli_can_skip_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(DockerSbxSandbox, "check_ready", lambda: calls.append("ready"))
    monkeypatch.setattr(
        DockerSbxSandbox,
        "ensure_agent_auth",
        lambda self, agent, run_config=None, **kwargs: None,
    )
    sandbox = DockerSbxSandbox(workspace=Path("."))
    runner = Runner(Agent(name="cli", backend=Codex()), sandbox=sandbox, default_prompt="fix")
    monkeypatch.setattr("sbx_agents.cli._load_target", lambda target: runner)
    monkeypatch.setattr(Runner, "_run_sync", lambda *args, **kwargs: _fake_result())

    result = CliRunner().invoke(app, ["run", "main:runner", "--no-preflight"])

    assert result.exit_code == 0, result.output
    assert calls == []


def test_cli_run_config_adds_pretty_filter() -> None:
    runner = Runner(
        Agent(name="cli", backend=Codex()),
        sandbox=DockerSbxSandbox(workspace=Path(".")),
    )

    run_config = _cli_run_config(runner, stream_output=True)

    assert run_config is not None
    assert run_config.stream_output is True
    assert "stream_filter" in run_config.metadata


def test_cli_run_config_raw_skips_pretty_filter() -> None:
    runner = Runner(
        Agent(name="cli", backend=Codex()),
        sandbox=DockerSbxSandbox(workspace=Path(".")),
    )

    run_config = _cli_run_config(runner, stream_output=True, raw=True)

    assert run_config is not None
    assert run_config.stream_output is True
    assert "stream_filter" not in run_config.metadata


def test_cli_rejects_localhost_provider_for_docker_sbx() -> None:
    runner = Runner(
        Agent(
            name="cli",
            backend=Codex(
                model="local-model",
                model_provider="local",
                extra_config={
                    "model_providers": {
                        "local": {"base_url": "http://localhost:8080/v1"}
                    }
                },
            ),
        ),
        sandbox=DockerSbxSandbox(workspace=Path(".")),
        default_prompt="fix",
    )

    try:
        _check_docker_sbx_local_provider(runner)
    except SandboxError as error:
        assert "host.docker.internal" in str(error)
    else:
        raise AssertionError("Expected SandboxError")
