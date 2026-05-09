# Multi-step workflows

Compose agent turns in your app code. One `Runner.run_sync()` call is one turn.

## One agent, many turns

Use backend-native sessions when available, or carry context in prompts.

```python
diagnosis = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Inspect failures. Do not edit files yet.",
    run_config=RunConfig(json_events=True),
)

session_id = diagnosis.thread_id or diagnosis.session_id

fix = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Implement the smallest safe fix.",
    run_config=RunConfig(json_events=True, resume_session_id=session_id),
)

verify = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Run relevant tests and report the result.",
    run_config=RunConfig(json_events=True, resume_session_id=session_id),
)
```

If `session_id` is missing, include prior output in the next prompt:

```python
fix = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt=f"Use this diagnosis:\n\n{diagnosis.output}\n\nNow fix the issue.",
)
```

## Many agents, one sandbox

Use one sandbox when agents should hand off through the same workspace and diff.

```python
review = Runner.run_sync(reviewer, sandbox=sandbox, prompt="Review risk. Do not edit.")

fix = Runner.run_sync(
    fixer,
    sandbox=sandbox,
    prompt=f"Use this review and fix the smallest safe issue:\n\n{review.output}",
)

verify = Runner.run_sync(verifier, sandbox=sandbox, prompt="pytest -q")
```

Good for reviewer → fixer → verifier flows.

## One agent, many sandboxes

Use multiple sandboxes when environments or tenants must remain isolated.

```python
Runner.run_sync(agent, sandbox=producer, prompt="Create artifacts/report.txt")

report = producer.get_file("artifacts/report.txt")
consumer.put_file("incoming/report.txt", report)

Runner.run_sync(agent, sandbox=consumer, prompt="Verify incoming/report.txt")
```

Good for producer/consumer validation, tenant isolation tests, and comparing environments.

## Branch-per-agent workflow

With Docker SBX, give each agent its own branch.

```python
review_sandbox = DockerSbxSandbox(workspace=Path("."), branch="agent/review")
fix_sandbox = DockerSbxSandbox(workspace=Path("."), branch="agent/fix")
```

Use branch isolation when multiple agents may write to the same repository.

## Next steps

- [File management](files.md) — copy explicit artifacts between runs.
- [Services](services.md) — expose workflows through FastAPI.
- [Examples](examples.md) — see runnable multi-step examples.
