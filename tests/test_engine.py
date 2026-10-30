from datetime import date

from rutanorte_dq.engine import run_suite
from rutanorte_dq.suite import CheckSpec, Suite, TableSpec
from rutanorte_dq.warehouse import connect


def _suite(tmp_path, checks) -> Suite:
    weights = {"critical": 5, "high": 3, "medium": 2, "low": 1}
    return Suite(
        name="tiny",
        description="tiny",
        as_of=date(2026, 10, 1),
        pass_score=95,
        fail_on_critical=True,
        severity_weights=weights,
        nodes=(),
        lineage=(),
        tables=(
            TableSpec(
                name="customers",
                business_date_column="created_date",
                key="customer_id",
                checks=tuple(checks),
            ),
        ),
        root=tmp_path,
    )


def test_completeness_returns_the_null_row(tmp_path):
    db_path = tmp_path / "tiny.duckdb"
    connection = connect(db_path)
    connection.execute(
        """
        CREATE TABLE customers (
            customer_id VARCHAR,
            created_date DATE,
            email VARCHAR
        )
        """
    )
    connection.execute(
        """
        INSERT INTO customers VALUES
            ('A', DATE '2026-10-01', 'a@example.com'),
            ('B', DATE '2026-10-01', NULL)
        """
    )
    suite = _suite(
        tmp_path,
        [
            CheckSpec(
                id="email_completeness",
                type="completeness",
                severity="high",
                description="Email is required.",
                column="email",
                max_null_rate=0.0,
            )
        ],
    )
    try:
        output = run_suite(connection, suite)
        stored = connection.execute(
            "SELECT status, failed_row_count FROM dq.check_results"
        ).fetchall()
    finally:
        connection.close()
    assert stored == [("fail", 1)]
    assert output["results"][0].sample_rows[0]["customer_id"] == "B"


def test_validity_ignores_nulls_and_flags_bad_rfc(tmp_path):
    db_path = tmp_path / "rfc.duckdb"
    connection = connect(db_path)
    connection.execute(
        """
        CREATE TABLE customers (
            customer_id VARCHAR,
            created_date DATE,
            rfc VARCHAR
        )
        """
    )
    connection.execute(
        """
        INSERT INTO customers VALUES
            ('A', DATE '2026-10-01', 'GARC850101AB1'),
            ('B', DATE '2026-10-01', NULL),
            ('C', DATE '2026-10-01', 'BADRFC')
        """
    )
    suite = _suite(
        tmp_path,
        [
            CheckSpec(
                id="rfc_validity",
                type="validity",
                severity="high",
                description="RFC format.",
                column="rfc",
                format="rfc_fisica",
                max_invalid_rate=0.0,
            )
        ],
    )
    try:
        output = run_suite(connection, suite)
    finally:
        connection.close()
    result = output["results"][0]
    assert result.status == "fail"
    assert result.failed_row_count == 1
    assert result.sample_rows[0]["customer_id"] == "C"
