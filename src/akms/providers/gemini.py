from __future__ import annotations

"""Gemini provider adapter using the google-genai SDK."""

from typing import Any, Iterator

from akms.core.message import Message, Response, Role
from akms.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini adapter via the google-genai SDK."""

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._models = models or ["gemini-2.5-pro"]
        self._default_model = self._models[0]

    def _to_provider_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert provider-agnostic messages to Gemini contents format.

        Gemini uses "model" instead of "assistant" for role.
        System messages are prepended as a user turn with "System: " prefix.
        """
        contents: list[dict[str, Any]] = []
        for m in messages:
            if m.role == Role.SYSTEM:
                contents.append({"role": "user", "parts": [{"text": f"System: {m.content}"}]})
            elif m.role == Role.ASSISTANT:
                contents.append({"role": "model", "parts": [{"text": m.content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": m.content}]})
        return contents

    def _from_provider_response(self, raw: Any, model: str) -> Response:
        """Convert Gemini response to our Response schema."""
        try:
            content = raw.text or ""
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
        """Send messages to Gemini and return a response."""
        model = model or self._default_model
        contents = self._to_provider_format(messages)
        raw = self._client.models.generate_content(model=model, contents=contents, **kwargs)
        return self._from_provider_response(raw, model)

    def stream(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Response]:
        """Stream responses from Gemini."""
        model = model or self._default_model
        contents = self._to_provider_format(messages)
        for chunk in self._client.models.generate_content_stream(
            model=model, contents=contents, **kwargs
        ):
            try:
                text = chunk.text or ""
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
