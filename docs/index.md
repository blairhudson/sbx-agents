<section class="sbx-hero" markdown="1">
<span class="sbx-kicker">python sdk for coding agents</span>

# Build with your favorite coding agent

Run real coding agents against real repositories in real sandboxes.

Use Claude Code, Codex, OpenCode, or your own agent whenever you need it. Run the same agent in Docker for CI, Docker Sandboxes for local isolation, and future cloud backends for production.

`sbx-agents` is the missing SDK layer between autonomous coding agents and isolated execution environments.

<div class="sbx-pill-row">
  <a class="sbx-pill" href="agents.md#codex">Codex</a>
  <a class="sbx-pill" href="agents.md#opencode">OpenCode</a>
  <a class="sbx-pill" href="agents.md#supported-agents">Claude Code ready</a>
  <a class="sbx-pill" href="sandboxes.md#docker-sbx">Docker SBX</a>
  <a class="sbx-pill" href="sandboxes.md#plain-docker">Plain Docker</a>
  <a class="sbx-pill" href="usage.md">SDK-first</a>
</div>
</section>

## Not another LLM app framework

OpenAI Agents SDK, Pydantic AI, LangGraph, and similar frameworks help orchestrate LLM calls, tool schemas, and chat workflows.

`sbx-agents` orchestrates coding agents that operate on repositories: edit files, run tests, use MCP, produce diffs, and return artifacts from isolated sandboxes.

| Need | LLM app frameworks | `sbx-agents` |
| --- | --- | --- |
| Chat/tool graph | first-class | not the focus |
| Run Codex/OpenCode/Claude Code-style CLIs | awkward | first-class |
| Isolated repo workspace | external concern | core abstraction |
| Collect `git diff` | hand-roll | built in |
| Swap sandbox runtime | hand-roll | backend interface |
| Multi-agent coding workflows | hand-roll | core pattern |

## Get started

Install the package:

=== "uv"

    ```console
    $ uv add sbx-agents
    ```

=== "pip"

    ```console
    $ pip install sbx-agents
    ```

Run Codex or OpenCode in Docker SBX:

=== "Codex"

    ```python
    from pathlib import Path

    from sbx_agents import Agent, Runner
    from sbx_agents.backends import Codex
    from sbx_agents.sandboxes import DockerSbxSandbox

    agent = Agent(name="fix-tests", backend=Codex(model="gpt-5-codex"))

    result = Runner.run_sync(
        agent,
        sandbox=DockerSbxSandbox(workspace=Path("."), branch="agent/fix-tests"),
        prompt="Fix the failing pytest suite.",
    )
    ```

=== "OpenCode"

    ```python
    from pathlib import Path

    from sbx_agents import Agent, Runner
    from sbx_agents.backends import OpenCode
    from sbx_agents.sandboxes import DockerSbxSandbox

    agent = Agent(name="reviewer", backend=OpenCode(model="anthropic/claude-sonnet-4-5"))

    result = Runner.run_sync(
        agent,
        sandbox=DockerSbxSandbox(workspace=Path("."), branch="agent/review"),
        prompt="Review this repository and produce a risk-ranked report.",
    )
    ```

See [Get started](get-started.md) for the full walkthrough.

Or define a reusable runner in Python and launch it from the terminal:

```console
$ sbxa run main:runner "Fix failing tests."
```

## What you can build

<div class="sbx-grid" markdown="1">
<div class="sbx-card" markdown="1">
**CI fixer agents**

Fix failing tests and open PRs from isolated branches.
</div>

<div class="sbx-card" markdown="1">
**Review fleets**

Compare Codex, OpenCode, and custom agents against same repo.
</div>

<div class="sbx-card" markdown="1">
**Agent products**

Launch one sandboxed agent per issue, incident, or customer request.
</div>

<div class="sbx-card" markdown="1">
**Tenant isolation**

Build FastAPI services with workspace-per-tenant execution.
</div>

<div class="sbx-card" markdown="1">
**Multi-agent workflows**

Reviewer, fixer, and verifier cooperate in one sandbox.
</div>

<div class="sbx-card" markdown="1">
**Multi-sandbox workflows**

Move selected artifacts between isolated environments.
</div>
</div>

## Supported backends

| Type | Backends |
| --- | --- |
| Agents | `Shell`, `Codex`, `OpenCode` |
| Sandboxes | `DockerSandbox`, `DockerSbxSandbox` |

## Learn more

- [Agents](agents.md) — supported agent backends and config.
- [Sandboxes](sandboxes.md) — Docker, Docker SBX, workspace mounting, and cleanup.
- [Running agents](usage.md) — `Runner`, `RunConfig`, JSON events, and results.
- [File management](files.md) — upload, download, list, delete, and copy files.
- [Multi-step workflows](workflows.md) — compose agents and sandboxes.
- [FastAPI services](services.md) — embed the SDK in APIs and isolate tenants.
- [Security](security.md) — trust boundaries, workspace trust, and production checks.
- [Customize](customize.md) — skills, MCP, permissions, and backend-native config.
- [Troubleshooting](troubleshooting.md) — common setup and runtime issues.
