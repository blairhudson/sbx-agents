from pydantic import BaseModel, Field


class MCPServer(BaseModel):
    name: str
    type: str
    enabled: bool = True
    required: bool = False
    startup_timeout_sec: int | None = None
    tool_timeout_sec: int | None = None
    enabled_tools: list[str] = Field(default_factory=list)
    disabled_tools: list[str] = Field(default_factory=list)
