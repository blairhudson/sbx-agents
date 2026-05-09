from pathlib import Path

import pytest

from sbx_agents import Agent
from sbx_agents.backends import Codex, CodexAuth, OpenCode, Shell
from sbx_agents.errors import SandboxError
from sbx_agents.result import CommandResult
from sbx_agents.sandboxes import DockerSandbox, DockerSbxSandbox
from sbx_agents.sandboxes import docker_sbx as docker_sbx_module


def test_docker_command_mounts_workspace() -> None:
    sandbox = DockerSandbox(
        workspace=Path("."),
        image="python:3.12-slim",
        name="test-sandbox",
        env={"FOO": "bar"},
    )
    session = sandbox.prepare(Agent(name="test", backend=Shell()), None)

    assert sandbox._docker_command(session, ["sh", "-lc", "python --version"]) == [
        "docker",
        "run",
        "--rm",
        "--name",
        "test-sandbox",
        "-e",
        "FOO=bar",
        "-v",
        f"{session.workspace}:/workspace",
        "-w",
        "/workspace",
        "python:3.12-slim",
        "sh",
        "-lc",
        "python --version",
    ]


def test_docker_sbx_command_for_shell() -> None:
    sandbox = DockerSbxSandbox(workspace=Path("."), name="test", branch="agent/test")
    session = sandbox.prepare(Agent(name="test", backend=Shell()), None)

    assert sandbox._sbx_command(session, ["sh", "-lc", "pytest"]) == [
        "sbx",
        "run",
        "--name",
        "test",
        "--branch",
        "agent/test",
        "shell",
        str(session.workspace),
        "--",
        "sh",
        "-lc",
        "pytest",
    ]


def test_docker_sbx_strips_codex_binary() -> None:
    sandbox = DockerSbxSandbox(workspace=Path("."))
    session = sandbox.prepare(Agent(name="test", backend=Codex()), None)

    assert sandbox._sbx_command(session, ["codex", "exec", "fix tests"]) == [
        "sbx",
        "run",
        "codex",
        str(session.workspace),
        "--",
        "exec",
        "fix tests",
    ]


def test_docker_sbx_strips_opencode_binary() -> None:
    sandbox = DockerSbxSandbox(workspace=Path("."))
    session = sandbox.prepare(Agent(name="test", backend=OpenCode()), None)

    assert sandbox._sbx_command(session, ["opencode", "run", "review"]) == [
        "sbx",
        "run",
        "opencode",
        str(session.workspace),
        "--",
        "run",
        "review",
    ]


def test_docker_sbx_retries_existing_workspace_sandbox() -> None:
    sandbox = DockerSbxSandbox(workspace=Path("."))
    session = sandbox.prepare(Agent(name="test", backend=Codex()), None)
    result = CommandResult(
        stdout="",
        stderr=(
            "ERROR: sandbox 'codex-sbx-agents-sdk' already exists; --name can only "
            "be used when creating a new sandbox\n\n"
            "To run it, use:\n  sbx run codex-sbx-agents-sdk [-- AGENT_ARGS...]"
        ),
        returncode=1,
        command=[],
    )

    assert sandbox._existing_sandbox_retry_command(
        session,
        ["codex", "exec", "fix tests"],
        result,
    ) == ["sbx", "run", "codex-sbx-agents-sdk", "--", "exec", "fix tests"]


def test_docker_sbx_applies_network_allow_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_command(command: list[str], timeout: int | None = None) -> CommandResult:
        calls.append(command)
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(
        workspace=Path("."),
        network_allow=["host.docker.internal:8080", "api.example.com"],
    )
    session = sandbox.prepare(Agent(name="test", backend=Shell()), None)

    sandbox._apply_policies(session)

    assert calls == [
        [
            "sbx",
            "policy",
            "allow",
            "network",
            "host.docker.internal:8080,api.example.com",
        ]
    ]


def test_docker_sbx_adds_openai_network_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_command(command: list[str], timeout: int | None = None) -> CommandResult:
        calls.append(command)
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(workspace=Path("."))
    session = sandbox.prepare(
        Agent(name="test", backend=Codex(model_provider="openai", auth="openai_oauth")),
        None,
    )

    sandbox._apply_policies(session)

    assert calls == [
        [
            "sbx",
            "policy",
            "allow",
            "network",
            "api.openai.com:443,chatgpt.com:443",
        ]
    ]


def test_docker_sbx_sets_secret_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], str | None]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
    ) -> CommandResult:
        calls.append((command, input_text))
        if command[:3] == ["sbx", "secret", "ls"]:
            return CommandResult(
                stdout="No secrets found",
                stderr="",
                returncode=0,
                command=command,
            )
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setenv("OPENAI_API_KEY", "test-token")
    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(
        workspace=Path("."),
        secret_env={"openai": "OPENAI_API_KEY"},
    )

    sandbox.ensure_agent_secret("codex")

    assert calls == [
        (["sbx", "secret", "ls", "-g", "--service", "openai"], None),
        (["sbx", "secret", "set", "-g", "openai"], "test-token"),
    ]


