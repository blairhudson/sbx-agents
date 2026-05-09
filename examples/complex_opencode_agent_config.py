from pathlib import Path

from sbx_agents import Agent, PermissionPolicy, RunConfig, Runner
from sbx_agents.backends import OpenCode
from sbx_agents.mcp import HttpMCP, StdioMCP
from sbx_agents.sandboxes import DockerSbxSandbox
from sbx_agents.skills import Skill

agent = Agent(
    name="read-only-reviewer",
    backend=OpenCode(
        model="anthropic/claude-sonnet-4-5",
        small_model="anthropic/claude-haiku-4-5",
        agent="build",
        permission={
            "edit": "deny",
            "bash": {
                "pytest*": "allow",
                "git diff*": "allow",
                "*": "ask",
            },
        },
        lsp=True,
        formatter=True,
        instructions=["README.md", "CONTRIBUTING.md"],
        disabled_providers=["example-disabled-provider"],
        snapshot=True,
        share="manual",
        compaction={"enabled": True, "threshold": 0.8},
    ),
    instructions="Review the repository for release risk. Do not modify files.",
    permission=PermissionPolicy(default="ask", tools={"edit": "deny", "bash": "allow"}),
    skills=[Skill.from_dir(Path(__file__).parent / "skills" / "review-risk")],
    mcp_servers=[
        StdioMCP(
            name="context7",
            command="npx",
            args=["-y", "@upstash/context7-mcp"],
            startup_timeout_sec=20,
        ),
        HttpMCP(
            name="docs",
            url="https://mcp.example.com/mcp",
            headers={"X-Workspace": "release"},
        ),
    ],
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSbxSandbox(
        workspace=Path("."),
        name="read-only-reviewer",
        branch="agent/read-only-reviewer",
    ),
    prompt="Review this repository and return a risk-ranked report.",
    run_config=RunConfig(
        json_events=True,
        extra_args=["--title", "Release risk review"],
    ),
)

print(result.output)
