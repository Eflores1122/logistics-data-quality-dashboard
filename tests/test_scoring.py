from datetime import date

from rutanorte_dq.results import CheckResult
from rutanorte_dq.scoring import score_group


def _row(status: str, severity: str) -> CheckResult:
    return CheckResult(
        business_date=date(2026, 10, 15),
        table_name="tracking_scans",
        check_id=f"{severity}-{status}",
        check_type="freshness",
        severity=severity,
        status=status,
        metric_name="lateness_hours",
        metric_value=12.0,
        threshold=0.0,
        comparator="<=",
        failed_row_count=0 if status == "pass" else 10,
        total_row_count=10,
        message="",
        description="",
    )


def test_critical_failure_fails_sla_even_when_the_score_is_high():
    results = [_row("pass", "critical") for _ in range(20)] + [_row("fail", "critical")]
    weights = {"critical": 5, "high": 3, "medium": 2, "low": 1}
    score = score_group(
        results,
        business_date=date(2026, 10, 15),
        table_name="tracking_scans",
        weights=weights,
        pass_score=95,
        fail_on_critical=True,
    )
    assert score.score > 95
    assert score.status == "fail"
    assert score.critical_failed == 1


def test_skipped_checks_do_not_change_the_score():
    results = [_row("pass", "high"), _row("skipped", "critical")]
    weights = {"critical": 5, "high": 3, "medium": 2, "low": 1}
    score = score_group(
        results,
        business_date=date(2026, 9, 1),
        table_name="transactions",
        weights=weights,
        pass_score=95,
        fail_on_critical=True,
    )
    assert score.score == 100
    assert score.status == "pass"
    assert score.checks_skipped == 1
    assert score.checks_total == 1
