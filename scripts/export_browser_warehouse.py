"""Export the seed-42 warehouse and the Python check results for the static site.

The browser runs the same checks with DuckDB-WASM. This script only freezes the
inputs (parquet, golden file, suite, defect catalog) and the Python reference
output used to prove the browser engine matches.
"""

from __future__ import annotations

import json
from pathlib import Path

from rutanorte_dq.engine import run_suite
from rutanorte_dq.evaluate import evaluate_results, load_defects
from rutanorte_dq.paths import repo_root
from rutanorte_dq.scoring import DAY_TABLE
from rutanorte_dq.suite import load_suite
from rutanorte_dq.synthetic import generate
from rutanorte_dq.warehouse import connect

TABLES = ("hubs", "customers", "tracking_scans", "shipments", "daily_route_kpis")


def _check_dict(check) -> dict:
    return {
        "id": check.id,
        "type": check.type,
        "severity": check.severity,
        "description": check.description,
        "scope": check.scope,
        "column": check.column,
        "columns": list(check.columns),
        "max_null_rate": check.max_null_rate,
        "max_invalid_rate": check.max_invalid_rate,
        "format": check.format,
        "values": list(check.values),
        "references_table": check.references_table,
        "references_column": check.references_column,
        "timestamp_column": check.timestamp_column,
        "deadline_hours": check.deadline_hours,
        "window_days": check.window_days,
        "max_deviation_pct": check.max_deviation_pct,
        "threshold": check.threshold,
        "bins": check.bins,
        "numeric": check.numeric,
        "metrics": [
            {
                "name": metric.name,
                "expression": metric.expression,
                "tolerance_abs": metric.tolerance_abs,
                "tolerance_pct": metric.tolerance_pct,
            }
            for metric in check.metrics
        ],
    }


def _suite_dict(suite) -> dict:
    return {
        "name": suite.name,
        "description": suite.description,
        "as_of": suite.as_of.isoformat(),
        "pass_score": suite.pass_score,
        "fail_on_critical": suite.fail_on_critical,
        "severity_weights": suite.severity_weights,
        "nodes": [
            {"id": node.id, "label": node.label, "layer": node.layer} for node in suite.nodes
        ],
        "lineage": [{"from": edge.source, "to": edge.target} for edge in suite.lineage],
        "tables": [
            {
                "name": table.name,
                "business_date_column": table.business_date_column,
                "key": table.key,
                "checks": [_check_dict(check) for check in table.checks],
            }
            for table in suite.tables
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    root = repo_root()
    out = root / "site" / "data"
    out.mkdir(parents=True, exist_ok=True)
    db_path = out / "_export.duckdb"
    if db_path.exists():
        db_path.unlink()
    golden_tmp = out / "_export_golden.csv"
    truth_tmp = out / "_export_defects.yaml"
    summary = generate(db_path, golden_tmp, truth_tmp, seed=42)
    repo_golden = root / "data" / "golden" / "shipment_daily_totals.csv"
    generated_golden = golden_tmp.read_text(encoding="utf-8")
    if generated_golden != repo_golden.read_text(encoding="utf-8"):
        raise SystemExit(
            "Generated golden file does not match data/golden/shipment_daily_totals.csv"
        )
    (out / "golden.csv").write_text(generated_golden, encoding="utf-8")

    suite = load_suite(root / "checks" / "rutanorte_daily.yaml", root=root)
    connection = connect(db_path)
    try:
        for table in TABLES:
            destination = (out / f"{table}.parquet").as_posix()
            connection.execute(f"COPY {table} TO '{destination}' (FORMAT PARQUET)")
        output = run_suite(connection, suite)
    finally:
        connection.close()

    defects = load_defects(root / "data" / "ground_truth" / "injected_defects.yaml")
    evaluation = evaluate_results(output["results"], defects)
    _write_json(
        out / "suite.json",
        _suite_dict(suite),
    )
    _write_json(
        out / "defects.json",
        {
            "description": "Labeled defects injected into the synthetic warehouse.",
            "seed": 42,
            "defects": [
                {
                    "id": defect.defect_id,
                    "business_date": defect.business_date.isoformat(),
                    "table": defect.table,
                    "check_id": defect.check_id,
                    "defect_type": defect.defect_type,
                    "description": defect.description,
                    "min_failed_rows": defect.min_failed_rows,
                }
                for defect in defects
            ],
        },
    )
    _write_json(
        out / "reference_results.json",
        {
            "seed": 42,
            "as_of": suite.as_of.isoformat(),
            "evaluation": evaluation.as_dict(),
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
                for score in output["scores"]
                if score.table_name == DAY_TABLE
            ],
            "results": [
                {
                    "business_date": row.business_date.isoformat(),
                    "check_id": row.check_id,
                    "table_name": row.table_name,
                    "check_type": row.check_type,
                    "severity": row.severity,
                    "status": row.status,
                    "metric_name": row.metric_name,
                    "metric_value": None if row.metric_value is None else float(row.metric_value),
                    "failed_row_count": int(row.failed_row_count),
                    "total_row_count": int(row.total_row_count),
                }
                for row in output["results"]
            ],
        },
    )
    check_count = sum(len(table.checks) for table in suite.tables)
    _write_json(
        out / "manifest.json",
        {
            "seed": summary["seed"],
            "window_start": summary["window_start"],
            "window_end": summary["window_end"],
            "days": summary["days"],
            "counts": {table: summary[table] for table in TABLES},
            "checks": check_count,
            "defects": summary["defects"],
            "suite": "checks/rutanorte_daily.yaml",
            "generator": "rutanorte-dq generate --seed 42",
            "engine": "src/rutanorte_dq/engine.py",
            "browser_engine": "site/js/engine.js",
        },
    )
    for leftover in (db_path, golden_tmp, truth_tmp, Path(str(db_path) + ".wal")):
        if leftover.exists():
            leftover.unlink()
    print(f"Exported {summary['shipments']} shipments and {check_count} checks to {out}")


if __name__ == "__main__":
    main()
