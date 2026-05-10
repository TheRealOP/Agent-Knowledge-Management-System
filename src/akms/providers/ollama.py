from __future__ import annotations

"""Ollama provider adapter using the ollama Python package."""

from typing import Any, Iterator

from akms.core.message import Message, Response, Role
from akms.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local model adapter."""

    provider_name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        models: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        import ollama as _ollama

        self._ollama = _ollama
        self._models = models or ["llama3"]
        self._default_model = self._models[0]
        if base_url:
            self._client = _ollama.Client(host=base_url)
        else:
            self._client = _ollama.Client()

    def _to_provider_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert provider-agnostic messages to ollama chat format."""
        role_map = {
            Role.SYSTEM: "system",
            Role.USER: "user",
            Role.ASSISTANT: "assistant",
            Role.TOOL: "tool",
        }
        return [
            {"role": role_map.get(m.role, "user"), "content": m.content}
            for m in messages
        ]

    def _from_provider_response(self, raw: Any, model: str) -> Response:
        """Convert ollama response to our Response schema."""
        try:
            content = raw.message.content or ""
        except Exception:
            content = ""
        return Response(
            message=Message(role=Role.ASSISTANT, content=content),
            provider=self.provider_name,
            model=model,
            tokens_used=0,
            raw_response=raw,
        )

    def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Send messages to Ollama and return a response."""
        model = model or self._default_model
        raw = self._client.chat(
            model=model,
            messages=self._to_provider_format(messages),
            **kwargs,
        )
        return self._from_provider_response(raw, model)

    def stream(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Response]:
        """Stream responses from Ollama."""
        model = model or self._default_model
        for chunk in self._client.chat(
            model=model,
            messages=self._to_provider_format(messages),
            stream=True,
            **kwargs,
        ):
            try:
                text = chunk.message.content or ""
            except Exception:
                text = ""
            if text:
                yield Response(
                    message=Message(role=Role.ASSISTANT, content=text),
                    provider=self.provider_name,
                    model=model,
                )

    def count_tokens(self, messages: list[Message]) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        return sum(len(m.content) for m in messages) // 4
