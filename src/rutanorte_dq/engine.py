"""Execute a declarative suite and append the run to the history tables.

Row-level checks are set-based SQL grouped by business date. Volume uses a
rolling median of prior days. Distribution drift compares each later day with
the pooled distribution of the first ``window_days`` dates, so an incident
cannot leak into the reference and raise follow-on alerts.
"""

from __future__ import annotations

import csv
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from rutanorte_dq.metrics import bin_edges, deviation_from_median, histogram, psi
from rutanorte_dq.results import CheckResult
from rutanorte_dq.scoring import score_run, weight_for
from rutanorte_dq.sql_safety import quote_ident
from rutanorte_dq.suite import CheckSpec, Suite, TableSpec
from rutanorte_dq.warehouse import FORMAT_TO_UDF, dump_samples, init_history

SAMPLE_LIMIT = 15


def run_suite(connection, suite: Suite) -> dict:
    init_history(connection)
    run_id = uuid.uuid4().hex
    run_ts = datetime.now(UTC).replace(microsecond=0, tzinfo=None)
    results: list[CheckResult] = []
    for table in suite.tables:
        for check in table.checks:
            results.extend(_run_check(connection, suite, table, check))
    scores = score_run(results, suite)
    _persist(connection, suite, run_id, run_ts, results, scores)
    return {"run_id": run_id, "run_ts": run_ts, "results": results, "scores": scores}


