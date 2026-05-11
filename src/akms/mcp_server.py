"""AKMS MCP server — exposes knowledge graph operations as structured tools.

Start with:
    akms-mcp          (after pip install -e ".[mcp]")
    python -m akms.mcp_server

Config is read from the AKMS_CONFIG env var (path to akms_config.yaml).
Falls back to ./akms_config.yaml then ~/.akms/config.yaml per load_config() defaults.

Relative knowledge paths in the config are resolved relative to the config file's
directory, not the server's CWD (which is unpredictable when launched by Claude Code).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ── Module-level state (lazy, initialized on first tool call) ─────────────────

_state: dict[str, Any] = {}


def _find_config_dir(env_path: str | None) -> Path | None:
    """Return the parent directory of the config file that load_config() will use."""
    candidates = [
        Path(env_path) if env_path else None,
        Path("akms_config.yaml"),
        Path.home() / ".akms" / "config.yaml",
    ]
    for p in candidates:
        if p and p.exists():
            return p.resolve().parent
    return None


def _absolutize_knowledge_paths(config: Any, config_dir: Path) -> None:
    """Patch relative KnowledgeConfig paths to absolute using config file's directory.

    HybridGraph passes paths directly to Path(...), so relative paths are resolved
    against the server's CWD at runtime — which is unpredictable. We fix them here
    before any graph code sees them.
    """
    k = config.knowledge
    for attr in ("graph_dir", "archives_dir", "logs_dir", "db_path"):
        p = Path(getattr(k, attr))
        if not p.is_absolute():
            setattr(k, attr, str((config_dir / p).resolve()))


def _ensure_initialized() -> None:
    if _state:
        return

    from akms.config import load_config
    from akms.core.orchestrator import Orchestrator
    from akms.knowledge.graph import HybridGraph
    from akms.providers.registry import build_default_registry

    env_path = os.environ.get("AKMS_CONFIG")
    config_dir = _find_config_dir(env_path)
    config = load_config(env_path)
    if config_dir:
        _absolutize_knowledge_paths(config, config_dir)

    registry = build_default_registry()
    graph = HybridGraph(config.knowledge)
    graph.init_graph_dirs()
    orchestrator = Orchestrator(config, registry, graph)

    _state.update(
        config=config,
        graph=graph,
        registry=registry,
        orchestrator=orchestrator,
    )


def _build_librarian() -> Any:
    """Build a LibrarianAgent on demand. Raises ValueError if not configured."""
    from akms.agents.librarian import LibrarianAgent

    config = _state["config"]
    registry = _state["registry"]

    assignment = config.agent_assignments.get("librarian")
    if not assignment:
        raise ValueError("No 'librarian' in agent_assignments — add it to akms_config.yaml")

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        raise ValueError(f"Provider '{assignment.provider}' not found in config")

    provider = registry.create_from_config(assignment.provider, provider_cfg)
    return LibrarianAgent(provider=provider, model=assignment.model, config=config)


# ── MCP server ────────────────────────────────────────────────────────────────

mcp = FastMCP("akms")


@mcp.tool()
def search_graph(query: str, top_k: int = 10) -> str:
    """Search the AKMS knowledge graph by keyword. Returns ranked nodes as JSON."""
    try:
        _ensure_initialized()
        results = _state["graph"].search(query, top_k=top_k)
        payload = [
            {
                "id": node.get("id"),
                "section": node.get("section"),
                "title": node.get("title"),
                "score": score,
            }
            for node, score in results
        ]
        return json.dumps(payload)
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def ask_section(section: str, question: str) -> str:
    """Ask the Expert agent a question about a specific knowledge section.

    The Expert loads the section's knowledge nodes and answers using the configured
    LLM provider (typically claude-opus-4-6 via claude_cli). May take 30-120s.
    """
    try:
        _ensure_initialized()
        return _state["orchestrator"].query_expert(section, question)
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def get_node(section: str, node_id: str) -> str:
    """Retrieve the full content of a knowledge node. Returns JSON or error string."""
    try:
        _ensure_initialized()
        node = _state["graph"].get_node(section, node_id)
        if node is None:
            return f"ERROR: node '{section}/{node_id}' not found"
        return json.dumps(node)
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def list_sections() -> str:
    """List all knowledge sections with node counts. Returns JSON array."""
    try:
        _ensure_initialized()
        graph = _state["graph"]
        sections = graph.list_sections()
        payload = [
            {"section": s, "node_count": len(graph.list_nodes(s))}
            for s in sections
        ]
        return json.dumps(payload)
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def ingest_document(file_path: str) -> str:
    """Ingest a markdown document into the knowledge graph via the Librarian agent.

    Chunks the document by headings and classifies each chunk. May take 30-120s
    since it makes LLM calls per chunk.
    """
    try:
        _ensure_initialized()
        librarian = _build_librarian()
        count = librarian.digest_document(file_path, _state["graph"])
        return f"Added {count} node(s) from {file_path}"
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def archive_node(section: str, node_id: str, reason: str) -> str:
    """Archive (retire) a knowledge node. Moves it to archives with reason and timestamp."""
    try:
        _ensure_initialized()
        librarian = _build_librarian()
        success = librarian.archive_node(section, node_id, reason, _state["graph"])
        if success:
            return f"Archived {section}/{node_id} — reason: {reason}"
        return f"ERROR: node '{section}/{node_id}' not found"
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def check_consistency() -> str:
    """Find broken wikilinks across the entire knowledge graph. Returns JSON array."""
    try:
        _ensure_initialized()
        librarian = _build_librarian()
        issues = librarian.check_consistency(_state["graph"])
        return json.dumps(issues)
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def get_research_queue() -> str:
    """Return the current research queue (knowledge gaps flagged for investigation)."""
    try:
        _ensure_initialized()
        graph_dir = Path(_state["config"].knowledge.graph_dir)
        queue_path = graph_dir.parent / "research_queue.md"
        if not queue_path.exists():
            return "Research queue is empty."
        return queue_path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def get_status() -> str:
    """Return configured providers and agent assignments as a status summary."""
    try:
        _ensure_initialized()
        config = _state["config"]
        lines: list[str] = ["AKMS status\n"]

        lines.append("Providers:")
        for name, pc in config.providers.items():
            key_status = "key=✓" if pc.api_key else ("url=" + pc.base_url if pc.base_url else "no key")
            models = ", ".join(pc.models) if pc.models else "none"
            lines.append(f"  {name}: {key_status}  models=[{models}]")

        lines.append("\nAgent assignments:")
        for role, aa in config.agent_assignments.items():
            lines.append(f"  {role}: {aa.provider}/{aa.model}")

        lines.append("\nKnowledge paths:")
        k = config.knowledge
        lines.append(f"  graph:    {k.graph_dir}")
        lines.append(f"  archives: {k.archives_dir}")
        lines.append(f"  db:       {k.db_path}")

        return "\n".join(lines)
    except Exception as exc:
        return f"ERROR: {exc}"


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
