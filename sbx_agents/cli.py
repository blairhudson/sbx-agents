from __future__ import annotations

import importlib
import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import typer

from sbx_agents.errors import SandboxError
from sbx_agents.result import RunResult
from sbx_agents.runner import RunConfig, Runner
from sbx_agents.sandboxes import DockerSandbox, DockerSbxSandbox
from sbx_agents.streaming import PrettyStreamFilter

app = typer.Typer(help="Run Python-defined sbx-agents runners.", no_args_is_help=True)


@app.command()
def run(
    target: str = typer.Argument(..., help="Python target, e.g. main.py:runner or pkg.mod:runner"),
    prompt: str | None = typer.Argument(None, help="Prompt override"),
    json_output: bool = typer.Option(False, "--json", help="Print full RunResult as JSON"),
    diff: bool = typer.Option(False, "--diff", help="Print collected diff after output"),
    raw: bool = typer.Option(False, "--raw", help="Stream raw sandbox output"),
    preflight: bool = typer.Option(
        True,
        "--preflight/--no-preflight",
        help="Check runtime readiness before run",
    ),
) -> None:
    """Run a Python-defined Runner."""

    loaded = _load_target(target)
    if not isinstance(loaded, Runner):
        raise typer.BadParameter(
            "Target must be a sbx_agents.Runner instance. "
            "Define `runner = Runner(agent, sandbox=..., default_prompt=...)`."
        )

    if not json_output:
        typer.echo(
            f"Running {loaded.agent.name} with {loaded.agent.backend.id} "
            f"in {loaded.sandbox.id}",
            err=True,
        )
    if preflight:
        try:
            _preflight(loaded, quiet=json_output)
        except SandboxError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(1) from error

    run_config = _cli_run_config(loaded, stream_output=not json_output, raw=raw)
    result = loaded.run_sync(prompt, run_config=run_config)
    _print_result(
        result,
        json_output=json_output,
        diff=diff,
        live_streamed=bool(run_config and run_config.stream_output)
        and isinstance(loaded.sandbox, DockerSandbox | DockerSbxSandbox),
    )
    if result.returncode != 0 and not json_output:
        _print_failure_hint(loaded, result)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@app.command()
def doctor(
    require: str | None = typer.Option(
        None,
        "--require",
        help="Require optional runtime: docker or docker-sbx",
    ),
) -> None:
    """Check local runtime availability."""

    docker_ok = shutil.which("docker") is not None
    docker_sbx_installed = DockerSbxSandbox.is_available()
    docker_sbx_ready: bool | None = None

    typer.echo("sbx-agents: ok")
    typer.echo(f"docker: {'found' if docker_ok else 'missing'}")
    typer.echo(f"docker-sbx: {'installed' if docker_sbx_installed else 'missing'}")

    if require is None:
        typer.echo("docker-sbx auth: not checked")
        return
    if require not in {"docker", "docker-sbx"}:
        raise typer.BadParameter("--require must be 'docker' or 'docker-sbx'")
    if require == "docker" and not docker_ok:
        raise typer.Exit(1)
    if require == "docker-sbx" and docker_sbx_installed:
        docker_sbx_ready = DockerSbxSandbox.is_ready()
        typer.echo(f"docker-sbx auth: {'ready' if docker_sbx_ready else 'not ready'}")
    if require == "docker-sbx" and not docker_sbx_ready:
        raise typer.Exit(1)


def _preflight(runner: Runner, *, quiet: bool = False) -> None:
    sandbox = runner.sandbox
    if isinstance(sandbox, DockerSbxSandbox):
        if not quiet:
            typer.echo("Checking Docker SBX readiness...", err=True)
        DockerSbxSandbox.check_ready()
        if _needs_sbx_secret(runner):
            service = _agent_secret_service_name(runner)
            if service is not None and not quiet:
                typer.echo(f"Ensuring Docker SBX `{service}` secret...", err=True)
            sandbox.ensure_agent_auth(
                runner.agent,
                runner.run_config,
                stream_output=not quiet,
            )
        _check_docker_sbx_local_provider(runner)
        if not quiet:
            typer.echo(
                "Docker SBX ready.",
                err=True,
            )
    elif isinstance(sandbox, DockerSandbox) and shutil.which("docker") is None:
        raise typer.BadParameter("Docker CLI `docker` was not found. Install Docker, then retry.")


