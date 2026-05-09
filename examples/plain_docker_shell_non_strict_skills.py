from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSandbox
from sbx_agents.skills import Skill

agent = Agent(
    name="shell-test",
    backend=Shell(),
    skills=[Skill.from_dir(Path(__file__).parent / "skills" / "fix-tests")],
    strict=False,
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSandbox(workspace=Path("."), image="python:3.12-slim"),
    prompt="python --version",
)

print(result.output)
