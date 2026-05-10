from __future__ import annotations

"""CheckpointStore — sqlite3-backed persistence for agent conversation checkpoints."""

import datetime
import json
import sqlite3
from pathlib import Path

from akms.core.message import Message


class CheckpointStore:
    """Persist and retrieve agent conversation checkpoints using sqlite3."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def init_db(self) -> None:
        """Create parent directories and apply schema.sql."""
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        schema = (Path(__file__).parent / "schema.sql").read_text()
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(schema)

    def save(
        self,
        agent_type: str,
        agent_id: str,
        name: str,
        messages: list,
        is_home_state: bool = False,
    ) -> int:
        """Persist a checkpoint. Returns the new checkpoint id."""
        messages_json = json.dumps([m.to_dict() for m in messages])
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO checkpoints
                    (agent_type, agent_id, name, messages_json, created_at, is_home_state)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (agent_type, agent_id, name, messages_json, created_at, int(is_home_state)),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def load(self, checkpoint_id: int) -> list:
        """Return the list of Messages for a checkpoint."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT messages_json FROM checkpoints WHERE id = ?",
                (checkpoint_id,),
            ).fetchone()
        if row is None:
            return []
        return [Message.from_dict(d) for d in json.loads(row[0])]

    def get_home_state_id(self, agent_id: str) -> int | None:
        """Return the latest home-state checkpoint id for agent_id, or None."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT id FROM checkpoints
                WHERE agent_id = ? AND is_home_state = 1
                ORDER BY id DESC LIMIT 1
                """,
                (agent_id,),
            ).fetchone()
        return row[0] if row is not None else None

    def list_checkpoints(self, agent_id: str) -> list[dict]:
        """Return checkpoint metadata dicts for all checkpoints of agent_id."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, agent_type, agent_id, name, created_at, is_home_state
                FROM checkpoints
                WHERE agent_id = ?
                ORDER BY id ASC
                """,
                (agent_id,),
            ).fetchall()
        return [
            {
                "id": r[0],
                "agent_type": r[1],
                "agent_id": r[2],
                "name": r[3],
                "created_at": r[4],
                "is_home_state": bool(r[5]),
            }
            for r in rows
        ]
