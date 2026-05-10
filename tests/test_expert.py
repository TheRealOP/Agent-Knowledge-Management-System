from __future__ import annotations

import pytest

from akms.agents.expert import ExpertAgent
from akms.checkpoints.store import CheckpointStore
from akms.knowledge.graph import HybridGraph
from akms.logging.conversation_log import ConversationLogger
from conftest import MockProvider


def _make_graph(knowledge_config) -> HybridGraph:
    g = HybridGraph(knowledge_config)
    g.init_graph_dirs()
    return g


def test_load_section(akms_config, knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall down.", tags=["force"])

    provider = MockProvider()
    expert = ExpertAgent(section="physics", provider=provider, model="mock-model", config=akms_config)
    count = expert.load_section(graph)
    assert count == 1
    assert any("Gravity" in m.content for m in expert._home_messages)


def test_answer_without_store(akms_config, knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall down.")

    provider = MockProvider(["Gravity pull things down."])
    expert = ExpertAgent(section="physics", provider=provider, model="mock-model", config=akms_config)
    expert.load_section(graph)

    answer = expert.answer("What is gravity?")
    assert "Gravity" in answer or "down" in answer
    assert expert._history == []


def test_answer_with_store_uses_fork(akms_config, knowledge_config, tmp_path):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall down.")

    store = CheckpointStore(str(tmp_path / "cp.db"))
    store.init_db()

    provider = MockProvider(["Gravity pull things down."])
    expert = ExpertAgent(section="physics", provider=provider, model="mock-model", config=akms_config)
    expert.load_section(graph)
    expert.set_home_state(store)

    answer = expert.answer("What is gravity?", store=store)
    assert isinstance(answer, str)
    assert expert._history == []


def test_load_nodes_subset(akms_config, knowledge_config):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall down.", tags=["force"])
    graph.add_node("physics", "light", "Light", "Photons travel fast.", tags=["wave"])

    provider = MockProvider()
    expert = ExpertAgent(section="physics", provider=provider, model="mock-model", config=akms_config)
    count = expert.load_nodes(graph, ["gravity"])
    assert count == 1
    assert "gravity" in expert._chunk_node_ids
    assert "light" not in expert._chunk_node_ids
    assert "force" in expert._chunk_tags


def test_fork_qa_logged(akms_config, knowledge_config, tmp_path):
    graph = _make_graph(knowledge_config)
    graph.add_node("physics", "gravity", "Gravity", "Objects fall down.")

    logger = ConversationLogger(str(tmp_path / "logs"))
    provider = MockProvider(["Gravity pull things down."])
    expert = ExpertAgent(
        section="physics", provider=provider, model="mock-model",
        config=akms_config, logger=logger,
    )
    expert.load_section(graph)
    expert.answer("What is gravity?")

    messages = logger.load_conversation("expert", expert.session_id)
    assert len(messages) == 2
    assert messages[0].role.value == "user"
    assert messages[1].role.value == "assistant"
    assert expert._history == []
