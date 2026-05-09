# FastAPI services

Embed `sbx-agents` in services when you need users or systems to launch isolated agent runs through an API.

## Minimal API

The service shape is small:

```python
@app.post("/runs")
def run_agent(request: RunRequest) -> RunResponse:
    agent = build_agent(request)
    sandbox = build_sandbox(request)

    result = Runner.run_sync(
        agent,
        sandbox=sandbox,
        prompt=request.prompt,
    )

    return RunResponse(output=result.output, returncode=result.returncode)
```

See `examples/fastapi_agent_service.py` for a complete example.

## File endpoints

Expose file APIs when clients need to upload specs or collect artifacts.

```text
POST /files       -> sandbox.put_file()
POST /files/read  -> sandbox.get_file()
GET  /files       -> sandbox.list_files()
DELETE /files     -> sandbox.delete_file()
```

Always scope file operations to a workspace controlled by the service.

## Multi-tenant isolation

Use tenant identity to choose workspaces and job keys.

```text
tenant id from auth
run id generated per request
workspace = TENANT_ROOT / tenant_id / run_id
job lookup key = (tenant_id, run_id)
sandbox name includes tenant + run id
file APIs scoped to run workspace
```

This prevents one tenant from reading another tenant's run even if it guesses a `run_id`.

## Cleanup

Every service needs a cleanup path.

```python
jobs.pop((tenant_id, run_id), None)
shutil.rmtree(workspace, ignore_errors=True)
```

Production systems should also add TTL cleanup for abandoned runs.

## Production checklist

- Authenticate users and derive tenant IDs from trusted auth, not raw headers.
- Use one workspace per tenant/run.
- Key all metadata by `(tenant_id, run_id)`.
- Enforce request, run, CPU, memory, and disk quotas.
- Keep secrets per tenant.
- Use restrictive network policy by default.
- Log sandbox name, run ID, tenant ID, command, return code, and duration.
- Delete old workspaces and sandbox state.

## Next steps

- [Security](security.md) — trust boundaries and tenant risks.
- [File management](files.md) — safe upload/download helpers.
- [Troubleshooting](troubleshooting.md) — common service failures.
