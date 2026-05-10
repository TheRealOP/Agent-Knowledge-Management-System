# edited by gemini
"""Provider-agnostic message schema for AKMS.

All inter-agent communication and checkpoint storage uses this format,
regardless of which LLM provider generated the message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# edited by gemini — message role enum
class Role(str, Enum):
    """Standard message roles across all providers."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# edited by gemini — message dataclass
@dataclass
class Message:
    """A single message in a provider-agnostic format."""

    role: Role
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    # edited by gemini — serialize to dict
    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    # edited by gemini — deserialize from dict
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Deserialize from a dictionary."""
        return cls(
            role=Role(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


# edited by gemini — response dataclass
@dataclass
class Response:
    """A response from an LLM provider, normalized to our schema."""

    message: Message
    provider: str = ""
    model: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    raw_response: Any = None  # edited by gemini — provider-specific raw response

    # edited by gemini — serialize to dict
    def to_dict(self) -> dict[str, Any]:
        """Serialize (excludes raw_response as it's provider-specific)."""
        return {
            "message": self.message.to_dict(),
            "provider": self.provider,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
        }


# edited by gemini — conversation dataclass
@dataclass
class Conversation:
    """An ordered list of messages forming a conversation."""

    messages: list[Message] = field(default_factory=list)
    conversation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # edited by gemini — add a message
    def add(self, message: Message) -> None:
        """Append a message to the conversation."""
        self.messages.append(message)

    # edited by gemini — fork conversation at a specific index
    def fork_at(self, index: int) -> Conversation:
        """Create a fork of this conversation up to (exclusive) the given index."""
        return Conversation(
            messages=list(self.messages[:index]),
            conversation_id=f"{self.conversation_id}_fork",
            metadata={**self.metadata, "forked_from": self.conversation_id, "fork_index": index},
        )

    # edited by gemini — serialize full conversation
    def to_dict(self) -> dict[str, Any]:
        """Serialize the full conversation."""
        return {
            "conversation_id": self.conversation_id,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }

    # edited by gemini — deserialize conversation
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Conversation:
        """Deserialize from a dictionary."""
        return cls(
            conversation_id=data.get("conversation_id", ""),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            metadata=data.get("metadata", {}),
        )
