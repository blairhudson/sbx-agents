from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import OpenCode
from sbx_agents.sandboxes import DockerSbxSandbox

agent = Agent(
    name="reviewer",
    backend=OpenCode(),
    instructions="Review the repo and produce a risk-ranked plan.",
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSbxSandbox(workspace=Path("."), branch="agent/review"),
    prompt="Review this repository.",
)

print(result.output)
