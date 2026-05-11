# edited by gemini
"""AKMS CLI — entry point for the Agent Knowledge Management System."""

from __future__ import annotations

import click

from akms import __version__
from akms.config import load_config
from akms.providers.registry import build_default_registry


# edited by gemini — main CLI group
@click.group()
@click.version_option(version=__version__, prog_name="akms")
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to akms_config.yaml",
)
@click.pass_context
def main(ctx: click.Context, config_path: str | None) -> None:
    """AKMS — Agent Knowledge Management System.

    A provider-agnostic, multi-agent knowledge management system.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)
    ctx.obj["registry"] = build_default_registry()


# edited by gemini — status command
@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system status — config, providers, knowledge graph."""
    config = ctx.obj["config"]
    registry = ctx.obj["registry"]

    click.echo(f"AKMS v{__version__}")
    click.echo()

    # edited by gemini — show configured providers
    click.echo("Configured providers:")
    for name, pc in config.providers.items():
        has_key = "✓" if pc.api_key else "✗"
        available = "loaded" if name in registry.available() else "missing deps"
        click.echo(f"  {name}: key={has_key}  models={pc.models}  ({available})")

    click.echo()

    # edited by gemini — show agent assignments
    click.echo("Agent assignments:")
    for role, assign in config.agent_assignments.items():
        click.echo(f"  {role}: {assign.provider}/{assign.model}")

    click.echo()

    # edited by gemini — show budget settings
    click.echo("Budget:")
    click.echo(f"  Daily limit: ${config.budget.daily_limit_usd:.2f}")
    click.echo(f"  Per-query warn: ${config.budget.per_query_warn_usd:.2f}")
    click.echo(f"  Token tracking: {config.budget.track_tokens}")


