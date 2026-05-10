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

    provider_cfg = config.providers.get(assignment.provider)
    if not provider_cfg:
        click.echo(f"Error: provider '{assignment.provider}' not configured", err=True)
        raise SystemExit(1)

    provider = registry.create_from_config(assignment.provider, provider_cfg)
    executor = ExecutorAgent(provider=provider, model=assignment.model, config=config)

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


if __name__ == "__main__":
    main()
