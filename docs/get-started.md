# Get started with sbx-agents

This page walks through a first session: install dependencies, run Codex or OpenCode in Docker SBX, inspect results, and clean up.

By the end, you will have composed an agent and a sandbox from Python. No hard-coded CLI wrapper. No single agent framework. No single runtime.

## Prerequisites

For Python SDK usage:

- Python 3.11 or later.
- `uv` installed.

For Docker SBX runs:

- Docker SBX CLI installed as `sbx`.
- `sbx login` completed.
- Agent credentials configured for the agent you run.

Install Docker SBX:

=== "macOS"

    ```console
    $ brew install docker/tap/sbx
    $ sbx login
    ```

=== "Windows"

    ```powershell
    > winget install -h Docker.sbx
    > sbx login
    ```

=== "Ubuntu"

    ```console
    $ curl -fsSL https://get.docker.com | sudo REPO_ONLY=1 sh
    $ sudo apt-get install docker-sbx
    $ sudo usermod -aG kvm "$USER"
    $ newgrp kvm
    $ sbx login
    ```

Verify:

```console
$ sbx --help
```

## Install

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

To install only the CLI as a standalone uv tool:

```console
$ uv tool install sbx-agents
$ sbxa --help
```

For local development from a checkout:

```console
$ uv tool install -e .
$ sbxa --help
```

## Run an agent in Docker SBX

Docker SBX runs the agent through Docker Sandboxes. Use it when you want stronger local isolation and branch/worktree handling.

Optional preflight check:

```python
from sbx_agents.sandboxes import DockerSbxSandbox

DockerSbxSandbox.check_available()
```

=== "Codex"

    ```python
    from pathlib import Path

    from sbx_agents import Agent, Runner
    from sbx_agents.backends import Codex
    from sbx_agents.sandboxes import DockerSbxSandbox

    agent = Agent(
        name="fix-tests",
        backend=Codex(model="gpt-5-codex", approval_policy="on-request"),
        instructions="Fix failing tests with the smallest safe diff.",
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
    ```

=== "OpenCode"

    ```python
    from pathlib import Path

    from sbx_agents import Agent, Runner
    from sbx_agents.backends import OpenCode
    from sbx_agents.sandboxes import DockerSbxSandbox

    agent = Agent(
        name="reviewer",
        backend=OpenCode(model="anthropic/claude-sonnet-4-5"),
        instructions="Review the repository and produce a risk-ranked report.",
    )

    result = Runner.run_sync(
        agent,
        sandbox=DockerSbxSandbox(
            workspace=Path("."),
            name="reviewer",
            branch="agent/review",
        ),
        prompt="Review this repository and identify the highest-risk issues.",
    )
    ```

The SDK asks `sbx` to run these shapes:

=== "Codex"

    ```console
    $ sbx run codex <workspace> --name fix-tests --branch agent/fix-tests -- exec "Fix the failing pytest suite."
    ```

=== "OpenCode"

    ```console
    $ sbx run opencode <workspace> --name reviewer --branch agent/review -- run "Review this repository and identify the highest-risk issues."
    ```

Same SDK shape, different coding agent.

## Review results

Each run returns `RunResult`:

```python
print(result.output)
print(result.stdout)
print(result.stderr)
print(result.returncode)
print(result.diff)
print(result.command)
```

## Run from the CLI

Define the same agent and sandbox as a reusable `Runner`:

```python
runner = Runner(
    agent,
    sandbox=DockerSbxSandbox(workspace=Path("."), branch="agent/fix-tests"),
    default_prompt="Fix the failing pytest suite.",
)
```

Then launch it with `sbxa`:

```console
$ sbxa run main:runner
```

Override the default prompt:

```console
$ sbxa run main:runner "Only fix lint failures."
```

## Clean up

Docker SBX sandboxes may persist depending on Docker SBX lifecycle settings. Remove unused sandboxes with the `sbx` CLI when finished:

```console
$ sbx ls
$ sbx rm <sandbox-name>
```

## Next steps

- [Agents](agents.md) — choose Codex, OpenCode, Shell, or a custom backend.
- [Sandboxes](sandboxes.md) — choose Docker or Docker SBX.
- [CLI](cli.md) — run Python-defined runners from the terminal.
- [Running agents](usage.md) — learn `RunConfig`, events, and sessions.
- [Examples](examples.md) — browse runnable examples.
