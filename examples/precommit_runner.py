from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSandbox

# Import-safe runner for a Git pre-commit hook.
# The hook calls this through `sbxa run examples/precommit_runner.py`.
# Keep pre-commit runners deterministic and non-mutating; hooks should fail fast.
runner = Runner(
    Agent(
        name="precommit-checks",
        backend=Shell(),
        instructions="Run deterministic pre-commit checks. Do not modify files.",
    ),
    sandbox=DockerSandbox(
        workspace=Path("."),
        image="python:3.12-slim",
        name="sbx-agents-precommit",
    ),
    default_prompt="python -m compileall .",
)
