"""Tests for CLISubprocessProvider."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from akms.core.message import Message, Role
from akms.providers.cli_subprocess import CLISubprocessProvider
from akms.providers.registry import build_default_registry


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def provider():
    return CLISubprocessProvider(
        cli_binary="claude",
        models=["claude-opus-4-6"],
    )


def _make_completed_process(stdout: str, returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    cp = MagicMock(spec=subprocess.CompletedProcess)
    cp.stdout = stdout
    cp.returncode = returncode
    cp.stderr = stderr
    return cp


# ── _flatten_messages ──────────────────────────────────────────────────────────

def test_flatten_system_only(provider):
    msgs = [Message(role=Role.SYSTEM, content="Be helpful.")]
    assert provider._flatten_messages(msgs) == "Be helpful."


def test_flatten_user_only(provider):
    msgs = [Message(role=Role.USER, content="Hello")]
    assert provider._flatten_messages(msgs) == "Human: Hello"


def test_flatten_mixed(provider):
    msgs = [
        Message(role=Role.SYSTEM, content="Context."),
        Message(role=Role.USER, content="Question?"),
        Message(role=Role.ASSISTANT, content="Answer."),
        Message(role=Role.USER, content="Follow-up?"),
    ]
    result = provider._flatten_messages(msgs)
    assert result == "Context.\n\nHuman: Question?\n\nAssistant: Answer.\n\nHuman: Follow-up?"


# ── _build_argv ────────────────────────────────────────────────────────────────

def test_build_argv_default(provider):
    argv = provider._build_argv("claude-opus-4-6", "my prompt")
    assert argv == ["claude", "-p", "--model", "claude-opus-4-6", "my prompt"]


def test_build_argv_no_model_flag():
    p = CLISubprocessProvider(cli_binary="codex", print_flag="exec", model_flag=None)
    argv = p._build_argv("gpt-5-codex", "my prompt")
    assert argv == ["codex", "exec", "my prompt"]


def test_build_argv_extra_args():
    p = CLISubprocessProvider(
        cli_binary="claude",
        extra_args=["--output-format", "text"],
    )
    argv = p._build_argv(None, "prompt")
    assert "--output-format" in argv
    assert "text" in argv
    assert argv[-1] == "prompt"


def test_build_argv_no_print_flag():
    p = CLISubprocessProvider(cli_binary="mycli", print_flag="")
    argv = p._build_argv(None, "prompt")
    assert argv == ["mycli", "prompt"]


# ── chat ──────────────────────────────────────────────────────────────────────

def test_chat_returns_response(provider):
    with patch("subprocess.run", return_value=_make_completed_process("Hello from Claude")):
        resp = provider.chat([Message(role=Role.USER, content="hi")])
    assert resp.message.content == "Hello from Claude"
    assert resp.provider == "cli_subprocess"
    assert resp.model == "claude-opus-4-6"


def test_chat_uses_override_model(provider):
    captured = {}
    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        return _make_completed_process("ok")

    with patch("subprocess.run", side_effect=fake_run):
        provider.chat([Message(role=Role.USER, content="hi")], model="claude-sonnet-4-6")

    assert "--model" in captured["argv"]
    assert "claude-sonnet-4-6" in captured["argv"]


def test_chat_raises_on_missing_binary(provider):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="not found on PATH"):
            provider.chat([Message(role=Role.USER, content="hi")])


def test_chat_raises_on_timeout(provider):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=300)):
        with pytest.raises(RuntimeError, match="timed out"):
            provider.chat([Message(role=Role.USER, content="hi")])


def test_chat_raises_on_nonzero_exit(provider):
    with patch("subprocess.run", return_value=_make_completed_process("", returncode=1, stderr="auth error")):
        with pytest.raises(RuntimeError, match="auth error"):
            provider.chat([Message(role=Role.USER, content="hi")])


# ── stream ────────────────────────────────────────────────────────────────────

def test_stream_yields_lines(provider):
    lines = ["line one\n", "line two\n"]
    mock_proc = MagicMock()
    mock_proc.__enter__ = lambda s: s
    mock_proc.__exit__ = MagicMock(return_value=False)
    mock_proc.stdout = iter(lines)
    mock_proc.returncode = 0
    mock_proc.wait = MagicMock()
    mock_proc.stderr = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        results = list(provider.stream([Message(role=Role.USER, content="hi")]))

    assert len(results) == 2
    assert results[0].message.content == "line one"
    assert results[1].message.content == "line two"


# ── count_tokens ──────────────────────────────────────────────────────────────

def test_count_tokens_is_char_estimate(provider):
    msgs = [Message(role=Role.USER, content="a" * 400)]
    assert provider.count_tokens(msgs) == 100


def test_count_tokens_returns_int(provider):
    result = provider.count_tokens([Message(role=Role.USER, content="hello")])
    assert isinstance(result, int)


# ── tmux pane logging ─────────────────────────────────────────────────────────

def test_chat_writes_to_pane_log(tmp_path, provider):
    provider._tmux_pane = "test-pane"
    with (
        patch("akms.providers._tmux._LOG_DIR", tmp_path),
        patch("subprocess.run", return_value=_make_completed_process("response")),
    ):
        provider.chat([Message(role=Role.USER, content="hi")])

    log_file = tmp_path / "test-pane.log"
    assert log_file.exists()
    content = log_file.read_text()
    assert "claude-opus-4-6" in content


# ── registry ─────────────────────────────────────────────────────────────────

def test_default_registry_has_cli_providers():
    registry = build_default_registry()
    available = registry.available()
    assert "claude_cli" in available
    assert "codex_cli" in available
    assert "gemini_cli" in available


def test_registry_creates_claude_cli_instance():
    registry = build_default_registry()
    p = registry.create("claude_cli", models=["claude-opus-4-6"])
    assert isinstance(p, CLISubprocessProvider)
    assert p._cli_binary == "claude"
