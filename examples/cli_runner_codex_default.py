from pathlib import Path

from sbx_agents import Agent, RunConfig, Runner
from sbx_agents.backends import Codex
from sbx_agents.sandboxes import DockerSbxSandbox

# CLI runner for Docker SBX + Codex defaults.
#
# This does not set a model. Codex chooses its default model. It does set the
# provider to OpenAI so stale project .codex/config.toml from other examples cannot
# accidentally point this run at a local provider.
# Codex declares OpenAI OAuth auth; Docker SBX implements it with its global
# OpenAI OAuth secret.
#
# One-time setup:
#   sbx login
#   sbxa doctor --require docker-sbx
#
# Run:
#   sbxa run examples.cli_runner_codex_default:runner
runner = Runner(
    Agent(
        name="codex-default-fixer",
        backend=Codex(model_provider="openai", auth="openai_oauth"),
        instructions="Fix failing tests with the smallest safe diff. Run tests before finishing.",
    ),
    sandbox=DockerSbxSandbox(
        workspace=Path("."),
        name="codex-default-fixer",
        branch="agent/codex-default-fixer",
    ),
    default_prompt="Fix the failing pytest suite.",
    run_config=RunConfig(json_events=True),
)
