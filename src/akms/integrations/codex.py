from __future__ import annotations

from typing import TYPE_CHECKING

from akms.integrations.generic import GenericWrapper

if TYPE_CHECKING:
    from akms.core.orchestrator import Orchestrator

_CODEX_ADDENDUM = """\
You are running inside OpenAI Codex. When querying the knowledge graph,
prefer brief, structured answers. Reference graph paths as `graph:section/node-id`.
For code-related queries, always check the knowledge graph for project-specific conventions first.
"""


class CodexWrapper(GenericWrapper):
    def __init__(self, orchestrator: Orchestrator) -> None:
        super().__init__(orchestrator=orchestrator, extra_system=_CODEX_ADDENDUM)
