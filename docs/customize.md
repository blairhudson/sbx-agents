# Customize

Customize agents with portable models first, then use backend-native escape hatches when exact behavior matters.

## Instructions

Instructions are written to backend-native files during materialisation.

```python
agent = Agent(
    name="fix-tests",
    backend=Codex(),
    instructions="Fix failing tests with the smallest safe diff.",
)
```

The SDK writes `AGENTS.md` when instructions or skills exist.

## Skills

Skills are portable directories with `SKILL.md`.

```python
from pathlib import Path

from sbx_agents.skills import Skill

skill = Skill.from_dir(Path("examples/skills/fix-tests"))
```

Skill file:

```markdown
---
name: fix-tests
description: Fix failing tests with smallest safe diff
---
# Fix Tests

Reproduce failures first. Prefer small, safe diffs.
```

Rendered locations:

- Codex: `.codex/skills/<name>/SKILL.md`
- OpenCode: `.opencode/skills/<name>/SKILL.md`

## MCP servers

Declare MCP once and let backend adapters render native config.

```python
from sbx_agents.mcp import HttpMCP, StdioMCP

mcp_servers = [
    StdioMCP(name="context7", command="npx", args=["-y", "@upstash/context7-mcp"]),
    HttpMCP(name="docs", url="https://mcp.example.com/mcp"),
]
```

Codex renders MCP into `.codex/config.toml`. OpenCode renders MCP into `opencode.jsonc`.

## Permissions

Use `PermissionPolicy` for common cross-backend intent.

```python
from sbx_agents import PermissionPolicy

permission = PermissionPolicy(
    default="ask",
    tools={"edit": "deny", "bash": "allow"},
)
```

OpenCode receives native `permission`. Codex receives best-effort approval-policy rendering.

## Backend-native escape hatches

Use backend fields and `extra_config` for exact native features.

```python
Codex(
    model="gpt-5-codex",
    model_reasoning_effort="high",
    features={"web_search_request": True},
    extra_config={"model_context_window": 200000},
)
```

```python
OpenCode(
    model="anthropic/claude-sonnet-4-5",
    lsp=True,
    formatter=True,
    compaction={"enabled": True, "threshold": 0.8},
)
```

## Docker-native settings

Plain Docker exposes `docker_args` for settings not yet modeled by the SDK.

```python
DockerSandbox(
    workspace=Path("."),
    docker_args=["--cpus", "2", "--memory", "4g", "--network", "none"],
)
```

## Strict mode

`strict=True` is the default. Unsupported features raise early instead of silently being ignored.

```python
Agent(name="shell", backend=Shell(), skills=[skill], strict=False)
```

Use `strict=False` only when skipping unsupported features is acceptable.

## Next steps

- [Agents](agents.md) — backend-specific behavior.
- [Examples](examples.md) — complex config examples.
- [API Reference](reference/sbx_agents/index.md) — model fields.
