"""Lock the parquet bundle the static site loads in the browser."""

import json

import duckdb
import pytest

from rutanorte_dq.paths import repo_root
from rutanorte_dq.suite import load_suite

ROOT = repo_root()
DATA = ROOT / "site" / "data"


def _read(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_site_bundle_matches_the_reference_run():
    manifest = _read("manifest.json")
    reference = _read("reference_results.json")
    suite_json = _read("suite.json")
    defects = _read("defects.json")

    assert manifest["seed"] == 42
    assert manifest["counts"] == {
        "hubs": 120,
        "customers": 3606,
        "tracking_scans": 3605,
        "shipments": 44220,
        "daily_route_kpis": 45,
    }
    assert manifest["checks"] == 39
    assert manifest["defects"] == 20
    assert len(defects["defects"]) == 20

    connection = duckdb.connect()
    try:
        for table, expected in manifest["counts"].items():
            found = connection.execute(
                "SELECT count(*) FROM read_parquet(?)",
                [str(DATA / f"{table}.parquet")],
            ).fetchone()[0]
            assert found == expected
    finally:
        connection.close()

    repo_golden = (ROOT / "data" / "golden" / "shipment_daily_totals.csv").read_text(
        encoding="utf-8"
    )
    assert (DATA / "golden.csv").read_text(encoding="utf-8") == repo_golden

    suite = load_suite(ROOT / "checks" / "rutanorte_daily.yaml", root=ROOT)
    exported_ids = {check["id"] for table in suite_json["tables"] for check in table["checks"]}
    assert exported_ids == suite.check_ids()
    assert suite_json["as_of"] == "2026-10-15"
    assert suite_json["pass_score"] == 95

    fails = [row for row in reference["results"] if row["status"] == "fail"]
    assert len(reference["results"]) == 1535
    assert len(fails) == 20
    assert reference["evaluation"]["precision"] == 1
    assert reference["evaluation"]["recall"] == 1
    assert reference["evaluation"]["row_level_recall"] == 1

    days = {row["business_date"]: row for row in reference["days"]}
    assert days["2026-09-20"]["score"] == 100
    assert days["2026-09-20"]["status"] == "pass"
    assert days["2026-10-07"]["score"] == 90.4762
    assert days["2026-10-08"]["score"] == 93.3333
    assert days["2026-10-10"]["checks_failed"] == 8
    assert days["2026-10-12"]["score"] == 92.381
    assert days["2026-10-13"]["status"] == "pass"
    assert days["2026-10-13"]["checks_failed"] == 1
    assert days["2026-10-15"]["score"] == 95.9016
    assert days["2026-10-15"]["status"] == "fail"

    by_key = {(row["business_date"], row["check_id"]): row for row in reference["results"]}
    assert by_key[("2026-10-08", "shipments_weight_drift")]["metric_value"] == pytest.approx(
        12.9071, abs=1e-3
    )
    assert by_key[("2026-10-13", "shipments_channel_drift")]["metric_value"] == pytest.approx(
        3.2783, abs=1e-3
    )
    assert by_key[("2026-10-15", "scans_freshness")]["metric_value"] == 12
    assert by_key[("2026-10-10", "customers_email_completeness")]["failed_row_count"] == 25
