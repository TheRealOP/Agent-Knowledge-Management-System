from __future__ import annotations

import pytest

from akms.agents.librarian import LibrarianAgent
from akms.config import AgentAssignment, ExpertConfig, ProviderConfig
from akms.core.orchestrator import Orchestrator
from akms.knowledge.graph import HybridGraph
from akms.providers.registry import ProviderRegistry
from conftest import MockProvider


def _make_orchestrator(akms_config, knowledge_config, provider=None, token_threshold=50000):
    if provider is None:
        provider = MockProvider()
    registry = ProviderRegistry()
    registry.register("mock", lambda **kwargs: provider)
    akms_config.providers["mock"] = ProviderConfig(name="mock")
    akms_config.agent_assignments["expert"] = AgentAssignment(provider="mock", model="mock-model")
    akms_config.expert = ExpertConfig(token_threshold=token_threshold)

    graph = HybridGraph(knowledge_config)
    graph.init_graph_dirs()

    return Orchestrator(config=akms_config, registry=registry, graph=graph), graph


def test_large_graph_many_sections(akms_config, knowledge_config):
    orc, graph = _make_orchestrator(akms_config, knowledge_config)

    for s in range(20):
        section = f"section_{s}"
        for n in range(5):
            graph.add_node(section, f"node_{n}", f"Node {n}", f"Content {s}-{n}.", tags=[])

    sections = graph.list_sections()
    assert len(sections) == 20

    results = graph.search("Content", top_k=10)
    assert len(results) > 0

    expert = orc.get_expert("section_0")
    assert expert is not None


def test_empty_section_query(akms_config, knowledge_config):
    orc, graph = _make_orchestrator(akms_config, knowledge_config)
    provider = MockProvider(["No knowledge found."])
    registry = ProviderRegistry()
    registry.register("mock", lambda **kwargs: provider)
    akms_config.providers["mock"] = ProviderConfig(name="mock")
    akms_config.agent_assignments["expert"] = AgentAssignment(provider="mock", model="mock-model")
    orc2 = Orchestrator(config=akms_config, registry=registry, graph=graph)
    answer = orc2.query_expert("empty_section", "What do you know?")
    assert isinstance(answer, str)


def test_broken_wikilinks(akms_config, knowledge_config):
    graph = HybridGraph(knowledge_config)
    graph.init_graph_dirs()

    graph.add_node(
        "history", "rome", "Rome",
        "An ancient city. See also [[nonexistent_city]] and [[also_gone]].",
        tags=[],
    )

    provider = MockProvider()
    librarian = LibrarianAgent(provider=provider, model="mock-model", config=akms_config)
    issues = librarian.check_consistency(graph)
    broken = [i for i in issues if i.get("issue") == "broken wikilink"]
    assert len(broken) >= 2