def _run_check(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    runners = {
        "completeness": _completeness,
        "uniqueness": _uniqueness,
        "validity": _validity,
        "accepted_values": _accepted_values,
        "referential_integrity": _referential,
        "freshness": _freshness,
        "volume_anomaly": _volume,
        "distribution_drift": _drift,
        "golden_reconciliation": _golden,
    }
    try:
        runner = runners[check.type]
    except KeyError as exc:
        raise ValueError(f"Unsupported check type {check.type}") from exc
    return runner(connection, suite, table, check)


def _result(
    table: TableSpec,
    check: CheckSpec,
    business_date: date,
    *,
    status: str,
    metric_name: str,
    metric_value: float | None,
    threshold: float | None,
    comparator: str,
    failed_row_count: int,
    total_row_count: int,
    message: str,
    sample_rows: list[dict] | None = None,
) -> CheckResult:
    return CheckResult(
        business_date=business_date,
        table_name=table.name,
        check_id=check.id,
        check_type=check.type,
        severity=check.severity,
        status=status,
        metric_name=metric_name,
        metric_value=metric_value,
        threshold=threshold,
        comparator=comparator,
        failed_row_count=failed_row_count,
        total_row_count=total_row_count,
        message=message,
        description=check.description,
        sample_rows=sample_rows or [],
    )


def _table(table: TableSpec) -> str:
    return quote_ident(table.name)


def _col(name: str) -> str:
    return quote_ident(name)


def _business_dates(connection, table: TableSpec) -> list[date]:
    if not table.business_date_column:
        return []
    rows = connection.execute(
        f"""
        SELECT DISTINCT {_col(table.business_date_column)} AS business_date
        FROM {_table(table)}
        WHERE {_col(table.business_date_column)} IS NOT NULL
        ORDER BY 1
        """
    ).fetchall()
    return [_coerce_date(row[0]) for row in rows]


def _coerce_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def _fetch_dicts(connection, sql: str, params: list | None = None) -> list[dict]:
    cursor = connection.execute(sql, params or [])
    columns = [item[0] for item in cursor.description]
    payload = []
    for row in cursor.fetchall():
        payload.append(
            {column: _jsonable(value) for column, value in zip(columns, row, strict=True)}
        )
    return payload


def _jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _date_predicate(
    table: TableSpec, check: CheckSpec, alias: str | None = None
) -> tuple[str, list]:
    if check.scope == "table":
        return "", []
    column = _col(table.business_date_column)
    if alias:
        column = f"{alias}.{column}"
    return f"{column} = ?", []


def _samples(
    connection,
    table: TableSpec,
    check: CheckSpec,
    business_date: date,
    where_sql: str,
    params: list,
) -> list[dict]:
    date_sql, _ = _date_predicate(table, check)
    clauses = [clause for clause in (date_sql, where_sql) if clause]
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order = f"ORDER BY {_col(table.key)}" if table.key else ""
    bound = list(params)
    if check.scope == "partition":
        bound = [business_date, *bound]
    sql = f"SELECT * FROM {_table(table)} {where} {order} LIMIT {SAMPLE_LIMIT}"
    return _fetch_dicts(connection, sql, bound)


def _grouped_metric(
    connection,
    table: TableSpec,
    check: CheckSpec,
    failed_sql: str,
    extra_select: str = "",
) -> list[tuple]:
    """Return ``(business_date, total, failed, ...)`` or one table-scoped row."""
    source = _table(table)
    if check.scope == "table":
        sql = f"""
            SELECT count(*) AS total, {failed_sql} AS failed {extra_select}
            FROM {source}
        """
        total, failed, *rest = connection.execute(sql).fetchone()
        return [(None, int(total), int(failed), *rest)]
    date_col = _col(table.business_date_column)
    sql = f"""
        SELECT {date_col} AS business_date,
               count(*) AS total,
               {failed_sql} AS failed
               {extra_select}
        FROM {source}
        GROUP BY 1
        ORDER BY 1
    """
    rows = []
    for business_date, total, failed, *rest in connection.execute(sql).fetchall():
        rows.append((_coerce_date(business_date), int(total), int(failed), *rest))
    return rows


def _completeness(
    connection, suite: Suite, table: TableSpec, check: CheckSpec
) -> list[CheckResult]:
    column = _col(check.column)
    failed_sql = (
        f"count(*) FILTER (WHERE {column} IS NULL OR length(trim(CAST({column} AS VARCHAR))) = 0)"
    )
    threshold = 0.0 if check.max_null_rate is None else check.max_null_rate
    results = []
    for business_date, total, failed in _grouped_metric(connection, table, check, failed_sql):
        when = suite.as_of if business_date is None else business_date
        rate = (failed / total) if total else 0.0
        status = "fail" if rate > threshold + 1e-12 else "pass"
        samples = []
        if status == "fail":
            samples = _samples(
                connection,
                table,
                check,
                when,
                f"({column} IS NULL OR length(trim(CAST({column} AS VARCHAR))) = 0)",
                [],
            )
        results.append(
            _result(
                table,
                check,
                when,
                status=status,
                metric_name="null_rate",
                metric_value=rate,
                threshold=threshold,
                comparator="<=",
                failed_row_count=failed if status == "fail" else 0,
                total_row_count=total,
                message=(
                    f"null rate {rate:.2%} ({failed} of {total} rows) exceeds {threshold:.2%}"
                    if status == "fail"
                    else f"null rate {rate:.2%} ({failed} of {total} rows) is within {threshold:.2%}"
                ),
                sample_rows=samples,
            )
        )
    return results


def _uniqueness(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    columns = check.columns or ((check.column,) if check.column else ())
    if not columns:
        raise ValueError(f"{check.id} requires columns")
    quoted = [_col(column) for column in columns]
    if check.scope == "table":
        group = ", ".join(quoted)
        sql = f"""
            WITH grouped AS (
                SELECT {group}, count(*) AS c
                FROM {_table(table)}
                GROUP BY {group}
            )
            SELECT coalesce(sum(c), 0) AS total,
                   coalesce(sum(CASE WHEN c > 1 THEN c ELSE 0 END), 0) AS failed
            FROM grouped
        """
        total, failed = connection.execute(sql).fetchone()
        measured = [(suite.as_of, int(total), int(failed))]
    else:
        date_col = _col(table.business_date_column)
        group = ", ".join([date_col, *quoted])
        sql = f"""
            WITH grouped AS (
                SELECT {date_col} AS business_date, {", ".join(quoted)}, count(*) AS c
                FROM {_table(table)}
                GROUP BY {group}
            )
            SELECT business_date,
                   coalesce(sum(c), 0) AS total,
                   coalesce(sum(CASE WHEN c > 1 THEN c ELSE 0 END), 0) AS failed
            FROM grouped
            GROUP BY 1
            ORDER BY 1
        """
        measured = [
            (_coerce_date(business_date), int(total), int(failed))
            for business_date, total, failed in connection.execute(sql).fetchall()
        ]
    results = []
    for business_date, total, failed in measured:
        status = "fail" if failed else "pass"
        samples = []
        if status == "fail":
            samples = _duplicate_samples(connection, table, check, business_date, columns)
        label = ", ".join(columns)
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="duplicate_rows",
                metric_value=float(failed),
                threshold=0.0,
                comparator="==",
                failed_row_count=failed,
                total_row_count=total,
                message=(
                    f"{failed} rows belong to duplicate {label} groups"
                    if status == "fail"
                    else f"{label} is unique across {total} rows"
                ),
                sample_rows=samples,
            )
        )
    return results


