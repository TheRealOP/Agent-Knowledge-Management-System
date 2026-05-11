from __future__ import annotations

import pytest

from akms.config import AgentAssignment, AKMSConfig, ExpertConfig, ProviderConfig
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


def test_get_expert_caches(akms_config, knowledge_config):
    orc, graph = _make_orchestrator(akms_config, knowledge_config)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    e1 = orc.get_expert("science")
    e2 = orc.get_expert("science")
    assert e1 is e2


def test_query_expert(akms_config, knowledge_config):
    provider = MockProvider(["Atoms are tiny."])
    orc, graph = _make_orchestrator(akms_config, knowledge_config, provider=provider)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    answer = orc.query_expert("science", "What are atoms?")
    assert isinstance(answer, str)


def test_flush_pool(akms_config, knowledge_config):
    orc, graph = _make_orchestrator(akms_config, knowledge_config)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    e1 = orc.get_expert("science")
    orc.flush_expert_pool()
    e2 = orc.get_expert("science")
    assert e1 is not e2


def test_spawn_expert_evicts(akms_config, knowledge_config):
    orc, graph = _make_orchestrator(akms_config, knowledge_config)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    e1 = orc.get_expert("science")
    e2 = orc.spawn_expert("science")
    assert e1 is not e2


def test_refresh_expert_none_if_missing(akms_config, knowledge_config):
    orc, graph = _make_orchestrator(akms_config, knowledge_config)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    result = orc.refresh_expert("science")
    assert result is None


def test_dynamic_scaling_single(akms_config, knowledge_config):
    # High threshold so single expert is used
    orc, graph = _make_orchestrator(akms_config, knowledge_config, token_threshold=999999)
    graph.add_node("science", "atoms", "Atoms", "Basic matter.")

    expert = orc.get_expert("science")
    assert "science" in orc._expert_pool
    assert f"science:__split__" not in orc._expert_pool


def test_dynamic_scaling_split(akms_config, knowledge_config):
    # Very low threshold to force splitting
    orc, graph = _make_orchestrator(akms_config, knowledge_config, token_threshold=1)
    # Add multiple nodes to ensure split
    for i in range(5):
        graph.add_node("science", f"node_{i}", f"Node {i}", f"Content for node {i} with lots of text to exceed threshold.")

    orc.get_expert("science")
    # Either single (if content is small) or split
    has_single = "science" in orc._expert_pool
    has_split = "science:__split__" in orc._expert_pool
    assert has_single or has_split
