from __future__ import annotations

import json
from typing import TYPE_CHECKING

from akms.agents.base import BaseAgent
from akms.core.message import Message, Role

if TYPE_CHECKING:
    from akms.core.orchestrator import Orchestrator

_EXECUTOR_SYSTEM = """\
You are an AI assistant with access to a knowledge graph via the query_knowledge tool.
Use it when a question requires stored facts about a specific domain section.

Tool: query_knowledge
Usage: call with {"tool": "query_knowledge", "section": "<section_name>", "question": "<question>"}
Response comes back as a JSON block you can parse.

When knowledge graph queries are not needed, answer directly.
"""

_TOOL_CALL_MARKER = '{"tool": "query_knowledge"'


class ExecutorAgent(BaseAgent):
    """Primary reasoning agent. Queries experts for context, returns final response."""

    agent_type = "executor"

    def run(self, task: str, orchestrator: Orchestrator | None = None) -> str:
        """Execute a task, routing knowledge queries through the orchestrator."""
        messages: list[Message] = [
            Message(role=Role.SYSTEM, content=_EXECUTOR_SYSTEM),
            Message(role=Role.USER, content=task),
        ]
        response = self.send(messages)
        content = response.message.content

        # Handle tool calls (simple text-based tool protocol)
        max_rounds = 5
        rounds = 0
        while orchestrator and _TOOL_CALL_MARKER in content and rounds < max_rounds:
            tool_result = self._handle_tool_calls(content, orchestrator)
            follow_up = [
                Message(role=Role.USER, content=f"Tool result:\n{tool_result}\n\nContinue."),
            ]
            response = self.send(follow_up)
            content = response.message.content
            rounds += 1

        return content

    def _handle_tool_calls(self, content: str, orchestrator: Orchestrator) -> str:
        """Extract and execute query_knowledge tool calls from response content."""
        results: list[str] = []
        # Find JSON blocks in the content
        start = 0
        while True:
            idx = content.find(_TOOL_CALL_MARKER, start)
            if idx == -1:
                break
            # Find matching closing brace
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
                section = call.get("section", "")
                question = call.get("question", "")
                if section and question:
                    answer = orchestrator.query_expert(section, question)
                    results.append(f"[{section}] {answer}")
                else:
                    results.append("[error] missing section or question in tool call")
            except Exception as e:
                results.append(f"[error] {e}")
            start = end

        return "\n".join(results) if results else "[no tool results]"
