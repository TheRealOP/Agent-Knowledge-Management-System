"""Hybrid knowledge graph combining wiki and SQLite layers."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from ..config import KnowledgeConfig
from .db import SQLiteLayer
from .wiki import WikiLayer


class HybridGraph:
    """Coordinates the markdown wiki and SQLite structured store."""

    def __init__(self, config: KnowledgeConfig) -> None:
        self.config = config
        self.wiki = WikiLayer(config.graph_dir)
        self.sqlite = SQLiteLayer(config.db_path)
        self.sqlite.init_db()

    def init_graph_dirs(self) -> None:
        for d in (
            self.config.graph_dir,
            self.config.archives_dir,
            self.config.logs_dir,
        ):
            Path(d).mkdir(parents=True, exist_ok=True)

    def add_node(
        self,
        section: str,
        node_id: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        confidence: float = 1.0,
        sources: list[Any] | None = None,
    ) -> dict[str, Any]:
        path = self.wiki.create_node(
            section=section,
            node_id=node_id,
            title=title,
            content=content,
            tags=tags,
            confidence=confidence,
            sources=sources,
        )
        today = datetime.date.today().isoformat()
        self.sqlite.upsert_node(
            {
                "id": node_id,
                "section": section,
                "file_path": str(path),
                "title": title,
                "created": today,
                "updated": today,
                "confidence": confidence,
            }
        )
        keywords = " ".join([title, " ".join(tags or []), content])
        self.sqlite.update_search_index(node_id, keywords)
        return {"id": node_id, "section": section, "file_path": str(path)}

    def get_node(self, section: str, node_id: str) -> dict[str, Any] | None:
        return self.wiki.read_node(section, node_id)

    def update_node(self, section: str, node_id: str, **fields: Any) -> bool:
        updated = self.wiki.update_node(section, node_id, **fields)
        if not updated:
            return False

        node = self.wiki.read_node(section, node_id)
        if node is None:
            return False

        path = self.wiki._node_path(section, node_id)
        existing = self.sqlite.get_node(node_id)
        created = existing["created"] if existing else datetime.date.today().isoformat()
        today = datetime.date.today().isoformat()

        self.sqlite.upsert_node(
            {
                "id": node_id,
                "section": section,
                "file_path": str(path),
                "title": node["title"],
                "created": created,
                "updated": today,
                "confidence": node["confidence"],
            }
        )
        keywords = " ".join(
            [node["title"], " ".join(node.get("tags") or []), node.get("content", "")]
        )
        self.sqlite.update_search_index(node_id, keywords)
        return True

    def get_related(self, node_id: str) -> list[dict[str, Any]]:
        edges = self.sqlite.get_edges(node_id)
        related: list[dict[str, Any]] = []
        for edge in edges:
            target = self.sqlite.get_node(edge["target_id"])
            if target is not None:
                related.append(target)
        return related

    def sync_links(self) -> int:
        count = 0
        for section in self.wiki.list_sections():
            for node_id in self.wiki.list_nodes(section):
                node = self.wiki.read_node(section, node_id)
                if node is None:
                    continue
                for target in node.get("wikilinks", []):
                    self.sqlite.upsert_edge(node_id, target, rel_type="wikilink")
                    count += 1
        return count

    def list_sections(self) -> list[str]:
        return self.wiki.list_sections()

    def list_nodes(self, section: str) -> list[str]:
        return self.wiki.list_nodes(section)

    def search(self, query: str, top_k: int = 10) -> list[tuple[dict[str, Any], float]]:
        from .search import GraphSearch

        return GraphSearch(self).search(query, top_k=top_k)
