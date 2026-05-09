from typing import Any, Protocol

from sbx_agents.context import MaterialiseContext


class AgentLike(Protocol):
    name: str
    instructions: str | None
    skills: list[Any]
    mcp_servers: list[Any]
    permission: Any
    strict: bool


class AgentBackend(Protocol):
    id: str

    def materialise(self, ctx: MaterialiseContext, agent: AgentLike) -> None:
        """Write backend-specific config into the workspace."""

    def command(self, prompt: str, run_config: Any | None = None) -> list[str]:
        """Return command to execute inside sandbox."""
