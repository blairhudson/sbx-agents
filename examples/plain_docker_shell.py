from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSandbox

agent = Agent(name="python-version", backend=Shell())

result = Runner.run_sync(
    agent,
    sandbox=DockerSandbox(workspace=Path("."), image="python:3.12-slim"),
    prompt="python --version",
)

print(result.output)
