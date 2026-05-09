from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from sbx_agents.backends._materialise import (
    render_codex_mcp_servers,
    render_toml,
    write_instructions,
    write_skills,
)
from sbx_agents.backends.base import AgentLike
from sbx_agents.context import MaterialiseContext


class CodexAuth(BaseModel):
    method: Literal["openai_oauth", "openai_api_key_env", "host_chatgpt", "none"]
    service: str = "openai"
    env_var: str | None = None
    refresh: bool = False

    @classmethod
    def openai_oauth(cls, *, refresh: bool = False) -> "CodexAuth":
        return cls(method="openai_oauth", refresh=refresh)

    @classmethod
    def openai_api_key_env(
        cls,
        env_var: str = "OPENAI_API_KEY",
        *,
        service: str = "openai",
    ) -> "CodexAuth":
        return cls(method="openai_api_key_env", env_var=env_var, service=service)

    @classmethod
    def host_chatgpt(cls) -> "CodexAuth":
        return cls(method="host_chatgpt")

    @classmethod
    def none(cls) -> "CodexAuth":
        return cls(method="none")


CodexAuthConfig = (
    CodexAuth
    | Literal["openai_oauth", "openai_api_key", "openai_api_key_env", "host_chatgpt", "none"]
    | dict[str, Any]
    | None
)


class Codex(BaseModel):
    id: str = "codex"
    model: str | None = None
    model_provider: str | None = None
    model_reasoning_effort: str | None = None
    model_reasoning_summary: str | None = None
    model_verbosity: str | None = None
    approval_policy: str | None = None
    sandbox_mode: str | None = None
    web_search: str | None = None
    auth: CodexAuthConfig = None
    features: dict[str, bool] = Field(default_factory=dict)
    shell_environment_policy: dict[str, Any] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("auth", mode="before")
    @classmethod
    def _normalise_auth(cls, value: Any) -> Any:
        if value == "openai_oauth":
            return CodexAuth.openai_oauth()
        if value == "openai_api_key" or value == "openai_api_key_env":
            return CodexAuth.openai_api_key_env()
        if value == "host_chatgpt":
            return CodexAuth.host_chatgpt()
        if value == "none":
            return CodexAuth.none()
        return value

    def materialise(self, ctx: MaterialiseContext, agent: AgentLike) -> None:
        config_dir = ctx.workspace / ".codex"
        config_dir.mkdir(parents=True, exist_ok=True)

        write_instructions(ctx.workspace, agent.instructions, agent.skills)
        write_skills(agent.skills, config_dir / "skills")

        config = dict(self.extra_config)
        if self.model is not None:
            config["model"] = self.model
        if self.model_provider is not None:
            config["model_provider"] = self.model_provider
        if self.model_reasoning_effort is not None:
            config["model_reasoning_effort"] = self.model_reasoning_effort
        if self.model_reasoning_summary is not None:
            config["model_reasoning_summary"] = self.model_reasoning_summary
        if self.model_verbosity is not None:
            config["model_verbosity"] = self.model_verbosity
        if self.approval_policy is not None:
            config["approval_policy"] = self.approval_policy
        elif agent.permission is not None:
            config["approval_policy"] = _codex_approval_policy(agent.permission.default)
        if self.sandbox_mode is not None:
            config["sandbox_mode"] = self.sandbox_mode
        if self.web_search is not None:
            config["web_search"] = self.web_search
        if self.features:
            config["features"] = self.features
        if self.shell_environment_policy:
            config["shell_environment_policy"] = self.shell_environment_policy
        if agent.mcp_servers:
            config["mcp_servers"] = render_codex_mcp_servers(agent.mcp_servers)
        if config:
            (config_dir / "config.toml").write_text(render_toml(config), encoding="utf-8")

    def command(self, prompt: str, run_config: Any | None = None) -> list[str]:
        command = ["codex", "exec"]
        if run_config is not None and getattr(run_config, "resume_session_id", None):
            command.extend(["resume", str(run_config.resume_session_id)])
        elif run_config is not None and getattr(run_config, "continue_last", False):
            command.extend(["resume", "--last"])
        if run_config is not None and getattr(run_config, "json_events", False):
            command.append("--json")
        if run_config is not None and getattr(run_config, "output_schema", None) is not None:
            command.extend(["--output-schema", str(run_config.output_schema)])
        if run_config is not None:
            for attachment in run_config.attachments:
                command.extend(["--image", str(attachment)])
            command.extend(run_config.extra_args)
        command.append(prompt)
        return command


def _codex_approval_policy(default: str | None) -> str | None:
    if default == "ask":
        return "on-request"
    if default == "deny":
        return "untrusted"
    if default == "allow":
        return "never"
    return None
