"""Locate the repository root when commands run from the project directory."""

from __future__ import annotations

from pathlib import Path

SUITE_RELATIVE = Path("checks") / "rutanorte_daily.yaml"


def repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / SUITE_RELATIVE).exists():
        return cwd
    packaged = Path(__file__).resolve().parents[2]
    if (packaged / SUITE_RELATIVE).exists():
        return packaged
    return cwd


def default_db_path() -> Path:
    return repo_root() / "data" / "warehouse" / "rutanorte.duckdb"


def default_suite_path() -> Path:
    return repo_root() / SUITE_RELATIVE


def default_golden_path() -> Path:
    return repo_root() / "data" / "golden" / "shipment_daily_totals.csv"


def default_ground_truth_path() -> Path:
    return repo_root() / "data" / "ground_truth" / "injected_defects.yaml"
