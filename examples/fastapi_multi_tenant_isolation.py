from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from sbx_agents import Agent, RunConfig, Runner, RunResult
from sbx_agents.backends import Codex, OpenCode, Shell
from sbx_agents.sandboxes import DockerSandbox, DockerSbxSandbox

app = FastAPI(title="sbx-agents multi-tenant isolation example")

# Production services should use durable storage and authenticated tenant identity.
# This example keeps per-tenant workspaces under one temp root for clarity.
TENANT_ROOT = Path(tempfile.gettempdir()) / "sbx-agents-tenants"

jobs: dict[tuple[str, str], TenantJob] = {}


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str
    root: Path


class TenantJob(BaseModel):
    tenant_id: str
    user_id: str
    run_id: str
    workspace: Path
    result: RunResult


class TenantRunRequest(BaseModel):
    prompt: str
    agent_backend: str = "shell"
    sandbox_backend: str = "docker"
    docker_image: str = "python:3.12-slim"
    json_events: bool = False
    files: dict[str, str] = Field(default_factory=dict)


class TenantRunResponse(BaseModel):
    tenant_id: str
    run_id: str
    output: str
    returncode: int
    diff: str | None


class TenantFileRequest(BaseModel):
    path: Path
    content: str


class TenantFileResponse(BaseModel):
    path: Path
    content: str


@app.post("/runs", response_model=TenantRunResponse)
def run_agent(
    request: TenantRunRequest,
    tenant: Annotated[TenantContext, Depends(require_tenant)],
) -> TenantRunResponse:
    run_id = uuid4().hex
    workspace = tenant.root / run_id
    workspace.mkdir(parents=True, exist_ok=False)

    sandbox = _build_sandbox(request, tenant, run_id, workspace)
    for path, content in request.files.items():
        sandbox.put_file(path, content)

    result = Runner.run_sync(
        _build_agent(request, tenant),
        sandbox=sandbox,
        prompt=request.prompt,
        run_config=RunConfig(json_events=request.json_events),
    )

    jobs[(tenant.tenant_id, run_id)] = TenantJob(
        tenant_id=tenant.tenant_id,
        user_id=tenant.user_id,
        run_id=run_id,
        workspace=workspace,
        result=result,
    )
    return TenantRunResponse(
        tenant_id=tenant.tenant_id,
        run_id=run_id,
        output=result.output,
        returncode=result.returncode,
        diff=result.diff,
    )


@app.get("/runs/{run_id}", response_model=RunResult)
def get_run(
    run_id: str,
    tenant: Annotated[TenantContext, Depends(require_tenant)],
) -> RunResult:
    return _tenant_job(tenant, run_id).result


@app.post("/runs/{run_id}/files", response_model=dict[str, str])
def put_file(
    run_id: str,
    request: TenantFileRequest,
    tenant: Annotated[TenantContext, Depends(require_tenant)],
) -> dict[str, str]:
    job = _tenant_job(tenant, run_id)
    sandbox = DockerSandbox(workspace=job.workspace)
    sandbox.put_file(request.path, request.content)
    return {"path": str(request.path)}


@app.post("/runs/{run_id}/files/read", response_model=TenantFileResponse)
def read_file(
    run_id: str,
    request: TenantFileRequest,
    tenant: Annotated[TenantContext, Depends(require_tenant)],
) -> TenantFileResponse:
    job = _tenant_job(tenant, run_id)
    sandbox = DockerSandbox(workspace=job.workspace)
    try:
        content = sandbox.get_file(request.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    return TenantFileResponse(path=request.path, content=content)


@app.delete("/runs/{run_id}", response_model=dict[str, str])
def delete_run(
    run_id: str,
    tenant: Annotated[TenantContext, Depends(require_tenant)],
) -> dict[str, str]:
    job = _tenant_job(tenant, run_id)
    jobs.pop((tenant.tenant_id, run_id), None)
    shutil.rmtree(job.workspace, ignore_errors=True)
    return {"deleted": run_id}


def require_tenant(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-ID")],
    x_user_id: Annotated[str, Header(alias="X-User-ID")],
) -> TenantContext:
    tenant_id = _safe_id(x_tenant_id, "tenant")
    user_id = _safe_id(x_user_id, "user")
    root = TENANT_ROOT / tenant_id
    root.mkdir(parents=True, exist_ok=True)
    return TenantContext(tenant_id=tenant_id, user_id=user_id, root=root)


def _build_agent(request: TenantRunRequest, tenant: TenantContext) -> Agent:
    if request.agent_backend == "shell":
        backend = Shell()
    elif request.agent_backend == "codex":
        backend = Codex(model="gpt-5-codex")
    elif request.agent_backend == "opencode":
        backend = OpenCode(model="anthropic/claude-sonnet-4-5")
    else:
        raise HTTPException(status_code=400, detail="Unsupported agent_backend")

    return Agent(
        name=f"tenant-{tenant.tenant_id}-{request.agent_backend}",
        backend=backend,
        instructions=(
            "You are running in an isolated tenant workspace. "
            "Never read or write outside the workspace."
        ),
    )


def _build_sandbox(
    request: TenantRunRequest,
    tenant: TenantContext,
    run_id: str,
    workspace: Path,
) -> DockerSandbox | DockerSbxSandbox:
    name = f"sbx-{tenant.tenant_id}-{run_id[:12]}"
    if request.sandbox_backend == "docker":
        return DockerSandbox(
            workspace=workspace,
            image=request.docker_image,
            name=name,
            docker_args=["--network", "none"],
        )
    if request.sandbox_backend == "docker_sbx":
        return DockerSbxSandbox(
            workspace=workspace,
            name=name,
            branch=f"agent/{tenant.tenant_id}/{run_id}",
        )
    raise HTTPException(status_code=400, detail="Unsupported sandbox_backend")


def _tenant_job(tenant: TenantContext, run_id: str) -> TenantJob:
    job = jobs.get((tenant.tenant_id, run_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Run not found for tenant")
    return job


def _safe_id(value: str, label: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
        raise HTTPException(status_code=400, detail=f"Invalid {label} id")
    return value


# Run:
#   uv add --dev fastapi uvicorn
#   uv run uvicorn examples.fastapi_multi_tenant_isolation:app --reload
#
# Tenant A:
#   curl -X POST http://127.0.0.1:8000/runs \
#     -H 'content-type: application/json' \
#     -H 'X-Tenant-ID: tenant-a' \
#     -H 'X-User-ID: alice' \
#     -d '{"prompt":"cat spec.md","files":{"spec.md":"tenant A spec"}}'
#
# Tenant B cannot read Tenant A run, even if it guesses run_id:
#   curl http://127.0.0.1:8000/runs/<tenant-a-run-id> \
#     -H 'X-Tenant-ID: tenant-b' \
#     -H 'X-User-ID: bob'
