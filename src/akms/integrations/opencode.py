from __future__ import annotations

from typing import TYPE_CHECKING

from akms.integrations.generic import GenericWrapper

if TYPE_CHECKING:
    from akms.core.orchestrator import Orchestrator

_OPENCODE_ADDENDUM = """\
You are running inside OpenCode. When querying the knowledge graph,
prefer concise answers that integrate with the coding workflow.
Reference graph paths as `graph:section/node-id`.
Check the knowledge graph for architectural decisions and project patterns before suggesting code changes.
"""


class OpenCodeWrapper(GenericWrapper):
    def __init__(self, orchestrator: Orchestrator) -> None:
        super().__init__(orchestrator=orchestrator, extra_system=_OPENCODE_ADDENDUM)
