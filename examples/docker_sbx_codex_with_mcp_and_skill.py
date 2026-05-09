from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Codex
from sbx_agents.mcp import StdioMCP
from sbx_agents.sandboxes import DockerSbxSandbox
from sbx_agents.skills import Skill

agent = Agent(
    name="fix-tests",
    backend=Codex(
        model="gpt-5-codex",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
    ),
    instructions="Fix failing tests with the smallest safe diff. Run tests before finishing.",
    skills=[Skill.from_dir(Path(__file__).parent / "skills" / "fix-tests")],
    mcp_servers=[
        StdioMCP(
            name="context7",
            command="npx",
            args=["-y", "@upstash/context7-mcp"],
        )
    ],
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSbxSandbox(
        workspace=Path("."),
        name="fix-tests",
        branch="agent/fix-tests",
    ),
    prompt="Fix the failing pytest suite.",
)

print(result.output)
print(result.diff)
