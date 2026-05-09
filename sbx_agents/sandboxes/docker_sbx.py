from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sbx_agents.errors import SandboxError
from sbx_agents.result import CommandResult, RunArtifacts
from sbx_agents.sandboxes._subprocess import collect_git_diff, run_command
from sbx_agents.sandboxes.base import AgentLike, RunConfigLike, SandboxSession
from sbx_agents.sandboxes.files import WorkspaceFileMixin

DOCKER_SBX_INSTALL_HINT = """Docker SBX CLI `sbx` was not found.

Install Docker SBX, then run `sbx login`:

macOS:
  brew install docker/tap/sbx
  sbx login

Windows:
  winget install -h Docker.sbx
  sbx login

Ubuntu:
  curl -fsSL https://get.docker.com | sudo REPO_ONLY=1 sh
  sudo apt-get install docker-sbx
  sudo usermod -aG kvm "$USER"
  newgrp kvm
  sbx login
"""

DOCKER_SBX_READY_HINT = """Docker SBX CLI `sbx` is installed but not ready.
"""


def _find_sbx() -> str | None:
    return shutil.which("sbx")


class DockerSbxSandbox(WorkspaceFileMixin, BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "docker_sbx"
    workspace: Path
    name: str | None = None
    branch: str | None = None
    cpus: int | None = None
    memory: str | None = None
    remove_on_exit: bool = True
    force_recreate: bool = False
    network_allow: list[str] = Field(default_factory=list)
    secret_env: dict[str, str] = Field(default_factory=dict)
    secret_oauth: list[str] = Field(default_factory=list)
    secret_oauth_refresh: list[str] = Field(default_factory=list)
    codex_auth_from_host: bool = False

    @classmethod
    def is_available(cls) -> bool:
        return _find_sbx() is not None

    @classmethod
    def check_available(cls) -> None:
        if not cls.is_available():
            raise SandboxError(DOCKER_SBX_INSTALL_HINT)

    @classmethod
    def is_ready(cls, *, timeout_seconds: int = 10) -> bool:
        try:
            cls.check_ready(timeout_seconds=timeout_seconds)
        except SandboxError:
            return False
        return True

    @classmethod
    def check_ready(cls, *, timeout_seconds: int = 10) -> None:
        cls.check_available()
        try:
            result = run_command(["sbx", "diagnose", "-o", "json"], timeout=timeout_seconds)
        except subprocess.TimeoutExpired as error:
            raise SandboxError(
                f"{DOCKER_SBX_READY_HINT}\n"
                f"`sbx diagnose -o json` timed out after {timeout_seconds}s."
            ) from error
        try:
            diagnose = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            if result.returncode != 0:
                details = (result.stderr or result.stdout).strip()
                message = DOCKER_SBX_READY_HINT
                if details:
                    message = f"{message}\n`sbx diagnose -o json` output:\n{details}"
                raise SandboxError(message) from error
            raise SandboxError(
                f"{DOCKER_SBX_READY_HINT}\nCould not parse `sbx diagnose -o json` output."
            ) from error

        failures = _diagnose_failures(diagnose)
        if failures:
            raise SandboxError(f"{DOCKER_SBX_READY_HINT}\n{failures}")
        if result.returncode != 0:
            raise SandboxError(f"{DOCKER_SBX_READY_HINT}\n`sbx diagnose -o json` failed.")

    @classmethod
    def check_agent_secrets(cls, agent_id: str, *, timeout_seconds: int = 10) -> None:
        service = _agent_secret_service(agent_id)
        if service is None:
            return
        cls.check_available()
        try:
            result = run_command(
                ["sbx", "secret", "ls", "-g", "--service", service],
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise SandboxError(
                f"Could not check Docker SBX {service} secret. "
                f"Run: sbx secret ls -g --service {service}"
            ) from error

        output = f"{result.stdout}\n{result.stderr}".lower()
        if result.returncode != 0 or "no secrets found" in output:
            raise SandboxError(
                f"Docker SBX needs a global `{service}` secret for `{agent_id}`.\n\n"
                "Run one of:\n"
                f"  sbx secret set -g {service}\n"
                + ("  sbx secret set -g openai --oauth\n" if service == "openai" else "")
                + "\nThen verify:\n"
                f"  sbx secret ls -g --service {service}"
            )

    @classmethod
    def has_global_secret(cls, service: str, *, timeout_seconds: int = 10) -> bool:
        cls.check_available()
        result = run_command(
            ["sbx", "secret", "ls", "-g", "--service", service],
            timeout=timeout_seconds,
        )
        output = f"{result.stdout}\n{result.stderr}".lower()
        return result.returncode == 0 and "no secrets found" not in output

    @classmethod
    def set_global_secret(
        cls,
        service: str,
        value: str,
        *,
        timeout_seconds: int = 10,
    ) -> None:
        cls.check_available()
        result = run_command(
            ["sbx", "secret", "set", "-g", service],
            input_text=value,
            timeout=timeout_seconds,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise SandboxError(
                f"Failed to set Docker SBX global `{service}` secret non-interactively."
                + (f"\n\nOutput:\n{details}" if details else "")
            )

    @classmethod
    def set_global_oauth_secret(
        cls,
        service: str,
        *,
        timeout_seconds: int = 120,
        stream_output: bool = False,
    ) -> None:
        cls.check_available()
        result = run_command(
            ["sbx", "secret", "set", "-g", service, "--oauth"],
            timeout=timeout_seconds,
            stream=stream_output,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise SandboxError(
                f"Failed to set Docker SBX global `{service}` OAuth secret.\n\n"
                f"Run manually:\n  sbx secret set -g {service} --oauth"
                + (f"\n\nOutput:\n{details}" if details else "")
            )

    def ensure_agent_secret(
        self,
        agent_id: str,
        *,
        timeout_seconds: int = 10,
        stream_output: bool = False,
    ) -> None:
        service = _agent_secret_service(agent_id)
        if service is None:
            return
        if service in self.secret_oauth_refresh:
            self.set_global_oauth_secret(service, stream_output=stream_output)
            return
        if self.has_global_secret(service, timeout_seconds=timeout_seconds):
            return
        if service in self.secret_oauth:
            self.set_global_oauth_secret(service, stream_output=stream_output)
            return
        env_var = self.secret_env.get(service)
        if env_var is None:
            self.check_agent_secrets(agent_id, timeout_seconds=timeout_seconds)
            return
        value = os.environ.get(env_var)
        if not value:
            raise SandboxError(
                f"Docker SBX needs global `{service}` secret for `{agent_id}`.\n\n"
                f"Set `{env_var}` or run:\n"
                f"  sbx secret set -g {service}\n"
                + ("  sbx secret set -g openai --oauth\n" if service == "openai" else "")
            )
        self.set_global_secret(service, value, timeout_seconds=timeout_seconds)

    def ensure_agent_auth(
        self,
        agent: AgentLike,
        run_config: RunConfigLike | None = None,
        *,
        stream_output: bool = False,
    ) -> None:
        session = self.prepare(agent, run_config)
        session.metadata["stream_output"] = stream_output
        self._apply_agent_auth(session)

    def _apply_agent_auth(self, session: SandboxSession) -> None:
        agent_id = str(session.metadata["agent_id"])
        if agent_id != "codex":
            self.ensure_agent_secret(
                agent_id,
                timeout_seconds=10,
                stream_output=bool(session.metadata.get("stream_output", False)),
            )
            return

        auth = session.metadata.get("backend_auth")
        if auth is None:
            provider = session.metadata.get("model_provider")
            if provider not in {None, "openai"}:
                return
            self.ensure_agent_secret(
                "codex",
                timeout_seconds=10,
                stream_output=bool(session.metadata.get("stream_output", False)),
            )
            return

        method = getattr(auth, "method", None)
        if method in {"none", "host_chatgpt"}:
            return
        service = str(getattr(auth, "service", "openai"))
        refresh = bool(getattr(auth, "refresh", False))
        stream = bool(session.metadata.get("stream_output", False))
        if method == "openai_oauth":
            if refresh or not self.has_global_secret(service):
                self.set_global_oauth_secret(service, stream_output=stream)
                session.metadata["auth_changed"] = True
            return
        if method == "openai_api_key_env":
            if not refresh and self.has_global_secret(service):
                return
            env_var = str(getattr(auth, "env_var", None) or "OPENAI_API_KEY")
            value = os.environ.get(env_var)
            if not value:
                raise SandboxError(
                    f"Docker SBX needs `{env_var}` to configure Codex API key auth."
                )
            self.set_global_secret(service, value)
            session.metadata["auth_changed"] = True
            return
        raise SandboxError(f"Unsupported Codex auth method for Docker SBX: {method}")

    def prepare(self, agent: AgentLike, run_config: RunConfigLike | None) -> SandboxSession:
        return SandboxSession(
            workspace=self.workspace.resolve(),
            sandbox_name=self.name,
            metadata={
                "agent_id": agent.backend.id,
                "backend_auth": getattr(agent.backend, "auth", None),
                "model_provider": getattr(agent.backend, "model_provider", None),
                "stream_output": bool(getattr(run_config, "stream_output", False)),
                "stream_filter": _stream_filter(run_config),
                "timeout_seconds": getattr(run_config, "timeout_seconds", None),
            },
        )

    def run(self, session: SandboxSession, command: list[str]) -> CommandResult:
        self.check_available()
        self._apply_agent_auth(session)
        self._apply_policies(session)
        auth_changed = bool(session.metadata.get("auth_changed", False))
        if self.force_recreate or auth_changed:
            if self.name is not None:
                self._remove_existing_sandbox(self.name)
            self._remove_workspace_sandboxes(session)
        elif self.name is not None and self._existing_sandbox_for_workspace(session) is None:
            self._remove_workspace_sandboxes(session)
        existing = self._existing_sandbox_for_workspace(session)
        backend_auth = session.metadata.get("backend_auth")
        sync_codex_auth = (
            self.codex_auth_from_host or getattr(backend_auth, "method", None) == "host_chatgpt"
        )
        if sync_codex_auth and session.metadata.get("agent_id") == "codex":
            if session.metadata.get("stream_output", False):
                print("Syncing host Codex ChatGPT auth into Docker SBX...", file=sys.stderr)
            existing = self._ensure_sandbox_for_session(session, existing=existing)
            self._sync_host_codex_auth(existing, session=session)
        sbx_command = (
            self._existing_sandbox_command(session, command, existing)
            if existing is not None
            else self._sbx_command(session, command)
        )
        result = run_command(
            sbx_command,
            cwd=session.workspace,
            stream=bool(session.metadata.get("stream_output", False)),
            stream_filter=session.metadata.get("stream_filter"),
            timeout=session.metadata.get("timeout_seconds"),
        )
        retry_command = self._existing_sandbox_retry_command(session, command, result)
        if retry_command is None:
            return result
        return run_command(
            retry_command,
            cwd=session.workspace,
            stream=bool(session.metadata.get("stream_output", False)),
            stream_filter=session.metadata.get("stream_filter"),
            timeout=session.metadata.get("timeout_seconds"),
        )

    def collect(self, session: SandboxSession) -> RunArtifacts:
        return RunArtifacts(diff=collect_git_diff(session.workspace))

    def cleanup(self, session: SandboxSession) -> None:
        return None

    def _sbx_command(self, session: SandboxSession, command: list[str]) -> list[str]:
        agent_id = str(session.metadata["agent_id"])
        inner_command = self._inner_command(agent_id, command)

        sbx_command = ["sbx", "run"]
        if self.name:
            sbx_command.extend(["--name", self.name])
        if self.branch:
            sbx_command.extend(["--branch", self.branch])
        if self.cpus is not None:
            sbx_command.extend(["--cpus", str(self.cpus)])
        if self.memory is not None:
            sbx_command.extend(["--memory", self.memory])
        if not self.remove_on_exit:
            sbx_command.append("--no-remove")
        sbx_command.extend([agent_id, str(session.workspace)])
        sbx_command.extend(["--", *inner_command])
        return sbx_command

    def _sbx_create_command(self, session: SandboxSession) -> list[str]:
        agent_id = str(session.metadata["agent_id"])
        command = ["sbx", "create", "--quiet"]
        if self.name:
            command.extend(["--name", self.name])
        if self.branch:
            command.extend(["--branch", self.branch])
        if self.cpus is not None:
            command.extend(["--cpus", str(self.cpus)])
        if self.memory is not None:
            command.extend(["--memory", self.memory])
        command.extend([agent_id, str(session.workspace)])
        return command

    def _inner_command(self, agent_id: str, command: list[str]) -> list[str]:
        if agent_id in {"codex", "opencode"} and command[:1] == [agent_id]:
            return command[1:]
        return command

    def _ensure_sandbox_for_session(
        self,
        session: SandboxSession,
        *,
        existing: str | None,
    ) -> str:
        if existing is not None:
            return existing
        result = run_command(
            self._sbx_create_command(session),
            cwd=session.workspace,
            stream=bool(session.metadata.get("stream_output", False)),
            stream_filter=session.metadata.get("stream_filter"),
            timeout=session.metadata.get("timeout_seconds"),
        )
        retry_command = self._existing_sandbox_retry_command(session, [], result)
        if retry_command is not None:
            return retry_command[2]
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise SandboxError(
                "Failed to create Docker SBX sandbox before syncing Codex auth."
                + (f"\n\nOutput:\n{details}" if details else "")
            )
        if self.name is not None:
            return self.name
        existing = self._existing_sandbox_for_workspace(session)
        if existing is None:
            raise SandboxError("Could not determine Docker SBX sandbox name after create.")
        return existing

    def _remove_existing_sandbox(self, sandbox_name: str) -> None:
        listed = run_command(["sbx", "ls"], timeout=10)
        if listed.returncode != 0 or sandbox_name not in listed.stdout:
            return
        result = run_command(["sbx", "rm", sandbox_name], timeout=60)
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise SandboxError(
                f"Failed to recreate Docker SBX sandbox `{sandbox_name}`.\n\n"
                f"Run manually:\n  sbx rm {sandbox_name}"
                + (f"\n\nOutput:\n{details}" if details else "")
            )

    def _remove_workspace_sandboxes(self, session: SandboxSession) -> None:
        for sandbox_name in self._workspace_sandbox_names(session):
            if sandbox_name == self.name:
                continue
            self._remove_existing_sandbox(sandbox_name)

    def _workspace_sandbox_names(self, session: SandboxSession) -> list[str]:
        result = run_command(["sbx", "ls"], timeout=10)
        if result.returncode != 0:
            return []
        agent_id = str(session.metadata["agent_id"])
        workspace = str(session.workspace)
        names: list[str] = []
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            sandbox_name = parts[0]
            agent = parts[1]
            listed_workspace = parts[-1]
            if agent == agent_id and listed_workspace == workspace:
                names.append(sandbox_name)
        return names

    def _sync_host_codex_auth(self, sandbox_name: str, *, session: SandboxSession) -> None:
        auth_path = _host_codex_auth_path()
        if not auth_path.exists():
            raise SandboxError(
                "Host Codex ChatGPT auth not found.\n\n"
                "Run on host first:\n  codex login\n\n"
                "Then retry."
            )
        try:
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SandboxError(f"Host Codex auth file is invalid JSON: {auth_path}") from error
        if auth.get("auth_mode") != "chatgpt":
            raise SandboxError(
                "Host Codex auth is not ChatGPT auth.\n\n"
                "Run on host first:\n  codex login\n\n"
                "Then retry."
            )

        stream = bool(session.metadata.get("stream_output", False))
        mkdir = run_command(
            ["sbx", "exec", sandbox_name, "mkdir", "-p", "/home/agent/.codex"],
            stream=stream,
            stream_filter=session.metadata.get("stream_filter"),
            timeout=session.metadata.get("timeout_seconds"),
        )
        if mkdir.returncode != 0:
            details = (mkdir.stderr or mkdir.stdout).strip()
            raise SandboxError(
                "Failed to prepare Codex auth directory in Docker SBX."
                + (f"\n\nOutput:\n{details}" if details else "")
            )
        copied = run_command(
            ["sbx", "cp", str(auth_path), f"{sandbox_name}:/home/agent/.codex/auth.json"],
            stream=stream,
            stream_filter=session.metadata.get("stream_filter"),
            timeout=session.metadata.get("timeout_seconds"),
        )
        if copied.returncode != 0:
            details = (copied.stderr or copied.stdout).strip()
            raise SandboxError(
                "Failed to copy host Codex auth into Docker SBX."
                + (f"\n\nOutput:\n{details}" if details else "")
            )
        fixed_permissions = run_command(
            [
                "sbx",
                "exec",
                "-u",
                "root",
                sandbox_name,
                "sh",
                "-lc",
                "chown agent:agent /home/agent/.codex/auth.json && "
                "chmod 600 /home/agent/.codex/auth.json",
            ],
            stream=stream,
            stream_filter=session.metadata.get("stream_filter"),
            timeout=session.metadata.get("timeout_seconds"),
        )
        if fixed_permissions.returncode != 0:
            details = (fixed_permissions.stderr or fixed_permissions.stdout).strip()
            raise SandboxError(
                "Failed to fix Codex auth permissions in Docker SBX."
                + (f"\n\nOutput:\n{details}" if details else "")
            )

    def _apply_policies(self, session: SandboxSession) -> None:
        resources = self._network_allow_resources(session)
        if not resources:
            return
        joined = ",".join(resources)
        result = run_command(["sbx", "policy", "allow", "network", joined], timeout=10)
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise SandboxError(
                "Failed to apply Docker SBX network policy.\n\n"
                f"Run manually:\n  sbx policy allow network {joined}\n"
                + (f"\nOutput:\n{details}" if details else "")
            )

    def _network_allow_resources(self, session: SandboxSession) -> list[str]:
        resources = list(self.network_allow)
        if session.metadata.get("agent_id") == "codex":
            provider = session.metadata.get("model_provider")
            auth = session.metadata.get("backend_auth")
            method = getattr(auth, "method", None)
            if provider in {None, "openai"} and "api.openai.com:443" not in resources:
                resources.append("api.openai.com:443")
            if method == "openai_oauth" and "chatgpt.com:443" not in resources:
                resources.append("chatgpt.com:443")
        return resources

    def _existing_sandbox_retry_command(
        self,
        session: SandboxSession,
        command: list[str],
        result: CommandResult,
    ) -> list[str] | None:
        if self.name is not None:
            return None
        if result.returncode == 0 or "--name can only be used" not in result.stderr:
            return None
        match = re.search(r"sbx run ([^\s]+) \[-- AGENT_ARGS", result.stderr)
        if match is None:
            return None
        return self._existing_sandbox_command(session, command, match.group(1))

    def _existing_sandbox_command(
        self,
        session: SandboxSession,
        command: list[str],
        sandbox_name: str,
    ) -> list[str]:
        agent_id = str(session.metadata["agent_id"])
        inner_command = self._inner_command(agent_id, command)
        return ["sbx", "run", sandbox_name, "--", *inner_command]

    def _existing_sandbox_for_workspace(self, session: SandboxSession) -> str | None:
        agent_id = str(session.metadata["agent_id"])
        result = run_command(["sbx", "ls"], timeout=10)
        if result.returncode != 0:
            return None
        workspace = str(session.workspace)
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            sandbox_name = parts[0]
            agent = parts[1]
            listed_workspace = parts[-1]
            if self.name is not None:
                if sandbox_name == self.name and agent == agent_id:
                    return sandbox_name
                continue
            if agent == agent_id and listed_workspace == workspace:
                return sandbox_name
        return None


def _diagnose_failures(diagnose: dict[str, Any]) -> str:
    checks = diagnose.get("checks")
    if not isinstance(checks, list):
        return "Unexpected diagnostics format."

    commands: list[str] = []
    problems: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        name = str(check.get("name", "unknown"))
        status = str(check.get("status", "unknown"))
        if status == "pass":
            continue
        if status in {"skip", "warn"}:
            continue

        message = str(check.get("message", "")).strip()
        hint = str(check.get("hint", "")).strip()
        if hint.startswith("Run: "):
            command = hint.removeprefix("Run: ").strip()
            if command and command not in commands:
                commands.append(command)
        elif name == "Authentication" and "sbx login" not in commands:
            commands.append("sbx login")

        line = f"- {name}: {status}"
        if message:
            line = f"{line} - {message}"
        problems.append(line)

    output: list[str] = []
    if commands:
        output.extend(["Try:", *(f"  {command}" for command in commands)])
        if "sbx login" not in commands:
            output.append("  sbx login")
        output.extend(["", "Then verify:", "  sbxa doctor --require docker-sbx"])
    if problems:
        output.extend(["", "Problem:", *problems])
    return "\n".join(output)


def _agent_secret_service(agent_id: str) -> str | None:
    if agent_id == "codex":
        return "openai"
    if agent_id in {"opencode", "claude"}:
        return "anthropic"
    return None


def _stream_filter(run_config: RunConfigLike | None) -> object | None:
    metadata = getattr(run_config, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    return metadata.get("stream_filter")


def _host_codex_auth_path() -> Path:
    return Path.home() / ".codex" / "auth.json"
