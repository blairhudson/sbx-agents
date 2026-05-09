# Sandboxes

A sandbox backend defines where the agent command runs and how results are collected.

Use whatever isolation boundary your product needs: local Docker for tests, Docker Sandboxes for stronger local isolation, Kubernetes or cloud sandboxes later.

## Supported sandboxes

| Backend | Isolation | Best for |
| --- | --- | --- |
| `DockerSandbox` | Docker container | CI, local fallback, basic tests |
| `DockerSbxSandbox` | Docker Sandboxes through `sbx` | local microVM-style agent isolation |

The agent code does not change when you move between these runtimes.

## Plain Docker

Plain Docker mounts the workspace into a container and runs the agent command inside it.

```python
from pathlib import Path

from sbx_agents.sandboxes import DockerSandbox

sandbox = DockerSandbox(
    workspace=Path("."),
    image="python:3.12-slim",
    name="agent-ci-run",
    env={"PYTHONUNBUFFERED": "1"},
    docker_args=["--cpus", "2", "--memory", "4g"],
)
```

The workspace is mounted at `/workspace` by default. Changes in the container appear in the host workspace.

## Docker SBX

Docker SBX uses the `sbx` CLI to run an agent in Docker Sandboxes.

Install and sign in before first run:

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

Apps can fail early with a helpful install message:

```python
from sbx_agents.sandboxes import DockerSbxSandbox

DockerSbxSandbox.check_available()
```

```python
from pathlib import Path

from sbx_agents.sandboxes import DockerSbxSandbox

sandbox = DockerSbxSandbox(
    workspace=Path("."),
    name="fix-tests",
    branch="agent/fix-tests",
    cpus=4,
    memory="8g",
    network_allow=["host.docker.internal:8080", "localhost:8080"],
)
```

The SDK maps `agent.backend.id` to the Docker SBX agent name:

| Agent backend | Docker SBX agent |
| --- | --- |
| `Codex` | `codex` |
| `OpenCode` | `opencode` |
| `Shell` | `shell` |

## Branch isolation

Use `branch` with Docker SBX to let an agent work in its own branch/worktree.

```python
DockerSbxSandbox(workspace=Path("."), branch="agent/fix-tests")
```

Branch isolation is useful when running multiple agents against the same repository.

## Network policy

Docker SBX blocks network access unless policy allows it. Declare allowed hosts in SDK config:

```python
DockerSbxSandbox(
    workspace=Path("."),
    network_allow=["host.docker.internal:8080", "localhost:8080", "api.example.com"],
)
```

The sandbox backend applies:

```console
$ sbx policy allow network host.docker.internal:8080,localhost:8080,api.example.com
```

Use `host.docker.internal` when a model server runs on your host at `localhost`. Include `localhost:<port>` too because Docker SBX policy logs may report the proxied request under that host.

## Secrets

Codex auth is declared on the Codex backend. Docker SBX implements that auth for its sandbox runtime.

For Codex with Docker SBX OpenAI OAuth:

```python
agent = Agent(
    name="fix-tests",
    backend=Codex(model_provider="openai", auth="openai_oauth"),
)

sandbox = DockerSbxSandbox(
    workspace=Path("."),
)
```

Docker SBX automatically allows `api.openai.com:443` for OpenAI Codex runs and `chatgpt.com:443` when `auth="openai_oauth"`.

If no global OpenAI secret exists, the backend runs:

```console
$ sbx secret set -g openai --oauth
```

If an existing OAuth secret is stale, force refresh from config:

```python
Codex(model_provider="openai", auth={"method": "openai_oauth", "refresh": True})
```

For non-OAuth token sources, map auth to an environment variable:

```python
Codex(auth="openai_api_key")
```

That stores `$OPENAI_API_KEY` with:

```console
$ sbx secret set -g openai
```

## Host Codex Auth

Prefer Docker SBX OAuth for Codex. If you need to reuse host `codex login` ChatGPT auth, enable explicit auth sync:

```python
agent = Agent(
    name="fix-tests",
    backend=Codex(auth="host_chatgpt"),
)

sandbox = DockerSbxSandbox(
    workspace=Path("."),
)
```

The backend copies `~/.codex/auth.json` into the sandbox before Codex starts. Run `codex login` on host first.

## Workspace mounting

Both current sandbox backends operate on a workspace path. File helpers and diff collection are scoped to that workspace.

!!! warning "Workspace trust"
    Agent changes can modify files you later execute, including scripts, test config, and CI files. Review diffs before running modified code on your host.

## Cleanup

Plain Docker uses `--rm` by default.

Docker SBX lifecycle is controlled by the `sbx` CLI. Inspect and remove old sandboxes with:

```console
$ sbx ls
$ sbx rm <sandbox-name>
```

Use `force_recreate=True` when a service should always start from a fresh named sandbox:

```python
DockerSbxSandbox(
    workspace=Path("."),
    name="fresh-run",
    force_recreate=True,
)
```

Without `force_recreate`, the backend reuses a matching named sandbox and removes conflicting default workspace sandboxes only when they would block the named run.

## Custom sandbox backends

Implement the `SandboxBackend` protocol:

```python
class MySandbox:
    id = "my-sandbox"
    name = None

    def prepare(self, agent, run_config):
        ...

    def run(self, session, command):
        ...

    def collect(self, session):
        ...

    def cleanup(self, session):
        ...
```

## Next steps

- [Running agents](usage.md) — understand the runner lifecycle.
- [File management](files.md) — move specific files in and out.
- [Security](security.md) — understand trust boundaries.
