"""Configuration loading and validation for AKMS."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProviderConfig:
    name: str
    api_key: str | None = None
    base_url: str | None = None
    models: list[str] = field(default_factory=list)
    tmux_pane: str | None = None


@dataclass
class AgentAssignment:
    provider: str
    model: str


@dataclass
class AgentPool:
    assignments: list[AgentAssignment] = field(default_factory=list)


@dataclass
class KnowledgeConfig:
    graph_dir: str = "knowledge/graph"
    archives_dir: str = "knowledge/archives"
    logs_dir: str = "knowledge/logs"
    db_path: str = "knowledge/akms.db"


@dataclass
class ExpertConfig:
    token_threshold: int = 50000


@dataclass
class AKMSConfig:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    agent_assignments: dict[str, AgentAssignment] = field(default_factory=dict)
    agent_pools: dict[str, AgentPool] = field(default_factory=dict)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    expert: ExpertConfig = field(default_factory=ExpertConfig)


def _resolve_env_vars(value: str) -> str:
    if not isinstance(value, str):
        return value
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.environ.get(env_name, "")
    return value


def _parse_providers(raw: dict[str, Any]) -> dict[str, ProviderConfig]:
    providers = {}
    for name, data in raw.items():
        providers[name] = ProviderConfig(
            name=name,
            api_key=_resolve_env_vars(data.get("api_key", "")) or None,
            base_url=data.get("base_url"),
            models=data.get("models", []),
            tmux_pane=data.get("tmux_pane"),
        )
    return providers


def _parse_assignments(raw: dict[str, Any]) -> dict[str, AgentAssignment]:
    assignments = {}
    for role, data in raw.items():
        assignments[role] = AgentAssignment(
            provider=data["provider"],
            model=data["model"],
        )
    return assignments


def _parse_pools(raw: dict[str, Any]) -> dict[str, AgentPool]:
    pools = {}
    for role, data in raw.items():
        assignments = []
        for item in data:
            assignments.append(
                AgentAssignment(
                    provider=item["provider"],
                    model=item["model"],
                )
            )
        pools[role] = AgentPool(assignments=assignments)
    return pools


def load_config(path: str | Path | None = None) -> AKMSConfig:
    """Load AKMS config. Searches: explicit path → ./akms_config.yaml → ~/.akms/config.yaml."""
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
        return AKMSConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    return AKMSConfig(
        providers=_parse_providers(raw.get("providers", {})),
        agent_assignments=_parse_assignments(raw.get("agent_assignments", {})),
        agent_pools=_parse_pools(raw.get("agent_pools", {})),
        knowledge=KnowledgeConfig(**raw.get("knowledge", {})),
        expert=ExpertConfig(**raw.get("expert", {})),
    )
