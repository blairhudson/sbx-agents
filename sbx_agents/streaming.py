from __future__ import annotations

import json
import re
from typing import Literal


class PrettyStreamFilter:
    def __init__(self, *, backend_id: str) -> None:
        self.backend_id = backend_id
        self._started_commands: set[str] = set()

    def __call__(self, line: str, source: Literal["stdout", "stderr"]) -> str | None:
        stripped = line.strip()
        if not stripped:
            return None
        if _is_sbx_noise(stripped):
            return None
        if self.backend_id == "codex":
            formatted = self._format_codex_json(stripped)
            if formatted is not None:
                return formatted
        return line

    def _format_codex_json(self, line: str) -> str | None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(event, dict):
            return None

        event_type = event.get("type")
        if event_type == "thread.started":
            thread_id = event.get("thread_id")
            return f"agent: started thread {thread_id}" if thread_id else "agent: started"
        if event_type == "turn.started":
            return None
        if event_type == "error":
            message = str(event.get("message", "unknown error"))
            return f"error: {message}"
        if event_type in {"item.started", "item.completed"}:
            item = event.get("item")
            if isinstance(item, dict):
                return self._format_codex_item(event_type, item)
        return None

    def _format_codex_item(self, event_type: str, item: dict[str, object]) -> str | None:
        item_type = item.get("type")
        if item_type == "agent_message" and event_type == "item.completed":
            text = str(item.get("text", "")).strip()
            return _indent_block("agent", text) if text else None
        if item_type != "command_execution":
            return None

        command = str(item.get("command", "")).strip()
        if not command:
            return None
        if event_type == "item.started":
            if command in self._started_commands:
                return None
            self._started_commands.add(command)
            return f"cmd: {command}"

        status = str(item.get("status", ""))
        exit_code = item.get("exit_code")
        if status == "completed" or exit_code == 0:
            return f"ok: {command}"
        output = str(item.get("aggregated_output", "")).strip()
        header = f"fail: {command}"
        if exit_code is not None:
            header = f"{header} (exit {exit_code})"
        if not output:
            return header
        return f"{header}\n{_trim_output(output)}"


def _is_sbx_noise(line: str) -> bool:
    noise_prefixes = (
        "✓ Git repository detected:",
        "Warning: uncommitted changes won't be included",
        "Creating Git worktree with branch:",
        "Warning: failed to create Git worktree:",
        "Continuing with direct workspace mount.",
        "Note: running Git on both host and sandbox",
        "Creating new sandbox '",
        "Using stored OpenAI OAuth credentials",
        "OpenAI OAuth takes precedence",
        "Digest: ",
        "Status: Image is up to date",
        "INFO: Configuring Docker",
        "✓ Created sandbox '",
        "Workspace: ",
        "Agent: ",
        "To connect to this sandbox, run:",
        "sbx run ",
        "INFO: Starting Docker daemon",
        "Starting codex agent in sandbox",
        "Starting opencode agent in sandbox",
    )
    if line.startswith(noise_prefixes):
        return True
    if re.fullmatch(r"[a-f0-9]{12}: Already exists", line):
        return True
    return False


def _indent_block(label: str, text: str) -> str:
    lines = text.splitlines() or [text]
    body = "\n".join(f"  {line}" for line in lines)
    return f"{label}:\n{body}"


def _trim_output(output: str, *, max_lines: int = 12, max_chars: int = 1200) -> str:
    lines = output.splitlines()
    trimmed = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        trimmed = f"{trimmed}\n... ({len(lines) - max_lines} more lines hidden; use --raw)"
    if len(trimmed) > max_chars:
        trimmed = f"{trimmed[:max_chars].rstrip()}\n... (output truncated; use --raw)"
    return "\n".join(f"  {line}" for line in trimmed.splitlines())
