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


# edited by gemini — allow running as module
if __name__ == "__main__":
    main()
