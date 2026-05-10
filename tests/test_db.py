from __future__ import annotations

import pytest
from pathlib import Path

from akms.knowledge.db import SQLiteLayer


def test_init_db_creates_file_and_tables(tmp_dir):
    """init_db() creates the database file and tables."""
    db_path = str(tmp_dir / "akms.db")
    layer = SQLiteLayer(db_path)
    layer.init_db()

    assert Path(db_path).exists()

    import sqlite3
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "nodes" in tables
    assert "edges" in tables
    assert "provenance" in tables
    assert "search_index" in tables


def test_upsert_and_get_node(tmp_dir):
    """upsert_node then get_node returns dict with correct id."""
    db_path = str(tmp_dir / "akms.db")
    layer = SQLiteLayer(db_path)
    layer.init_db()

    layer.upsert_node({
        "id": "n1",
        "section": "ds",
        "file_path": "ds/n1.md",
        "title": "Node One",
        "created": "2026-05-10",
        "updated": "2026-05-10",
        "confidence": 0.9,
    })

    node = layer.get_node("n1")
    assert node is not None
    assert node["id"] == "n1"


def test_search_keywords(tmp_dir):
    """search_keywords('Node') returns list containing the upserted node."""
    db_path = str(tmp_dir / "akms.db")
    layer = SQLiteLayer(db_path)
    layer.init_db()

    layer.upsert_node({
        "id": "n1",
        "section": "ds",
        "file_path": "ds/n1.md",
        "title": "Node One",
        "created": "2026-05-10",
        "updated": "2026-05-10",
        "confidence": 0.9,
    })

    results = layer.search_keywords("Node")
    ids = [r["id"] for r in results]
    assert "n1" in ids


def test_upsert_edge_and_get_edges(tmp_dir):
    """upsert_edge then get_edges returns list with one edge."""
    db_path = str(tmp_dir / "akms.db")
    layer = SQLiteLayer(db_path)
    layer.init_db()

    layer.upsert_edge("n1", "n2", "wikilink")
    edges = layer.get_edges("n1")
    assert len(edges) == 1
    assert edges[0]["source_id"] == "n1"
    assert edges[0]["target_id"] == "n2"


def test_delete_node(tmp_dir):
    """delete_node then get_node returns None."""
    db_path = str(tmp_dir / "akms.db")
    layer = SQLiteLayer(db_path)
    layer.init_db()

    layer.upsert_node({
        "id": "n1",
        "section": "ds",
        "file_path": "ds/n1.md",
        "title": "Node One",
        "created": "2026-05-10",
        "updated": "2026-05-10",
        "confidence": 0.9,
    })
    layer.delete_node("n1")
    assert layer.get_node("n1") is None
