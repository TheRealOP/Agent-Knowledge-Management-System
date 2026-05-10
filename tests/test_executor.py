from __future__ import annotations

import pytest

from akms.agents.executor import ExecutorAgent
from conftest import MockProvider


def test_run_simple_response(akms_config):
    provider = MockProvider(["Hello, world!"])
    agent = ExecutorAgent(provider=provider, model="mock-model", config=akms_config)
    result = agent.run("Say hello")
    assert "Hello" in result


def test_run_with_tool_call(akms_config):
    tool_response = '{"tool": "query_knowledge", "section": "science", "question": "what is gravity?"}'
    provider = MockProvider([tool_response, "Gravity is a force."])
    agent = ExecutorAgent(provider=provider, model="mock-model", config=akms_config)

    class FakeOrchestrator:
        def query_expert(self, section, question):
            return f"Expert answer about {section}: pull toward ground"

    result = agent.run("Ask about gravity", orchestrator=FakeOrchestrator())
    assert isinstance(result, str)
    assert len(result) > 0


def test_run_max_rounds(akms_config):
    always_tool = '{"tool": "query_knowledge", "section": "x", "question": "y"}'
    provider = MockProvider([always_tool] * 10)
    agent = ExecutorAgent(provider=provider, model="mock-model", config=akms_config)

    class FakeOrchestrator:
        def query_expert(self, section, question):
            return "answer"

    result = agent.run("loop forever", orchestrator=FakeOrchestrator())
    assert isinstance(result, str)
    # max_rounds=5 so provider called at most 6 times (1 initial + 5 rounds)
    assert provider._call_index <= 7
