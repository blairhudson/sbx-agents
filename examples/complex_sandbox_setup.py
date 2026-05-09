from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSandbox, DockerSbxSandbox

workspace = Path(".")

agent = Agent(
    name="sandbox-smoke-test",
    backend=Shell(),
    instructions="Run diagnostics inside the sandbox and report the environment.",
)

# Plain Docker: useful in CI or Linux environments where Docker SBX is unavailable.
# `docker_args` is the escape hatch for Docker-native settings the SDK has not modeled yet.
plain_docker = DockerSandbox(
    workspace=workspace,
    image="python:3.12-slim",
    name="sbx-agents-smoke-test",
    workdir="/workspace",
    env={
        "PYTHONUNBUFFERED": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    },
    docker_args=[
        "--cpus",
        "2",
        "--memory",
        "4g",
        "--network",
        "bridge",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=512m",
        "-v",
        f"{(Path.home() / '.cache' / 'pip').resolve()}:/root/.cache/pip",
    ],
)

plain_result = Runner.run_sync(
    agent,
    sandbox=plain_docker,
    prompt="python --version && pwd && ls",
)

print("Plain Docker output:")
print(plain_result.output)

# Docker SBX: better local isolation for real coding agents, with branch/resource controls.
docker_sbx = DockerSbxSandbox(
    workspace=workspace,
    name="sbx-agents-isolated-smoke-test",
    branch="agent/sandbox-smoke-test",
    cpus=4,
    memory="8g",
    remove_on_exit=True,
)

sbx_result = Runner.run_sync(
    agent,
    sandbox=docker_sbx,
    prompt="pwd && git status --short && python --version || true",
)

print("Docker SBX output:")
print(sbx_result.output)
print("Docker SBX diff:")
print(sbx_result.diff)
