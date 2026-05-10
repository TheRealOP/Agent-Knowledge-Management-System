from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from akms.config import load_config, AKMSConfig, BudgetConfig, KnowledgeConfig


def test_load_config_no_file_returns_defaults(tmp_path, monkeypatch):
    """load_config() with no config file returns AKMSConfig with default budget."""
    # Ensure no akms_config.yaml exists in cwd and home doesn't have one
    monkeypatch.chdir(tmp_path)
    # Patch home to a temp dir with no config
    monkeypatch.setenv("HOME", str(tmp_path))
    config = load_config()
    assert isinstance(config, AKMSConfig)
    assert config.budget.daily_limit_usd == 5.0
    assert config.budget.per_query_warn_usd == 0.50


def test_load_config_parses_providers(tmp_path):
    """load_config(path) parses providers correctly from YAML."""
    yaml_content = {
        "providers": {
            "claude": {
                "api_key": "test-key",
                "models": ["claude-sonnet-4"],
            }
        }
    }
    config_file = tmp_path / "akms_config.yaml"
    config_file.write_text(yaml.safe_dump(yaml_content), encoding="utf-8")

    config = load_config(str(config_file))
    assert "claude" in config.providers
    assert config.providers["claude"].api_key == "test-key"
    assert config.providers["claude"].models == ["claude-sonnet-4"]


def test_load_config_parses_budget(tmp_path):
    """load_config(path) parses budget fields."""
    yaml_content = {
        "budget": {
            "daily_limit_usd": 10.0,
            "per_query_warn_usd": 1.0,
        }
    }
    config_file = tmp_path / "akms_config.yaml"
    config_file.write_text(yaml.safe_dump(yaml_content), encoding="utf-8")

    config = load_config(str(config_file))
    assert config.budget.daily_limit_usd == 10.0
    assert config.budget.per_query_warn_usd == 1.0


def test_load_config_knowledge_defaults_when_missing(tmp_path):
    """KnowledgeConfig has correct defaults when not specified in YAML."""
    yaml_content = {"providers": {}}
    config_file = tmp_path / "akms_config.yaml"
    config_file.write_text(yaml.safe_dump(yaml_content), encoding="utf-8")

    config = load_config(str(config_file))
    assert isinstance(config.knowledge, KnowledgeConfig)
    assert config.knowledge.graph_dir == "knowledge/graph"
    assert config.knowledge.db_path == "knowledge/akms.db"
