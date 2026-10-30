"""DuckDB connection helpers and the data-quality history schema."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb

from rutanorte_dq.identifiers import (
    valid_curp,
    valid_email,
    valid_phone_mx,
    valid_rfc_fisica,
    valid_rfc_moral,
)

UDF_FUNCTIONS = {
    "dq_rfc_fisica": valid_rfc_fisica,
    "dq_rfc_moral": valid_rfc_moral,
    "dq_curp": valid_curp,
    "dq_email": valid_email,
    "dq_phone_mx": valid_phone_mx,
}

FORMAT_TO_UDF = {
    "rfc_fisica": "dq_rfc_fisica",
    "rfc_moral": "dq_rfc_moral",
    "curp": "dq_curp",
    "email": "dq_email",
    "phone_mx": "dq_phone_mx",
}


def connect(path: Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = Path(path)
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path), read_only=read_only)
    if not read_only:
        register_udfs(connection)
    return connection


def register_udfs(connection: duckdb.DuckDBPyConnection) -> None:
    for name, function in UDF_FUNCTIONS.items():
        connection.create_function(name, function, return_type="BOOLEAN")


def init_history(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS dq")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dq.runs (
            run_id VARCHAR PRIMARY KEY,
            run_ts TIMESTAMP NOT NULL,
            suite_name VARCHAR NOT NULL,
            as_of DATE,
            suite_path VARCHAR,
            pass_score DOUBLE,
            fail_on_critical BOOLEAN
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dq.check_results (
            run_id VARCHAR NOT NULL,
            run_ts TIMESTAMP NOT NULL,
            business_date DATE NOT NULL,
            table_name VARCHAR NOT NULL,
            check_id VARCHAR NOT NULL,
            check_type VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            metric_name VARCHAR,
            metric_value DOUBLE,
            threshold DOUBLE,
            comparator VARCHAR,
            failed_row_count BIGINT,
            total_row_count BIGINT,
            weight DOUBLE,
            message VARCHAR,
            sample_rows VARCHAR,
            description VARCHAR
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dq.sla_scores (
            run_id VARCHAR NOT NULL,
            run_ts TIMESTAMP NOT NULL,
            business_date DATE NOT NULL,
            table_name VARCHAR NOT NULL,
            score DOUBLE NOT NULL,
            status VARCHAR NOT NULL,
            checks_total INTEGER NOT NULL,
            checks_failed INTEGER NOT NULL,
            checks_skipped INTEGER NOT NULL,
            critical_failed INTEGER NOT NULL,
            weight_passed DOUBLE NOT NULL,
            weight_total DOUBLE NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW dq.latest_check_results AS
        SELECT *
        FROM dq.check_results
        WHERE run_id = (SELECT run_id FROM dq.runs ORDER BY run_ts DESC LIMIT 1)
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW dq.latest_sla_scores AS
        SELECT *
        FROM dq.sla_scores
        WHERE run_id = (SELECT run_id FROM dq.runs ORDER BY run_ts DESC LIMIT 1)
        """
    )


def json_ready(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def dump_samples(samples: list[dict]) -> str:
    return json.dumps(samples, default=json_ready)


def load_samples(payload: str | None) -> list[dict]:
    if not payload:
        return []
    return json.loads(payload)


def latest_run(connection: duckdb.DuckDBPyConnection):
    row = connection.execute(
        """
        SELECT run_id, run_ts, suite_name, as_of, suite_path, pass_score, fail_on_critical
        FROM dq.runs
        ORDER BY run_ts DESC
        LIMIT 1
        """
    ).fetchone()
    return row