def _duplicate_samples(connection, table, check, business_date, columns) -> list[dict]:
    quoted = [_col(column) for column in columns]
    date_filter = ""
    params: list = []
    if check.scope == "partition":
        date_filter = f"WHERE {_col(table.business_date_column)} = ?"
        params.append(business_date)
    join_on = " AND ".join(
        f"src.{quoted[index]} = dup.{quoted[index]}" for index in range(len(quoted))
    )
    sql = f"""
        WITH dup AS (
            SELECT {", ".join(quoted)}
            FROM {_table(table)}
            {date_filter}
            GROUP BY {", ".join(quoted)}
            HAVING count(*) > 1
        )
        SELECT src.*
        FROM {_table(table)} AS src
        JOIN dup ON {join_on}
        {"WHERE src." + _col(table.business_date_column) + " = ?" if check.scope == "partition" else ""}
        LIMIT {SAMPLE_LIMIT}
    """
    if check.scope == "partition":
        params.append(business_date)
    return _fetch_dicts(connection, sql, params)


def _validity(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    if check.format not in FORMAT_TO_UDF:
        raise ValueError(f"{check.id} has unknown format {check.format!r}")
    function = FORMAT_TO_UDF[check.format]
    column = _col(check.column)
    present_sql = (
        f"count(*) FILTER (WHERE {column} IS NOT NULL "
        f"AND length(trim(CAST({column} AS VARCHAR))) > 0)"
    )
    failed_sql = (
        f"count(*) FILTER (WHERE {column} IS NOT NULL "
        f"AND length(trim(CAST({column} AS VARCHAR))) > 0 "
        f"AND NOT {function}(CAST({column} AS VARCHAR)))"
    )
    threshold = 0.0 if check.max_invalid_rate is None else check.max_invalid_rate
    source_rows = _grouped_metric(
        connection,
        table,
        check,
        failed_sql,
        extra_select=f", {present_sql} AS present",
    )
    results = []
    for business_date, total, failed, present in source_rows:
        when = suite.as_of if business_date is None else business_date
        rate = (failed / present) if present else 0.0
        status = "fail" if rate > threshold + 1e-12 else "pass"
        samples = []
        if status == "fail":
            samples = _samples(
                connection,
                table,
                check,
                when,
                (
                    f"{column} IS NOT NULL AND length(trim(CAST({column} AS VARCHAR))) > 0 "
                    f"AND NOT {function}(CAST({column} AS VARCHAR))"
                ),
                [],
            )
        results.append(
            _result(
                table,
                check,
                when,
                status=status,
                metric_name="invalid_rate",
                metric_value=rate,
                threshold=threshold,
                comparator="<=",
                failed_row_count=failed if status == "fail" else 0,
                total_row_count=total,
                message=(
                    f"{failed} of {present} non-blank values fail {check.format} "
                    f"(invalid rate {rate:.2%}, max {threshold:.2%})"
                    if status == "fail"
                    else f"{check.format} invalid rate {rate:.2%} is within {threshold:.2%}"
                ),
                sample_rows=samples,
            )
        )
    return results


def _accepted_values(
    connection, suite: Suite, table: TableSpec, check: CheckSpec
) -> list[CheckResult]:
    if not check.values:
        raise ValueError(f"{check.id} requires values")
    column = _col(check.column)
    placeholders = ", ".join(["?"] * len(check.values))
    failed_sql = (
        f"count(*) FILTER (WHERE {column} IS NULL "
        f"OR CAST({column} AS VARCHAR) NOT IN ({placeholders}))"
    )
    # Parameters cannot be embedded inside the grouped helper, so build SQL here.
    params = list(check.values)
    if check.scope == "table":
        sql = f"SELECT count(*) AS total, {failed_sql} AS failed FROM {_table(table)}"
        total, failed = connection.execute(sql, params).fetchone()
        measured = [(suite.as_of, int(total), int(failed))]
    else:
        date_col = _col(table.business_date_column)
        sql = f"""
            SELECT {date_col} AS business_date, count(*) AS total, {failed_sql} AS failed
            FROM {_table(table)}
            GROUP BY 1
            ORDER BY 1
        """
        measured = [
            (_coerce_date(business_date), int(total), int(failed))
            for business_date, total, failed in connection.execute(sql, params).fetchall()
        ]
    results = []
    for business_date, total, failed in measured:
        status = "fail" if failed else "pass"
        samples = []
        if status == "fail":
            samples = _samples(
                connection,
                table,
                check,
                business_date,
                f"({column} IS NULL OR CAST({column} AS VARCHAR) NOT IN ({placeholders}))",
                params,
            )
        allowed = ", ".join(check.values)
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="rejected_rows",
                metric_value=float(failed),
                threshold=0.0,
                comparator="==",
                failed_row_count=failed,
                total_row_count=total,
                message=(
                    f"{failed} of {total} rows are outside accepted values ({allowed})"
                    if status == "fail"
                    else f"all {total} rows are inside accepted values ({allowed})"
                ),
                sample_rows=samples,
            )
        )
    return results


