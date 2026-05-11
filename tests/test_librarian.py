from __future__ import annotations

import json
import pytest

from akms.agents.librarian import LibrarianAgent
from akms.knowledge.graph import HybridGraph
from conftest import MockProvider


def _make_graph(knowledge_config) -> HybridGraph:
    g = HybridGraph(knowledge_config)
    g.init_graph_dirs()
    return g


def test_ingest_log_extracts_insights(akms_config, knowledge_config, tmp_path):
    log_file = tmp_path / "convo.jsonl"
    entry = {"role": "assistant", "content": "Python uses indentation for blocks."}
    log_file.write_text(json.dumps({"message": entry}) + "\n", encoding="utf-8")

    insights_json = json.dumps([
        {"section": "python", "node_id": "indentation", "title": "Indentation",
         "content": "Python uses indentation.", "tags": ["syntax"], "confidence": 0.9}
    ])
    provider = MockProvider([insights_json])
    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)
    graph = _make_graph(knowledge_config)
    insights = librarian.ingest_log(str(log_file), graph)
    assert isinstance(insights, list)


def test_update_graph_from_insights(akms_config, knowledge_config):
    graph = _make_graph(knowledge_config)
    provider = MockProvider()
    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)

    insights = [
        {"section": "python", "node_id": "lists", "title": "Lists",
         "content": "Python lists are dynamic.", "tags": ["data"], "confidence": 1.0}
    ]
    count = librarian.update_graph_from_insights(insights, graph)
    assert count == 1
    node = graph.get_node("python", "lists")
    assert node is not None
    assert "Lists" in node.get("title", "")


def test_digest_document(akms_config, knowledge_config, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(
        "## Introduction\n\nThis is a test document with some content about Python.\n\n"
        "## Advanced Topics\n\nDeep dive into async programming and event loops.\n",
        encoding="utf-8",
    )
    meta_json = json.dumps({
        "section": "python", "node_id": "intro", "title": "Introduction",
        "tags": ["basics"], "confidence": 0.8
    })
    provider = MockProvider([meta_json, meta_json])
    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)
    graph = _make_graph(knowledge_config)
    count = librarian.digest_document(str(doc), graph)
    assert count >= 1


def test_check_consistency(akms_config, knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("python", "lists", "Lists", "Python lists.", tags=[])
    # Add a node with a broken wikilink manually by updating wikilinks
    graph.wiki.create_node(
        section="python",
        node_id="broken_node",
        title="Broken",
        content="References [[nonexistent_node]].",
        tags=[],
    )
    # Patch wiki file to add wikilinks
    import re
    wiki_path = graph.wiki._node_path("python", "broken_node")
    content = wiki_path.read_text(encoding="utf-8")
    # Insert wikilinks into frontmatter
    content = content.replace("wikilinks: []", "wikilinks:\n- nonexistent_node")
    wiki_path.write_text(content, encoding="utf-8")

    provider = MockProvider()
    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)
    issues = librarian.check_consistency(graph)
    assert isinstance(issues, list)


def test_archive_node(akms_config, knowledge_config, tmp_path):
    graph = _make_graph(knowledge_config)
    graph.add_node("python", "old_node", "Old Node", "Outdated content.")

    provider = MockProvider()
    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)
    result = librarian.archive_node("python", "old_node", "outdated", graph)
    assert result is True
    assert graph.get_node("python", "old_node") is None


def test_spawn_expert_delegates(akms_config, knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    from akms.core.orchestrator import Orchestrator
    from akms.providers.registry import ProviderRegistry

    provider = MockProvider()
    registry = ProviderRegistry()
    registry.register("mock", lambda **kwargs: provider)

    from akms.config import AgentAssignment, ProviderConfig
    akms_config.providers["mock"] = ProviderConfig(name="mock")
    akms_config.agent_assignments["expert"] = AgentAssignment(provider="mock", model="mock-model")

    orchestrator = Orchestrator(config=akms_config, registry=registry, graph=graph)

    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)
    expert = librarian.spawn_expert("science", orchestrator)
    assert expert is not None
    assert expert.section == "science"


def test_refresh_expert_delegates(akms_config, knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    from akms.core.orchestrator import Orchestrator
    from akms.providers.registry import ProviderRegistry
    from akms.config import AgentAssignment, ProviderConfig

    provider = MockProvider()
    registry = ProviderRegistry()
    registry.register("mock", lambda **kwargs: provider)
    akms_config.providers["mock"] = ProviderConfig(name="mock")
    akms_config.agent_assignments["expert"] = AgentAssignment(provider="mock", model="mock-model")

    orchestrator = Orchestrator(config=akms_config, registry=registry, graph=graph)

    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)
    result = librarian.refresh_expert("science", orchestrator)
    assert result is None  # not yet in pool

    orchestrator.get_expert("science")
    result2 = librarian.refresh_expert("science", orchestrator)
    assert result2 is not None
