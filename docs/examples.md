# Examples

Runnable examples live in `examples/`. These are product patterns, not toy demos.

Use them as starting points for CI fixers, review bots, hosted agent APIs, tenant-isolated services, and multi-agent coding workflows. Every example source is embedded below.

## First runs

| File | Shows |
| --- | --- |
| `examples/plain_docker_shell.py` | Shell backend in plain Docker |
| `examples/docker_sbx_codex.py` | Codex backend in Docker SBX |
| `examples/docker_sbx_opencode.py` | OpenCode backend in Docker SBX |
| `examples/cli_runner.py` | reusable `Runner` loaded by `sbxa` CLI |
| `examples/cli_runner_codex_default.py` | `sbxa` runner using Docker SBX Codex defaults and host-managed auth |

??? example "examples/plain_docker_shell.py"
    ```python
    --8<-- "examples/plain_docker_shell.py"
    ```

??? example "examples/docker_sbx_codex.py"
    ```python
    --8<-- "examples/docker_sbx_codex.py"
    ```

??? example "examples/docker_sbx_opencode.py"
    ```python
    --8<-- "examples/docker_sbx_opencode.py"
    ```

??? example "examples/cli_runner.py"
    ```python
    --8<-- "examples/cli_runner.py"
    ```

??? example "examples/cli_runner_codex_default.py"
    ```python
    --8<-- "examples/cli_runner_codex_default.py"
    ```

## Composition

| File | Shows |
| --- | --- |
| `examples/multi_step_codex.py` | diagnose -> fix -> verify with backend-native resume |
| `examples/multi_step_app_managed.py` | app-managed context between turns |
| `examples/multi_agent_same_sandbox.py` | reviewer, fixer, and verifier share one sandbox |
| `examples/one_agent_multiple_sandboxes_copy_files.py` | same agent across sandboxes with explicit file transfer |

??? example "examples/multi_step_codex.py"
    ```python
    --8<-- "examples/multi_step_codex.py"
    ```

??? example "examples/multi_step_app_managed.py"
    ```python
    --8<-- "examples/multi_step_app_managed.py"
    ```

??? example "examples/multi_agent_same_sandbox.py"
    ```python
    --8<-- "examples/multi_agent_same_sandbox.py"
    ```

??? example "examples/one_agent_multiple_sandboxes_copy_files.py"
    ```python
    --8<-- "examples/one_agent_multiple_sandboxes_copy_files.py"
    ```

## Agent config

| File | Shows |
| --- | --- |
| `examples/docker_sbx_codex_with_mcp_and_skill.py` | Codex with skill and stdio MCP |
| `examples/docker_sbx_opencode_with_http_mcp_and_skill.py` | OpenCode with skill and HTTP MCP |
| `examples/complex_codex_agent_config.py` | Codex reasoning, MCP, skills, permissions, JSON events, output schema |
| `examples/complex_opencode_agent_config.py` | OpenCode permissions, LSP, formatter, MCP, skills, session flags |

??? example "examples/docker_sbx_codex_with_mcp_and_skill.py"
    ```python
    --8<-- "examples/docker_sbx_codex_with_mcp_and_skill.py"
    ```

??? example "examples/docker_sbx_opencode_with_http_mcp_and_skill.py"
    ```python
    --8<-- "examples/docker_sbx_opencode_with_http_mcp_and_skill.py"
    ```

??? example "examples/complex_codex_agent_config.py"
    ```python
    --8<-- "examples/complex_codex_agent_config.py"
    ```

??? example "examples/complex_opencode_agent_config.py"
    ```python
    --8<-- "examples/complex_opencode_agent_config.py"
    ```

## Sandbox config

| File | Shows |
| --- | --- |
| `examples/complex_sandbox_setup.py` | Docker resource/env args and Docker SBX branch/resources |
| `examples/sandbox_file_management.py` | `put_file`, `get_file`, `list_files`, `delete_file` |
| `examples/plain_docker_shell_non_strict_skills.py` | skipping unsupported shell features with `strict=False` |

