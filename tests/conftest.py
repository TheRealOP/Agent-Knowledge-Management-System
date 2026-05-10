from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import tempfile
import shutil
from pathlib import Path
from akms.config import KnowledgeConfig, AKMSConfig, BudgetConfig


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
    return AKMSConfig(knowledge=knowledge_config, budget=BudgetConfig())
