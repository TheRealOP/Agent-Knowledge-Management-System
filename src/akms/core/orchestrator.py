from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from akms.agents.expert import ExpertAgent
    from akms.checkpoints.store import CheckpointStore
    from akms.config import AKMSConfig
    from akms.knowledge.graph import HybridGraph
    from akms.providers.registry import ProviderRegistry


class Orchestrator:
    """Coordinates agents, experts, and knowledge graph for a session."""

    def __init__(
        self,
        config: AKMSConfig,
        registry: ProviderRegistry,
        graph: HybridGraph,
        checkpoint_store: CheckpointStore,
    ) -> None:
        self._config = config
        self._registry = registry
        self._graph = graph
        self._store = checkpoint_store
        self._expert_pool: dict[str, ExpertAgent] = {}

    def start_session(self) -> str:
        return uuid.uuid4().hex

    def _build_provider(self, role: str) -> tuple[Any, str]:
        """Return (provider_instance, model_name) for the given agent role."""
        assignment = self._config.agent_assignments.get(role)
        if assignment is None:
            raise ValueError(f"No agent assignment configured for role '{role}'")
        provider_cfg = self._config.providers.get(assignment.provider)
        if provider_cfg is None:
            raise ValueError(f"Provider '{assignment.provider}' not found in config")
        provider = self._registry.create_from_config(assignment.provider, provider_cfg)
        return provider, assignment.model

    def get_expert(self, section: str) -> ExpertAgent:
        """Return a loaded ExpertAgent for the given section (cached per session)."""
        if section in self._expert_pool:
            return self._expert_pool[section]

        from akms.agents.expert import ExpertAgent

        provider, model = self._build_provider("expert")
        expert = ExpertAgent(
            section=section,
            provider=provider,
            model=model,
            config=self._config,
        )
        expert.load_section(self._graph)
        expert.set_home_state(self._store)
        self._expert_pool[section] = expert
        return expert

    def query_expert(self, section: str, question: str) -> str:
        """Query the expert for a section and return the answer."""
        expert = self.get_expert(section)
        return expert.answer(question, store=self._store)

    def list_sections(self) -> list[str]:
        return self._graph.list_sections()

    def search_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        results = self._graph.search(query, top_k=top_k)
        return [node for node, _score in results]

    def flush_expert_pool(self) -> None:
        """Clear cached experts (call after graph updates)."""
        self._expert_pool.clear()
