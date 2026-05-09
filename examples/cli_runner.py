from pathlib import Path

from sbx_agents import Agent, Runner
from sbx_agents.backends import Codex
from sbx_agents.sandboxes import DockerSbxSandbox

# This file is meant to be loaded by the `sbxa` CLI. Importing it should not run the
# agent. `sbxa run examples/cli_runner.py` loads this object and calls `run_sync()`.
#
# Docker SBX examples require login first:
#   sbx login
#   sbxa doctor --require docker-sbx
runner = Runner(
    Agent(
        name="fix-tests",
        backend=Codex(
            model="LiquidAI/LFM2.5-1.2B-Instruct-MLX-8bit",
            model_provider="local-mlx",
            extra_config={
                "model_providers": {
                    "local-mlx": {
                        "name": "Local MLX",
                        # Inside Docker SBX, localhost is the sandbox. Use host.docker.internal
                        # for a model server running on your host at localhost:8080.
                        "base_url": "http://host.docker.internal:8080/v1",
                        # Codex requires an env_key even for local unauthenticated providers.
                        # PATH is always present and is only used to satisfy that check.
                        "env_key": "PATH",
                        "wire_api": "responses",
                    }
                }
            },
        ),
        instructions="Fix failing tests with the smallest safe diff. Run tests before finishing.",
    ),
    sandbox=DockerSbxSandbox(
        workspace=Path("."),
        name="cli-fix-tests",
        branch="agent/cli-fix-tests",
        # Docker SBX reaches the host via host.docker.internal, but policy logs may
        # report the proxied request as localhost:8080. Allow both.
        network_allow=["host.docker.internal:8080", "localhost:8080"],
    ),
    default_prompt="Fix the failing pytest suite.",
)
