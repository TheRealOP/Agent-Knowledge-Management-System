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



# edited by gemini — init command to set up knowledge directory
@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the knowledge graph directory structure."""
    from pathlib import Path  # edited by gemini

    config = ctx.obj["config"]
    kc = config.knowledge

    # edited by gemini — create directory structure
    dirs = [kc.graph_dir, kc.archives_dir, kc.logs_dir]
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




if __name__ == "__main__":
    main()
