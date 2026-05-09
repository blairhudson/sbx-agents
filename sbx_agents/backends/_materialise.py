from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from sbx_agents.mcp import HttpMCP, MCPServer, StdioMCP
from sbx_agents.skills import Skill


def write_instructions(workspace: Path, instructions: str | None, skills: list[Skill]) -> None:
    if not instructions and not skills:
        return
    lines: list[str] = []
    if instructions:
        lines.extend([instructions.strip(), ""])
    if skills:
        lines.append("## Skills")
        for skill in skills:
            description = f": {skill.description}" if skill.description else ""
            lines.append(f"- {skill.name}{description}")
        lines.append("")
    (workspace / "AGENTS.md").write_text("\n".join(lines), encoding="utf-8")


def write_skills(skills: list[Skill], destination: Path, *, frontmatter: bool = False) -> None:
    for skill in skills:
        skill_dir = destination / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)
        if skill.path is not None:
            _copy_skill_assets(skill.path, skill_dir)
        (skill_dir / "SKILL.md").write_text(
            skill.to_skill_md(frontmatter=frontmatter),
            encoding="utf-8",
        )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_codex_mcp_servers(servers: list[MCPServer]) -> dict[str, Any]:
    rendered: dict[str, Any] = {}
    for server in servers:
        if isinstance(server, StdioMCP):
            data: dict[str, Any] = {
                "command": server.command,
                "args": server.args,
            }
            if server.env:
                data["env"] = server.env
            if server.cwd is not None:
                data["cwd"] = str(server.cwd)
            if server.env_vars:
                data["env_vars"] = server.env_vars
            rendered[server.name] = _with_common_mcp_options(data, server)
        elif isinstance(server, HttpMCP):
            data = {"url": server.url}
            if server.bearer_token_env_var is not None:
                data["bearer_token_env_var"] = server.bearer_token_env_var
            if server.headers:
                data["http_headers"] = server.headers
            if server.env_http_headers:
                data["env_http_headers"] = server.env_http_headers
            if server.scopes:
                data["scopes"] = server.scopes
            rendered[server.name] = _with_common_mcp_options(data, server)
        else:
            rendered[server.name] = server.model_dump(exclude_none=True)
    return rendered


def render_opencode_mcp_servers(servers: list[MCPServer]) -> dict[str, Any]:
    rendered: dict[str, Any] = {}
    for server in servers:
        if isinstance(server, StdioMCP):
            data: dict[str, Any] = {
                "type": "local",
                "command": [server.command, *server.args],
            }
            if server.env:
                data["environment"] = server.env
            rendered[server.name] = _with_opencode_mcp_options(data, server)
        elif isinstance(server, HttpMCP):
            data = {"type": "remote", "url": server.url}
            if server.headers:
                data["headers"] = server.headers
            if server.oauth is not None:
                data["oauth"] = server.oauth
            rendered[server.name] = _with_opencode_mcp_options(data, server)
        else:
            rendered[server.name] = server.model_dump(exclude_none=True)
    return rendered


def render_toml(data: dict[str, Any]) -> str:
    return _render_toml_section(data, [])


def _with_common_mcp_options(data: dict[str, Any], server: MCPServer) -> dict[str, Any]:
    if not server.enabled:
        data["enabled"] = False
    if server.required:
        data["required"] = True
    if server.startup_timeout_sec is not None:
        data["startup_timeout_sec"] = server.startup_timeout_sec
    if server.tool_timeout_sec is not None:
        data["tool_timeout_sec"] = server.tool_timeout_sec
    if server.enabled_tools:
        data["enabled_tools"] = server.enabled_tools
    if server.disabled_tools:
        data["disabled_tools"] = server.disabled_tools
    return data


def _with_opencode_mcp_options(data: dict[str, Any], server: MCPServer) -> dict[str, Any]:
    if not server.enabled:
        data["enabled"] = False
    if server.startup_timeout_sec is not None:
        data["timeout"] = server.startup_timeout_sec * 1000
    return data


def _render_toml_section(data: dict[str, Any], path: list[str]) -> str:
    lines: list[str] = []
    nested: list[tuple[str, dict[str, Any]]] = []
    if path:
        lines.append(f"[{'.'.join(path)}]")
    for key, value in data.items():
        if isinstance(value, dict) and _should_render_nested(path, key, value):
            nested.append((key, value))
        elif value is not None:
            lines.append(f"{key} = {_toml_value(value)}")
    for key, value in nested:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(_render_toml_section(value, [*path, key]).rstrip())
    return "\n".join(lines) + ("\n" if lines else "")


def _should_render_nested(path: list[str], key: str, value: dict[str, Any]) -> bool:
    if not path and key == "mcp_servers":
        return True
    if path == ["mcp_servers"]:
        return True
    return any(isinstance(item, dict) for item in value.values())


def _copy_skill_assets(source: Path, destination: Path) -> None:
    for item in source.iterdir():
        if item.name == "SKILL.md":
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        items = ", ".join(f"{key} = {_toml_value(item)}" for key, item in value.items())
        return "{ " + items + " }"
    return json.dumps(value)
