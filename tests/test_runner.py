from pathlib import Path

from sbx_agents import Agent, CommandResult, RunArtifacts, RunConfig, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes.base import AgentLike, RunConfigLike, SandboxSession


class FakeSandbox:
    id = "fake"
    name: str | None = "fake-name"

    def __init__(self) -> None:
        self.cleaned = False
        self.seen_command: list[str] | None = None

    def prepare(self, agent: AgentLike, run_config: RunConfigLike | None) -> SandboxSession:
        return SandboxSession(workspace=Path("."), sandbox_name=self.name)

    def run(self, session: SandboxSession, command: list[str]) -> CommandResult:
        self.seen_command = command
        return CommandResult(stdout="ok", stderr="", returncode=0, command=command)

    def collect(self, session: SandboxSession) -> RunArtifacts:
        return RunArtifacts(diff="diff --git a/file b/file")

    def cleanup(self, session: SandboxSession) -> None:
        self.cleaned = True


class JsonEventSandbox(FakeSandbox):
    def run(self, session: SandboxSession, command: list[str]) -> CommandResult:
        self.seen_command = command
        stdout = '\n'.join(
            [
                '{"type":"thread.started","thread_id":"thread-1"}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}',
                '{"type":"turn.completed","usage":{"input_tokens":1}}',
            ]
        )
        return CommandResult(stdout=stdout, stderr="", returncode=0, command=command)


def test_runner_run_sync_lifecycle() -> None:
    sandbox = FakeSandbox()
    agent = Agent(name="test", backend=Shell())

    result = Runner.run_sync(agent, sandbox=sandbox, prompt="echo ok")

    assert sandbox.cleaned is True
    assert sandbox.seen_command == ["sh", "-lc", "echo ok"]
    assert result.output == "ok"
    assert result.returncode == 0
    assert result.agent_backend == "shell"
    assert result.sandbox_backend == "fake"
    assert result.diff == "diff --git a/file b/file"


def test_runner_parses_opt_in_json_events() -> None:
    sandbox = JsonEventSandbox()
    agent = Agent(name="test", backend=Shell())

    result = Runner.run_sync(
        agent,
        sandbox=sandbox,
        prompt="echo ok",
        run_config=RunConfig(json_events=True),
    )

    assert result.output == "done"
    assert result.thread_id == "thread-1"
    assert result.usage == {"input_tokens": 1}
    assert len(result.events) == 3


def test_runner_instance_uses_default_prompt() -> None:
    sandbox = FakeSandbox()
    agent = Agent(name="test", backend=Shell())
    runner = Runner(agent, sandbox=sandbox, default_prompt="echo default")

    result = runner.run_sync()

    assert sandbox.seen_command == ["sh", "-lc", "echo default"]
    assert result.output == "ok"


def test_runner_instance_prompt_override() -> None:
    sandbox = FakeSandbox()
    agent = Agent(name="test", backend=Shell())
    runner = Runner(agent, sandbox=sandbox, default_prompt="echo default")

    runner.run_sync("echo override")

    assert sandbox.seen_command == ["sh", "-lc", "echo override"]


def test_runner_instance_requires_prompt() -> None:
    sandbox = FakeSandbox()
    agent = Agent(name="test", backend=Shell())
    runner = Runner(agent, sandbox=sandbox)

    try:
        runner.run_sync()
    except ValueError as error:
        assert "Prompt required" in str(error)
    else:
        raise AssertionError("Expected ValueError")
