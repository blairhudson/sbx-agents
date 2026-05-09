import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSbxSandbox

pytestmark = pytest.mark.integration


def _require_docker_sbx() -> None:
    if os.environ.get("RUN_DOCKER_SBX_TESTS") != "1":
        pytest.skip("Set RUN_DOCKER_SBX_TESTS=1 to run Docker SBX integration tests")
    if shutil.which("sbx") is None:
        pytest.skip("Docker SBX CLI `sbx` not found")


def _sandbox_name(prefix: str) -> str:
    return f"sbx-agents-{prefix}-{uuid.uuid4().hex[:8]}"


def _remove_sandbox(name: str) -> None:
    subprocess.run(
        ["sbx", "rm", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _git(workspace: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(workspace), *args], check=True)


def test_docker_sbx_shell_runs_command(tmp_path: Path) -> None:
    _require_docker_sbx()
    name = _sandbox_name("shell")
    sandbox = DockerSbxSandbox(workspace=tmp_path, name=name)
    session = sandbox.prepare(Agent(name="shell", backend=Shell()), None)

    try:
        result = sandbox.run(
            session,
            ["sh", "-lc", "printf 'sbx-ok' > sbx-output.txt && printf 'stdout-ok'"],
        )
    finally:
        _remove_sandbox(name)

    assert result.returncode == 0, result.stderr
    assert "stdout-ok" in result.stdout
    assert (tmp_path / "sbx-output.txt").read_text(encoding="utf-8") == "sbx-ok"


def test_docker_sbx_runner_collects_tracked_diff(tmp_path: Path) -> None:
    _require_docker_sbx()
    name = _sandbox_name("runner")
    (tmp_path / "tracked.txt").write_text("before\n", encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "add", "tracked.txt")
    _git(
        tmp_path,
        "-c",
        "user.name=sbx-agents-test",
        "-c",
        "user.email=sbx-agents-test@example.com",
        "commit",
        "-m",
        "init",
    )

    try:
        result = Runner.run_sync(
            Agent(name="shell", backend=Shell()),
            sandbox=DockerSbxSandbox(workspace=tmp_path, name=name),
            prompt="printf 'after\\n' > tracked.txt && printf 'changed'",
        )
    finally:
        _remove_sandbox(name)

    assert result.returncode == 0, result.stderr
    assert "changed" in result.output
    assert result.diff is not None
    assert "-before" in result.diff
    assert "+after" in result.diff
