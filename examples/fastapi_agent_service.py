from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sbx_agents import Agent, PermissionPolicy, RunConfig, Runner, RunResult
from sbx_agents.backends import Codex, OpenCode, Shell
from sbx_agents.sandboxes import DockerSandbox, DockerSbxSandbox

app = FastAPI(title="sbx-agents example")

jobs: dict[str, RunResult] = {}


class RunRequest(BaseModel):
    prompt: str
    workspace: Path = Path(".")
    agent_backend: str = "shell"
    sandbox_backend: str = "docker"
    branch: str | None = None
    json_events: bool = False
    readonly: bool = False
    docker_image: str = "python:3.12-slim"
    extra_args: list[str] = Field(default_factory=list)


class RunResponse(BaseModel):
    job_id: str
    output: str
    returncode: int
    diff: str | None
    command: list[str]


class FileWriteRequest(BaseModel):
    workspace: Path = Path(".")
    path: Path
    content: str


class FileReadRequest(BaseModel):
    workspace: Path = Path(".")
    path: Path


class FileReadResponse(BaseModel):
    path: Path
    content: str


class FileListResponse(BaseModel):
    files: list[Path]


@app.post("/runs", response_model=RunResponse)
def run_agent(request: RunRequest) -> RunResponse:
    agent = _build_agent(request)
    sandbox = _build_sandbox(request)
    result = Runner.run_sync(
        agent,
        sandbox=sandbox,
        prompt=request.prompt,
        run_config=RunConfig(
            json_events=request.json_events,
            extra_args=request.extra_args,
        ),
    )

    job_id = str(uuid4())
    jobs[job_id] = result
    return RunResponse(
        job_id=job_id,
        output=result.output,
        returncode=result.returncode,
        diff=result.diff,
        command=result.command,
    )


@app.get("/runs/{job_id}", response_model=RunResult)
def get_run(job_id: str) -> RunResult:
    result = jobs.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.post("/files")
def put_file(request: FileWriteRequest) -> dict[str, str]:
    sandbox = DockerSandbox(workspace=request.workspace)
    path = sandbox.put_file(request.path, request.content)
    return {"path": str(path)}


@app.post("/files/read", response_model=FileReadResponse)
def read_file(request: FileReadRequest) -> FileReadResponse:
    sandbox = DockerSandbox(workspace=request.workspace)
    try:
        content = sandbox.get_file(request.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    return FileReadResponse(path=request.path, content=content)


@app.get("/files", response_model=FileListResponse)
def list_files(workspace: Path = Path("."), pattern: str = "**/*") -> FileListResponse:
    sandbox = DockerSandbox(workspace=workspace)
    return FileListResponse(files=sandbox.list_files(pattern))


@app.delete("/files")
def delete_file(workspace: Path, path: Path) -> dict[str, str]:
    sandbox = DockerSandbox(workspace=workspace)
    try:
        sandbox.delete_file(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    return {"deleted": str(path)}


def _build_agent(request: RunRequest) -> Agent:
    permission = None
    if request.readonly:
        permission = PermissionPolicy(default="ask", tools={"edit": "deny", "bash": "allow"})

    if request.agent_backend == "codex":
        backend = Codex(model="gpt-5-codex")
    elif request.agent_backend == "opencode":
        backend = OpenCode(model="anthropic/claude-sonnet-4-5")
    elif request.agent_backend == "shell":
        backend = Shell()
    else:
        raise HTTPException(status_code=400, detail="Unsupported agent_backend")

    return Agent(
        name=f"api-{request.agent_backend}",
        backend=backend,
        instructions="Run inside sandbox. Keep changes focused and report what happened.",
        permission=permission,
    )


def _build_sandbox(request: RunRequest) -> DockerSandbox | DockerSbxSandbox:
    if request.sandbox_backend == "docker":
        return DockerSandbox(
            workspace=request.workspace,
            image=request.docker_image,
        )
    if request.sandbox_backend == "docker_sbx":
        return DockerSbxSandbox(
            workspace=request.workspace,
            branch=request.branch,
        )
    raise HTTPException(status_code=400, detail="Unsupported sandbox_backend")


# Run:
#   uv add --dev fastapi uvicorn
#   uv run uvicorn examples.fastapi_agent_service:app --reload
#
# Example request:
#   curl -X POST http://127.0.0.1:8000/runs \
#     -H 'content-type: application/json' \
#     -d '{"prompt":"python --version","agent_backend":"shell","sandbox_backend":"docker"}'
#
# Write a file:
#   curl -X POST http://127.0.0.1:8000/files \
#     -H 'content-type: application/json' \
#     -d '{"path":"tmp/spec.md","content":"# Spec"}'
#
# Read a file:
#   curl -X POST http://127.0.0.1:8000/files/read \
#     -H 'content-type: application/json' \
#     -d '{"path":"tmp/spec.md"}'
