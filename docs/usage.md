# Running agents

The runner coordinates an agent backend and a sandbox backend for one agent turn.

## Basic run

```python
result = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Fix failing tests.",
)
```

Or define a reusable runner and execute it later:

```python
runner = Runner(
    agent,
    sandbox=sandbox,
    default_prompt="Fix failing tests.",
)

result = runner.run_sync()
result = runner.run_sync("Only fix lint failures.")
```

One call to `run_sync()` is one turn. Your app decides whether to run another turn, change agents, or change sandboxes.

## Lifecycle

```text
sandbox.prepare()
backend.materialise()
sandbox.run(backend.command())
sandbox.collect()
sandbox.cleanup()
```

The backend never knows whether it runs in Docker or Docker SBX. The sandbox never knows how to render Codex or OpenCode config.

## RunConfig

`RunConfig` controls per-run behavior.

```python
from pathlib import Path

from sbx_agents import RunConfig

run_config = RunConfig(
    json_events=True,
    output_schema={"type": "object"},
    attachments=[Path("screenshot.png")],
    resume_session_id=None,
    continue_last=False,
    extra_args=["--skip-git-repo-check"],
)
```

Common fields:

| Field | Purpose |
| --- | --- |
| `json_events` | ask supported backends to emit machine-readable output |
| `output_schema` | pass structured-output schema to supported backends |
| `attachments` | attach files or images when backend supports it |
| `resume_session_id` | resume a prior backend-native session |
| `continue_last` | ask backend to continue latest session |
| `stream_output` | forward sandbox stdout/stderr live while still collecting result |
| `extra_args` | pass backend-native CLI flags |

## RunResult

Every run returns `RunResult`.

```python
print(result.output)
print(result.stdout)
print(result.stderr)
print(result.returncode)
print(result.command)
print(result.diff)
print(result.events)
```

Important fields:

| Field | Meaning |
| --- | --- |
| `output` | best useful final output |
| `stdout`, `stderr` | raw process output |
| `returncode` | process exit code |
| `command` | command passed to sandbox backend |
| `diff` | collected `git diff` |
| `events` | parsed JSON events when enabled |
| `session_id`, `thread_id` | backend-native continuation IDs when emitted |
| `usage` | token or usage metadata when emitted |

## JSON events

JSON event parsing is opt-in.

```python
result = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Review this repo.",
    run_config=RunConfig(json_events=True),
)
```

Backend command changes:

- Codex: `codex exec --json ...`
- OpenCode: `opencode run --format json ...`

Unknown events are preserved in `result.events`.

## Sessions and resume

Backends may emit `session_id` or `thread_id`. Store it and pass it into the next run.

```python
first = Runner.run_sync(agent, sandbox=sandbox, prompt="Diagnose.", run_config=RunConfig(json_events=True))

session_id = first.thread_id or first.session_id

second = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Implement the fix.",
    run_config=RunConfig(json_events=True, resume_session_id=session_id),
)
```

If no session ID is emitted, carry context in the next prompt.

## Next steps

- [File management](files.md) — provide specs and collect artifacts.
- [Multi-step workflows](workflows.md) — compose multiple turns and agents.
- [Troubleshooting](troubleshooting.md) — fix common runtime issues.
