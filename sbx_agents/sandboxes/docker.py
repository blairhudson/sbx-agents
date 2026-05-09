from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from sbx_agents.result import CommandResult, RunArtifacts
from sbx_agents.sandboxes._subprocess import collect_git_diff, run_command
from sbx_agents.sandboxes.base import AgentLike, RunConfigLike, SandboxSession
from sbx_agents.sandboxes.files import WorkspaceFileMixin


class DockerSandbox(WorkspaceFileMixin, BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "docker"
    workspace: Path
    image: str = "python:3.12-slim"
    name: str | None = None
    workdir: str = "/workspace"
    docker_args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    remove_on_exit: bool = True

    def prepare(self, agent: AgentLike, run_config: RunConfigLike | None) -> SandboxSession:
        return SandboxSession(
            workspace=self.workspace.resolve(),
            sandbox_name=self.name,
            metadata={
                "agent_id": agent.backend.id,
                "stream_output": bool(getattr(run_config, "stream_output", False)),
                "stream_filter": _stream_filter(run_config),
                "timeout_seconds": getattr(run_config, "timeout_seconds", None),
            },
        )

    def run(self, session: SandboxSession, command: list[str]) -> CommandResult:
        docker_command = self._docker_command(session, command)
        return run_command(
            docker_command,
            cwd=session.workspace,
            stream=bool(session.metadata.get("stream_output", False)),
            stream_filter=session.metadata.get("stream_filter"),
            timeout=session.metadata.get("timeout_seconds"),
        )

    def collect(self, session: SandboxSession) -> RunArtifacts:
        return RunArtifacts(diff=collect_git_diff(session.workspace))

    def cleanup(self, session: SandboxSession) -> None:
        return None

    def _docker_command(self, session: SandboxSession, command: list[str]) -> list[str]:
        docker_command = ["docker", "run"]
        if self.remove_on_exit:
            docker_command.append("--rm")
        if self.name:
            docker_command.extend(["--name", self.name])
        for key, value in self.env.items():
            docker_command.extend(["-e", f"{key}={value}"])
        docker_command.extend(
            [
                "-v",
                f"{session.workspace}:{self.workdir}",
                "-w",
                self.workdir,
                *self.docker_args,
                self.image,
                *command,
            ]
        )
        return docker_command


def _stream_filter(run_config: RunConfigLike | None) -> object | None:
    metadata = getattr(run_config, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    return metadata.get("stream_filter")
