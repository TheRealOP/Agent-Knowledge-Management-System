# edited by gemini
"""Claude (Anthropic) provider adapter."""

from __future__ import annotations

from typing import Any, Iterator

import anthropic

from akms.core.message import Message, Response, Role
from akms.providers.base import LLMProvider


# edited by gemini — Claude provider implementation
class ClaudeProvider(LLMProvider):
    """Anthropic Claude adapter."""

    provider_name = "claude"  # edited by gemini

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        # edited by gemini — initialize Anthropic client
        self._client = anthropic.Anthropic(api_key=api_key)
        self._models = models or ["claude-sonnet-4"]
        self._default_model = self._models[0]

    # edited by gemini — convert messages to Anthropic format
    def _to_provider_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert to Anthropic messages format (system handled separately)."""
        return [
            {"role": m.role.value, "content": m.content}
            for m in messages
            if m.role != Role.SYSTEM
        ]

    # edited by gemini — extract system prompt
    def _get_system_prompt(self, messages: list[Message]) -> str:
        """Extract system message content (Anthropic handles it separately)."""
        system_msgs = [m for m in messages if m.role == Role.SYSTEM]
        return "\n".join(m.content for m in system_msgs) if system_msgs else ""

    # edited by gemini — convert Anthropic response to our schema
    def _from_provider_response(self, raw: Any, model: str) -> Response:
        content = raw.content[0].text if raw.content else ""
        tokens = (raw.usage.input_tokens or 0) + (raw.usage.output_tokens or 0)
        return Response(
            message=Message(role=Role.ASSISTANT, content=content),
            provider=self.provider_name,
            model=model,
            tokens_used=tokens,
            raw_response=raw,
        )

    # edited by gemini — main chat method
    def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Send messages to Claude and return a response."""
        model = model or self._default_model
        system = self._get_system_prompt(messages)
        api_msgs = self._to_provider_format(messages)

        api_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if system:
            api_kwargs["system"] = system

        raw = self._client.messages.create(**api_kwargs)
        return self._from_provider_response(raw, model)

    # edited by gemini — streaming (yields partial responses)
    def stream(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Response]:
        """Stream responses from Claude."""
        model = model or self._default_model
        system = self._get_system_prompt(messages)
        api_msgs = self._to_provider_format(messages)

        api_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if system:
            api_kwargs["system"] = system

        with self._client.messages.stream(**api_kwargs) as stream:
            for text in stream.text_stream:
                yield Response(
                    message=Message(role=Role.ASSISTANT, content=text),
                    provider=self.provider_name,
                    model=model,
                )

    # edited by gemini — token counting
    def count_tokens(self, messages: list[Message]) -> int:
        """Estimate token count using Anthropic's counter."""
        try:
            result = self._client.messages.count_tokens(
                model=self._default_model,
                messages=self._to_provider_format(messages),
            )
            return result.input_tokens
        except Exception:
            # edited by gemini — rough fallback estimate
            total_chars = sum(len(m.content) for m in messages)
            return total_chars // 4
