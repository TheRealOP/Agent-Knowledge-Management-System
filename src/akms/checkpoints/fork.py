from __future__ import annotations

"""Fork and rollback helpers for checkpoint-based conversation branching."""

import datetime
import json
import sqlite3

from akms.checkpoints.store import CheckpointStore
from akms.core.message import Message


def fork_from_checkpoint(
    store: CheckpointStore,
    checkpoint_id: int,
    extra_messages: list | None = None,
) -> int:
    """Load checkpoint messages, optionally append extra_messages, insert as an active fork.

    Returns the new fork_id.
    """
    messages = store.load(checkpoint_id)
    if extra_messages:
        messages = messages + list(extra_messages)
    fork_messages_json = json.dumps([m.to_dict() for m in messages])
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with sqlite3.connect(store._db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO forks (checkpoint_id, fork_messages_json, created_at, status)
            VALUES (?, ?, ?, 'active')
            """,
            (checkpoint_id, fork_messages_json, created_at),
        )
        return cur.lastrowid  # type: ignore[return-value]


def discard_fork(store: CheckpointStore, fork_id: int) -> None:
    """Set fork status to 'discarded'."""
    with sqlite3.connect(store._db_path) as conn:
        conn.execute(
            "UPDATE forks SET status = 'discarded' WHERE id = ?",
            (fork_id,),
        )


def restore_home_state(store: CheckpointStore, agent_id: str) -> list:
    """Return messages for the latest home-state checkpoint of agent_id.

    Returns an empty list if no home-state checkpoint exists.
    """
    checkpoint_id = store.get_home_state_id(agent_id)
    if checkpoint_id is None:
        return []
    return store.load(checkpoint_id)
