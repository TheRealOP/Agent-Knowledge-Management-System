from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from akms.core.message import Message, Response, Role

if TYPE_CHECKING:
    from akms.config import AKMSConfig
    from akms.logging.conversation_log import ConversationLogger
    from akms.providers.base import LLMProvider


class BaseAgent(ABC):
    """Abstract base for all AKMS agents."""

    agent_type: str = "base"

    def __init__(
        self,
        provider: LLMProvider,
        model: str,
        config: AKMSConfig,
        logger: ConversationLogger | None = None,
        session_id: str | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._config = config
        self._logger = logger
        self._session_id = session_id or uuid.uuid4().hex
        self._history: list[Message] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def conversation_history(self) -> list[Message]:
        return list(self._history)

    def send(self, messages: list[Message], **kwargs: Any) -> Response:
        """Send messages to the provider, log exchange, update history."""
        response = self._provider.chat(messages, model=self._model, **kwargs)
        for msg in messages:
            self._history.append(msg)
            if self._logger:
                self._logger.log_message(self.agent_type, self._session_id, msg)
        self._history.append(response.message)
        if self._logger:
            self._logger.log_message(self.agent_type, self._session_id, response.message)
        return response

    def ask(self, prompt: str, system: str | None = None, **kwargs: Any) -> Response:
        """Shortcut: send a single user message, optionally with a system prompt."""
        messages: list[Message] = []
        if system:
            messages.append(Message(role=Role.SYSTEM, content=system))
        messages.append(Message(role=Role.USER, content=prompt))
        return self.send(messages, **kwargs)

    def reset(self) -> None:
        """Clear conversation history and start a new session."""
        self._history = []
        self._session_id = uuid.uuid4().hex
