---
title: Sandbox File Management for Coding Agents
description: Put, get, list, delete, and copy files across coding-agent sandboxes with workspace-scoped file helpers.
---

# File management

Use sandbox file helpers to put specific inputs into a workspace and retrieve selected outputs after a run.

## Put files before a run

```python
sandbox.put_file(
    "tmp/spec.md",
    "# Task Spec\nCreate a JSON report at tmp/report.json.",
)
```

Then run the agent:

```python
result = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Read tmp/spec.md and produce tmp/report.json.",
)
```

## Get files after a run

```python
report = sandbox.get_file("tmp/report.json")
print(report)
```

Binary files use `put_bytes` and `get_bytes`:

```python
sandbox.put_bytes("tmp/input.bin", b"abc")
payload = sandbox.get_bytes("tmp/output.bin")
```

## List files

```python
files = sandbox.list_files("tmp/*.json")
```

The returned paths are relative to the sandbox workspace.

## Delete files

```python
sandbox.delete_file("tmp/spec.md")
```

## Copy files between sandboxes

Copying is explicit. Your app reads from one sandbox workspace and writes to another.

```python
Runner.run_sync(producer_agent, sandbox=producer, prompt="Create artifacts/report.txt")

report = producer.get_file("artifacts/report.txt")
consumer.put_file("incoming/report.txt", report)

Runner.run_sync(consumer_agent, sandbox=consumer, prompt="Verify incoming/report.txt")
```

This keeps transfer policy in your app instead of implicitly sharing filesystems between sandboxes.

## Path safety

File helpers are scoped to the workspace.

```python
sandbox.put_file("../secrets.txt", "bad")
```

This raises `ValueError` because the path escapes the workspace.

!!! note
    Current file helpers operate on the mounted workspace path. They are not a hidden VM file store.

## Next steps

- [Multi-step workflows](workflows.md) — use files as handoff points.
- [FastAPI services](services.md) — expose file endpoints safely.
- [Security](security.md) — understand workspace trust.
