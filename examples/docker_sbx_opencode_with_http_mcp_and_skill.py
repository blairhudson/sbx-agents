from pathlib import Path

from sbx_agents import Agent, PermissionPolicy, Runner
from sbx_agents.backends import OpenCode
from sbx_agents.mcp import HttpMCP
from sbx_agents.sandboxes import DockerSbxSandbox
from sbx_agents.skills import Skill

agent = Agent(
    name="reviewer",
    backend=OpenCode(
        model="anthropic/claude-sonnet-4-5",
    ),
    permission=PermissionPolicy(tools={"edit": "deny", "bash": "allow"}),
    instructions="Review the repo and produce a risk-ranked plan.",
    skills=[Skill.from_dir(Path(__file__).parent / "skills" / "review-risk")],
    mcp_servers=[
        HttpMCP(
            name="docs",
            url="https://mcp.example.com/mcp",
            bearer_token_env_var="DOCS_MCP_TOKEN",
        )
    ],
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSbxSandbox(
        workspace=Path("."),
        name="reviewer",
        branch="agent/review",
    ),
    prompt="Review this repository for release risk.",
)

print(result.output)
