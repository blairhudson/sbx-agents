from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSandbox

sandbox = DockerSandbox(
    workspace=Path("."),
    image="python:3.12-slim",
)

agent = Agent(
    name="file-worker",
    backend=Shell(),
    instructions="Read and write only requested files.",
)

# Put a specific input file into the sandbox workspace before the run.
sandbox.put_file(
    "tmp/sbx-agent-spec.md",
    """
# Task Spec

Create a short JSON report at tmp/sbx-agent-report.json.
""".strip(),
)

result = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="""
python - <<'PY'
from pathlib import Path
spec = Path('tmp/sbx-agent-spec.md').read_text()
Path('tmp/sbx-agent-report.json').write_text(
    '{"status":"ok","spec_chars":%d}\n' % len(spec)
)
PY
""".strip(),
)

print(result.output)

# Get a specific output file back from the sandbox workspace after the run.
report = sandbox.get_file("tmp/sbx-agent-report.json")
print(report)

# List and clean specific files.
print(sandbox.list_files("tmp/sbx-agent-*"))
sandbox.delete_file("tmp/sbx-agent-spec.md")
sandbox.delete_file("tmp/sbx-agent-report.json")
