# edited by gemini
"""Configuration loading and validation for AKMS."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# edited by gemini — provider config dataclass
@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""

    name: str
    api_key: str | None = None
    base_url: str | None = None
    models: list[str] = field(default_factory=list)


# edited by gemini — agent assignment dataclass
@dataclass
class AgentAssignment:
    """Which provider/model an agent role should use."""

    provider: str
    model: str


@dataclass
class KnowledgeConfig:
    """Paths for knowledge graph storage."""

    graph_dir: str = "knowledge/graph"
    archives_dir: str = "knowledge/archives"
    logs_dir: str = "knowledge/logs"
    db_path: str = "knowledge/akms.db"
    checkpoints_db_path: str = "knowledge/checkpoints.db"


@dataclass
class ExpertConfig:
    token_threshold: int = 50000


# edited by gemini — top-level config dataclass
@dataclass
class AKMSConfig:
    """Top-level AKMS configuration."""

    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    agent_assignments: dict[str, AgentAssignment] = field(default_factory=dict)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    expert: ExpertConfig = field(default_factory=ExpertConfig)


# edited by gemini — resolve env vars in strings
def _resolve_env_vars(value: str) -> str:
    """Replace ${ENV_VAR} patterns with actual environment values."""
    if not isinstance(value, str):
        return value
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.environ.get(env_name, "")
    return value


# edited by gemini — parse provider section
def _parse_providers(raw: dict[str, Any]) -> dict[str, ProviderConfig]:
    """Parse the providers section of the config."""
    providers = {}
    for name, data in raw.items():
        providers[name] = ProviderConfig(
            name=name,
            api_key=_resolve_env_vars(data.get("api_key", "")) or None,
            base_url=data.get("base_url"),
            models=data.get("models", []),
        )
    return providers


# edited by gemini — parse agent assignments section
def _parse_assignments(raw: dict[str, Any]) -> dict[str, AgentAssignment]:
    """Parse the agent_assignments section of the config."""
    assignments = {}
    for role, data in raw.items():
        assignments[role] = AgentAssignment(
            provider=data["provider"],
            model=data["model"],
        )
    return assignments


# edited by gemini — main config loader
def load_config(path: str | Path | None = None) -> AKMSConfig:
    """Load AKMS configuration from a YAML file.

    Searches in order: explicit path, ./akms_config.yaml, ~/.akms/config.yaml.
    """
    search_paths = [
        Path(path) if path else None,
        Path("akms_config.yaml"),
        Path.home() / ".akms" / "config.yaml",
    ]

    config_path = None
    for p in search_paths:
        if p and p.exists():
            config_path = p
            break

    if config_path is None:
        return AKMSConfig()  # edited by gemini — return defaults if no config found

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    return AKMSConfig(
        providers=_parse_providers(raw.get("providers", {})),
        agent_assignments=_parse_assignments(raw.get("agent_assignments", {})),
        knowledge=KnowledgeConfig(**raw.get("knowledge", {})),
        expert=ExpertConfig(**raw.get("expert", {})),
    )
