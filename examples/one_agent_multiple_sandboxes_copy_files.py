from pathlib import Path
from tempfile import TemporaryDirectory

from sbx_agents import Agent, Runner
from sbx_agents.backends import Shell
from sbx_agents.sandboxes import DockerSandbox

agent = Agent(
    name="portable-worker",
    backend=Shell(),
    instructions="Run requested shell commands inside whichever sandbox is provided.",
)

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    producer_workspace = root / "producer"
    consumer_workspace = root / "consumer"
    producer_workspace.mkdir()
    consumer_workspace.mkdir()

    producer = DockerSandbox(
        workspace=producer_workspace,
        image="python:3.12-slim",
        name="producer-sandbox",
    )
    consumer = DockerSandbox(
        workspace=consumer_workspace,
        image="python:3.12-slim",
        name="consumer-sandbox",
    )

    # Put an input file only into the producer sandbox.
    producer.put_file(
        "inputs/spec.txt",
        "Build a JSON artifact with status, source, and spec length.",
    )

    # Same agent works in sandbox A.
    producer_result = Runner.run_sync(
        agent,
        sandbox=producer,
        prompt="""
python - <<'PY'
from pathlib import Path
spec = Path('inputs/spec.txt').read_text()
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/report.json').write_text(
    '{"status":"ok","source":"producer","spec_chars":%d}\n' % len(spec)
)
PY
""".strip(),
    )

    print("Producer output:")
    print(producer_result.output)

    # Copy one selected file from sandbox A to sandbox B through app code.
    # This keeps transfer explicit and tenant/workspace boundaries clear.
    report = producer.get_file("artifacts/report.json")
    consumer.put_file("incoming/report.json", report)

    # Same agent now works in sandbox B against copied file.
    consumer_result = Runner.run_sync(
        agent,
        sandbox=consumer,
        prompt="""
python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('incoming/report.json').read_text())
Path('verified.txt').write_text(f"verified {report['status']} from {report['source']}\n")
print(Path('verified.txt').read_text(), end='')
PY
""".strip(),
    )

    print("Consumer output:")
    print(consumer_result.output)

    print("Consumer files:")
    print(consumer.list_files("**/*"))

    verified = consumer.get_file("verified.txt")
    print("Verified file:")
    print(verified)
