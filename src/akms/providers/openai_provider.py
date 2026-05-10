# edited by gemini
"""OpenAI provider adapter (also works for DeepSeek via base_url)."""

from __future__ import annotations

from typing import Any, Iterator

import openai

from akms.core.message import Message, Response, Role
from akms.providers.base import LLMProvider


# edited by gemini — OpenAI provider implementation
class OpenAIProvider(LLMProvider):
    """OpenAI (and OpenAI-compatible) adapter."""

    provider_name = "openai"  # edited by gemini

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        models: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        # edited by gemini — initialize OpenAI client
        client_kwargs: dict[str, Any] = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**client_kwargs)
        self._models = models or ["gpt-4o"]
        self._default_model = self._models[0]

    # edited by gemini — convert messages to OpenAI format
    def _to_provider_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert to OpenAI chat format."""
        return [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]

    # edited by gemini — convert OpenAI response to our schema
    def _from_provider_response(self, raw: Any, model: str) -> Response:
        choice = raw.choices[0]
        content = choice.message.content or ""
        tokens = raw.usage.total_tokens if raw.usage else 0
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
        """Send messages to OpenAI and return a response."""
        model = model or self._default_model
        raw = self._client.chat.completions.create(
            model=model,
            messages=self._to_provider_format(messages),
            **{k: v for k, v in kwargs.items() if k != "model"},
        )
        return self._from_provider_response(raw, model)

    # edited by gemini — streaming
    def stream(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Response]:
        """Stream responses from OpenAI."""
        model = model or self._default_model
        stream = self._client.chat.completions.create(
            model=model,
            messages=self._to_provider_format(messages),
            stream=True,
            **{k: v for k, v in kwargs.items() if k != "model"},
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield Response(
                    message=Message(
                        role=Role.ASSISTANT,
                        content=chunk.choices[0].delta.content,
                    ),
                    provider=self.provider_name,
                    model=model,
                )

    # edited by gemini — token counting (rough estimate)
    def count_tokens(self, messages: list[Message]) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        total_chars = sum(len(m.content) for m in messages)
        return total_chars // 4