def _referential(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    if not check.references_table or not check.references_column or not check.column:
        raise ValueError(f"{check.id} requires column and references")
    child = _col(check.column)
    parent_table = quote_ident(check.references_table)
    parent_column = _col(check.references_column)
    failed_sql = f"count(*) FILTER (WHERE parent.{parent_column} IS NULL)"
    join = (
        f"LEFT JOIN (SELECT DISTINCT {parent_column} FROM {parent_table}) AS parent "
        f"ON src.{child} = parent.{parent_column}"
    )
    if check.scope == "table":
        sql = f"SELECT count(*) AS total, {failed_sql} AS failed FROM {_table(table)} AS src {join}"
        total, failed = connection.execute(sql).fetchone()
        measured = [(suite.as_of, int(total), int(failed))]
    else:
        date_col = _col(table.business_date_column)
        sql = f"""
            SELECT src.{date_col} AS business_date, count(*) AS total, {failed_sql} AS failed
            FROM {_table(table)} AS src
            {join}
            GROUP BY 1
            ORDER BY 1
        """
        measured = [
            (_coerce_date(business_date), int(total), int(failed))
            for business_date, total, failed in connection.execute(sql).fetchall()
        ]
    results = []
    for business_date, total, failed in measured:
        status = "fail" if failed else "pass"
        samples = []
        if status == "fail":
            date_sql = ""
            params: list = []
            if check.scope == "partition":
                date_sql = f"AND src.{_col(table.business_date_column)} = ?"
                params.append(business_date)
            order = f"ORDER BY src.{_col(table.key)}" if table.key else ""
            samples = _fetch_dicts(
                connection,
                f"""
                SELECT src.*
                FROM {_table(table)} AS src
                {join}
                WHERE parent.{parent_column} IS NULL
                {date_sql}
                {order}
                LIMIT {SAMPLE_LIMIT}
                """,
                params,
            )
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="orphan_rows",
                metric_value=float(failed),
                threshold=0.0,
                comparator="==",
                failed_row_count=failed,
                total_row_count=total,
                message=(
                    f"{failed} of {total} rows reference a missing "
                    f"{check.references_table}.{check.references_column}"
                    if status == "fail"
                    else f"every row references {check.references_table}.{check.references_column}"
                ),
                sample_rows=samples,
            )
        )
    return results


