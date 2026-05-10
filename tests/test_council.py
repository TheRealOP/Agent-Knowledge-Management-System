from __future__ import annotations

import pytest

from akms.agents.council import CouncilAgent
from conftest import MockProvider


def test_convene_returns_synthesis(akms_config):
    responses = [
        "Advocate view",
        "Critic view",
        "Historian view",
        "Innovator view",
        "Synthesizer recommendation",
    ]
    provider = MockProvider(responses)
    council = CouncilAgent(provider=provider, model="mock-model", config=akms_config)
    result = council.convene("Should we use microservices?", context="Small team, MVP stage.")
    assert isinstance(result, str)
    assert len(result) > 0


def test_convene_detailed_all_roles(akms_config):
    responses = [
        "Advocate view",
        "Critic view",
        "Historian view",
        "Innovator view",
        "Synthesizer recommendation",
    ]
    provider = MockProvider(responses)
    council = CouncilAgent(provider=provider, model="mock-model", config=akms_config)
    result = council.convene_detailed("Should we use microservices?")
    assert isinstance(result, dict)
    for role in ["Advocate", "Critic", "Historian", "Innovator", "Synthesizer"]:
        assert role in result
        assert isinstance(result[role], str)
        assert len(result[role]) > 0
