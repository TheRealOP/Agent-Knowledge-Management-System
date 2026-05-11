"""SQLite structured layer for the knowledge graph."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class SQLiteLayer:
    """Synchronous SQLite store for nodes, edges, provenance, and search index."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).parent / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema_sql)
            conn.commit()

    def upsert_node(self, node: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO nodes
                    (id, section, file_path, title, created, updated, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node["id"],
                    node["section"],
                    node["file_path"],
                    node["title"],
                    node["created"],
                    node["updated"],
                    node.get("confidence", 1.0),
                ),
            )
            conn.commit()

    def upsert_edge(
        self,
        source_id: str,
        target_id: str,
        rel_type: str = "wikilink",
        weight: float = 1.0,
        auto_discovered: bool = True,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO edges
                    (source_id, target_id, relationship_type, weight, auto_discovered)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source_id, target_id, rel_type, weight, 1 if auto_discovered else 0),
            )
            conn.commit()

    def add_provenance(
        self,
        node_id: str,
        source_type: str,
        source_ref: str,
        date: str,
        verified_by: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO provenance (node_id, source_type, source_ref, date, verified_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (node_id, source_type, source_ref, date, verified_by),
            )
            conn.commit()

    def update_search_index(self, node_id: str, keywords: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO search_index (node_id, keywords)
                VALUES (?, ?)
                ON CONFLICT(node_id) DO UPDATE SET keywords = excluded.keywords
                """,
                (node_id, keywords),
            )
            conn.commit()

    def search_keywords(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        like = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT n.*
                FROM nodes n
                LEFT JOIN search_index s ON s.node_id = n.id
                WHERE n.title LIKE ? OR s.keywords LIKE ?
                LIMIT ?
                """,
                (like, like, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_edges(self, source_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM edges WHERE source_id = ?", (source_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_node(self, node_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            conn.execute(
                "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
                (node_id, node_id),
            )
            conn.execute("DELETE FROM provenance WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM search_index WHERE node_id = ?", (node_id,))
            conn.commit()