# edited by gemini — init command to set up knowledge directory
@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the knowledge graph directory structure."""
    from pathlib import Path  # edited by gemini

    config = ctx.obj["config"]
    kc = config.knowledge

    # edited by gemini — create directory structure
    dirs = [kc.graph_dir, kc.archives_dir, kc.user_overlay_dir, kc.logs_dir]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        click.echo(f"  Created: {d}/")

    # edited by gemini — create starter index file
    index_path = Path(kc.graph_dir) / "_index.md"
    if not index_path.exists():
        index_path.write_text(
            "---\ntitle: Knowledge Graph Root\ncreated: auto\n---\n\n"
            "# Knowledge Graph\n\nThis is the root of your AKMS knowledge graph.\n"
            "Sections will appear here as the system learns.\n"
        )
        click.echo(f"  Created: {index_path}")

    # edited by gemini — create research queue
    rq_path = Path(kc.graph_dir).parent / "research_queue.md"
    if not rq_path.exists():
        rq_path.write_text(
            "# Research Queue\n\n"
            "## Pending (Awaiting Approval)\n\n"
            "## Approved\n\n"
            "## Completed\n"
        )
        click.echo(f"  Created: {rq_path}")

    click.echo("\n✓ Knowledge graph initialized.")


def _build_orchestrator(config: object, registry: object) -> object:
    """Build a fully-initialized Orchestrator from config + registry."""
    from akms.checkpoints.store import CheckpointStore
    from akms.config import AKMSConfig
    from akms.core.orchestrator import Orchestrator
    from akms.knowledge.graph import HybridGraph
    from akms.providers.registry import ProviderRegistry

    cfg: AKMSConfig = config  # type: ignore[assignment]
    reg: ProviderRegistry = registry  # type: ignore[assignment]

    graph = HybridGraph(cfg.knowledge)
    graph.init_graph_dirs()
    store = CheckpointStore(cfg.knowledge.checkpoints_db_path)
    store.init_db()
    return Orchestrator(config=cfg, registry=reg, graph=graph, checkpoint_store=store)


@main.command()
@click.pass_context
def chat(ctx: click.Context) -> None:
    """Start an interactive chat session with the Executor agent."""
    config = ctx.obj["config"]
    registry = ctx.obj["registry"]

    if not config.agent_assignments:
        click.echo("Error: no agent_assignments configured in akms_config.yaml", err=True)
        raise SystemExit(1)

    orchestrator = _build_orchestrator(config, registry)
    assignment = config.agent_assignments.get("executor")
    if not assignment:
        click.echo("Error: no 'executor' assignment in agent_assignments", err=True)
        raise SystemExit(1)

    from akms.agents.executor import ExecutorAgent
    from akms.logging.conversation_log import ConversationLogger

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        click.echo(f"Error: provider '{assignment.provider}' not configured", err=True)
        raise SystemExit(1)

    provider = registry.create_from_config(assignment.provider, provider_cfg)
    logger = ConversationLogger(config.knowledge.logs_dir)
    executor = ExecutorAgent(provider=provider, model=assignment.model, config=config, logger=logger)

    click.echo(f"AKMS Chat (executor/{assignment.model}) — type 'quit' to exit\n")
    while True:
        try:
            user_input = click.prompt("You", prompt_suffix="> ")
        except (click.Abort, EOFError):
            click.echo("\nGoodbye.")
            break
        if user_input.strip().lower() in {"quit", "exit", "q"}:
            click.echo("Goodbye.")
            break
        response = executor.run(user_input, orchestrator=orchestrator)
        click.echo(f"\nAssistant: {response}\n")


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def ingest(ctx: click.Context, file: str) -> None:
    """Ingest a document into the knowledge graph via the Librarian agent."""
    config = ctx.obj["config"]
    registry = ctx.obj["registry"]

    if not config.agent_assignments:
        click.echo("Error: no agent_assignments configured", err=True)
        raise SystemExit(1)

    assignment = config.agent_assignments.get("librarian")
    if not assignment:
        click.echo("Error: no 'librarian' assignment in agent_assignments", err=True)
        raise SystemExit(1)

    from akms.agents.librarian import LibrarianAgent
    from akms.knowledge.graph import HybridGraph

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        click.echo(f"Error: provider '{assignment.provider}' not configured", err=True)
        raise SystemExit(1)

    provider = registry.create_from_config(assignment.provider, provider_cfg)
    graph = HybridGraph(config.knowledge)
    graph.init_graph_dirs()
    librarian = LibrarianAgent(provider=provider, model=assignment.model, config=config)

    click.echo(f"Ingesting: {file}")
    count = librarian.digest_document(file, graph)
    click.echo(f"Done. {count} node(s) added to knowledge graph.")


def _build_graph(config: object) -> object:
    """Build a HybridGraph from config."""
    from akms.config import AKMSConfig
    from akms.knowledge.graph import HybridGraph

    cfg: AKMSConfig = config  # type: ignore[assignment]
    graph = HybridGraph(cfg.knowledge)
    graph.init_graph_dirs()
    return graph


@main.command()
@click.argument("query")
@click.option("--top-k", default=10, show_default=True, help="Max results to return")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def search(ctx: click.Context, query: str, top_k: int, as_json: bool) -> None:
    """Search the knowledge graph and return ranked results."""
    import json as _json

    config = ctx.obj["config"]
    graph = _build_graph(config)
    results = graph.search(query, top_k=top_k)

    if not results:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No results found.")
        return

    if as_json:
        payload = [
            {"id": node.get("id"), "section": node.get("section"), "title": node.get("title"), "score": score}
            for node, score in results
        ]
        click.echo(_json.dumps(payload, indent=2))
    else:
        for node, score in results:
            click.echo(f"  [{score:.0f}] {node.get('section')}/{node.get('id')}  {node.get('title', '')}")


@main.command()
@click.argument("section")
@click.argument("question")
@click.pass_context
def ask(ctx: click.Context, section: str, question: str) -> None:
    """Route a question to the Expert for a knowledge section."""
    config = ctx.obj["config"]
    registry = ctx.obj["registry"]

    assignment = config.agent_assignments.get("expert") or config.agent_assignments.get("librarian")
    if not assignment:
        click.echo("Error: no 'expert' or 'librarian' assignment in agent_assignments", err=True)
        raise SystemExit(1)

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        click.echo(f"Error: provider '{assignment.provider}' not configured", err=True)
        raise SystemExit(1)

    from akms.agents.expert import ExpertAgent

    graph = _build_graph(config)
    provider = registry.create_from_config(assignment.provider, provider_cfg)
    expert = ExpertAgent(section=section, provider=provider, model=assignment.model, config=config)
    count = expert.load_section(graph)
    if count == 0:
        click.echo(f"Warning: section '{section}' has no nodes.", err=True)
    click.echo(expert.answer(question))


@main.command()
@click.argument("path")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get(ctx: click.Context, path: str, as_json: bool) -> None:
    """Get full content of a node. PATH format: section/node-id"""
    import json as _json

    if "/" not in path:
        click.echo("Error: PATH must be section/node-id", err=True)
        raise SystemExit(1)

    section, node_id = path.split("/", 1)
    config = ctx.obj["config"]
    graph = _build_graph(config)
    node = graph.get_node(section, node_id)

    if node is None:
        click.echo(f"Node '{path}' not found.", err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(_json.dumps(node, indent=2, default=str))
    else:
        click.echo(f"# {node.get('title', node_id)}")
        click.echo(f"Section: {section}  |  ID: {node_id}")
        tags = node.get("tags") or []
        if tags:
            click.echo(f"Tags: {', '.join(tags)}")
        click.echo()
        click.echo(node.get("content", ""))


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def sections(ctx: click.Context, as_json: bool) -> None:
    """List all available knowledge sections."""
    import json as _json

    config = ctx.obj["config"]
    graph = _build_graph(config)
    section_names = graph.list_sections()

    if as_json:
        payload = [{"section": s, "node_count": len(graph.list_nodes(s))} for s in section_names]
        click.echo(_json.dumps(payload, indent=2))
    else:
        if not section_names:
            click.echo("No sections found.")
            return
        for s in section_names:
            count = len(graph.list_nodes(s))
            click.echo(f"  {s}  ({count} node{'s' if count != 1 else ''})")


@main.command()
@click.argument("section")
@click.argument("node_id")
@click.argument("reason")
@click.pass_context
def archive(ctx: click.Context, section: str, node_id: str, reason: str) -> None:
    """Archive a node — moves it out of the live graph."""
    config = ctx.obj["config"]
    registry = ctx.obj["registry"]

    assignment = config.agent_assignments.get("librarian")
    if not assignment:
        click.echo("Error: no 'librarian' assignment in agent_assignments", err=True)
        raise SystemExit(1)

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        click.echo(f"Error: provider '{assignment.provider}' not configured", err=True)
        raise SystemExit(1)

    from akms.agents.librarian import LibrarianAgent

    graph = _build_graph(config)
    provider = registry.create_from_config(assignment.provider, provider_cfg)
    librarian = LibrarianAgent(provider=provider, model=assignment.model, config=config)

    ok = librarian.archive_node(section, node_id, reason, graph)
    if not ok:
        click.echo(f"Node '{section}/{node_id}' not found.", err=True)
        raise SystemExit(1)
    click.echo(f"Archived {section}/{node_id}  (reason: {reason})")


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def check(ctx: click.Context, as_json: bool) -> None:
    """Find broken wikilinks across the knowledge graph."""
    import json as _json

    config = ctx.obj["config"]
    registry = ctx.obj["registry"]

    assignment = config.agent_assignments.get("librarian")
    if not assignment:
        click.echo("Error: no 'librarian' assignment in agent_assignments", err=True)
        raise SystemExit(1)

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        click.echo(f"Error: provider '{assignment.provider}' not configured", err=True)
        raise SystemExit(1)

    from akms.agents.librarian import LibrarianAgent

    graph = _build_graph(config)
    provider = registry.create_from_config(assignment.provider, provider_cfg)
    librarian = LibrarianAgent(provider=provider, model=assignment.model, config=config)

    issues = librarian.check_consistency(graph)

    if as_json:
        click.echo(_json.dumps(issues, indent=2))
    else:
        if not issues:
            click.echo("No broken wikilinks found.")
            return
        click.echo(f"{len(issues)} broken wikilink(s):")
        for item in issues:
            click.echo(f"  {item['section']}/{item['node_id']}  →  [[{item['broken_link']}]]")


@main.command()
@click.argument("task")
@click.argument("context", default="")
@click.option("--detailed", is_flag=True, help="Show all role perspectives, not just synthesis")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def council(ctx: click.Context, task: str, context: str, detailed: bool, as_json: bool) -> None:
    """Run 5-role Council deliberation and return a recommendation."""
    import json as _json

    config = ctx.obj["config"]
    registry = ctx.obj["registry"]

    assignment = config.agent_assignments.get("council") or config.agent_assignments.get("expert") or config.agent_assignments.get("librarian")
    if not assignment:
        click.echo("Error: no council/expert/librarian assignment in agent_assignments", err=True)
        raise SystemExit(1)

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        click.echo(f"Error: provider '{assignment.provider}' not configured", err=True)
        raise SystemExit(1)

    from akms.agents.council import CouncilAgent

    provider = registry.create_from_config(assignment.provider, provider_cfg)
    agent = CouncilAgent(provider=provider, model=assignment.model, config=config)

    if detailed or as_json:
        result = agent.convene_detailed(task, context)
        if as_json:
            click.echo(_json.dumps(result, indent=2))
        else:
            for role, text in result.items():
                click.echo(f"\n## {role}\n{text}")
    else:
        click.echo(agent.convene(task, context))


@main.command()
@click.pass_context
def research(ctx: click.Context) -> None:
    """Show the current research queue."""
    from pathlib import Path

    config = ctx.obj["config"]
    queue_path = Path(config.knowledge.graph_dir).parent / "research_queue.md"
    if not queue_path.exists():
        click.echo("Research queue not found. Run 'akms init' first.")
        return
    click.echo(queue_path.read_text())


@main.command()
@click.pass_context
def budget(ctx: click.Context) -> None:
    """Show today's token usage and cost."""
    config = ctx.obj["config"]
    log_path = config.budget.token_log_path

    from akms.logging.token_tracker import TokenTracker

    tracker = TokenTracker(log_path)
    records = tracker.load_today()
    if not records:
        click.echo("No token usage recorded today.")
        return

    total_tokens = sum(r.get("tokens", 0) for r in records)
    total_cost = sum(r.get("cost_usd", 0.0) for r in records)
    click.echo(f"Today's usage: {total_tokens:,} tokens  ${total_cost:.4f}")
    click.echo()
    by_provider: dict[str, float] = {}
    for r in records:
        p = r.get("provider", "unknown")
        by_provider[p] = by_provider.get(p, 0.0) + r.get("cost_usd", 0.0)
    for provider, cost in sorted(by_provider.items()):
        click.echo(f"  {provider}: ${cost:.4f}")

    if total_cost >= config.budget.daily_limit_usd:
        click.echo(f"\nWARNING: Daily limit (${config.budget.daily_limit_usd:.2f}) reached!")


