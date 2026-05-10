from __future__ import annotations

import pytest

from akms.agents.executor import ExecutorAgent
from akms.agents.librarian import LibrarianAgent
from akms.checkpoints.store import CheckpointStore
from akms.config import AgentAssignment, ExpertConfig, ProviderConfig
from akms.core.budget import BudgetTracker
from akms.core.orchestrator import Orchestrator
from akms.knowledge.graph import HybridGraph
from akms.knowledge.user_overlay import UserOverlay
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

    store = CheckpointStore(akms_config.knowledge.checkpoints_db_path)
    store.init_db()

    return (
        Orchestrator(config=akms_config, registry=registry, graph=graph, checkpoint_store=store),
        graph,
        store,
    )


def test_large_graph_many_sections(akms_config, knowledge_config):
    orc, graph, _ = _make_orchestrator(akms_config, knowledge_config)

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


def test_budget_exhaustion(tmp_dir):
    tracker = BudgetTracker()
    tracker.record_usage("mock", "model", 1000, 500, 10.0)
    assert tracker.is_over_limit(5.0) is True


def test_provider_failure(akms_config):
    class FailingProvider:
        provider_name = "failing"

        def chat(self, messages, model=None, **kwargs):
            raise RuntimeError("Provider unavailable")

        def stream(self, messages, model=None, **kwargs):
            raise RuntimeError("Provider unavailable")

        def count_tokens(self, messages) -> int:
            return 0

        def _to_provider_format(self, messages):
            return []

        def _from_provider_response(self, raw, model):
            raise RuntimeError("Provider unavailable")

    provider = FailingProvider()
    executor = ExecutorAgent(provider=provider, model="mock-model", config=akms_config)

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        executor.run("Hello")


def test_empty_section_query(akms_config, knowledge_config):
    orc, graph, _ = _make_orchestrator(akms_config, knowledge_config)
    # Section exists but has no nodes
    # query_expert should return some response (mock)
    provider = MockProvider(["No knowledge found."])
    registry = ProviderRegistry()
    registry.register("mock", lambda **kwargs: provider)
    akms_config.providers["mock"] = ProviderConfig(name="mock")
    akms_config.agent_assignments["expert"] = AgentAssignment(provider="mock", model="mock-model")
    store = CheckpointStore(akms_config.knowledge.checkpoints_db_path)
    store.init_db()
    orc2 = Orchestrator(
        config=akms_config, registry=registry, graph=graph, checkpoint_store=store
    )
    answer = orc2.query_expert("empty_section", "What do you know?")
    assert isinstance(answer, str)


def test_broken_wikilinks(akms_config, knowledge_config):
    graph = HybridGraph(knowledge_config)
    graph.init_graph_dirs()

    # Add node with wikilinks to nonexistent targets
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


def test_overlay_round_trip(tmp_path):
    uo = UserOverlay(str(tmp_path / "overlay"))

    uo.set_concept("neural_networks", 0.7, "Understand backprop")
    data = uo.get_concept("neural_networks")
    assert data is not None
    assert abs(data["understanding"] - 0.7) < 1e-9
    assert data["notes"] == "Understand backprop"

    concepts = uo.list_concepts()
    assert "neural_networks" in concepts

    removed = uo.remove_concept("neural_networks")
    assert removed is True
    assert uo.get_concept("neural_networks") is None

    # JSON file should still be valid after removal
    import json
    overlay_file = tmp_path / "overlay" / "understanding.json"
    data = json.loads(overlay_file.read_text(encoding="utf-8"))
    assert "concepts" in data
    assert "neural_networks" not in data["concepts"]