def _freshness(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    if check.deadline_hours is None or not check.timestamp_column:
        raise ValueError(f"{check.id} requires timestamp_column and deadline_hours")
    timestamp = _col(check.timestamp_column)
    if check.scope == "table":
        sql = f"SELECT count(*) AS total, max({timestamp}) AS max_loaded FROM {_table(table)}"
        total, max_loaded = connection.execute(sql).fetchone()
        measured = [(suite.as_of, int(total), max_loaded)]
    else:
        date_col = _col(table.business_date_column)
        sql = f"""
            SELECT {date_col} AS business_date, count(*) AS total, max({timestamp}) AS max_loaded
            FROM {_table(table)}
            GROUP BY 1
            ORDER BY 1
        """
        measured = [
            (_coerce_date(business_date), int(total), max_loaded)
            for business_date, total, max_loaded in connection.execute(sql).fetchall()
        ]
    results = []
    for business_date, total, max_loaded in measured:
        deadline = datetime.combine(business_date, time.min) + timedelta(hours=check.deadline_hours)
        if max_loaded is None:
            lateness = None
            status = "fail"
            message = f"no {check.timestamp_column} value for {business_date.isoformat()}"
        else:
            loaded = (
                max_loaded.replace(tzinfo=None)
                if getattr(max_loaded, "tzinfo", None)
                else max_loaded
            )
            lateness = (loaded - deadline).total_seconds() / 3600
            status = "fail" if lateness > 1e-9 else "pass"
            message = (
                f"arrived {lateness:.2f} hours after the deadline "
                f"(loaded_at {loaded:%Y-%m-%d %H:%M}, deadline {deadline:%Y-%m-%d %H:%M})"
                if status == "fail"
                else (
                    f"arrived {-lateness:.2f} hours before the deadline "
                    f"(loaded_at {loaded:%Y-%m-%d %H:%M}, deadline {deadline:%Y-%m-%d %H:%M})"
                )
            )
        samples = []
        if status == "fail":
            samples = _samples(connection, table, check, business_date, "1 = 1", [])
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="lateness_hours",
                metric_value=None if lateness is None else float(lateness),
                threshold=0.0,
                comparator="<=",
                failed_row_count=total if status == "fail" else 0,
                total_row_count=total,
                message=message,
                sample_rows=samples,
            )
        )
    return results


