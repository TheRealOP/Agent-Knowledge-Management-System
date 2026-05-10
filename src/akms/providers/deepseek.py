from __future__ import annotations

"""DeepSeek provider adapter — thin subclass of OpenAIProvider."""

from typing import Any

from akms.providers.openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek adapter (OpenAI-compatible API)."""

    provider_name = "deepseek"
    _DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=self._DEEPSEEK_BASE_URL,
            models=models or ["deepseek-chat"],
            **kwargs,
        )
