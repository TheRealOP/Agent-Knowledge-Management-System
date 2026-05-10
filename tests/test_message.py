from __future__ import annotations

import pytest

from akms.core.message import Message, Conversation, Role


def test_message_to_dict_has_required_keys():
    """Message.to_dict() has keys: role, content, timestamp, metadata."""
    msg = Message(role=Role.USER, content="hi")
    d = msg.to_dict()
    assert "role" in d
    assert "content" in d
    assert "timestamp" in d
    assert "metadata" in d


def test_message_round_trip():
    """Message.from_dict(msg.to_dict()) round-trips role and content."""
    msg = Message(role=Role.USER, content="hello world")
    restored = Message.from_dict(msg.to_dict())
    assert restored.role == Role.USER
    assert restored.content == "hello world"


def test_role_values():
    """Role enum values are correct strings."""
    assert Role.USER.value == "user"
    assert Role.ASSISTANT.value == "assistant"


def test_conversation_fork_at_middle():
    """Conversation.fork_at(2) on a 4-message conversation has exactly 2 messages."""
    conv = Conversation(conversation_id="test-conv")
    for i in range(4):
        conv.add(Message(role=Role.USER, content=f"msg {i}"))

    fork = conv.fork_at(2)
    assert len(fork.messages) == 2
    assert fork.messages[0].content == "msg 0"
    assert fork.messages[1].content == "msg 1"


def test_conversation_fork_at_zero():
    """Conversation.fork_at(0) returns empty messages list."""
    conv = Conversation(conversation_id="test-conv")
    for i in range(3):
        conv.add(Message(role=Role.USER, content=f"msg {i}"))

    fork = conv.fork_at(0)
    assert fork.messages == []


def test_conversation_round_trip():
    """Conversation.to_dict() / from_dict() round-trips conversation_id and all messages."""
    conv = Conversation(conversation_id="my-convo")
    conv.add(Message(role=Role.USER, content="first"))
    conv.add(Message(role=Role.ASSISTANT, content="second"))

    d = conv.to_dict()
    restored = Conversation.from_dict(d)

    assert restored.conversation_id == "my-convo"
    assert len(restored.messages) == 2
    assert restored.messages[0].content == "first"
    assert restored.messages[0].role == Role.USER
    assert restored.messages[1].content == "second"
    assert restored.messages[1].role == Role.ASSISTANT
