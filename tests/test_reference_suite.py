import py_compile
from datetime import date

import pytest

from rutanorte_dq.engine import run_suite
from rutanorte_dq.evaluate import evaluate_results, load_defects
from rutanorte_dq.history import load_run
from rutanorte_dq.paths import repo_root
from rutanorte_dq.report import render_markdown
from rutanorte_dq.scoring import DAY_TABLE
from rutanorte_dq.suite import load_suite
from rutanorte_dq.synthetic import (
    EXPECTED_DEFECTS,
    WINDOW_END,
    generate,
)
from rutanorte_dq.warehouse import connect

ROOT = repo_root()
SUITE_PATH = ROOT / "checks" / "rutanorte_daily.yaml"


def test_suite_covers_the_declared_check_types_and_defect_catalog():
    suite = load_suite(SUITE_PATH)
    kinds = {check.type for table in suite.tables for check in table.checks}
    assert {
        "completeness",
        "uniqueness",
        "validity",
        "accepted_values",
        "referential_integrity",
        "freshness",
        "volume_anomaly",
        "distribution_drift",
        "golden_reconciliation",
    } <= kinds
    formats = {check.format for table in suite.tables for check in table.checks}
    assert {"rfc_fisica", "rfc_moral", "curp", "email", "phone_mx"} <= formats
    assert suite.as_of == WINDOW_END
    missing = {item["check_id"] for item in EXPECTED_DEFECTS} - suite.check_ids()
    assert not missing


def test_reference_run_catches_every_injected_defect(tmp_path):
    db_path = tmp_path / "rutanorte.duckdb"
    golden = tmp_path / "data" / "golden" / "shipment_daily_totals.csv"
    catalog = tmp_path / "data" / "ground_truth" / "injected_defects.yaml"
    summary = generate(db_path, golden, catalog, seed=42)
    assert summary["defects"] == 20
    assert summary["shipments"] == 44220

    suite = load_suite(SUITE_PATH, root=tmp_path)
    connection = connect(db_path)
    try:
        run_suite(connection, suite)
        stored = load_run(connection)
    finally:
        connection.close()

    evaluation = evaluate_results(stored.checks, load_defects(catalog))
    assert evaluation.missed == []
    assert evaluation.unexpected == []
    assert evaluation.defects_caught == 20
    assert evaluation.precision == 1
    assert evaluation.recall == 1
    assert evaluation.row_level_recall == 1

    days = {row.business_date: row for row in stored.scores if row.table_name == DAY_TABLE}
    assert days[date(2026, 9, 20)].status == "pass"
    assert days[date(2026, 9, 20)].score == 100
    assert days[date(2026, 10, 7)].score == pytest.approx(90.4762)
    assert days[date(2026, 10, 8)].score == pytest.approx(93.3333)
    assert days[date(2026, 10, 10)].score == pytest.approx(79.0476)
    assert days[date(2026, 10, 10)].checks_failed == 8
    assert days[date(2026, 10, 11)].score == pytest.approx(80.9524)
    assert days[date(2026, 10, 12)].score == pytest.approx(92.381)
    assert days[date(2026, 10, 13)].status == "pass"
    assert days[date(2026, 10, 13)].score == pytest.approx(98.0952)
    assert days[date(2026, 10, 13)].checks_failed == 1
    assert days[date(2026, 10, 15)].status == "fail"
    assert days[date(2026, 10, 15)].score == pytest.approx(95.9016)
    assert days[date(2026, 10, 15)].critical_failed >= 1
    channel = next(
        row
        for row in stored.checks
        if row.check_id == "shipments_channel_drift" and row.business_date == date(2026, 10, 13)
    )
    assert channel.status == "fail"
    report = render_markdown(stored, evaluation)
    assert "Precision: 1.000" in report
    assert "Recall: 1.000" in report


def test_committed_catalog_matches_the_generator():
    catalog = ROOT / "data" / "ground_truth" / "injected_defects.yaml"
    defects = load_defects(catalog)
    assert [item.defect_id for item in defects] == [item["id"] for item in EXPECTED_DEFECTS]


def test_dashboard_source_compiles():
    py_compile.compile(str(ROOT / "dashboard" / "app.py"), doraise=True)
