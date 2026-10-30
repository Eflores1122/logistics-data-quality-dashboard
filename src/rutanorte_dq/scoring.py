"""Severity weights and per-table, per-day SLA scores."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

SCORED_STATUSES = {"pass", "fail", "error"}
DAY_TABLE = "__day__"


@dataclass(frozen=True)
class SlaScore:
    business_date: object
    table_name: str
    score: float
    status: str
    checks_total: int
    checks_failed: int
    checks_skipped: int
    critical_failed: int
    weight_passed: float
    weight_total: float


def weight_for(severity: str, weights: dict[str, float]) -> float:
    try:
        return float(weights[severity])
    except KeyError as exc:
        raise ValueError(f"Unknown severity {severity!r}") from exc


def score_group(
    results: list,
    *,
    business_date,
    table_name: str,
    weights: dict[str, float],
    pass_score: float,
    fail_on_critical: bool,
) -> SlaScore:
    skipped = [row for row in results if row.status == "skipped"]
    considered = [row for row in results if row.status in SCORED_STATUSES]
    weight_total = sum(weight_for(row.severity, weights) for row in considered)
    weight_passed = sum(
        weight_for(row.severity, weights) for row in considered if row.status == "pass"
    )
    failed = [row for row in considered if row.status != "pass"]
    critical_failed = sum(1 for row in failed if row.severity == "critical")
    score = 100.0 if weight_total == 0 else 100.0 * weight_passed / weight_total
    status = "pass"
    if score + 1e-9 < pass_score or (fail_on_critical and critical_failed > 0):
        status = "fail"
    return SlaScore(
        business_date=business_date,
        table_name=table_name,
        score=round(score, 4),
        status=status,
        checks_total=len(considered),
        checks_failed=len(failed),
        checks_skipped=len(skipped),
        critical_failed=critical_failed,
        weight_passed=weight_passed,
        weight_total=weight_total,
    )


def score_run(results: list, suite) -> list[SlaScore]:
    """Build one SLA row per table-day and one ``__day__`` rollup."""
    grouped: dict[tuple, list] = defaultdict(list)
    by_day: dict[object, list] = defaultdict(list)
    for row in results:
        grouped[(row.business_date, row.table_name)].append(row)
        by_day[row.business_date].append(row)

    scores: list[SlaScore] = []
    for (business_date, table_name), rows in sorted(
        grouped.items(), key=lambda item: (str(item[0][0]), item[0][1])
    ):
        scores.append(
            score_group(
                rows,
                business_date=business_date,
                table_name=table_name,
                weights=suite.severity_weights,
                pass_score=suite.pass_score,
                fail_on_critical=suite.fail_on_critical,
            )
        )
    for business_date, rows in sorted(by_day.items(), key=lambda item: str(item[0])):
        scores.append(
            score_group(
                rows,
                business_date=business_date,
                table_name=DAY_TABLE,
                weights=suite.severity_weights,
                pass_score=suite.pass_score,
                fail_on_critical=suite.fail_on_critical,
            )
        )
    return scores
