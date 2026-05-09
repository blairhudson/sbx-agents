from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    path: Path
    kind: str = "file"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandResult(BaseModel):
    stdout: str = ""
    stderr: str = ""
    returncode: int
    command: list[str] = Field(default_factory=list)
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunArtifacts(BaseModel):
    diff: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    output: str
    stdout: str
    stderr: str
    returncode: int
    agent_name: str
    agent_backend: str
    sandbox_backend: str
    sandbox_name: str | None = None
    command: list[str]
    duration_ms: int | None = None
    diff: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None
    thread_id: str | None = None
    usage: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_parts(
        cls,
        *,
        agent_name: str,
        agent_backend: str,
        sandbox_backend: str,
        sandbox_name: str | None,
        command_result: CommandResult,
        artifacts: RunArtifacts,
        events: list[dict[str, Any]] | None = None,
    ) -> "RunResult":
        parsed_events = events or []
        output = (
            _output_from_events(parsed_events)
            or command_result.stdout
            or command_result.stderr
        )
        return cls(
            output=output,
            stdout=command_result.stdout,
            stderr=command_result.stderr,
            returncode=command_result.returncode,
            agent_name=agent_name,
            agent_backend=agent_backend,
            sandbox_backend=sandbox_backend,
            sandbox_name=sandbox_name,
            command=command_result.command,
            duration_ms=command_result.duration_ms,
            diff=artifacts.diff,
            artifacts=artifacts.artifacts,
            events=parsed_events,
            session_id=_first_event_value(parsed_events, "session_id"),
            thread_id=_first_event_value(parsed_events, "thread_id"),
            usage=_last_event_value(parsed_events, "usage"),
            metadata={**command_result.metadata, **artifacts.metadata},
        )


def _output_from_events(events: list[dict[str, Any]]) -> str | None:
    for event in reversed(events):
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str):
                return text
        message = event.get("message")
        if isinstance(message, str):
            return message
    return None


def _first_event_value(events: list[dict[str, Any]], key: str) -> str | None:
    for event in events:
        value = event.get(key)
        if isinstance(value, str):
            return value
    return None


def _last_event_value(events: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for event in reversed(events):
        value = event.get(key)
        if isinstance(value, dict):
            return value
    return None