def test_docker_sbx_sets_oauth_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
    ) -> CommandResult:
        calls.append(command)
        if command[:3] == ["sbx", "secret", "ls"]:
            return CommandResult(
                stdout="No secrets found",
                stderr="",
                returncode=0,
                command=command,
            )
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(
        workspace=Path("."),
        secret_oauth=["openai"],
    )

    sandbox.ensure_agent_secret("codex")

    assert calls == [
        ["sbx", "secret", "ls", "-g", "--service", "openai"],
        ["sbx", "secret", "set", "-g", "openai", "--oauth"],
    ]


def test_docker_sbx_applies_codex_backend_oauth_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
    ) -> CommandResult:
        calls.append(command)
        if command[:3] == ["sbx", "secret", "ls"]:
            return CommandResult(
                stdout="No secrets found",
                stderr="",
                returncode=0,
                command=command,
            )
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(workspace=Path("."))
    session = sandbox.prepare(
        Agent(name="test", backend=Codex(auth="openai_oauth")),
        None,
    )

    sandbox._apply_agent_auth(session)

    assert calls == [
        ["sbx", "secret", "ls", "-g", "--service", "openai"],
        ["sbx", "secret", "set", "-g", "openai", "--oauth"],
    ]


def test_docker_sbx_applies_codex_backend_api_key_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], str | None]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
    ) -> CommandResult:
        calls.append((command, input_text))
        if command[:3] == ["sbx", "secret", "ls"]:
            return CommandResult(
                stdout="No secrets found",
                stderr="",
                returncode=0,
                command=command,
            )
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setenv("OPENAI_TOKEN", "test-token")
    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(workspace=Path("."))
    session = sandbox.prepare(
        Agent(name="test", backend=Codex(auth=CodexAuth.openai_api_key_env("OPENAI_TOKEN"))),
        None,
    )

    sandbox._apply_agent_auth(session)

    assert calls == [
        (["sbx", "secret", "ls", "-g", "--service", "openai"], None),
        (["sbx", "secret", "set", "-g", "openai"], "test-token"),
    ]


def test_docker_sbx_refreshes_oauth_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
    ) -> CommandResult:
        calls.append(command)
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(
        workspace=Path("."),
        secret_oauth_refresh=["openai"],
    )

    sandbox.ensure_agent_secret("codex")

    assert calls == [["sbx", "secret", "set", "-g", "openai", "--oauth"]]


def test_docker_sbx_syncs_host_codex_auth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    auth_path = tmp_path / "auth.json"
    auth_path.write_text('{"auth_mode": "chatgpt"}', encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
        stream_filter: object | None = None,
        cwd: Path | None = None,
    ) -> CommandResult:
        calls.append(command)
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "_host_codex_auth_path", lambda: auth_path)
    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(workspace=Path("."))
    session = sandbox.prepare(Agent(name="test", backend=Codex()), None)

    sandbox._sync_host_codex_auth("test-sandbox", session=session)

    assert calls == [
        ["sbx", "exec", "test-sandbox", "mkdir", "-p", "/home/agent/.codex"],
        ["sbx", "cp", str(auth_path), "test-sandbox:/home/agent/.codex/auth.json"],
        [
            "sbx",
            "exec",
            "-u",
            "root",
            "test-sandbox",
            "sh",
            "-lc",
            "chown agent:agent /home/agent/.codex/auth.json && "
            "chmod 600 /home/agent/.codex/auth.json",
        ],
    ]


def test_docker_sbx_force_recreate_removes_existing_named_sandbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
        cwd: Path | None = None,
    ) -> CommandResult:
        calls.append(command)
        if command == ["sbx", "ls"]:
            return CommandResult(
                stdout="SANDBOX AGENT STATUS PORTS WORKSPACE\nexample codex stopped /repo",
                stderr="",
                returncode=0,
                command=command,
            )
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(workspace=Path("."), name="example", force_recreate=True)

    sandbox._remove_existing_sandbox("example")

    assert calls == [["sbx", "ls"], ["sbx", "rm", "example"]]


