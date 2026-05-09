from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSandbox

agent = Agent(
    name="shell-workflow",
    backend=Shell(),
    instructions="Run shell commands requested by the orchestration layer.",
)

sandbox = DockerSandbox(
    workspace=Path("."),
    image="python:3.12-slim",
)

# Step 1: collect context.
inspect = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="python --version",
)

print("Inspect:")
print(inspect.output)

# Step 2: app carries prior output into the next prompt.
test = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt=f"""
Previous command output:

{inspect.output}

Now check whether pytest is installed:
python -m pytest --version
""".strip(),
)

print("Test check:")
print(test.output)

# Step 3: app decides what to do from prior result.
summary = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt=f"""
Summarize this workflow result in one line.

Step 1 output:
{inspect.output}

Step 2 output:
{test.output}
""".strip(),
)

print("Summary:")
print(summary.output)
