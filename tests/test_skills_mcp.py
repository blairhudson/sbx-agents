from pathlib import Path

import pytest

from sbx_agents import Agent, PermissionPolicy, RunConfig
from sbx_agents.backends import Codex, OpenCode, Shell
from sbx_agents.context import MaterialiseContext
from sbx_agents.errors import UnsupportedFeatureError
from sbx_agents.mcp import HttpMCP, StdioMCP
from sbx_agents.sandboxes.base import SandboxSession
from sbx_agents.skills import Skill


def test_skill_from_dir(tmp_path: Path) -> None:
    skill_dir = tmp_path / "fix-tests"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: fix-tests\ndescription: Fix Tests\nmetadata:\n  team: sdk\n---\n"
        "# Fix Tests\n\nRun tests first.\n",
        encoding="utf-8",
    )

    skill = Skill.from_dir(skill_dir)

    assert skill.name == "fix-tests"
    assert skill.description == "Fix Tests"
    assert skill.metadata == {"team": "sdk"}
    assert "Run tests first" in skill.instructions


def test_codex_materialises_skills_and_mcp(tmp_path: Path) -> None:
    skill = Skill(name="fix-tests", description="Fix Tests", instructions="# Fix Tests\n")
    agent = Agent(
        name="fixer",
        backend=Codex(model="gpt-5-codex", approval_policy="on-request"),
        instructions="Fix tests.",
        skills=[skill],
        mcp_servers=[StdioMCP(name="context7", command="npx", args=["-y", "pkg"])],
    )

    agent.backend.materialise(_ctx(tmp_path), agent)

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8").startswith("Fix tests.")
    assert (tmp_path / ".codex" / "skills" / "fix-tests" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == "# Fix Tests\n"
    assert 'model = "gpt-5-codex"' in (tmp_path / ".codex" / "config.toml").read_text(
        encoding="utf-8"
    )
    config = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.context7]" in config
    assert 'command = "npx"' in config
    assert 'args = ["-y", "pkg"]' in config


def test_opencode_materialises_skills_and_http_mcp(tmp_path: Path) -> None:
    skill = Skill(name="review-risk", description="Risk Review", instructions="# Risk Review\n")
    agent = Agent(
        name="reviewer",
        backend=OpenCode(model="anthropic/claude-sonnet-4-5"),
        permission=PermissionPolicy(tools={"edit": "deny"}),
        skills=[skill],
        mcp_servers=[
            HttpMCP(name="docs", url="https://mcp.example.com/mcp", headers={"X-Test": "1"})
        ],
    )

    agent.backend.materialise(_ctx(tmp_path), agent)

    skill_text = (tmp_path / ".opencode" / "skills" / "review-risk" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "name: review-risk" in skill_text
    assert "description: Risk Review" in skill_text
    config = (tmp_path / "opencode.jsonc").read_text(encoding="utf-8")
    assert '"model": "anthropic/claude-sonnet-4-5"' in config
    assert '"permission"' in config
    assert '"edit": "deny"' in config
    assert '"docs"' in config
    assert '"type": "remote"' in config
    assert '"url": "https://mcp.example.com/mcp"' in config


def test_opencode_materialises_local_mcp(tmp_path: Path) -> None:
    agent = Agent(
        name="reviewer",
        backend=OpenCode(),
        mcp_servers=[StdioMCP(name="context7", command="npx", args=["-y", "pkg"])],
    )

    agent.backend.materialise(_ctx(tmp_path), agent)

    config = (tmp_path / "opencode.jsonc").read_text(encoding="utf-8")
    assert '"type": "local"' in config
    assert '"command": [\n        "npx",\n        "-y",\n        "pkg"\n      ]' in config


def test_backend_commands_include_json_and_session_flags() -> None:
    codex = Codex()
    codex_config = RunConfig(json_events=True, output_schema=Path("schema.json"))
    assert codex.command("review", codex_config) == [
        "codex",
        "exec",
        "--json",
        "--output-schema",
        "schema.json",
        "review",
    ]
    opencode = OpenCode()
    assert opencode.command("review", RunConfig(json_events=True, resume_session_id="sess")) == [
        "opencode",
        "run",
        "--format",
        "json",
        "--session",
        "sess",
        "review",
    ]


def test_shell_strict_rejects_skills(tmp_path: Path) -> None:
    agent = Agent(
        name="shell",
        backend=Shell(),
        skills=[Skill(name="fix-tests", instructions="# Fix Tests\n")],
    )

    with pytest.raises(UnsupportedFeatureError):
        agent.backend.materialise(_ctx(tmp_path), agent)


def test_shell_non_strict_ignores_skills(tmp_path: Path) -> None:
    agent = Agent(
        name="shell",
        backend=Shell(),
        skills=[Skill(name="fix-tests", instructions="# Fix Tests\n")],
        strict=False,
    )

    agent.backend.materialise(_ctx(tmp_path), agent)


def _ctx(workspace: Path) -> MaterialiseContext:
    return MaterialiseContext(
        workspace=workspace,
        sandbox=SandboxSession(workspace=workspace),
    )
