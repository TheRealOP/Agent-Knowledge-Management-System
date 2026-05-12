"""CLI-subprocess LLM provider for AKMS.

Wraps any CLI binary that supports a one-shot/print mode (e.g. ``claude -p``,
``codex exec``) so that AKMS agents can use subscription-authenticated CLIs
without requiring a separate API key.

Observability: set ``tmux_pane: <name>`` in the provider config block, then
run ``tail -f ~/.akms/panes/<name>.log`` in a terminal or tmux pane to watch
the agent's prompts and responses in real time.

Example config (akms_config.yaml)::

    providers:
      claude_cli:
        models: [claude-opus-4-6]
        tmux_pane: akms-expert

    agent_assignments:
      expert:
        provider: claude_cli
        model: claude-opus-4-6
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Iterator

from akms.core.message import Message, Response, Role
from akms.providers import _tmux
from akms.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class CLISubprocessProvider(LLMProvider):
    """LLM provider that delegates to a local CLI binary in one-shot mode.

    Each ``chat()`` call spawns a fresh subprocess, captures stdout as the
    completion, and returns. No persistent session state is kept, so
    Expert fork/rollback works without any special handling.
    """

    provider_name = "cli_subprocess"

    def __init__(
        self,
        cli_binary: str,
        print_flag: str = "-p",
        model_flag: str | None = "--model",
        extra_args: list[str] | None = None,
        models: list[str] | None = None,
        tmux_pane: str | None = None,
        timeout_s: int = 300,
        **kwargs: Any,  # absorb api_key / base_url passed by create_from_config
    ) -> None:
        self._cli_binary = cli_binary
        self._print_flag = print_flag
        self._model_flag = model_flag
        self._extra_args = list(extra_args or [])
        self._models = list(models or [])
        self._default_model: str | None = self._models[0] if self._models else None
        self._tmux_pane = tmux_pane
        self._timeout_s = timeout_s

    # ── LLMProvider ABC ───────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Spawn the CLI in one-shot mode and return the full completion."""
        effective_model = model or self._default_model
        prompt = self._flatten_messages(messages)
        argv = self._build_argv(effective_model, prompt)

        if self._tmux_pane:
            _tmux.write_to_pane(
                self._tmux_pane,
                f">>> [{effective_model}]\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}",
            )

        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"CLI binary '{self._cli_binary}' not found on PATH. "
                "Install it and authenticate before using this provider."
            ) from None
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"'{self._cli_binary}' timed out after {self._timeout_s}s."
            ) from None

        if result.returncode != 0:
            err = result.stderr.strip()
            raise RuntimeError(
                f"'{self._cli_binary}' exited {result.returncode}"
                + (f": {err}" if err else "")
            )

        completion = result.stdout.strip()

        if self._tmux_pane:
            _tmux.write_to_pane(
                self._tmux_pane,
                f"<<< [{effective_model}]\n{completion[:500]}{'...' if len(completion) > 500 else ''}",
            )

        return self._from_provider_response(completion, effective_model or "")

    def stream(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Response]:
        """Stream output line-by-line from the CLI subprocess."""
        effective_model = model or self._default_model
        prompt = self._flatten_messages(messages)
        argv = self._build_argv(effective_model, prompt)

        if self._tmux_pane:
            _tmux.write_to_pane(
                self._tmux_pane,
                f">>> [{effective_model}] (stream)\n{prompt[:200]}",
            )

        try:
            with subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as proc:
                assert proc.stdout is not None
                for line in proc.stdout:
                    yield self._from_provider_response(line.rstrip("\n"), effective_model or "")
                proc.wait(timeout=self._timeout_s)
                if proc.returncode != 0:
                    assert proc.stderr is not None
                    err = proc.stderr.read().strip()
                    raise RuntimeError(
                        f"'{self._cli_binary}' exited {proc.returncode}"
                        + (f": {err}" if err else "")
                    )
        except FileNotFoundError:
            raise RuntimeError(
                f"CLI binary '{self._cli_binary}' not found on PATH."
            ) from None

    def count_tokens(self, messages: list[Message]) -> int:
        """Character-based token estimate (CLIs don't expose a token count API)."""
        return sum(len(m.content) for m in messages) // 4

    def _to_provider_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    def _from_provider_response(self, raw: Any, model: str) -> Response:
        text = str(raw)
        return Response(
            message=Message(role=Role.ASSISTANT, content=text),
            provider=self.provider_name,
            model=model,
            tokens_used=len(text) // 4,
        )

    # ── Internals ─────────────────────────────────────────────────────────────

    def _flatten_messages(self, messages: list[Message]) -> str:
        """Flatten message list to a single prompt string for CLI consumption."""
        parts: list[str] = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                parts.append(msg.content)
            elif msg.role == Role.USER:
                parts.append(f"Human: {msg.content}")
            elif msg.role == Role.ASSISTANT:
                parts.append(f"Assistant: {msg.content}")
        return "\n\n".join(parts)

    def _build_argv(self, model: str | None, prompt: str) -> list[str]:
        """Build the subprocess argv for a one-shot CLI call."""
        argv = [self._cli_binary]
        if model and self._model_flag:
            argv.extend([self._model_flag, model])
        argv.extend(self._extra_args)
        if self._print_flag:
            argv.append(self._print_flag)
        argv.append(prompt)
        return argv
