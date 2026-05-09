# Security model

`sbx-agents` gives you orchestration primitives; your sandbox backend determines the isolation boundary.

## Trust boundaries

Current backends have different trust properties.

| Backend | Boundary | Notes |
| --- | --- | --- |
| `DockerSandbox` | Docker container | Good for CI and trusted workloads. Shares host Docker daemon. |
| `DockerSbxSandbox` | Docker Sandboxes via `sbx` | Stronger local isolation, branch mode, and Docker SBX policy mechanisms. |

Choose Docker SBX when autonomous agents need stronger host isolation.

## What crosses into the sandbox

Depending on backend and config:

- workspace files
- agent instructions
- generated agent config
- skills
- MCP server config
- environment variables you explicitly pass
- files you put with `put_file` or `put_bytes`

No host secrets should be passed implicitly by application code.

## What crosses back to the host

The SDK collects:

- stdout and stderr
- process return code
- `git diff`
- parsed JSON events when enabled
- files you explicitly read with file helpers

Workspace changes are visible on the host for mounted-workspace backends.

## Workspace trust

Agents can change files that later execute on your host or CI runner.

Review changes to:

- shell scripts
- test configuration
- package manager scripts
- CI workflows
- Git hooks
- generated code
- dependency lockfiles

!!! warning
    `git diff` may not show everything security-sensitive. Git hooks and ignored files need separate review if your workflow uses them.

## Credentials

Pass credentials deliberately.

For Docker SBX, prefer Docker SBX secret and policy mechanisms where possible. For services, scope secrets by tenant and run class.

Do not mount host credential directories into generic Docker containers unless you fully trust the agent and image.

## Network policy

Plain Docker can use Docker-native network flags:

```python
DockerSandbox(
    workspace=Path("."),
    docker_args=["--network", "none"],
)
```

Docker SBX should use Docker SBX policy controls for outbound access.

## Multi-tenant risks

Service code must prevent tenant cross-talk.

Minimum controls:

- derive tenant ID from trusted auth
- use workspace per tenant/run
- key metadata by `(tenant_id, run_id)`
- scope file APIs to one run workspace
- reject workspace path escapes
- avoid shared sandbox names
- enforce quotas
- clean up old workspaces

See `examples/fastapi_multi_tenant_isolation.py`.

## Production checklist

- Use the strongest sandbox backend available for autonomous coding agents.
- Do not forward host Docker socket to untrusted agents.
- Do not forward host secrets implicitly.
- Use branch/worktree isolation for repository writes.
- Restrict network by default.
- Log commands, return codes, durations, tenant IDs, and sandbox names.
- Require human review before merging agent changes.

## Next steps

- [Sandboxes](sandboxes.md) — compare backend isolation.
- [FastAPI services](services.md) — tenant-scoped service pattern.
- [Troubleshooting](troubleshooting.md) — fix common security-related setup issues.
