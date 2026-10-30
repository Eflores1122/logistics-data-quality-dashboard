"""Command line for the RutaNorte Paqueteria reference data-quality suite."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from rutanorte_dq.evaluate import evaluate_results, load_defects
from rutanorte_dq.history import load_run
from rutanorte_dq.paths import (
    default_db_path,
    default_golden_path,
    default_ground_truth_path,
    default_suite_path,
    repo_root,
)
from rutanorte_dq.report import render_html, render_markdown
from rutanorte_dq.scoring import DAY_TABLE
from rutanorte_dq.suite import load_suite
from rutanorte_dq.synthetic import WINDOW_END, WINDOW_START, generate
from rutanorte_dq.warehouse import connect

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Reference data-quality checks for the fictitious RutaNorte Paqueteria warehouse.",
)


@app.command("generate")
def generate_warehouse(
    db: Path | None = typer.Option(None, "--db", help="DuckDB file to create."),
    seed: int = typer.Option(42, "--seed", help="Deterministic synthetic-data seed."),
    golden: Path | None = typer.Option(None, "--golden", help="Golden daily-totals CSV."),
    ground_truth: Path | None = typer.Option(
        None, "--ground-truth", help="Injected-defect catalog to write."
    ),
) -> None:
    """Seed the local warehouse with synthetic data and labeled defects."""
    summary = generate(
        db or default_db_path(),
        golden or default_golden_path(),
        ground_truth or default_ground_truth_path(),
        seed=seed,
    )
    typer.echo(
        "Seeded {days} days ({window_start} to {window_end}): "
        "{customers} customers, {shipments} shipments, {defects} injected defects.".format(
            **summary
        )
    )
    typer.echo(f"Warehouse: {summary['db_path']}")


@app.command()
def run(
    db: Path | None = typer.Option(None, "--db", help="DuckDB warehouse."),
    suite: Path | None = typer.Option(None, "--suite", help="YAML check suite."),
) -> None:
    """Run the YAML suite and append results to the history tables."""
    from rutanorte_dq.engine import run_suite

    suite_path = suite or default_suite_path()
    loaded = load_suite(suite_path, root=repo_root())
    connection = connect(db or default_db_path())
    try:
        output = run_suite(connection, loaded)
    finally:
        connection.close()
    failed = sum(1 for row in output["results"] if row.status == "fail")
    typer.echo(
        f"Run {output['run_id']} stored {len(output['results'])} check results "
        f"({failed} failing) for as-of {loaded.as_of.isoformat()}."
    )


@app.command()
def evaluate(
    db: Path | None = typer.Option(None, "--db", help="DuckDB warehouse."),
    ground_truth: Path | None = typer.Option(None, "--ground-truth"),
    json_output: Path | None = typer.Option(
        None, "--json", help="Optional path for the evaluation JSON."
    ),
) -> None:
    """Compare the latest run with the injected-defect catalog."""
    connection = connect(db or default_db_path())
    try:
        stored = load_run(connection)
    finally:
        connection.close()
    if stored is None:
        raise typer.BadParameter("No data-quality run found. Run `rutanorte-dq run` first.")
    catalog = load_defects(ground_truth or default_ground_truth_path())
    result = evaluate_results(stored.checks, catalog)
    typer.echo(f"Window: {WINDOW_START.isoformat()} to {WINDOW_END.isoformat()}")
    typer.echo(f"Run: {stored.run_id} at {stored.run_ts} UTC")
    typer.echo(
        f"Injected defects: {result.defects_total}; caught: {result.defects_caught}; "
        f"missed: {result.false_negatives}; unexpected fails: {result.false_positives}"
    )
    typer.echo(f"Precision: {result.precision:.3f}")
    typer.echo(f"Recall: {result.recall:.3f}")
    typer.echo(
        f"Row-level recall: {result.row_level_caught}/{result.row_level_applicable} "
        f"({result.row_level_recall:.3f})"
    )
    typer.echo("Daily SLA:")
    for score in stored.scores:
        if score.table_name != DAY_TABLE:
            continue
        typer.echo(
            f"  {score.business_date.isoformat()}  score={score.score:.2f}  "
            f"sla={score.status}  failed={score.checks_failed}  "
            f"critical={score.critical_failed}"
        )
    if result.missed:
        typer.echo("Missed defects:")
        for item in result.missed:
            typer.echo(
                f"  {item['id']} {item['check_id']} {item['business_date']} status={item['status']}"
            )
    if result.unexpected:
        typer.echo("Unexpected failing checks:")
        for item in result.unexpected:
            typer.echo(f"  {item['business_date']} {item['check_id']}: {item['message']}")
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": stored.run_id,
            "run_ts": str(stored.run_ts),
            "as_of": stored.as_of.isoformat(),
            "evaluation": result.as_dict(),
            "days": [
                {
                    "business_date": score.business_date.isoformat(),
                    "score": score.score,
                    "status": score.status,
                    "checks_failed": score.checks_failed,
                    "critical_failed": score.critical_failed,
                    "checks_total": score.checks_total,
                    "checks_skipped": score.checks_skipped,
                }
                for score in stored.scores
                if score.table_name == DAY_TABLE
            ],
        }
        json_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        typer.echo(f"Wrote {json_output}")


@app.command()
def report(
    db: Path | None = typer.Option(None, "--db", help="DuckDB warehouse."),
    ground_truth: Path | None = typer.Option(None, "--ground-truth"),
    report_format: str = typer.Option("markdown", "--format", help="markdown or html."),
    output: Path | None = typer.Option(None, "--output", help="File to write. Defaults to stdout."),
) -> None:
    """Export the latest run as Markdown or HTML."""
    if report_format not in {"markdown", "html"}:
        raise typer.BadParameter("--format must be markdown or html")
    connection = connect(db or default_db_path())
    try:
        stored = load_run(connection)
    finally:
        connection.close()
    if stored is None:
        raise typer.BadParameter("No data-quality run found. Run `rutanorte-dq run` first.")
    catalog_path = ground_truth or default_ground_truth_path()
    evaluation = None
    if catalog_path.exists():
        evaluation = evaluate_results(stored.checks, load_defects(catalog_path))
    document = (
        render_html(stored, evaluation)
        if report_format == "html"
        else render_markdown(stored, evaluation)
    )
    if output is None:
        typer.echo(document)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    typer.echo(f"Wrote {output}")
