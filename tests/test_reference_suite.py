import json
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
    CLEAN_DAILY_WEIGHT_G,
    CLEAN_SHIPMENTS_PER_DAY,
    EXPECTED_DEFECTS,
    WINDOW_END,
    WINDOW_START,
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
    assert f"Precision: {evaluation.precision:.3f}" in report
    assert f"Recall: {evaluation.recall:.3f}" in report
    _assert_readme_matches_run(summary, suite, stored, evaluation)
    _assert_committed_samples_match_run(stored, evaluation)


def test_committed_catalog_matches_the_generator():
    catalog = ROOT / "data" / "ground_truth" / "injected_defects.yaml"
    defects = load_defects(catalog)
    assert [item.defect_id for item in defects] == [item["id"] for item in EXPECTED_DEFECTS]


def test_dashboard_source_compiles():
    py_compile.compile(str(ROOT / "dashboard" / "app.py"), doraise=True)


# Incident days called out in the README, including the clean calibration day.
_PUBLISHED_DAYS = (
    date(2026, 9, 20),
    date(2026, 10, 7),
    date(2026, 10, 8),
    date(2026, 10, 10),
    date(2026, 10, 11),
    date(2026, 10, 12),
    date(2026, 10, 13),
    date(2026, 10, 15),
)


def _assert_readme_matches_run(summary, suite, stored, evaluation) -> None:
    """The README figures have to be this run, not a separately typed table."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check_count = sum(len(table.checks) for table in suite.tables)
    days = {row.business_date: row for row in stored.scores if row.table_name == DAY_TABLE}
    failing_days = sum(1 for row in days.values() if row.status == "fail")
    precision = f"{evaluation.precision:.3f}"
    recall = f"{evaluation.recall:.3f}"
    row_level = (
        f"{evaluation.row_level_caught} / {evaluation.row_level_applicable} "
        f"({evaluation.row_level_recall:.3f})"
    )

    assert f"| Hubs | {summary['hubs']:,} |" in readme
    assert f"| Customers | {summary['customers']:,} |" in readme
    assert f"| Tracking scans | {summary['tracking_scans']:,} |" in readme
    assert f"| Shipments | {summary['shipments']:,} |" in readme
    assert f"| Published route-KPI days | {summary['daily_route_kpis']} |" in readme
    assert (
        f"| Clean day, before defects | {CLEAN_SHIPMENTS_PER_DAY:,} shipments and "
        f"{CLEAN_DAILY_WEIGHT_G:,.2f} g |"
    ) in readme
    assert f"| Declarative checks | {check_count} |" in readme
    assert f"| Check results stored | {len(stored.checks):,} |" in readme
    assert f"| Failing checks | {evaluation.fails_total} |" in readme
    assert f"| Injected defects | {evaluation.defects_total} |" in readme
    assert f"| Defects caught | {evaluation.defects_caught} |" in readme
    assert f"| Missed | {evaluation.false_negatives} |" in readme
    assert f"| Unexpected failing checks | {evaluation.false_positives} |" in readme
    assert f"| **Precision** | **{precision}** |" in readme
    assert f"| **Recall** | **{recall}** |" in readme
    assert f"| Row-level recall | {row_level} |" in readme
    assert f"{failing_days} days fail the SLA" in readme
    assert f"2026-09-20 scores **{days[date(2026, 9, 20)].score:.2f}**" in readme
    assert (
        f"2026-10-13 still **passes** the SLA at **{days[date(2026, 10, 13)].score:.2f}**" in readme
    )
    assert f"2026-10-15 scores **{days[date(2026, 10, 15)].score:.2f}**" in readme

    weight = _check(stored, "shipments_weight_drift", date(2026, 10, 8))
    channel = _check(stored, "shipments_channel_drift", date(2026, 10, 13))
    freshness = _check(stored, "scans_freshness", date(2026, 10, 15))
    assert f"PSI {weight.metric_value:.2f}" in readme
    assert f"PSI {channel.metric_value:.2f}" in readme
    assert f"{freshness.metric_value:.2f} hours late" in readme

    assert f"Window: {WINDOW_START.isoformat()} to {WINDOW_END.isoformat()}" in readme
    assert (
        f"Injected defects: {evaluation.defects_total}; caught: {evaluation.defects_caught}; "
        f"missed: {evaluation.false_negatives}; unexpected fails: {evaluation.false_positives}"
    ) in readme
    assert f"Precision: {precision}" in readme
    assert f"Recall: {recall}" in readme
    assert (
        f"Row-level recall: {evaluation.row_level_caught}/{evaluation.row_level_applicable} "
        f"({evaluation.row_level_recall:.3f})"
    ) in readme
    for business_date in _PUBLISHED_DAYS:
        row = days[business_date]
        assert (
            f"  {business_date.isoformat()}  score={row.score:.2f}  sla={row.status}  "
            f"failed={row.checks_failed}  critical={row.critical_failed}"
        ) in readme


def _check(stored, check_id: str, business_date: date):
    return next(
        row
        for row in stored.checks
        if row.check_id == check_id and row.business_date == business_date
    )


def _assert_committed_samples_match_run(stored, evaluation) -> None:
    """Committed sample files have to carry this run's detection result."""
    fresh_days = {
        row.business_date.isoformat(): row for row in stored.scores if row.table_name == DAY_TABLE
    }
    for relative in ("reports/evaluation.json", "site/data/reference_results.json"):
        payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        committed = payload["evaluation"]
        fresh = evaluation.as_dict()
        for key in (
            "defects_total",
            "defects_caught",
            "fails_total",
            "true_positives",
            "false_positives",
            "false_negatives",
            "row_level_applicable",
            "row_level_caught",
        ):
            assert committed[key] == fresh[key], relative
        assert committed["precision"] == pytest.approx(fresh["precision"])
        assert committed["recall"] == pytest.approx(fresh["recall"])
        assert committed["row_level_recall"] == pytest.approx(fresh["row_level_recall"])
        assert committed["missed"] == []
        assert committed["unexpected"] == []
        assert len(payload["days"]) == len(fresh_days)
        for day in payload["days"]:
            row = fresh_days[day["business_date"]]
            assert day["score"] == pytest.approx(row.score), relative
            assert day["status"] == row.status
            assert day["checks_failed"] == row.checks_failed
            assert day["critical_failed"] == row.critical_failed
