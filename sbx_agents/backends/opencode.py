from typing import Any

from pydantic import BaseModel, Field

from sbx_agents.backends._materialise import (
    render_opencode_mcp_servers,
    write_instructions,
    write_json,
    write_skills,
)
from sbx_agents.backends.base import AgentLike
from sbx_agents.context import MaterialiseContext
from sbx_agents.errors import UnsupportedFeatureError
from sbx_agents.permissions import PermissionAction, PermissionPolicy, PermissionRule


class OpenCode(BaseModel):
    id: str = "opencode"
    model: str | None = None
    agent: str | None = None
    permission: PermissionAction | dict[str, PermissionRule] | PermissionPolicy | None = None
    provider: dict[str, Any] = Field(default_factory=dict)
    small_model: str | None = None
    lsp: bool | dict[str, Any] | None = None
    formatter: bool | dict[str, Any] | None = None
    instructions: list[str] = Field(default_factory=list)
    disabled_providers: list[str] = Field(default_factory=list)
    enabled_providers: list[str] = Field(default_factory=list)
    snapshot: bool | None = None
    autoupdate: bool | str | None = None
    share: str | None = None
    compaction: dict[str, Any] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)

    def materialise(self, ctx: MaterialiseContext, agent: AgentLike) -> None:
        write_instructions(ctx.workspace, agent.instructions, agent.skills)
        for skill in agent.skills:
            skill.validate_opencode_name()
        write_skills(agent.skills, ctx.workspace / ".opencode" / "skills", frontmatter=True)

        config = dict(self.extra_config)
        if self.model is not None:
            config["model"] = self.model
        if self.small_model is not None:
            config["small_model"] = self.small_model
        if self.agent is not None:
            config["default_agent"] = self.agent
        permission = _render_permission(self.permission) or _render_permission(agent.permission)
        if permission is not None:
            config["permission"] = permission
        if self.provider:
            config["provider"] = self.provider
        if self.lsp is not None:
            config["lsp"] = self.lsp
        if self.formatter is not None:
            config["formatter"] = self.formatter
        if self.instructions:
            config["instructions"] = self.instructions
        if self.disabled_providers:
            config["disabled_providers"] = self.disabled_providers
        if self.enabled_providers:
            config["enabled_providers"] = self.enabled_providers
        if self.snapshot is not None:
            config["snapshot"] = self.snapshot
        if self.autoupdate is not None:
            config["autoupdate"] = self.autoupdate
        if self.share is not None:
            config["share"] = self.share
        if self.compaction:
            config["compaction"] = self.compaction
        if agent.mcp_servers:
            config["mcp"] = render_opencode_mcp_servers(agent.mcp_servers)
        if config:
            write_json(ctx.workspace / "opencode.jsonc", config)

    def command(self, prompt: str, run_config: Any | None = None) -> list[str]:
        command = ["opencode", "run"]
        if run_config is not None and getattr(run_config, "output_schema", None) is not None:
            raise UnsupportedFeatureError("OpenCode backend does not support output_schema")
        if run_config is not None and getattr(run_config, "json_events", False):
            command.extend(["--format", "json"])
        if run_config is not None and getattr(run_config, "continue_last", False):
            command.append("--continue")
        if run_config is not None and getattr(run_config, "resume_session_id", None):
            command.extend(["--session", str(run_config.resume_session_id)])
        if run_config is not None and getattr(run_config, "fork_session", False):
            command.append("--fork")
        if run_config is not None:
            for attachment in run_config.attachments:
                command.extend(["--file", str(attachment)])
            command.extend(run_config.extra_args)
        command.append(prompt)
        return command


def _render_permission(
    permission: PermissionAction | dict[str, PermissionRule] | PermissionPolicy | None,
) -> PermissionAction | dict[str, PermissionRule] | None:
    if isinstance(permission, PermissionPolicy):
        return permission.to_opencode()
    return permission
