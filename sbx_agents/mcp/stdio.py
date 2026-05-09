from pathlib import Path
from typing import Any

from pydantic import Field

from sbx_agents.mcp.base import MCPServer


class StdioMCP(MCPServer):
    type: str = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None
    env_vars: list[str | dict[str, Any]] = Field(default_factory=list)
