from pydantic import BaseModel, Field

from sbx_agents.backends.base import AgentLike
from sbx_agents.context import MaterialiseContext
from sbx_agents.errors import UnsupportedFeatureError


class Shell(BaseModel):
    id: str = "shell"
    command_prefix: list[str] = Field(default_factory=lambda: ["sh", "-lc"])

    def materialise(self, ctx: MaterialiseContext, agent: AgentLike) -> None:
        if agent.strict and (agent.skills or agent.mcp_servers):
            raise UnsupportedFeatureError("Shell backend does not support skills or MCP")
        return None

    def command(self, prompt: str, run_config: object | None = None) -> list[str]:
        return [*self.command_prefix, prompt]
