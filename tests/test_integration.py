from __future__ import annotations

import pytest

from akms.agents.executor import ExecutorAgent
from akms.agents.librarian import LibrarianAgent
from akms.checkpoints.store import CheckpointStore
from akms.config import AgentAssignment, ExpertConfig, ProviderConfig
from akms.core.orchestrator import Orchestrator
from akms.knowledge.graph import HybridGraph
from akms.providers.registry import ProviderRegistry
from conftest import MockProvider


def _make_orchestrator(akms_config, knowledge_config, provider=None):
    if provider is None:
        provider = MockProvider()

    registry = ProviderRegistry()
    registry.register("mock", lambda **kwargs: provider)
    akms_config.providers["mock"] = ProviderConfig(name="mock")
    akms_config.agent_assignments["expert"] = AgentAssignment(provider="mock", model="mock-model")
    akms_config.expert = ExpertConfig(token_threshold=50000)

    graph = HybridGraph(knowledge_config)
    graph.init_graph_dirs()

    store = CheckpointStore(akms_config.knowledge.checkpoints_db_path)
    store.init_db()

    return (
        Orchestrator(config=akms_config, registry=registry, graph=graph, checkpoint_store=store),
        graph,
        store,
    )


def test_ingest_to_query_flow(akms_config, knowledge_config):
    provider = MockProvider(["Atoms are smallest particles."])
    orc, graph, _ = _make_orchestrator(akms_config, knowledge_config, provider=provider)

    graph.add_node("chemistry", "atoms", "Atoms", "Smallest unit of matter.", tags=["basics"])

    akms_config.agent_assignments["executor"] = AgentAssignment(provider="mock", model="mock-model")
    executor = ExecutorAgent(provider=provider, model="mock-model", config=akms_config)

    result = executor.run("What are atoms?", orchestrator=orc)
    assert isinstance(result, str)
    assert len(result) > 0


def test_librarian_digest_then_expert_query(akms_config, knowledge_config, tmp_path):
    import json

    meta_json = json.dumps({
        "section": "biology",
        "node_id": "cells",
        "title": "Cells",
        "tags": ["basics"],
        "confidence": 0.9,
    })
    digest_provider = MockProvider([meta_json])
    query_provider = MockProvider(["Cells are the basic unit of life."])

    graph = HybridGraph(knowledge_config)
    graph.init_graph_dirs()

    librarian = LibrarianAgent(
        provider=digest_provider, model="mock-model", config=akms_config
    )

    doc = tmp_path / "bio.md"
    doc.write_text(
        "## Cells\n\nCells are the basic structural unit of all living organisms.\n",
        encoding="utf-8",
    )
    count = librarian.digest_document(str(doc), graph)
    assert count >= 1

    registry = ProviderRegistry()
    registry.register("mock", lambda **kwargs: query_provider)
    akms_config.providers["mock"] = ProviderConfig(name="mock")
    akms_config.agent_assignments["expert"] = AgentAssignment(provider="mock", model="mock-model")
    akms_config.expert = ExpertConfig(token_threshold=50000)

    store = CheckpointStore(akms_config.knowledge.checkpoints_db_path)
    store.init_db()
    orc = Orchestrator(
        config=akms_config, registry=registry, graph=graph, checkpoint_store=store
    )

    answer = orc.query_expert("biology", "What are cells?")
    assert isinstance(answer, str)
