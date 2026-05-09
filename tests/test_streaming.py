from sbx_agents.streaming import PrettyStreamFilter


def test_pretty_stream_filter_formats_codex_agent_message() -> None:
    stream_filter = PrettyStreamFilter(backend_id="codex")

    assert stream_filter(
        '{"type":"item.completed","item":{"type":"agent_message","text":"hello"}}\n',
        "stdout",
    ) == "agent:\n  hello"


def test_pretty_stream_filter_formats_codex_command_failure() -> None:
    stream_filter = PrettyStreamFilter(backend_id="codex")

    assert stream_filter(
        '{"type":"item.started","item":{"type":"command_execution","command":"pytest -q"}}\n',
        "stdout",
    ) == "cmd: pytest -q"
    assert stream_filter(
        "{"
        '"type":"item.completed",'
        '"item":{"type":"command_execution","command":"pytest -q",'
        '"aggregated_output":"pytest: command not found\\n",'
        '"exit_code":127,"status":"failed"}'
        "}\n",
        "stdout",
    ) == "fail: pytest -q (exit 127)\n  pytest: command not found"


def test_pretty_stream_filter_hides_sbx_noise() -> None:
    stream_filter = PrettyStreamFilter(backend_id="codex")

    assert stream_filter("143758b7c085: Already exists\n", "stderr") is None
    assert stream_filter("INFO: Starting Docker daemon\n", "stderr") is None
