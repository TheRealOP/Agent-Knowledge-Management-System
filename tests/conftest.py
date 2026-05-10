from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import tempfile
import shutil
from pathlib import Path
from akms.config import KnowledgeConfig, AKMSConfig, BudgetConfig, ExpertConfig
from akms.core.message import Message, Response, Role


class MockProvider:
    provider_name = "mock"

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or ["mock response"])
        self._call_index = 0

    def chat(self, messages, model=None, **kwargs):
        content = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        return Response(
            message=Message(role=Role.ASSISTANT, content=content),
            provider="mock",
            model=model or "mock-model",
            tokens_used=10,
            cost_usd=0.0,
        )

    def stream(self, messages, model=None, **kwargs):
        yield self.chat(messages, model, **kwargs)

    def count_tokens(self, messages) -> int:
        return sum(len(m.content) for m in messages) // 4

    def _to_provider_format(self, messages):
        return [{"role": m.role.value, "content": m.content} for m in messages]

    def _from_provider_response(self, raw, model):
        return Response(
            message=Message(role=Role.ASSISTANT, content=str(raw)),
            provider="mock",
            model=model or "mock-model",
            tokens_used=0,
            cost_usd=0.0,
        )


@pytest.fixture
def tmp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def knowledge_config(tmp_dir):
    return KnowledgeConfig(
        graph_dir=str(tmp_dir / "graph"),
        archives_dir=str(tmp_dir / "archives"),
        user_overlay_dir=str(tmp_dir / "user_overlay"),
        logs_dir=str(tmp_dir / "logs"),
        db_path=str(tmp_dir / "akms.db"),
        checkpoints_db_path=str(tmp_dir / "cp.db"),
    )


@pytest.fixture
def akms_config(knowledge_config):
    return AKMSConfig(
        knowledge=knowledge_config,
        budget=BudgetConfig(),
        expert=ExpertConfig(token_threshold=50000),
    )


@pytest.fixture
def mock_provider():
    return MockProvider()
