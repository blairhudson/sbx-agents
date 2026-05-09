from __future__ import annotations

import subprocess
import sys
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from time import perf_counter, sleep
from typing import Literal, TextIO

from sbx_agents.result import CommandResult

StreamFilter = Callable[[str, Literal["stdout", "stderr"]], str | None]


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    timeout: int | None = None,
    stream: bool = False,
    stream_filter: StreamFilter | None = None,
) -> CommandResult:
    started = perf_counter()
    if stream:
        return _run_command_streamed(
            command,
            cwd=cwd,
            env=env,
            timeout=timeout,
            stream_filter=stream_filter,
            started=started,
        )

    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=input_text,
        timeout=timeout,
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
        command=command,
        duration_ms=int((perf_counter() - started) * 1000),
    )


def _run_command_streamed(
    command: list[str],
    *,
    cwd: Path | None,
    env: Mapping[str, str] | None,
    timeout: int | None,
    stream_filter: StreamFilter | None,
    started: float,
) -> CommandResult:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    stdout_thread = threading.Thread(
        target=_stream_pipe,
        args=(process.stdout, sys.stdout, stdout_chunks, "stdout", stream_filter),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_pipe,
        args=(process.stderr, sys.stderr, stderr_chunks, "stderr", stream_filter),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    heartbeat_seconds = 30
    last_activity = perf_counter()
    last_stdout_len = 0
    last_stderr_len = 0
    try:
        while True:
            returncode = process.poll()
            if returncode is not None:
                break
            now = perf_counter()
            if len(stdout_chunks) != last_stdout_len or len(stderr_chunks) != last_stderr_len:
                last_stdout_len = len(stdout_chunks)
                last_stderr_len = len(stderr_chunks)
                last_activity = now
            elif now - last_activity >= heartbeat_seconds:
                sys.stderr.write("Still running; waiting for sandbox output...\n")
                sys.stderr.flush()
                last_activity = now
            if timeout is not None and now - started >= timeout:
                raise subprocess.TimeoutExpired(command, timeout)
            sleep(1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
    finally:
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

    return CommandResult(
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
        returncode=returncode,
        command=command,
        duration_ms=int((perf_counter() - started) * 1000),
    )


def _stream_pipe(
    pipe: TextIO | None,
    target: TextIO,
    chunks: list[str],
    source: Literal["stdout", "stderr"],
    stream_filter: StreamFilter | None,
) -> None:
    if pipe is None:
        return
    for line in pipe:
        chunks.append(line)
        output = stream_filter(line, source) if stream_filter is not None else line
        if output is None:
            continue
        target.write(output)
        if output and not output.endswith("\n"):
            target.write("\n")
        target.flush()


def collect_git_diff(workspace: Path) -> str | None:
    result = run_command(["git", "-C", str(workspace), "diff", "--no-ext-diff"])
    if result.returncode != 0:
        return None
    return result.stdout