??? example "examples/complex_sandbox_setup.py"
    ```python
    --8<-- "examples/complex_sandbox_setup.py"
    ```

??? example "examples/sandbox_file_management.py"
    ```python
    --8<-- "examples/sandbox_file_management.py"
    ```

??? example "examples/plain_docker_shell_non_strict_skills.py"
    ```python
    --8<-- "examples/plain_docker_shell_non_strict_skills.py"
    ```

## Skills

| File | Shows |
| --- | --- |
| `examples/skills/fix-tests/SKILL.md` | portable skill with OpenCode-compatible frontmatter |
| `examples/skills/review-risk/SKILL.md` | review skill with risk-focused instructions |

??? example "examples/skills/fix-tests/SKILL.md"
    ```markdown
    --8<-- "examples/skills/fix-tests/SKILL.md"
    ```

??? example "examples/skills/review-risk/SKILL.md"
    ```markdown
    --8<-- "examples/skills/review-risk/SKILL.md"
    ```

## Services and CI

| File | Shows |
| --- | --- |
| `examples/fastapi_agent_service.py` | minimal FastAPI API for runs and file endpoints |
| `examples/fastapi_multi_tenant_isolation.py` | tenant-scoped workspaces, jobs, files, and sandbox names |
| `examples/github_actions_fix_tests.py` | GitHub Actions script entrypoint |
| `examples/github-actions/fix-tests.yml` | workflow template that runs the SDK and opens a PR |
| `examples/precommit_runner.py` | import-safe Runner for Git pre-commit hooks |
| `examples/git-hooks/pre-commit` | Git pre-commit hook template that calls `sbxa` |

??? example "examples/fastapi_agent_service.py"
    ```python
    --8<-- "examples/fastapi_agent_service.py"
    ```

??? example "examples/fastapi_multi_tenant_isolation.py"
    ```python
    --8<-- "examples/fastapi_multi_tenant_isolation.py"
    ```

??? example "examples/github_actions_fix_tests.py"
    ```python
    --8<-- "examples/github_actions_fix_tests.py"
    ```

??? example "examples/github-actions/fix-tests.yml"
    ```yaml
    --8<-- "examples/github-actions/fix-tests.yml"
    ```

??? example "examples/precommit_runner.py"
    ```python
    --8<-- "examples/precommit_runner.py"
    ```

??? example "examples/git-hooks/pre-commit"
    ```sh
    --8<-- "examples/git-hooks/pre-commit"
    ```

## How to run examples

Most examples are scripts:

```console
$ uv add sbx-agents
$ uv run python examples/plain_docker_shell.py
```

The CLI runner example is import-safe and runs through `sbxa`:

```console
$ sbx login
$ sbxa doctor --require docker-sbx
$ sbxa run examples/cli_runner.py
$ sbxa run examples/cli_runner.py "Only fix lint failures."
```

Use Codex defaults and Docker SBX OAuth auth:

```console
$ sbxa run examples.cli_runner_codex_default:runner
```

The runner declares auth on the Codex backend. Docker SBX adds required OpenAI network policy automatically:

```python
backend=Codex(model_provider="openai", auth="openai_oauth")
```

FastAPI examples require FastAPI and Uvicorn:

```console
$ uv add sbx-agents fastapi uvicorn
$ uv run uvicorn examples.fastapi_agent_service:app --reload
```

Docker SBX examples require `sbx` and agent credentials.

Install the pre-commit hook example:

```console
$ cp examples/git-hooks/pre-commit .git/hooks/pre-commit
$ chmod +x .git/hooks/pre-commit
```

## Next steps

- [Get started](get-started.md) — run the first example.
- [Customize](customize.md) — understand complex config examples.
- [FastAPI services](services.md) — build service integrations.
