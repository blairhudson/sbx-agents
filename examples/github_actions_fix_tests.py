import os
from pathlib import Path

from sbx_agents import Agent, PermissionPolicy, RunConfig, Runner
from sbx_agents.backends import Codex, OpenCode, Shell
from sbx_agents.sandboxes import DockerSandbox, DockerSbxSandbox


def main() -> None:
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    prompt = os.environ.get("SBX_AGENT_PROMPT", "Run the test suite and fix failures.")

    agent = Agent(
        name="github-actions-agent",
        backend=_backend(),
        instructions=(
            "You are running in GitHub Actions. Keep diffs small. "
            "Run relevant tests before finishing."
        ),
        permission=PermissionPolicy(default="ask", tools={"bash": "allow"}),
    )

    result = Runner.run_sync(
        agent,
        sandbox=_sandbox(workspace),
        prompt=prompt,
        run_config=RunConfig(json_events=_bool_env("SBX_JSON_EVENTS")),
    )

    print(result.output)
    if result.diff:
        print("\n--- diff ---")
        print(result.diff)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text(_summary(result.output, result.diff), encoding="utf-8")

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def _backend() -> Shell | Codex | OpenCode:
    backend = os.environ.get("SBX_AGENT_BACKEND", "shell")
    if backend == "shell":
        return Shell()
    if backend == "codex":
        return Codex(model=os.environ.get("SBX_CODEX_MODEL"))
    if backend == "opencode":
        return OpenCode(model=os.environ.get("SBX_OPENCODE_MODEL"))
    raise ValueError(f"Unsupported SBX_AGENT_BACKEND: {backend}")


def _sandbox(workspace: Path) -> DockerSandbox | DockerSbxSandbox:
    sandbox = os.environ.get("SBX_SANDBOX_BACKEND", "docker")
    if sandbox == "docker":
        return DockerSandbox(
            workspace=workspace,
            image=os.environ.get("SBX_DOCKER_IMAGE", "python:3.12-slim"),
        )
    if sandbox == "docker_sbx":
        return DockerSbxSandbox(
            workspace=workspace,
            name="github-actions-agent",
            branch=os.environ.get("SBX_BRANCH"),
        )
    raise ValueError(f"Unsupported SBX_SANDBOX_BACKEND: {sandbox}")


def _summary(output: str, diff: str | None) -> str:
    body = ["# sbx-agents run", "", "## Output", "", "```", output, "```"]
    if diff:
        body.extend(["", "## Diff", "", "```diff", diff, "```"])
    return "\n".join(body) + "\n"


def _bool_env(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
