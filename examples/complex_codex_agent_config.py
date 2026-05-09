from pathlib import Path

from sbx_agents import Agent, PermissionPolicy, RunConfig, Runner
from sbx_agents.backends import Codex
from sbx_agents.mcp import HttpMCP, StdioMCP
from sbx_agents.sandboxes import DockerSbxSandbox
from sbx_agents.skills import Skill

agent = Agent(
    name="release-risk-fixer",
    backend=Codex(
        model="gpt-5-codex",
        model_provider="openai",
        model_reasoning_effort="high",
        model_reasoning_summary="auto",
        model_verbosity="medium",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
        web_search="enabled",
        features={"web_search_request": True},
        shell_environment_policy={
            "inherit": "core",
            "include_only": ["PATH", "HOME", "OPENAI_API_KEY", "GITHUB_TOKEN"],
        },
        extra_config={
            "model_context_window": 200000,
        },
    ),
    instructions=(
        "Act as a release engineer. Identify high-risk failures, fix only the smallest "
        "safe issue, and return structured release risk output."
    ),
    permission=PermissionPolicy(default="ask", tools={"bash": "allow", "edit": "ask"}),
    skills=[
        Skill.from_dir(Path(__file__).parent / "skills" / "fix-tests"),
        Skill.from_dir(Path(__file__).parent / "skills" / "review-risk"),
    ],
    mcp_servers=[
        StdioMCP(
            name="context7",
            command="npx",
            args=["-y", "@upstash/context7-mcp"],
            env={"NODE_OPTIONS": "--max-old-space-size=2048"},
            startup_timeout_sec=20,
            tool_timeout_sec=60,
            enabled_tools=["resolve-library-id", "get-library-docs"],
        ),
        HttpMCP(
            name="internal-docs",
            url="https://mcp.example.com/mcp",
            bearer_token_env_var="DOCS_MCP_TOKEN",
            required=True,
        ),
    ],
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSbxSandbox(
        workspace=Path("."),
        name="release-risk-fixer",
        branch="agent/release-risk-fixer",
        cpus=4,
        memory="8g",
    ),
    prompt="Review release risk, fix the smallest critical issue, and summarize validation.",
    run_config=RunConfig(
        json_events=True,
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                "tests_run": {"type": "array", "items": {"type": "string"}},
                "follow_ups": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "risk", "tests_run"],
        },
        extra_args=["--skip-git-repo-check"],
    ),
)

print(result.output)
print(result.diff)