def test_docker_sbx_force_recreate_removes_conflicting_workspace_sandboxes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        input_text: str | None = None,
        timeout: int | None = None,
        stream: bool = False,
        cwd: Path | None = None,
    ) -> CommandResult:
        calls.append(command)
        if command == ["sbx", "ls"]:
            return CommandResult(
                stdout=(
                    "SANDBOX AGENT STATUS PORTS WORKSPACE\n"
                    "codex-sbx-repo codex stopped /repo\n"
                    "named codex stopped /other"
                ),
                stderr="",
                returncode=0,
                command=command,
            )
        return CommandResult(stdout="", stderr="", returncode=0, command=command)

    monkeypatch.setattr(docker_sbx_module, "run_command", fake_run_command)
    sandbox = DockerSbxSandbox(workspace=Path("/repo"), name="named", force_recreate=True)
    session = sandbox.prepare(Agent(name="test", backend=Codex()), None)

    sandbox._remove_workspace_sandboxes(session)

    assert calls == [
        ["sbx", "ls"],
        ["sbx", "ls"],
        ["sbx", "rm", "codex-sbx-repo"],
    ]


def test_docker_sbx_does_not_retry_unrelated_sandbox_when_named() -> None:
    sandbox = DockerSbxSandbox(workspace=Path("."), name="wanted")
    session = sandbox.prepare(Agent(name="test", backend=Codex()), None)
    result = CommandResult(
        stdout="",
        stderr=(
            "ERROR: sandbox 'codex-sbx-repo' already exists; "
            "--name can only be used when creating a new sandbox\n"
            "To run it, use:\n  sbx run codex-sbx-repo [-- AGENT_ARGS...]"
        ),
        returncode=1,
        command=["sbx", "run"],
    )

    assert (
        sandbox._existing_sandbox_retry_command(session, ["codex", "exec", "fix"], result)
        is None
    )


def test_docker_sbx_check_available_raises_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docker_sbx_module, "_find_sbx", lambda: None)

    with pytest.raises(SandboxError, match="brew install docker/tap/sbx"):
        DockerSbxSandbox.check_available()


def test_docker_sbx_check_available_passes_when_sbx_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docker_sbx_module, "_find_sbx", lambda: "/usr/local/bin/sbx")

    DockerSbxSandbox.check_available()


def test_docker_sbx_check_ready_passes_when_sbx_ls_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docker_sbx_module, "_find_sbx", lambda: "/usr/local/bin/sbx")
    monkeypatch.setattr(
        docker_sbx_module,
        "run_command",
        lambda command, timeout=None: CommandResult(
            stdout=(
                '{"checks":[{"name":"CLI binary","status":"pass"},'
                '{"name":"Daemon","status":"pass"},'
                '{"name":"Authentication","status":"pass"}]}'
            ),
            stderr="",
            returncode=0,
            command=command,
        ),
    )

    DockerSbxSandbox.check_ready()


def test_docker_sbx_check_ready_raises_when_sbx_ls_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docker_sbx_module, "_find_sbx", lambda: "/usr/local/bin/sbx")
    monkeypatch.setattr(
        docker_sbx_module,
        "run_command",
        lambda command, timeout=None: CommandResult(
            stdout=(
                '{"checks":[{"name":"CLI binary","status":"pass"},'
                '{"name":"Authentication","status":"fail","message":"login required"}]}'
            ),
            stderr="",
            returncode=0,
            command=command,
        ),
    )

    with pytest.raises(SandboxError, match="sbx login"):
        DockerSbxSandbox.check_ready()


def test_docker_sbx_check_agent_secrets_raises_for_missing_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docker_sbx_module, "_find_sbx", lambda: "/usr/local/bin/sbx")
    monkeypatch.setattr(
        docker_sbx_module,
        "run_command",
        lambda command, timeout=None: CommandResult(
            stdout='No secrets found for scope "(global)" and service "openai".',
            stderr="",
            returncode=0,
            command=command,
        ),
    )

    with pytest.raises(SandboxError, match="sbx secret set -g openai"):
        DockerSbxSandbox.check_agent_secrets("codex")


def test_sandbox_file_management(tmp_path: Path) -> None:
    sandbox = DockerSandbox(workspace=tmp_path)

    written = sandbox.put_file("nested/spec.md", "# Spec\n")

    assert written == tmp_path / "nested" / "spec.md"
    assert sandbox.get_file("nested/spec.md") == "# Spec\n"
    assert sandbox.list_files("nested/*.md") == [Path("nested/spec.md")]

    sandbox.put_bytes("nested/blob.bin", b"abc")
    assert sandbox.get_bytes("nested/blob.bin") == b"abc"

    sandbox.delete_file("nested/spec.md")
    assert sandbox.list_files("nested/*.md") == []


def test_sandbox_file_management_rejects_workspace_escape(tmp_path: Path) -> None:
    sandbox = DockerSandbox(workspace=tmp_path)

    try:
        sandbox.put_file("../escape.txt", "bad")
    except ValueError as error:
        assert "escapes workspace" in str(error)
    else:
        raise AssertionError("Expected ValueError")