def _cli_run_config(runner: Runner, *, stream_output: bool, raw: bool = False) -> RunConfig | None:
    if not stream_output:
        return runner.run_config
    if runner.run_config is None:
        run_config = RunConfig(stream_output=True)
    else:
        run_config = runner.run_config.model_copy(update={"stream_output": True})
    if raw:
        return run_config
    metadata = dict(run_config.metadata)
    metadata["stream_filter"] = PrettyStreamFilter(backend_id=runner.agent.backend.id)
    return run_config.model_copy(update={"metadata": metadata})


def _needs_sbx_secret(runner: Runner) -> bool:
    backend = runner.agent.backend
    if backend.id == "codex":
        if isinstance(runner.sandbox, DockerSbxSandbox) and runner.sandbox.codex_auth_from_host:
            return False
        auth = getattr(backend, "auth", None)
        method = getattr(auth, "method", None)
        if method in {"none", "host_chatgpt"}:
            return False
        if method in {"openai_oauth", "openai_api_key_env"}:
            return True
        provider = getattr(backend, "model_provider", None)
        return provider in {None, "openai"}
    return backend.id in {"opencode", "claude"}


def _agent_secret_service_name(runner: Runner) -> str | None:
    backend_id = runner.agent.backend.id
    if backend_id == "codex":
        return "openai"
    if backend_id == "opencode":
        return "anthropic"
    if backend_id == "claude":
        return "anthropic"
    return None


def _check_docker_sbx_local_provider(runner: Runner) -> None:
    backend = runner.agent.backend
    if backend.id != "codex":
        return
    provider_name = getattr(backend, "model_provider", None)
    extra_config = getattr(backend, "extra_config", {})
    providers = extra_config.get("model_providers", {}) if isinstance(extra_config, dict) else {}
    provider = providers.get(provider_name) if isinstance(providers, dict) else None
    if not isinstance(provider, dict):
        return
    base_url = str(provider.get("base_url", ""))
    if "localhost" not in base_url and "127.0.0.1" not in base_url:
        return
    raise SandboxError(
        "Local model provider uses localhost, but Docker SBX runs inside a sandbox.\n\n"
        "Use host.docker.internal instead:\n"
        "  http://host.docker.internal:8080/v1\n\n"
        "Then allow the sandbox to reach it:\n"
        "  sbx policy allow network host.docker.internal:8080"
    )


def _print_result(
    result: RunResult,
    *,
    json_output: bool,
    diff: bool,
    live_streamed: bool,
) -> None:
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    if result.output and not live_streamed:
        typer.echo(result.output.rstrip())
    if diff and result.diff:
        typer.echo("\n--- diff ---")
        typer.echo(result.diff.rstrip())


def _print_failure_hint(runner: Runner, result: RunResult) -> None:
    combined = f"{result.stdout}\n{result.stderr}"
    if "401 Unauthorized" not in combined:
        return
    if not isinstance(runner.sandbox, DockerSbxSandbox):
        return
    if runner.agent.backend.id != "codex":
        return
    typer.echo(
        "\nDocker SBX OpenAI auth was rejected. Refresh OAuth secret:\n"
        "  sbx secret set -g openai --oauth\n\n"
        "Or set in Python config:\n"
        "  Codex(auth={\"method\": \"openai_oauth\", \"refresh\": True})",
        err=True,
    )


def _load_target(target: str) -> Any:
    module_ref, _, attr = target.partition(":")
    attr = attr or "runner"
    module = _load_module(module_ref)
    try:
        return getattr(module, attr)
    except AttributeError as error:
        raise typer.BadParameter(f"Target `{target}` has no `{attr}` object") from error


def _load_module(module_ref: str) -> ModuleType:
    path = Path(module_ref)
    if module_ref.endswith(".py") or path.exists():
        return _load_file_module(path)
    return importlib.import_module(module_ref)


def _load_file_module(path: Path) -> ModuleType:
    resolved = path.resolve()
    if not resolved.exists():
        raise typer.BadParameter(f"Python file not found: {path}")

    module_name = f"_sbxa_{abs(hash(resolved))}"
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    if spec is None or spec.loader is None:
        raise typer.BadParameter(f"Could not load Python file: {path}")

    module = importlib.util.module_from_spec(spec)
    parent = str(resolved.parent)
    sys.path.insert(0, parent)
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(parent)
        except ValueError:
            pass
    return module


if __name__ == "__main__":
    app()
