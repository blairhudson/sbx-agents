# sbx-agents

Build with Codex, OpenCode, Claude Code, or your favorite AI coding agent from Python.

`sbx-agents` runs coding agents in isolated sandboxes and gives your app structured access to output, logs, diffs, files, and events.

## Install

With `uv`:

```bash
uv add sbx-agents
```

With `pip`:

```bash
pip install sbx-agents
```

Install the `sbxa` CLI as a standalone uv tool:

```bash
uv tool install sbx-agents
sbxa --help
```

For local development:

```bash
uv tool install -e .
sbxa --help
```

## Basic Example

```python
from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Codex
from sbx_agents.sandboxes import DockerSbxSandbox

agent = Agent(
    name="fix-tests",
    backend=Codex(model="gpt-5-codex"),
    instructions="Fix failing tests with the smallest safe diff.",
)

result = Runner.run_sync(
    agent,
    sandbox=DockerSbxSandbox(
        workspace=Path("."),
        branch="agent/fix-tests",
    ),
    prompt="Fix the failing pytest suite.",
)

print(result.output)
print(result.diff)
```

Define a reusable runner and launch it later with `sbxa`:

```python
runner = Runner(
    agent,
    sandbox=DockerSbxSandbox(workspace=Path("."), branch="agent/fix-tests"),
    default_prompt="Fix the failing pytest suite.",
)
```

```bash
sbxa run main:runner
```

## Backends

Agent backends:

- `Codex`
- `OpenCode`
- `Shell`
- custom backends

Sandbox backends:

- `DockerSbxSandbox`
- `DockerSandbox`
- custom backends

## Docs

Full docs, examples, API reference:

https://blairhudson.com/sbx-agents/
