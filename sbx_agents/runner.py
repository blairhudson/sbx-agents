import json
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from sbx_agents.agent import Agent
from sbx_agents.context import MaterialiseContext
from sbx_agents.permissions import PermissionPolicy
from sbx_agents.result import RunResult
from sbx_agents.sandboxes.base import SandboxBackend


class RunConfig(BaseModel):
    timeout_seconds: int | None = None
    json_events: bool = False
    stream_events: bool = False
    stream_output: bool = False
    output_schema: Path | dict[str, Any] | None = None
    attachments: list[Path] = Field(default_factory=list)
    resume_session_id: str | None = None
    continue_last: bool = False
    fork_session: bool = False
    env: dict[str, str] = Field(default_factory=dict)
    forward_env: list[str] = Field(default_factory=list)
    secret_env: list[str] = Field(default_factory=list)
    permission: PermissionPolicy | None = None
    network: str | None = None
    secrets: list[str] = Field(default_factory=list)
    remove_on_exit: bool = True
    extra_args: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Runner:
    run_sync: Any

    def __init__(
        self,
        agent: Agent,
        *,
        sandbox: SandboxBackend,
        run_config: RunConfig | None = None,
        default_prompt: str | None = None,
    ) -> None:
        self.agent = agent
        self.sandbox = sandbox
        self.run_config = run_config
        self.default_prompt = default_prompt

    @staticmethod
    def _run_sync(
        agent: Agent,
        *,
        sandbox: SandboxBackend,
        prompt: str,
        run_config: RunConfig | None = None,
    ) -> RunResult:
        started = perf_counter()
        session = sandbox.prepare(agent, run_config)
        try:
            ctx = MaterialiseContext(workspace=session.workspace, sandbox=session)
            for capability in agent.capabilities:
                apply = getattr(capability, "apply", None)
                if apply is not None:
                    apply(agent)

            agent.backend.materialise(ctx, agent)
            if run_config is not None and isinstance(run_config.output_schema, dict):
                schema_path = session.workspace / ".sbx-agents" / "output-schema.json"
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_text(
                    json.dumps(run_config.output_schema, indent=2),
                    encoding="utf-8",
                )
                run_config.output_schema = schema_path

            command = agent.backend.command(prompt, run_config)
            command_result = sandbox.run(session, command)
            if command_result.duration_ms is None:
                command_result.duration_ms = int((perf_counter() - started) * 1000)

            artifacts = sandbox.collect(session)
            events = []
            if run_config is not None and run_config.json_events:
                events = _parse_json_events(command_result.stdout)
            return RunResult.from_parts(
                agent_name=agent.name,
                agent_backend=agent.backend.id,
                sandbox_backend=sandbox.id,
                sandbox_name=session.sandbox_name,
                command_result=command_result,
                artifacts=artifacts,
                events=events,
            )
        finally:
            sandbox.cleanup(session)


class _RunSyncDescriptor:
    def __get__(self, instance: Runner | None, owner: type[Runner]) -> Any:
        if instance is None:

            def class_run_sync(
                agent: Agent,
                *,
                sandbox: SandboxBackend,
                prompt: str,
                run_config: RunConfig | None = None,
            ) -> RunResult:
                return owner._run_sync(
                    agent,
                    sandbox=sandbox,
                    prompt=prompt,
                    run_config=run_config,
                )

            return class_run_sync

        def instance_run_sync(
            prompt: str | None = None,
            *,
            run_config: RunConfig | None = None,
        ) -> RunResult:
            final_prompt = prompt or instance.default_prompt
            if final_prompt is None:
                raise ValueError(
                    "Prompt required. Pass prompt to run_sync(...) or set default_prompt."
                )
            return owner._run_sync(
                instance.agent,
                sandbox=instance.sandbox,
                prompt=final_prompt,
                run_config=run_config or instance.run_config,
            )

        return instance_run_sync


Runner.run_sync = _RunSyncDescriptor()


def _parse_json_events(output: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
        elif isinstance(value, list):
            events.extend(item for item in value if isinstance(item, dict))
    return events
