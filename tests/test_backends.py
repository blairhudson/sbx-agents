from sbx_agents.backends import Codex, CodexAuth, OpenCode, Shell


def test_shell_command() -> None:
    assert Shell().command("python --version") == ["sh", "-lc", "python --version"]


def test_codex_command() -> None:
    assert Codex().command("fix tests") == ["codex", "exec", "fix tests"]


def test_codex_auth_helpers() -> None:
    assert CodexAuth.openai_oauth().method == "openai_oauth"
    assert CodexAuth.openai_oauth(refresh=True).refresh is True
    assert CodexAuth.openai_api_key_env("OPENAI_TOKEN").env_var == "OPENAI_TOKEN"
    assert CodexAuth.host_chatgpt().method == "host_chatgpt"


def test_codex_accepts_string_auth() -> None:
    backend = Codex(auth="openai_oauth")

    assert isinstance(backend.auth, CodexAuth)
    assert backend.auth.method == "openai_oauth"


def test_opencode_command() -> None:
    assert OpenCode().command("review") == ["opencode", "run", "review"]
