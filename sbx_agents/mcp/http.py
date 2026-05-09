from typing import Any

from pydantic import Field

from sbx_agents.mcp.base import MCPServer


class HttpMCP(MCPServer):
    type: str = "http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    bearer_token_env_var: str | None = None
    env_http_headers: dict[str, str] = Field(default_factory=dict)
    oauth: dict[str, Any] | bool | None = None
    scopes: list[str] = Field(default_factory=list)