@main.group()
@click.pass_context
def overlay(ctx: click.Context) -> None:
    """Manage user understanding overlays for knowledge concepts."""
    pass


@overlay.command(name="list")
@click.pass_context
def overlay_list(ctx: click.Context) -> None:
    """List all tracked concepts and understanding scores."""
    from akms.knowledge.user_overlay import UserOverlay

    config = ctx.obj["config"]
    uo = UserOverlay(config.knowledge.user_overlay_dir)
    concepts = uo.list_concepts()
    if not concepts:
        click.echo("No concepts tracked yet.")
        return
    for cid, data in sorted(concepts.items()):
        score = data.get("understanding", 0.0)
        notes = data.get("notes", "")
        reviewed = data.get("last_reviewed", "")
        click.echo(f"  {cid}: {score:.2f}  (reviewed: {reviewed})  {notes}")


@overlay.command(name="set")
@click.argument("concept_id")
@click.option("--score", type=float, required=True, help="Understanding score 0.0–1.0")
@click.option("--notes", default="", help="Optional notes about this concept")
@click.pass_context
def overlay_set(ctx: click.Context, concept_id: str, score: float, notes: str) -> None:
    """Set understanding score for a concept."""
    from akms.knowledge.user_overlay import UserOverlay

    config = ctx.obj["config"]
    uo = UserOverlay(config.knowledge.user_overlay_dir)
    uo.set_concept(concept_id, score, notes)
    clamped = max(0.0, min(1.0, score))
    click.echo(f"Set '{concept_id}' understanding to {clamped:.2f}")


