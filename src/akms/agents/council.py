from __future__ import annotations

from typing import TYPE_CHECKING

from akms.core.message import Message, Role

if TYPE_CHECKING:
    from akms.config import AKMSConfig
    from akms.providers.base import LLMProvider

_COUNCIL_ROLES = {
    "Advocate": (
        "You are the Advocate. Your role: argue strongly FOR the proposed approach. "
        "Identify its strengths, why it will work, and why it is the right path. "
        "Be concise and direct. 3-5 bullet points max."
    ),
    "Critic": (
        "You are the Critic. Your role: find flaws, risks, and weaknesses in the proposed approach. "
        "What could go wrong? What is being overlooked? "
        "Be specific. 3-5 bullet points max."
    ),
    "Historian": (
        "You are the Historian. Your role: check what past experience and knowledge says about similar attempts. "
        "What patterns have been seen before? What succeeded or failed in analogous situations? "
        "Ground your response in evidence. 3-5 bullet points max."
    ),
    "Innovator": (
        "You are the Innovator. Your role: propose alternative approaches that haven't been considered. "
        "Think laterally. What unconventional path might work better? "
        "Be creative but realistic. 3-5 bullet points max."
    ),
    "Synthesizer": (
        "You are the Synthesizer. You have seen the perspectives of the Advocate, Critic, Historian, and Innovator. "
        "Your role: merge all perspectives into a single, balanced recommendation. "
        "What is the best path forward, considering all views? "
        "Produce a clear, actionable recommendation in 3-6 sentences."
    ),
}


class CouncilAgent:
    """5-subagent deliberation council for complex or ambiguous tasks."""

    def __init__(
        self,
        provider: LLMProvider,
        model: str,
        config: AKMSConfig,
    ) -> None:
        self._provider = provider
        self._model = model
        self._config = config

    def _consult_role(self, system_prompt: str, task: str, context: str) -> str:
        """Run a single council member conversation and return their perspective."""
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(
                role=Role.USER,
                content=f"Task under consideration:\n{task}\n\nContext:\n{context}",
            ),
        ]
        response = self._provider.chat(messages, model=self._model)
        return response.message.content

    def _gather_perspectives(self, task: str, context: str) -> dict[str, str]:
        """Run the four non-Synthesizer roles and return their perspectives."""
        perspectives: dict[str, str] = {}
        for role, system_prompt in _COUNCIL_ROLES.items():
            if role == "Synthesizer":
                continue
            perspectives[role] = self._consult_role(system_prompt, task, context)
        return perspectives

    def _synthesize(self, task: str, context: str, perspectives: dict[str, str]) -> str:
        perspective_block = "\n\n".join(
            f"## {role} Perspective\n{text}" for role, text in perspectives.items()
        )
        synth_context = (
            f"Original context:\n{context}\n\n"
            f"Council perspectives gathered:\n\n{perspective_block}"
        )
        return self._consult_role(_COUNCIL_ROLES["Synthesizer"], task, synth_context)

    def convene(self, task: str, context: str = "") -> str:
        """Run all 5 council roles and return the Synthesizer's recommendation."""
        perspectives = self._gather_perspectives(task, context)
        return self._synthesize(task, context, perspectives)

    def convene_detailed(self, task: str, context: str = "") -> dict[str, str]:
        """Like convene() but returns all perspectives including synthesis."""
        result = self._gather_perspectives(task, context)
        result["Synthesizer"] = self._synthesize(task, context, result)
        return result
