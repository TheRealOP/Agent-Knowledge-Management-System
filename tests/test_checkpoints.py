from __future__ import annotations

import pytest

from akms.checkpoints.store import CheckpointStore
from akms.checkpoints.fork import fork_from_checkpoint, discard_fork, restore_home_state
from akms.core.message import Message, Role


def _make_store(tmp_dir):
    db_path = str(tmp_dir / "cp.db")
    store = CheckpointStore(db_path)
    store.init_db()
    return store


def _make_messages(n=2):
    return [Message(role=Role.USER, content=f"msg {i}") for i in range(n)]


def test_save_returns_int(tmp_dir):
    """save() returns int checkpoint id."""
    store = _make_store(tmp_dir)
    cid = store.save("planner", "agent-1", "checkpoint-1", _make_messages())
    assert isinstance(cid, int)


def test_load_returns_messages(tmp_dir):
    """load(checkpoint_id) returns list of Message objects matching original."""
    store = _make_store(tmp_dir)
    messages = _make_messages(3)
    cid = store.save("planner", "agent-1", "cp1", messages)

    loaded = store.load(cid)
    assert len(loaded) == 3
    for orig, restored in zip(messages, loaded):
        assert isinstance(restored, Message)
        assert restored.role == orig.role
        assert restored.content == orig.content


def test_get_home_state_id_none_when_not_set(tmp_dir):
    """get_home_state_id returns None when no home state set."""
    store = _make_store(tmp_dir)
    result = store.get_home_state_id("agent-1")
    assert result is None


def test_save_home_state_then_get_id(tmp_dir):
    """save(..., is_home_state=True) then get_home_state_id returns that id."""
    store = _make_store(tmp_dir)
    cid = store.save("planner", "agent-1", "home", _make_messages(), is_home_state=True)
    home_id = store.get_home_state_id("agent-1")
    assert home_id == cid


def test_list_checkpoints_has_is_home_state_bool(tmp_dir):
    """list_checkpoints returns list of dicts with is_home_state bool."""
    store = _make_store(tmp_dir)
    store.save("planner", "agent-1", "cp1", _make_messages(), is_home_state=False)
    store.save("planner", "agent-1", "cp2", _make_messages(), is_home_state=True)

    checkpoints = store.list_checkpoints("agent-1")
    assert len(checkpoints) == 2
    assert isinstance(checkpoints[0]["is_home_state"], bool)
    assert checkpoints[0]["is_home_state"] is False
    assert checkpoints[1]["is_home_state"] is True


def test_fork_from_checkpoint_returns_int(tmp_dir):
    """fork_from_checkpoint returns fork_id (int)."""
    store = _make_store(tmp_dir)
    cid = store.save("planner", "agent-1", "cp1", _make_messages())
    extra = [Message(role=Role.ASSISTANT, content="extra")]
    fork_id = fork_from_checkpoint(store, cid, extra_messages=extra)
    assert isinstance(fork_id, int)


def test_discard_fork_does_not_raise(tmp_dir):
    """discard_fork does not raise."""
    store = _make_store(tmp_dir)
    cid = store.save("planner", "agent-1", "cp1", _make_messages())
    fork_id = fork_from_checkpoint(store, cid)
    # Should not raise
    discard_fork(store, fork_id)


def test_restore_home_state_returns_messages(tmp_dir):
    """restore_home_state returns messages from home-state checkpoint."""
    store = _make_store(tmp_dir)
    messages = _make_messages(2)
    store.save("planner", "agent-1", "home", messages, is_home_state=True)

    restored = restore_home_state(store, "agent-1")
    assert len(restored) == 2
    assert restored[0].content == messages[0].content
    assert restored[1].content == messages[1].content


def test_restore_home_state_nonexistent_returns_empty(tmp_dir):
    """restore_home_state for nonexistent agent returns []."""
    store = _make_store(tmp_dir)
    result = restore_home_state(store, "nonexistent-agent")
    assert result == []
