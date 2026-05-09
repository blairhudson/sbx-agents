from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Codex
from sbx_agents.sandboxes import DockerSbxSandbox

agent = Agent(
    name="fix-tests",
    backend=Codex(),
    instructions="Fix failing tests with the smallest safe diff.",
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSbxSandbox(workspace=Path("."), branch="agent/fix-tests"),
    prompt="Fix the failing tests.",
)

print(result.output)
