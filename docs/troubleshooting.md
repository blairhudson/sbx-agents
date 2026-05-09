# Troubleshooting

This page lists common setup and runtime issues.

## Docker command not found

Plain Docker runs require Docker installed and running.

Check:

```console
$ docker version
```

If Docker is unavailable, use a different sandbox backend or install Docker for your platform.

## Docker image lacks the agent CLI

`DockerSandbox` runs whatever command the backend builds inside your chosen image. If you use `Codex` or `OpenCode`, the image must contain that CLI.

Fix options:

- use `Shell` for simple commands
- choose an image with the agent CLI installed
- build a custom image
- use `DockerSbxSandbox` if the agent is supported by Docker SBX

## `sbx` command not found

`DockerSbxSandbox` requires the Docker SBX CLI.

Check:

```console
$ sbx --help
```

Install and sign in with Docker SBX before using `DockerSbxSandbox`.

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

You can also check from your app:

```python
from sbx_agents.sandboxes import DockerSbxSandbox

DockerSbxSandbox.check_available()
```

Use `check_ready()` when you also need Docker SBX auth to be ready:

```python
DockerSbxSandbox.check_ready()
```

## Docker SBX opens browser login

`sbxa` preflights Docker SBX with `sbx diagnose -o json` before launching an agent. If Docker SBX still opens browser login during a manual `sbx run`, sign in before launching agent:

```console
$ sbx login
$ sbx ls
$ sbxa doctor --require docker-sbx
```

Then retry:

```console
$ sbxa run examples/cli_runner.py
```

## Docker SBX says network already exists

A stale Docker SBX sandbox can leave runtime state behind. Remove the named sandbox or reset Docker SBX state.

Try targeted cleanup first:

```console
$ sbx ls
$ sbx rm <sandbox-name>
```

If the runtime is still stuck, reset Docker SBX state:

```console
$ sbx reset
$ sbx daemon start
```

For examples, avoid fixed sandbox names unless you need to reattach to the same sandbox.

## Docker SBX worktree fails with invalid reference HEAD

Docker SBX branch/worktree mode needs a Git repository with `HEAD` pointing at a commit. If the repo has no commits yet, either make an initial commit or omit `branch`.

## Local model server is unreachable from Docker SBX

If your model server runs on host `localhost:8080`, use `host.docker.internal` from inside Docker SBX:

```python
"base_url": "http://host.docker.internal:8080/v1"
```

Allow the sandbox network policy in SDK config:

```python
DockerSbxSandbox(
    workspace=Path("."),
    network_allow=["host.docker.internal:8080", "localhost:8080"],
)
```

Equivalent manual command:

```console
$ sbx policy allow network host.docker.internal:8080,localhost:8080
```

Verify from sandbox:

```console
$ sbx exec <sandbox-name> curl http://host.docker.internal:8080/v1/models
```

## No diff returned

`RunResult.diff` comes from `git diff` in the workspace.

Common causes:

- workspace is not a Git repository
- agent did not change tracked files
- changes were written outside the workspace
- files are untracked and not represented in normal `git diff`

Check manually:

```console
$ git status --short
$ git diff
```

## JSON events are empty

JSON parsing is opt-in and backend-dependent.

Use:

```python
RunConfig(json_events=True)
```

Backend flags:

- Codex: `--json`
- OpenCode: `--format json`

If the backend emits plain text or malformed JSON lines, `result.events` may be empty.

## No `session_id` or `thread_id`

Not every backend emits continuation IDs. Fall back to app-managed context:

```python
next_prompt = f"Previous result:\n\n{result.output}\n\nContinue."
```

## File path escapes workspace

File helpers reject paths outside the workspace.

```python
sandbox.put_file("../secret.txt", "bad")
```

Use a relative path inside the workspace instead:

```python
sandbox.put_file("tmp/spec.md", "ok")
```

## Next steps

- [Get started](get-started.md) — verify basic setup.
- [Security](security.md) — review trust boundaries.
- [Examples](examples.md) — compare against known-good examples.
