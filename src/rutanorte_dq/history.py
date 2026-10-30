"""Read a persisted data-quality run back into plain objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from rutanorte_dq.warehouse import load_samples


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


@dataclass
class StoredCheck:
    business_date: date
    table_name: str
    check_id: str
    check_type: str
    severity: str
    status: str
    metric_name: str
    metric_value: float | None
    threshold: float | None
    comparator: str
    failed_row_count: int
    total_row_count: int
    message: str
    description: str
    sample_rows: list


@dataclass
class StoredScore:
    business_date: date
    table_name: str
    score: float
    status: str
    checks_total: int
    checks_failed: int
    checks_skipped: int
    critical_failed: int
    weight_passed: float
    weight_total: float


@dataclass
class StoredRun:
    run_id: str
    run_ts: datetime
    suite_name: str
    as_of: date
    suite_path: str | None
    pass_score: float
    fail_on_critical: bool
    checks: list[StoredCheck]
    scores: list[StoredScore]


def load_run(connection, run_id: str | None = None) -> StoredRun | None:
    if run_id is None:
        found = connection.execute(
            "SELECT run_id FROM dq.runs ORDER BY run_ts DESC LIMIT 1"
        ).fetchone()
        if found is None:
            return None
        run_id = found[0]
    header = connection.execute(
        """
        SELECT run_id, run_ts, suite_name, as_of, suite_path, pass_score, fail_on_critical
        FROM dq.runs
        WHERE run_id = ?
        """,
        [run_id],
    ).fetchone()
    if header is None:
        return None
    checks = [
        StoredCheck(
            business_date=_as_date(row[0]),
            table_name=row[1],
            check_id=row[2],
            check_type=row[3],
            severity=row[4],
            status=row[5],
            metric_name=row[6],
            metric_value=None if row[7] is None else float(row[7]),
            threshold=None if row[8] is None else float(row[8]),
            comparator=row[9],
            failed_row_count=int(row[10] or 0),
            total_row_count=int(row[11] or 0),
            message=row[12] or "",
            description=row[13] or "",
            sample_rows=load_samples(row[14]),
        )
        for row in connection.execute(
            """
            SELECT business_date, table_name, check_id, check_type, severity, status,
                   metric_name, metric_value, threshold, comparator, failed_row_count,
                   total_row_count, message, description, sample_rows
            FROM dq.check_results
            WHERE run_id = ?
            ORDER BY business_date, table_name, check_id
            """,
            [run_id],
        ).fetchall()
    ]
    scores = [
        StoredScore(
            business_date=_as_date(row[0]),
            table_name=row[1],
            score=float(row[2]),
            status=row[3],
            checks_total=int(row[4]),
            checks_failed=int(row[5]),
            checks_skipped=int(row[6]),
            critical_failed=int(row[7]),
            weight_passed=float(row[8]),
            weight_total=float(row[9]),
        )
        for row in connection.execute(
            """
            SELECT business_date, table_name, score, status, checks_total, checks_failed,
                   checks_skipped, critical_failed, weight_passed, weight_total
            FROM dq.sla_scores
            WHERE run_id = ?
            ORDER BY business_date, table_name
            """,
            [run_id],
        ).fetchall()
    ]
    return StoredRun(
        run_id=header[0],
        run_ts=header[1],
        suite_name=header[2],
        as_of=_as_date(header[3]),
        suite_path=header[4],
        pass_score=float(header[5]),
        fail_on_critical=bool(header[6]),
        checks=checks,
        scores=scores,
    )
