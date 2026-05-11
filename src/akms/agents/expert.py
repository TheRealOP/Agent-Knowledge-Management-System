from __future__ import annotations

"""ExpertAgent — owns a section of the knowledge graph, answers queries without mutating home state."""

from typing import TYPE_CHECKING

from akms.agents.base import BaseAgent
from akms.core.message import Message, Role

if TYPE_CHECKING:
    from akms.config import AKMSConfig
    from akms.knowledge.graph import HybridGraph
    from akms.logging.conversation_log import ConversationLogger
    from akms.providers.base import LLMProvider


class ExpertAgent(BaseAgent):
    """Agent that owns a section of the knowledge graph.

    Maintains a clean home state (system prompt + section knowledge).
    Each Q&A creates a new message list via list concatenation — home state is never mutated.
    """

    agent_type = "expert"

    def __init__(
        self,
        section: str,
        provider: LLMProvider,
        model: str,
        config: AKMSConfig,
        logger: ConversationLogger | None = None,
    ) -> None:
        super().__init__(provider=provider, model=model, config=config, logger=logger)
        self.section = section
        self._home_messages: list[Message] = []

    def load_section(self, graph: HybridGraph) -> int:
        """Load all nodes from the section into the home-state system message.

        Returns the count of nodes loaded.
        """
        node_ids = graph.list_nodes(self.section)
        knowledge_parts: list[str] = []
        for node_id in node_ids:
            node = graph.get_node(self.section, node_id)
            if node is None:
                continue
            title = node.get("title", node_id)
            content = node.get("content", "")
            wikilinks = node.get("wikilinks", [])
            connections = ", ".join(wikilinks) if wikilinks else "none"
            knowledge_parts.append(
                f"## {title}\n{content}\n\nConnections: {connections}\n"
            )

        knowledge_block = "\n".join(knowledge_parts)
        system_content = (
            f"You are an Expert for the '{self.section}' knowledge section.\n"
            "You answer questions concisely in caveman format: compressed, direct, "
            "references graph paths.\n\n"
            "Knowledge section contents:\n"
            f"{knowledge_block}"
        )
        self._home_messages = [Message(role=Role.SYSTEM, content=system_content)]
        return len(node_ids)

    def load_nodes(self, graph: HybridGraph, node_ids: list[str]) -> int:
        knowledge_parts: list[str] = []
        self._chunk_node_ids: set[str] = set()
        self._chunk_tags: set[str] = set()
        for node_id in node_ids:
            node = graph.get_node(self.section, node_id)
            if node is None:
                continue
            self._chunk_node_ids.add(node_id)
            self._chunk_tags.update(node.get("tags", []))
            title = node.get("title", node_id)
            content = node.get("content", "")
            wikilinks = node.get("wikilinks", [])
            connections = ", ".join(wikilinks) if wikilinks else "none"
            knowledge_parts.append(f"## {title}\n{content}\n\nConnections: {connections}\n")
        knowledge_block = "\n".join(knowledge_parts)
        system_content = (
            f"You are an Expert for the '{self.section}' knowledge section (chunk {node_ids[:1]}).\n"
            "Answer concisely in caveman format.\n\n"
            f"Knowledge:\n{knowledge_block}"
        )
        self._home_messages = [Message(role=Role.SYSTEM, content=system_content)]
        return len(self._chunk_node_ids)

    def answer(self, question: str) -> str:
        """Answer a question without mutating home state.

        List concatenation creates a new list — _home_messages is never modified.
        """
        messages = self._home_messages + [Message(role=Role.USER, content=question)]
        response = self._provider.chat(messages, model=self._model)
        if self._logger:
            self._logger.log_message(
                self.agent_type, self._session_id, Message(role=Role.USER, content=question)
            )
            self._logger.log_message(self.agent_type, self._session_id, response.message)
        return response.message.content
