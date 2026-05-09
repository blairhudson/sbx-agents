from pydantic import BaseModel, ConfigDict, Field, SkipValidation

from sbx_agents.backends.base import AgentBackend
from sbx_agents.mcp.base import MCPServer
from sbx_agents.permissions import PermissionPolicy
from sbx_agents.skills import Skill


class Agent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    backend: SkipValidation[AgentBackend]
    instructions: str | None = None
    skills: list[Skill] = Field(default_factory=list)
    mcp_servers: list[MCPServer] = Field(default_factory=list)
    capabilities: list[object] = Field(default_factory=list)
    permission: PermissionPolicy | None = None
    env: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)
    strict: bool = True
