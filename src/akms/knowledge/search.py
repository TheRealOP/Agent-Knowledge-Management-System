"""Keyword search over the hybrid knowledge graph."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .graph import HybridGraph


_TOKEN_RE = re.compile(r"\w+")


class GraphSearch:
    """Tokenized keyword search backed by the SQLite layer."""

    def __init__(self, graph: HybridGraph) -> None:
        self.graph = graph

    def _tokenize(self, query: str) -> list[str]:
        return [t.lower() for t in _TOKEN_RE.findall(query) if t]

    def search(
        self, query: str, top_k: int = 10
    ) -> list[tuple[dict[str, Any], float]]:
        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores: dict[str, float] = {}
        nodes: dict[str, dict[str, Any]] = {}
        for token in tokens:
            for node in self.graph.sqlite.search_keywords(token, limit=top_k * 5):
                node_id = node["id"]
                scores[node_id] = scores.get(node_id, 0.0) + 1.0
                nodes[node_id] = node

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [(nodes[nid], score) for nid, score in ranked[:top_k]]

    def search_section(
        self, section: str, query: str
    ) -> list[tuple[dict[str, Any], float]]:
        results = self.search(query, top_k=100)
        return [(node, score) for node, score in results if node.get("section") == section]
