"""Typer command line interface for ChangeWeaver."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, cast

import typer

from changeweaver.application.services import (
    build_snapshot,
    check_contract,
    diff_snapshots,
    has_error_findings,
    impact_report,
    make_change_plan,
)
from changeweaver.domain.errors import ChangeWeaverError
from changeweaver.domain.models import ChangeSet, Finding, dataclass_value
from changeweaver.infrastructure.config import DEFAULT_CONFIG, load_contract
from changeweaver.infrastructure.filesystem import safe_root
from changeweaver.infrastructure.serialization import read_snapshot, write_snapshot
from changeweaver.presentation.renderers import (
    changes_result,
    envelope,
    impact_result,
    plan_result,
    render_html,
    render_json,
    render_mermaid,
    render_sarif,
    render_text_changes,
    render_text_findings,
    render_text_impact,
    render_text_plan,
    render_text_snapshot,
    snapshot_result,
)

app = typer.Typer(
    name="changeweaver",
    help="Explainable architecture contracts and change-impact analysis for Dart/Flutter repositories.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def init(
    path: Annotated[Path, typer.Argument(help="Repository root to initialize.")] = Path("."),
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing contract.")] = False,
) -> None:
    """Create a minimal ChangeWeaver contract and artifact directory."""

    try:
        root = safe_root(path)
        contract_path = root / "changeweaver.yaml"
        if contract_path.exists() and not force:
            raise ChangeWeaverError("changeweaver.yaml already exists; use --force to replace it")
        contract_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        (root / ".changeweaver" / "snapshots").mkdir(parents=True, exist_ok=True)
        typer.echo(f"Initialized ChangeWeaver in {root}")
        typer.echo("Next: edit changeweaver.yaml, then run changeweaver snapshot")
    except (ChangeWeaverError, OSError, ValueError) as exc:
        _fail(str(exc), 2)


@app.command()
def snapshot(
    root: Annotated[Path, typer.Option("--root", "-r", help="Repository root.")] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Snapshot output path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit the versioned JSON envelope.")] = False,
) -> None:
    """Analyze Dart files and write a deterministic snapshot."""

    try:
        repository = safe_root(root)
        contract = load_contract(repository)
        result = build_snapshot(repository, contract)
        path = output or Path(".changeweaver/snapshots/current.json")
        destination = path if path.is_absolute() else repository / path
        write_snapshot(destination, result)
        if json_output:
            typer.echo(render_json(envelope("snapshot", "ok", snapshot_result(result))))
        else:
            typer.echo(render_text_snapshot(result), nl=False)
            typer.echo(f"Wrote: {_display_path(destination, repository)}")
    except (ChangeWeaverError, OSError, ValueError) as exc:
        _fail(str(exc), 2)


@app.command()
def diff(
    baseline: Annotated[Path, typer.Option("--baseline", help="Baseline snapshot path.")] = Path(".changeweaver/snapshots/baseline.json"),
    current: Annotated[Path, typer.Option("--current", help="Current snapshot path.")] = Path(".changeweaver/snapshots/current.json"),
    json_output: Annotated[bool, typer.Option("--json", help="Emit the versioned JSON envelope.")] = False,
) -> None:
    """Compare two snapshots without reading or changing source files."""

    try:
        changes = diff_snapshots(read_snapshot(baseline), read_snapshot(current))
        if json_output:
            typer.echo(render_json(envelope("diff", "ok", changes_result(changes))))
        else:
            typer.echo(render_text_changes(changes), nl=False)
    except (ChangeWeaverError, OSError, ValueError) as exc:
        _fail(str(exc), 3 if "not comparable" in str(exc) else 2)


@app.command()
def impact(
    targets: Annotated[list[str], typer.Argument(help="File paths or node IDs to analyze.")],
    snapshot_path: Annotated[Path, typer.Option("--snapshot", help="Snapshot path.")] = Path(".changeweaver/snapshots/current.json"),
    max_nodes: Annotated[int, typer.Option("--max-nodes", min=1, help="Maximum affected nodes.")] = 10_000,
    max_path_samples: Annotated[int, typer.Option("--max-path-samples", min=1, help="Maximum explanation paths.")] = 8,
    json_output: Annotated[bool, typer.Option("--json", help="Emit the versioned JSON envelope.")] = False,
) -> None:
    """Compute the reverse dependency blast radius of one or more targets."""

    try:
        loaded = read_snapshot(snapshot_path)
        result = impact_report(loaded, tuple(targets), max_nodes, max_path_samples)
        status = "error" if result.diagnostics else "ok"
        if json_output:
            typer.echo(render_json(envelope("impact", status, impact_result(result), result.diagnostics)))
        else:
            typer.echo(render_text_impact(result), nl=False)
            for diagnostic in result.diagnostics:
                typer.echo(f"error: {diagnostic.message}", err=True)
        if result.diagnostics:
            raise typer.Exit(code=2)
    except typer.Exit:
        raise
    except (ChangeWeaverError, OSError, ValueError) as exc:
        _fail(str(exc), 2)


@app.command()
def check(
    root: Annotated[Path, typer.Option("--root", "-r", help="Repository root.")] = Path("."),
    strict: Annotated[bool, typer.Option("--strict", help="Treat unclassified nodes as errors.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit the versioned JSON envelope.")] = False,
    sarif: Annotated[bool, typer.Option("--sarif", help="Emit SARIF 2.1.0 instead of terminal output.")] = False,
) -> None:
    """Check the current repository graph against its architecture contract."""

    try:
        repository = safe_root(root)
        contract = load_contract(repository)
        snapshot_value = build_snapshot(repository, contract)
        findings = check_contract(snapshot_value, contract, strict)
        errors = has_error_findings(findings)
        if sarif:
            typer.echo(render_sarif(findings), nl=False)
        elif json_output:
            result = {"snapshot": snapshot_result(snapshot_value), "findings": [*map(_finding_dict, findings)]}
            typer.echo(render_json(envelope("check", "failed" if errors else "ok", result)))
        else:
            typer.echo(render_text_findings(findings), nl=False)
        if errors:
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except (ChangeWeaverError, OSError, ValueError) as exc:
        _fail(str(exc), 2)


@app.command()
def plan(
    root: Annotated[Path, typer.Option("--root", "-r", help="Repository root.")] = Path("."),
    target: Annotated[list[str] | None, typer.Option("--target", help="Optional impact target.")] = None,
    baseline: Annotated[Path | None, typer.Option("--baseline", help="Optional baseline snapshot.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit the versioned JSON envelope.")] = False,
) -> None:
    """Generate a no-mutation verification plan from current evidence."""

    try:
        repository = safe_root(root)
        contract = load_contract(repository)
        current = build_snapshot(repository, contract)
        if baseline is not None:
            changes = diff_snapshots(read_snapshot(baseline), current)
        else:
            changes = ChangeSet((), (), (), (), current.diagnostics)
        impact = (
            impact_report(
                current,
                tuple(target or ()),
                contract.limits.max_nodes,
                contract.limits.max_path_samples,
            )
            if target
            else None
        )
        findings = check_contract(current, contract)
        result = make_change_plan(changes, impact, findings)
        if json_output:
            typer.echo(render_json(envelope("plan", "ok", plan_result(result))))
        else:
            typer.echo(render_text_plan(result), nl=False)
    except (ChangeWeaverError, OSError, ValueError) as exc:
        _fail(str(exc), 2)


@app.command(name="render")
def render_snapshot(
    snapshot_path: Annotated[Path, typer.Argument(help="Snapshot path.")],
    format_name: Annotated[str, typer.Option("--format", help="json, mermaid, or html.")] = "json",
) -> None:
    """Render a snapshot artifact in a portable format."""

    try:
        loaded = read_snapshot(snapshot_path)
        if format_name == "json":
            typer.echo(render_json(snapshot_result(loaded)), nl=False)
        elif format_name == "mermaid":
            typer.echo(render_mermaid(loaded), nl=False)
        elif format_name == "html":
            typer.echo(render_html("ChangeWeaver snapshot", render_text_snapshot(loaded)), nl=False)
        else:
            raise ChangeWeaverError("--format must be json, mermaid, or html")
    except (ChangeWeaverError, OSError, ValueError) as exc:
        _fail(str(exc), 2)


def _finding_dict(finding: Finding) -> dict[str, Any]:
    return cast(dict[str, Any], dataclass_value(finding))


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _fail(message: str, code: int) -> None:
    typer.echo(f"changeweaver: error: {message}", err=True)
    raise typer.Exit(code=code)
