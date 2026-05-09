from pathlib import Path

from sbx_agents import Agent, PermissionPolicy, Runner
from sbx_agents.backends import Codex, OpenCode, Shell
from sbx_agents.sandboxes import DockerSbxSandbox

# One sandbox config, many agents. Each run uses the same workspace and branch.
# This lets agents hand off through repo state and `git diff`.
sandbox = DockerSbxSandbox(
    workspace=Path("."),
    name="multi-agent-fix",
    branch="agent/multi-agent-fix",
)

reviewer = Agent(
    name="reviewer",
    backend=OpenCode(model="anthropic/claude-sonnet-4-5"),
    instructions="Review the repo. Identify likely test failures and risks. Do not edit files.",
    permission=PermissionPolicy(default="ask", tools={"edit": "deny", "bash": "allow"}),
)

fixer = Agent(
    name="fixer",
    backend=Codex(model="gpt-5-codex"),
    instructions="Implement the smallest safe fix. Do not do unrelated cleanup.",
)

verifier = Agent(
    name="verifier",
    backend=Shell(),
    instructions="Run verification commands and report results.",
)

# Step 1: OpenCode performs a read-only review.
review = Runner.run_sync(
    reviewer,
    sandbox=sandbox,
    prompt="Review this repository and identify the smallest useful fix plan.",
)

print("Review:")
print(review.output)

# Step 2: Codex applies the fix in the same sandbox workspace/branch.
fix = Runner.run_sync(
    fixer,
    sandbox=sandbox,
    prompt=f"""
Use this review as context:

{review.output}

Implement the smallest safe fix now.
""".strip(),
)

print("Fix:")
print(fix.output)
print("Diff after fix:")
print(fix.diff)

# Step 3: Shell verifies the result in the same sandbox workspace/branch.
verify = Runner.run_sync(
    verifier,
    sandbox=sandbox,
    prompt="pytest -q",
)

print("Verification:")
print(verify.output)
print("Final diff:")
print(verify.diff)
