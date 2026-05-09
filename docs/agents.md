---
title: Agent Backends for Codex, OpenCode, Shell, and Claude Code
description: Choose and configure coding-agent backends, including Codex, OpenCode, Shell, and future Claude Code adapters.
---

# Agents

An agent backend defines what coding agent runs and how agent-specific config is materialised.

Use whatever agent is best this week. The backend boundary exists because the coding-agent market changes fast.

## Supported agents

| Backend | Command shape | Best for |
| --- | --- | --- |
| `Shell` | `sh -lc <prompt>` | Smoke tests, CI commands, sandbox plumbing |
| `Codex` | `codex exec <prompt>` | Coding tasks, structured output, JSON events |
| `OpenCode` | `opencode run <prompt>` | Review agents, permissioned workflows, sessions |

Future backends can wrap Claude Code, Gemini, Cursor, Docker Agent, or any internal agent CLI without changing sandbox orchestration.

## Shell

Use `Shell` when you want no agent CLI at all.

```python
from sbx_agents import Agent
from sbx_agents.backends import Shell

agent = Agent(name="test-runner", backend=Shell())
```

Shell ignores agent-only features such as skills and MCP only when `strict=False`. With `strict=True`, unsupported features raise an error.

## Codex

Use `Codex` for coding tasks that should run through the Codex CLI.

```python
from sbx_agents import Agent
from sbx_agents.backends import Codex

agent = Agent(
    name="fix-tests",
    backend=Codex(
        model="gpt-5-codex",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
    ),
    instructions="Fix failing tests with the smallest safe diff.",
)
```

Codex materialisation writes:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/skills/<skill>/SKILL.md`

Codex MCP servers are rendered into `.codex/config.toml` under `[mcp_servers.<name>]`.

## OpenCode

Use `OpenCode` for review agents, permission-controlled workflows, and session-oriented runs.

```python
from sbx_agents import Agent, PermissionPolicy
from sbx_agents.backends import OpenCode

agent = Agent(
    name="reviewer",
    backend=OpenCode(model="anthropic/claude-sonnet-4-5"),
    instructions="Review the repository and return a risk-ranked report.",
    permission=PermissionPolicy(tools={"edit": "deny", "bash": "allow"}),
)
```

OpenCode materialisation writes:

- `AGENTS.md`
- `opencode.jsonc`
- `.opencode/skills/<skill>/SKILL.md`

OpenCode MCP servers are rendered as `local` or `remote` entries in `opencode.jsonc`.

## Backend-native config

Portable models cover common cases. Use backend-native fields when you need exact CLI behavior.

```python
backend = Codex(
    model="gpt-5-codex",
    extra_config={"model_context_window": 200000},
)
```

```python
backend = OpenCode(
    model="anthropic/claude-sonnet-4-5",
    lsp=True,
    formatter=True,
    compaction={"enabled": True, "threshold": 0.8},
)
```

## Custom agent backends

Implement the `AgentBackend` protocol:

```python
class MyBackend:
    id = "my-agent"

    def materialise(self, ctx, agent):
        ...

    def command(self, prompt, run_config=None):
        return ["my-agent", "run", prompt]
```

## Next steps

- [Sandboxes](sandboxes.md) — choose where agents run.
- [Customize](customize.md) — add skills, MCP, and permissions.
- [Running agents](usage.md) — run and inspect results.