def _volume(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    if check.scope != "partition":
        raise ValueError(f"{check.id} volume checks must be partition scoped")
    if check.max_deviation_pct is None:
        raise ValueError(f"{check.id} requires max_deviation_pct")
    window = check.window_days or 14
    date_col = _col(table.business_date_column)
    rows = connection.execute(
        f"""
        SELECT {date_col} AS business_date, count(*) AS n
        FROM {_table(table)}
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchall()
    series = [(_coerce_date(business_date), int(count)) for business_date, count in rows]
    results = []
    for index, (business_date, count) in enumerate(series):
        history = [value for _, value in series[max(0, index - window) : index]]
        if len(history) < window:
            results.append(
                _result(
                    table,
                    check,
                    business_date,
                    status="skipped",
                    metric_name="volume_deviation",
                    metric_value=None,
                    threshold=check.max_deviation_pct,
                    comparator="<=",
                    failed_row_count=0,
                    total_row_count=count,
                    message=f"skipped; need {window} prior days and have {len(history)}",
                )
            )
            continue
        deviation, center = deviation_from_median(count, history)
        finite = deviation != float("inf")
        status = "fail" if (not finite or deviation > check.max_deviation_pct + 1e-12) else "pass"
        gap = abs(count - int(round(center)))
        samples = []
        if status == "fail":
            samples = _samples(connection, table, check, business_date, "1 = 1", [])
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="volume_deviation",
                metric_value=None if not finite else float(deviation),
                threshold=check.max_deviation_pct,
                comparator="<=",
                failed_row_count=gap if status == "fail" else 0,
                total_row_count=count,
                message=(
                    f"row count {count} deviates {deviation:.2%} from the trailing {window}-day "
                    f"median {center:.0f} (limit {check.max_deviation_pct:.2%})"
                    if finite
                    else f"row count {count} cannot be compared with a zero median"
                ),
                sample_rows=samples,
            )
        )
    return results


def _drift(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    if check.scope != "partition":
        raise ValueError(f"{check.id} drift checks must be partition scoped")
    if check.threshold is None:
        raise ValueError(f"{check.id} requires threshold")
    window = check.window_days or 14
    if check.numeric:
        return _numeric_drift(connection, table, check, window)
    return _categorical_drift(connection, table, check, window)


def _categorical_drift(
    connection, table: TableSpec, check: CheckSpec, window: int
) -> list[CheckResult]:
    date_col = _col(table.business_date_column)
    column = _col(check.column)
    rows = connection.execute(
        f"""
        SELECT {date_col} AS business_date, CAST({column} AS VARCHAR) AS category, count(*) AS n
        FROM {_table(table)}
        GROUP BY 1, 2
        ORDER BY 1
        """
    ).fetchall()
    counts: dict[date, dict[str, int]] = defaultdict(dict)
    for business_date, category, count in rows:
        counts[_coerce_date(business_date)][str(category)] = int(count)
    dates = sorted(counts)
    return _psi_results(table, check, window, dates, counts)


def _numeric_drift(
    connection, table: TableSpec, check: CheckSpec, window: int
) -> list[CheckResult]:
    date_col = _col(table.business_date_column)
    column = _col(check.column)
    rows = connection.execute(
        f"""
        SELECT {date_col} AS business_date, CAST({column} AS DOUBLE) AS value, count(*) AS n
        FROM {_table(table)}
        GROUP BY 1, 2
        """
    ).fetchall()
    grouped: dict[date, list[tuple[float, int]]] = defaultdict(list)
    for business_date, value, count in rows:
        grouped[_coerce_date(business_date)].append((float(value), int(count)))
    dates = sorted(grouped)
    results = []
    bins = check.bins or 5
    for index, business_date in enumerate(dates):
        total = sum(count for _, count in grouped[business_date])
        if index < window:
            results.append(_skip_drift(table, check, business_date, total, window, index))
            continue
        reference_pairs: list[tuple[float, int]] = []
        for prior in dates[:window]:
            reference_pairs.extend(grouped[prior])
        reference_values = _expand_values(reference_pairs)
        edges = bin_edges(reference_values, bins)
        expected = histogram(reference_values, edges)
        actual = histogram(_expand_values(grouped[business_date]), edges)
        value = psi(expected, actual)
        status = "fail" if value > check.threshold + 1e-12 else "pass"
        samples = _bin_samples(edges, expected, actual) if status == "fail" else []
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="psi",
                metric_value=float(value),
                threshold=check.threshold,
                comparator="<=",
                failed_row_count=total if status == "fail" else 0,
                total_row_count=total,
                message=_drift_message(check, value, window, status),
                sample_rows=samples,
            )
        )
    return results


def _psi_results(table, check, window, dates, counts) -> list[CheckResult]:
    results = []
    for index, business_date in enumerate(dates):
        total = sum(counts[business_date].values())
        if index < window:
            results.append(_skip_drift(table, check, business_date, total, window, index))
            continue
        categories: set[str] = set()
        for prior in dates[:window]:
            categories.update(counts[prior])
        categories.update(counts[business_date])
        ordered = sorted(categories)
        expected = [
            sum(counts[prior].get(category, 0) for prior in dates[:window]) for category in ordered
        ]
        actual = [counts[business_date].get(category, 0) for category in ordered]
        value = psi(expected, actual)
        status = "fail" if value > check.threshold + 1e-12 else "pass"
        samples = []
        if status == "fail":
            expected_total = sum(expected) or 1
            actual_total = sum(actual) or 1
            samples = [
                {
                    "category": category,
                    "actual_rows": actual_count,
                    "actual_share": actual_count / actual_total,
                    "reference_rows": expected_count,
                    "reference_share": expected_count / expected_total,
                }
                for category, actual_count, expected_count in zip(
                    ordered, actual, expected, strict=True
                )
            ]
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="psi",
                metric_value=float(value),
                threshold=check.threshold,
                comparator="<=",
                failed_row_count=total if status == "fail" else 0,
                total_row_count=total,
                message=_drift_message(check, value, window, status),
                sample_rows=samples,
            )
        )
    return results


def _skip_drift(table, check, business_date, total, window, index) -> CheckResult:
    return _result(
        table,
        check,
        business_date,
        status="skipped",
        metric_name="psi",
        metric_value=None,
        threshold=check.threshold,
        comparator="<=",
        failed_row_count=0,
        total_row_count=total,
        message=(
            f"skipped; the first {window} business dates are the calibration window "
            f"(this is day {index + 1})"
        ),
    )


def _drift_message(check: CheckSpec, value: float, window: int, status: str) -> str:
    relation = "exceeds" if status == "fail" else "is within"
    return (
        f"PSI {value:.4f} {relation} {check.threshold:.2f} for {check.column} "
        f"against the first {window} business dates"
    )


def _expand_values(pairs: list[tuple[float, int]]) -> list[float]:
    values: list[float] = []
    for value, count in pairs:
        values.extend([value] * count)
    return values


def _bin_samples(edges: list[float], expected: list[int], actual: list[int]) -> list[dict]:
    expected_total = sum(expected) or 1
    actual_total = sum(actual) or 1
    samples = []
    for index, (expected_count, actual_count) in enumerate(zip(expected, actual, strict=True)):
        right = edges[index + 1]
        left = edges[index]
        samples.append(
            {
                "bin": index + 1,
                "left": None if left == float("-inf") else left,
                "right": None if right == float("inf") else right,
                "actual_rows": actual_count,
                "actual_share": actual_count / actual_total,
                "reference_rows": expected_count,
                "reference_share": expected_count / expected_total,
            }
        )
    return samples


def _golden(connection, suite: Suite, table: TableSpec, check: CheckSpec) -> list[CheckResult]:
    if not check.golden_path or not check.metrics:
        raise ValueError(f"{check.id} requires golden_path and metrics")
    if check.scope != "partition":
        raise ValueError(f"{check.id} golden reconciliation must be partition scoped")
    golden_path = Path(check.golden_path)
    if not golden_path.is_absolute():
        root = suite.root or Path.cwd()
        golden_path = root / golden_path
    expected_rows = _read_golden(golden_path)
    select_list = ", ".join(
        f"{metric.expression} AS {quote_ident(metric.name)}" for metric in check.metrics
    )
    date_col = _col(table.business_date_column)
    actual_rows = connection.execute(
        f"""
        SELECT {date_col} AS business_date, {select_list}
        FROM {_table(table)}
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchall()
    columns = ["business_date", *[metric.name for metric in check.metrics]]
    actual = {}
    for row in actual_rows:
        payload = dict(zip(columns, row, strict=True))
        actual[_coerce_date(payload["business_date"])] = payload
    dates = sorted(set(actual) | set(expected_rows))
    results = []
    for business_date in dates:
        breaches = []
        evidence = []
        for metric in check.metrics:
            actual_value = (
                None if business_date not in actual else actual[business_date][metric.name]
            )
            expected_value = expected_rows.get(business_date, {}).get(metric.name)
            breach = _metric_breach(metric.name, actual_value, expected_value, metric)
            evidence.append(
                {
                    "metric": metric.name,
                    "actual": None if actual_value is None else str(actual_value),
                    "expected": None if expected_value is None else str(expected_value),
                    "breached": breach is not None,
                }
            )
            if breach:
                breaches.append(breach)
        status = "fail" if breaches else "pass"
        message = (
            "; ".join(breaches)
            if breaches
            else f"all {len(check.metrics)} golden metrics match for {business_date.isoformat()}"
        )
        results.append(
            _result(
                table,
                check,
                business_date,
                status=status,
                metric_name="metrics_breached",
                metric_value=float(len(breaches)),
                threshold=0.0,
                comparator="==",
                failed_row_count=len(breaches),
                total_row_count=len(check.metrics),
                message=message,
                sample_rows=evidence if status == "fail" else [],
            )
        )
    return results


def _read_golden(path: Path) -> dict[date, dict[str, Decimal]]:
    if not path.exists():
        raise FileNotFoundError(f"Golden file not found: {path}")
    parsed: dict[date, dict[str, Decimal]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            business_date = date.fromisoformat(row["business_date"][:10])
            parsed[business_date] = {
                key: Decimal(str(value))
                for key, value in row.items()
                if key != "business_date" and value not in (None, "")
            }
    return parsed


def _metric_breach(name: str, actual, expected, metric) -> str | None:
    if actual is None or expected is None:
        return f"{name} is missing (actual={actual}, expected={expected})"
    actual_decimal = Decimal(str(actual))
    expected_decimal = Decimal(str(expected))
    difference = abs(actual_decimal - expected_decimal)
    if metric.tolerance_abs is not None:
        if difference > Decimal(str(metric.tolerance_abs)):
            return (
                f"{name} actual {actual_decimal} expected {expected_decimal} "
                f"(abs diff {difference}, tolerance {metric.tolerance_abs})"
            )
        return None
    if metric.tolerance_pct is not None:
        if expected_decimal == 0:
            breached = actual_decimal != 0
            ratio = Decimal("1") if breached else Decimal("0")
        else:
            ratio = difference / abs(expected_decimal)
            breached = ratio > Decimal(str(metric.tolerance_pct))
        if breached:
            return (
                f"{name} actual {actual_decimal} expected {expected_decimal} "
                f"(pct diff {ratio}, tolerance {metric.tolerance_pct})"
            )
        return None
    if difference != 0:
        return f"{name} actual {actual_decimal} expected {expected_decimal}"
    return None


def _persist(connection, suite: Suite, run_id: str, run_ts: datetime, results, scores) -> None:
    connection.execute(
        """
        INSERT INTO dq.runs (run_id, run_ts, suite_name, as_of, suite_path, pass_score, fail_on_critical)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            run_ts,
            suite.name,
            suite.as_of,
            None if suite.path is None else str(suite.path),
            suite.pass_score,
            suite.fail_on_critical,
        ],
    )
    connection.executemany(
        """
        INSERT INTO dq.check_results (
            run_id, run_ts, business_date, table_name, check_id, check_type, severity, status,
            metric_name, metric_value, threshold, comparator, failed_row_count, total_row_count,
            weight, message, sample_rows, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                run_ts,
                row.business_date,
                row.table_name,
                row.check_id,
                row.check_type,
                row.severity,
                row.status,
                row.metric_name,
                row.metric_value,
                row.threshold,
                row.comparator,
                row.failed_row_count,
                row.total_row_count,
                weight_for(row.severity, suite.severity_weights),
                row.message,
                dump_samples(row.sample_rows),
                row.description,
            )
            for row in results
        ],
    )
    connection.executemany(
        """
        INSERT INTO dq.sla_scores (
            run_id, run_ts, business_date, table_name, score, status, checks_total,
            checks_failed, checks_skipped, critical_failed, weight_passed, weight_total
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                run_ts,
                row.business_date,
                row.table_name,
                row.score,
                row.status,
                row.checks_total,
                row.checks_failed,
                row.checks_skipped,
                row.critical_failed,
                row.weight_passed,
                row.weight_total,
            )
            for row in scores
        ],
    )