@overlay.command(name="get")
@click.argument("concept_id")
@click.pass_context
def overlay_get(ctx: click.Context, concept_id: str) -> None:
    """Get understanding score for a concept."""
    from akms.knowledge.user_overlay import UserOverlay

    config = ctx.obj["config"]
    uo = UserOverlay(config.knowledge.user_overlay_dir)
    data = uo.get_concept(concept_id)
    if data is None:
        click.echo(f"Concept '{concept_id}' not found.")
        return
    score = data.get("understanding", 0.0)
    notes = data.get("notes", "")
    reviewed = data.get("last_reviewed", "")
    click.echo(f"{concept_id}: {score:.2f}  (reviewed: {reviewed})  {notes}")


@overlay.command(name="remove")
@click.argument("concept_id")
@click.pass_context
def overlay_remove(ctx: click.Context, concept_id: str) -> None:
    """Remove a concept from the overlay."""
    from akms.knowledge.user_overlay import UserOverlay

    config = ctx.obj["config"]
    uo = UserOverlay(config.knowledge.user_overlay_dir)
    removed = uo.remove_concept(concept_id)
    if removed:
        click.echo(f"Removed '{concept_id}'.")
    else:
        click.echo(f"Concept '{concept_id}' not found.")


if __name__ == "__main__":
    main()
