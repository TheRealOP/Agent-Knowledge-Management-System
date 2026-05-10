from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from akms.core.message import Message, Role

if TYPE_CHECKING:
    from akms.core.orchestrator import Orchestrator

_AKMS_SYSTEM_PREAMBLE = """\
You have access to an AKMS knowledge graph. Use the query_knowledge tool to look up
domain knowledge stored in the graph before answering complex questions.

Available tool:
  query_knowledge(section, question) — queries the expert for a knowledge section.
  Usage: emit a JSON object: {"tool": "query_knowledge", "section": "...", "question": "..."}

Available sections: {sections}
"""


class GenericWrapper:
    """Wraps any provider+orchestrator to inject AKMS capabilities."""

    def __init__(self, orchestrator: Orchestrator, extra_system: str = "") -> None:
        self._orchestrator = orchestrator
        self._extra_system = extra_system

    def _build_system_prompt(self) -> str:
        sections = ", ".join(self._orchestrator.list_sections()) or "none yet"
        prompt = _AKMS_SYSTEM_PREAMBLE.format(sections=sections)
        if self._extra_system:
            prompt = prompt + "\n\n" + self._extra_system
        return prompt

    def wrap_messages(self, user_messages: list[Message]) -> list[Message]:
        """Prepend the AKMS system prompt to a message list."""
        system = Message(role=Role.SYSTEM, content=self._build_system_prompt())
        return [system] + list(user_messages)

    def handle_tool_call(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """Route a single parsed tool call to the orchestrator."""
        if tool_name == "query_knowledge":
            section = tool_args.get("section", "")
            question = tool_args.get("question", "")
            if section and question:
                return self._orchestrator.query_expert(section, question)
            return "[error] query_knowledge requires 'section' and 'question'"
        return f"[error] unknown tool: {tool_name}"

    def run(self, user_input: str, provider: Any, model: str) -> str:
        """Send wrapped message through the provider, handle tool calls, return final response."""
        messages = self.wrap_messages([Message(role=Role.USER, content=user_input)])

        max_rounds = 5
        for _ in range(max_rounds):
            response = provider.chat(messages, model=model)
            content = response.message.content

            # Check for tool call JSON blocks
            tool_marker = '{"tool":'
            if tool_marker not in content:
                return content

            # Parse and execute tool calls
            tool_results: list[str] = []
            start = 0
            while True:
                idx = content.find(tool_marker, start)
                if idx == -1:
                    break
                depth = 0
                end = idx
                for i, ch in enumerate(content[idx:], idx):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                try:
                    call = json.loads(content[idx:end])
                    result = self.handle_tool_call(call.get("tool", ""), call)
                    tool_results.append(result)
                except Exception as e:
                    tool_results.append(f"[error] {e}")
                start = end

            messages.append(response.message)
            messages.append(
                Message(
                    role=Role.USER,
                    content="Tool results:\n" + "\n".join(tool_results) + "\n\nContinue.",
                )
            )

        return content
