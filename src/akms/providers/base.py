# edited by gemini
"""Base protocol and abstract class for LLM providers.

Every provider adapter (Claude, OpenAI, Gemini, etc.) must implement
the LLMProvider protocol so that agents can swap providers freely.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator

from akms.core.message import Conversation, Message, Response


# edited by gemini — abstract base provider
class LLMProvider(ABC):
    """Abstract base class for all LLM provider adapters."""

    provider_name: str = ""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Send messages and get a single response."""
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        model: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Response]:
        """Stream responses token-by-token."""
        ...

    @abstractmethod
    def count_tokens(self, messages: list[Message]) -> int:
        """Estimate token count for a list of messages."""
        ...

    # edited by gemini — convenience method for single-turn
    def ask(self, prompt: str, model: str | None = None, **kwargs: Any) -> Response:
        """Shortcut: send a single user prompt and get a response."""
        from akms.core.message import Role  # edited by gemini

        msg = Message(role=Role.USER, content=prompt)
        return self.chat([msg], model=model, **kwargs)

    # edited by gemini — convert our messages to provider format
    @abstractmethod
    def _to_provider_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert provider-agnostic messages to provider-specific format."""
        ...

    # edited by gemini — convert provider response to our format
    @abstractmethod
    def _from_provider_response(self, raw: Any, model: str) -> Response:
        """Convert provider-specific response to our Response schema."""
        ...
