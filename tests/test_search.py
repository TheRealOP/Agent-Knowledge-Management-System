from __future__ import annotations

import pytest

from akms.knowledge.graph import HybridGraph
from akms.knowledge.search import GraphSearch


def _make_graph(knowledge_config) -> HybridGraph:
    g = HybridGraph(knowledge_config)
    g.init_graph_dirs()
    return g


def test_search_ranked(knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall due to gravity.", tags=["force"])
    graph.add_node("physics", "light", "Light", "Photons travel fast.", tags=["wave"])

    search = GraphSearch(graph)
    results = search.search("gravity force")
    assert len(results) > 0
    top_node, top_score = results[0]
    assert top_score > 0


def test_search_empty_query(knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall.", tags=[])

    search = GraphSearch(graph)
    results = search.search("")
    assert results == []


def test_search_section_filter(knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall due to gravity.", tags=[])
    graph.add_node("biology", "cells", "Cells", "Basic unit of life.", tags=[])

    search = GraphSearch(graph)
    results = search.search_section("physics", "gravity")
    assert all(node.get("section") == "physics" for node, _ in results)
