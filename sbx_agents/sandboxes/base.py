from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from sbx_agents.result import CommandResult, RunArtifacts


class SandboxSession(BaseModel):
    workspace: Path
    sandbox_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentLike(Protocol):
    name: str
    backend: Any


class RunConfigLike(Protocol):
    pass


class SandboxBackend(Protocol):
    id: str

    name: str | None

    def prepare(self, agent: AgentLike, run_config: RunConfigLike | None) -> SandboxSession:
        """Create workspace, worktree, sandbox, pod, etc."""

    def run(self, session: SandboxSession, command: list[str]) -> CommandResult:
        """Execute command inside sandbox."""

    def collect(self, session: SandboxSession) -> RunArtifacts:
        """Collect diff, logs, output files."""

    def cleanup(self, session: SandboxSession) -> None:
        """Stop/remove sandbox if configured."""
