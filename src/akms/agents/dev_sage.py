"""Dev-Sage — High-agency development agent leveraging multi-provider AKMS pools."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from akms.core.message import Message, Role

if TYPE_CHECKING:
    from akms.config import AKMSConfig
    from akms.core.multi_orchestrator import MultiProviderOrchestrator
    from akms.knowledge.graph import HybridGraph
    from akms.logging.conversation_log import ConversationLogger


class DevSageAgent:
    """
    Stateless development agent.
    
    Orchestrates specialized roles (Architect, Executor, Specialist) to achieve a goal.
    Maintains memory as AKMS graph nodes to minimize context window usage.
    """

    def __init__(
        self,
        orchestrator: MultiProviderOrchestrator,
        graph: HybridGraph,
        config: AKMSConfig,
        logger: ConversationLogger | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._graph = graph
        self._config = config
        self._logger = logger
        self._current_plan: list[str] = []

    def _get_provider(self, role: str) -> tuple[Any, str]:
        return self._orchestrator._build_provider(role)

    def _ask_role(self, role: str, prompt: str, system: str | None = None) -> str:
        provider, model = self._get_provider(role)
        messages = []
        if system:
            messages.append(Message(role=Role.SYSTEM, content=system))
        messages.append(Message(role=Role.USER, content=prompt))
        
        response = provider.chat(messages, model=model)
        return response.message.content

    def solve(self, goal: str) -> str:
        """Main loop: Plan -> Execute steps -> Refine."""
        
        # 1. Planning Phase (Architect)
        print(f"[*] Planning goal: {goal}")
        plan_raw = self._ask_role(
            "architect",
            f"Given the goal: '{goal}', break it down into a list of specific, actionable steps. "
            "Return a JSON list of strings.",
            system="You are a senior system architect. Be concise and strategic."
        )
        try:
            self._current_plan = json.loads(plan_raw)
        except json.JSONDecodeError:
            # Simple regex fallback
            self._current_plan = re.findall(r'"(.*?)"', plan_raw)

        results = []
        for i, step in enumerate(self._current_plan):
            print(f"[*] Executing step {i+1}/{len(self._current_plan)}: {step}")
            
            # 2. Execution Phase (Executor)
            # Inject context from AKMS if relevant
            context = self._retrieve_context(step)
            exec_prompt = f"Step: {step}\n\nRelevant Context from AKMS:\n{context}\n\nExecute this step and return a summary of what you did."
            
            summary = self._ask_role(
                "executor",
                exec_prompt,
                system="You are an expert developer. Execute the requested step and document your work."
            )
            
            # 3. Compaction (Librarian-like behavior)
            self._store_result(f"dev_sage_step_{i}", step, summary)
            results.append(summary)

        return "\n\n".join(results)

    def _retrieve_context(self, query: str) -> str:
        """Search AKMS for relevant information to minimize prompt size."""
        nodes = self._graph.sqlite.search_keywords(query, limit=3)
        context_parts = []
        for node in nodes:
            context_parts.append(f"### {node['title']}\n{node.get('content', '')}")
        return "\n---\n".join(context_parts) if context_parts else "No direct AKMS context found."

    def _store_result(self, node_id: str, title: str, content: str) -> None:
        """Write result to AKMS to clear agent memory for next step."""
        self._graph.add_node(
            section="dev_progress",
            node_id=node_id,
            title=title,
            content=content,
            tags=["dev_sage", "automation"],
            confidence=0.9
        )
