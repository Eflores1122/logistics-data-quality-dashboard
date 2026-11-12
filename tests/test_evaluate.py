"""Detection metrics on a hand-built result list, away from the perfect reference run."""

from datetime import date
from types import SimpleNamespace

from rutanorte_dq.evaluate import Defect, evaluate_results


def _row(check_id: str, business_date: date, status: str, failed_rows: int):
    return SimpleNamespace(
        check_id=check_id,
        business_date=business_date,
        status=status,
        failed_row_count=failed_rows,
        table_name="shipments",
        message=check_id,
    )


def test_precision_and_recall_count_misses_and_unexpected_fails():
    day = date(2026, 10, 1)
    later = date(2026, 10, 2)
    results = [
        _row("caught", day, "fail", 10),
        _row("status_miss", day, "pass", 0),
        _row("row_miss", later, "fail", 1),
        _row("unexpected", later, "fail", 3),
    ]
    defects = [
        Defect("1", day, "shipments", "caught", "completeness", "caught", 5),
        Defect("2", day, "shipments", "status_miss", "completeness", "status miss", 1),
        Defect("3", later, "shipments", "row_miss", "completeness", "row minimum missed", 9),
    ]
    evaluation = evaluate_results(results, defects)
    assert evaluation.true_positives == 1
    assert evaluation.false_negatives == 2
    assert evaluation.false_positives == 1
    assert evaluation.precision == 0.5
    assert evaluation.recall == 1 / 3
    assert evaluation.row_level_applicable == 3
    assert evaluation.row_level_caught == 1
    assert evaluation.row_level_recall == 1 / 3
    assert [item["id"] for item in evaluation.missed] == ["2", "3"]
    assert evaluation.unexpected[0]["check_id"] == "unexpected"


def test_empty_catalog_and_no_failures_uses_the_empty_ratio():
    evaluation = evaluate_results([], [])
    assert evaluation.precision == 1
    assert evaluation.recall == 1
    assert evaluation.row_level_recall == 1
    assert evaluation.defects_total == 0
    assert evaluation.fails_total == 0
