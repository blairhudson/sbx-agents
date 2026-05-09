---
title: sbxa CLI for Python-Defined Coding Agent Runners
description: Define a Runner in Python and launch it from the terminal with sbxa, including pretty output, JSON output, and Docker SBX checks.
---

# CLI

`sbxa` runs Python-defined `Runner` objects from the terminal.

## Install

Install with your project:

=== "uv"

    ```console
    $ uv add sbx-agents
    $ uv run sbxa --help
    ```

=== "pip"

    ```console
    $ pip install sbx-agents
    $ sbxa --help
    ```

Install as a standalone uv tool:

```console
$ uv tool install sbx-agents
$ sbxa --help
```

Install from a local checkout during development:

```console
$ uv tool install -e .
$ sbxa --help
```

If already installed, reinstall after edits:

```console
$ uv tool install -e . --force
```

## Define a runner

Create a Python file with a `runner` variable.

```python
# main.py
from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Codex
from sbx_agents.sandboxes import DockerSbxSandbox

agent = Agent(
    name="fix-tests",
    backend=Codex(model="gpt-5-codex"),
    instructions="Fix failing tests with the smallest safe diff.",
)

sandbox = DockerSbxSandbox(
    workspace=Path("."),
    branch="agent/fix-tests",
    network_allow=["host.docker.internal:8080", "localhost:8080"],
)

runner = Runner(
    agent,
    sandbox=sandbox,
    default_prompt="Fix the failing pytest suite.",
)
```

## Run it

```console
$ sbxa run main:runner
```

Before running a `DockerSbxSandbox`, `sbxa` checks readiness with `sbx diagnose -o json`. This checks daemon/auth state without launching an agent.

If not ready, sign in first:

```console
$ sbx login
$ sbxa doctor --require docker-sbx
```

Override the default prompt:

```console
$ sbxa run main:runner "Only fix lint failures."
```

File targets work too:

```console
$ sbxa run main.py:runner "Fix tests."
```

If no object name is provided, `sbxa` loads `runner` by default:

```console
$ sbxa run main.py
```

## Output modes

By default, `sbxa run` streams a human-readable view of sandbox and agent output while still collecting the final `RunResult`.

Run with pretty live output:

```console
$ sbxa run main:runner
```

Show raw provider/runtime output for debugging:

```console
$ sbxa run main:runner --raw
```

Print output plus collected diff:

```console
$ sbxa run main:runner --diff
```

Print full `RunResult` JSON:

```console
$ sbxa run main:runner --json
```

`--json` disables live streaming so stdout stays valid JSON.

Skip runtime checks when you know the sandbox is ready:

```console
$ sbxa run main:runner --no-preflight
```

## Doctor

Check local runtime tools:

```console
$ sbxa doctor
```

`doctor` reports whether Docker is installed, whether Docker SBX is installed, and whether Docker SBX auth is ready.

`sbxa doctor --require docker-sbx` runs same non-agent readiness check.

Require Docker SBX:

```console
$ sbxa doctor --require docker-sbx
```

Require Docker:

```console
$ sbxa doctor --require docker
```

## Design

`sbxa` is a launcher, not a separate orchestration layer. Your Python code defines the agent, sandbox, run config, and default prompt. The CLI loads the `Runner` and calls `runner.run_sync()`.

## Next steps

- [Get started](get-started.md) — install and run first agent.
- [Running agents](usage.md) — use `Runner` directly from Python.
- [Examples](examples.md) — browse complete source examples.
