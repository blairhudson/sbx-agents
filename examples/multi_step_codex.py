from pathlib import Path

from sbx_agents import Agent, RunConfig, Runner
from sbx_agents.backends import Codex
from sbx_agents.sandboxes import DockerSbxSandbox

agent = Agent(
    name="fix-tests",
    backend=Codex(model="gpt-5-codex"),
    instructions=(
        "You are a careful coding agent. Use the smallest safe diff. "
        "Run relevant tests before finishing."
    ),
)

sandbox = DockerSbxSandbox(
    workspace=Path("."),
    name="fix-tests",
    branch="agent/fix-tests",
)

# Step 1: inspect only. JSON events are opt-in; Codex may emit a thread_id.
diagnosis = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Inspect the repo and identify why tests are failing. Do not edit files yet.",
    run_config=RunConfig(json_events=True),
)

session_id = diagnosis.thread_id or diagnosis.session_id

print("Diagnosis:")
print(diagnosis.output)

# Step 2: resume the backend conversation if possible.
fix = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Now implement the smallest safe fix. Do not do unrelated cleanup.",
    run_config=RunConfig(
        json_events=True,
        resume_session_id=session_id,
    ),
)

session_id = fix.thread_id or fix.session_id or session_id

print("Fix output:")
print(fix.output)
print("Diff:")
print(fix.diff)

# Step 3: verify in the same conversation.
verify = Runner.run_sync(
    agent,
    sandbox=sandbox,
    prompt="Run the relevant test suite and report the result. Fix only if needed.",
    run_config=RunConfig(
        json_events=True,
        resume_session_id=session_id,
    ),
)

print("Verification:")
print(verify.output)
print("Final diff:")
print(verify.diff)
