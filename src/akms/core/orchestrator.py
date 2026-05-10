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
        self._expert_pool: dict[str, Any] = {}

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
        """Return a loaded ExpertAgent for the given section (cached per session).

        If the section's knowledge exceeds token_threshold, splits into chunk experts
        stored under '{section}:0', '{section}:1', ... with a sentinel '{section}:__split__'.
        """
        if section in self._expert_pool:
            return self._expert_pool[section]
        if f"{section}:__split__" in self._expert_pool:
            chunk_keys: list[str] = self._expert_pool[f"{section}:__split__"]
            return self._expert_pool[chunk_keys[0]]

        from akms.agents.expert import ExpertAgent
        from akms.core.message import Message, Role

        provider, model = self._build_provider("expert")
        node_ids = self._graph.list_nodes(section)

        threshold = self._config.expert.token_threshold

        # Build full knowledge block to estimate tokens
        knowledge_parts: list[str] = []
        for node_id in node_ids:
            node = self._graph.get_node(section, node_id)
            if node is None:
                continue
            title = node.get("title", node_id)
            content = node.get("content", "")
            wikilinks = node.get("wikilinks", [])
            connections = ", ".join(wikilinks) if wikilinks else "none"
            knowledge_parts.append(f"## {title}\n{content}\n\nConnections: {connections}\n")

        knowledge_block = "\n".join(knowledge_parts)
        probe_messages = [Message(role=Role.SYSTEM, content=knowledge_block)]
        estimated_tokens = provider.count_tokens(probe_messages)

        if estimated_tokens <= threshold or len(node_ids) == 0:
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

        # Split nodes into chunks where each chunk fits under threshold
        chunks: list[list[str]] = []
        current_chunk: list[str] = []
        current_tokens = 0

        for node_id in node_ids:
            node = self._graph.get_node(section, node_id)
            if node is None:
                continue
            title = node.get("title", node_id)
            content = node.get("content", "")
            wikilinks = node.get("wikilinks", [])
            connections = ", ".join(wikilinks) if wikilinks else "none"
            node_text = f"## {title}\n{content}\n\nConnections: {connections}\n"
            node_tokens = provider.count_tokens([Message(role=Role.SYSTEM, content=node_text)])

            if current_chunk and current_tokens + node_tokens > threshold:
                chunks.append(current_chunk)
                current_chunk = [node_id]
                current_tokens = node_tokens
            else:
                current_chunk.append(node_id)
                current_tokens += node_tokens

        if current_chunk:
            chunks.append(current_chunk)

        chunk_keys: list[str] = []
        for i, chunk_node_ids in enumerate(chunks):
            chunk_key = f"{section}:{i}"
            chunk_expert = ExpertAgent(
                section=section,
                provider=provider,
                model=model,
                config=self._config,
            )
            chunk_expert.load_nodes(self._graph, chunk_node_ids)
            chunk_expert.set_home_state(self._store)
            self._expert_pool[chunk_key] = chunk_expert
            chunk_keys.append(chunk_key)

        self._expert_pool[f"{section}:__split__"] = chunk_keys
        return self._expert_pool[chunk_keys[0]]

    def query_expert(self, section: str, question: str) -> str:
        """Query the expert for a section and return the answer.

        If the section is split, scores chunks by keyword overlap with node IDs and
        tags, queries the top-2 chunks, and concatenates their answers.
        """
        split_key = f"{section}:__split__"
        if split_key not in self._expert_pool:
            expert = self.get_expert(section)
            return expert.answer(question, store=self._store)

        chunk_keys: list[str] = self._expert_pool[split_key]
        if len(chunk_keys) <= 2:
            answers = [
                self._expert_pool[k].answer(question, store=self._store)
                for k in chunk_keys
            ]
            return "\n\n".join(answers)

        # Score chunks by keyword overlap
        question_tokens = set(question.lower().split())

        def _score(chunk_key: str) -> int:
            expert = self._expert_pool[chunk_key]
            node_ids: set[str] = getattr(expert, "_chunk_node_ids", set())
            tags: set[str] = getattr(expert, "_chunk_tags", set())
            keywords = {k.lower() for k in node_ids | tags}
            return len(question_tokens & keywords)

        ranked = sorted(chunk_keys, key=_score, reverse=True)
        top_two = ranked[:2]
        answers = [
            self._expert_pool[k].answer(question, store=self._store)
            for k in top_two
        ]
        return "\n\n".join(answers)

    def list_sections(self) -> list[str]:
        return self._graph.list_sections()

    def search_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        results = self._graph.search(query, top_k=top_k)
        return [node for node, _score in results]

    def flush_expert_pool(self) -> None:
        """Clear cached experts (call after graph updates)."""
        self._expert_pool.clear()

    def spawn_expert(self, section: str) -> ExpertAgent:
        """Force-create a fresh Expert for section, evicting any cached instance."""
        keys_to_remove = [
            k for k in self._expert_pool
            if k == section or k.startswith(f"{section}:")
        ]
        for k in keys_to_remove:
            del self._expert_pool[k]
        return self.get_expert(section)

    def refresh_expert(self, section: str) -> ExpertAgent | None:
        """Reload an existing Expert's section after graph changes."""
        if section not in self._expert_pool and f"{section}:__split__" not in self._expert_pool:
            return None
        return self.spawn_expert(section)
