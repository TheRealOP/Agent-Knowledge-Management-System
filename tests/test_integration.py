from __future__ import annotations

import pytest

from akms.agents.librarian import LibrarianAgent
from akms.config import AgentAssignment, ExpertConfig, ProviderConfig
from akms.core.orchestrator import Orchestrator
from akms.knowledge.graph import HybridGraph
from akms.providers.registry import ProviderRegistry
from conftest import MockProvider


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

    orc = Orchestrator(config=akms_config, registry=registry, graph=graph)

    answer = orc.query_expert("biology", "What are cells?")
    assert isinstance(answer, str)
