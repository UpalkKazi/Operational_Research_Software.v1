"""Command-line interface for deterministic OR Studio workflows (no AI provider needed)."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from src.modeling.format_detect import detect_format
from src.services import catalog, exporters
from src.services.interpretation import fmt
from src.services.model_entry import ParseOutcome, import_upload, parse_structured
from src.solvers.backends import SOLVER_ORDER, SOLVERS, availability, solve_spec

console = Console()
SYNTAX = click.Choice(["auto", "orlearn", "ampl"], case_sensitive=False)


@click.group()
@click.version_option(version="0.3.0")
def cli() -> None:
    """OR Studio: parse and solve compact optimization models."""


def _parse(source: str, syntax: str) -> ParseOutcome:
    fmt_key = syntax.lower()
    if fmt_key == "auto":
        detection = detect_format(source)
        if detection.format not in ("orlearn", "ampl"):
            raise click.ClickException(
                f"Could not tell the format ({detection.format}); pass --syntax orlearn or --syntax ampl."
            )
        fmt_key = detection.format
    outcome = parse_structured(source, fmt_key)
    if not outcome.ok:
        where = f"line {outcome.line}" + (f", column {outcome.column}" if outcome.column else "") if outcome.line else ""
        raise click.ClickException(f"{where + ': ' if where else ''}{outcome.message}")
    if outcome.spec is None:
        raise click.ClickException(outcome.message or "This OR-Learn call has no solvable linear model.")
    return outcome


def _load(problem, file) -> tuple:
    if bool(problem) == bool(file):
        raise click.UsageError("Provide exactly one of --problem or --file.")
    if file and file.name.lower().endswith((".mps", ".mps.gz")):
        imported = import_upload(file.name, file.read_bytes())
        if not imported.ok:
            raise click.ClickException(imported.message)
        return imported.spec, None
    return None, file.read_text(encoding="utf-8") if file else problem


@cli.command()
@click.option("--problem", "-p", help="Inline OR-Learn or AMPL-style model.")
@click.option("--file", "-f", type=click.Path(exists=True, path_type=Path), help="Model file (.mod/.txt/.py/.mps/.mps.gz).")
@click.option("--syntax", type=SYNTAX, default="auto", show_default=True)
@click.option("--solver", "-s", type=click.Choice(SOLVER_ORDER), default="auto", show_default=True)
@click.option("--max-time", default=60, type=click.IntRange(1, 86400), show_default=True)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Write the result as JSON.")
def solve(problem, file, syntax, solver, max_time, output) -> None:
    """Validate and solve a model without an AI API."""
    spec, source = _load(problem, file)
    if spec is None:
        spec = _parse(source, syntax).spec
    result = solve_spec(spec, solver, max_time)

    console.print(f"[bold]{result['status']}[/bold] · objective {fmt(result['objective'])} · {result.get('backend') or SOLVERS[solver]['full']}")
    if result.get("explanation"):
        console.print(f"[dim]{result['explanation']}[/dim]")
    for message in result.get("messages", []):
        console.print(f"[yellow]{message}[/yellow]")

    table = Table(title="Decision variables")
    table.add_column("Variable", style="cyan")
    table.add_column("Value", justify="right")
    for name, value in result.get("variables", {}).items():
        table.add_row(name, "—" if value is None else fmt(value))
    console.print(table)

    if output:
        output.write_text(exporters.result_json(result, spec, {"solver": solver, "time_limit": max_time}), encoding="utf-8")
        console.print(f"[dim]Saved {output}[/dim]")
    if result["kind"] != "optimal":
        raise click.exceptions.Exit(2)


@cli.command("validate")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--syntax", type=SYNTAX, default="auto")
def validate_model(file: Path, syntax: str) -> None:
    """Validate a model without solving it."""
    outcome = _parse(file.read_text(encoding="utf-8"), syntax)
    stats = outcome.spec.stats()
    console.print(f"[green]Valid {outcome.format.upper()} model[/green]")
    console.print(f"{stats['variables']} variables · {stats['constraints']} constraints")


@cli.command()
def examples() -> None:
    """List bundled, attributed starter models."""
    table = Table(title="OR Studio examples")
    for column in ("ID", "Category", "Format", "Title", "Source"):
        table.add_column(column, style="cyan" if column == "ID" else None)
    for example in catalog.EXAMPLES:
        table.add_row(example["id"], example["category"], example["format"], example["title"], example["source"])
    console.print(table)


@cli.command()
def solvers() -> None:
    """Show solver availability."""
    table = Table(title="Solver backends")
    for column in ("Key", "Solver", "Available", "Version / reason"):
        table.add_column(column, style="cyan" if column == "Key" else None)
    info = availability()
    for key in SOLVER_ORDER:
        row = info[key]
        table.add_row(key, SOLVERS[key]["full"], "[green]Yes[/green]" if row["available"] else "[red]No[/red]",
                      row["version"] or row["reason"])
    console.print(table)


if __name__ == "__main__":
    cli()
