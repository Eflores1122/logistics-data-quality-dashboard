"""Compare a persisted run with the injected-defect catalog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Defect:
    defect_id: str
    business_date: date
    table: str
    check_id: str
    defect_type: str
    description: str
    min_failed_rows: int | None = None


@dataclass
class Evaluation:
    defects_total: int
    defects_caught: int
    fails_total: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    row_level_applicable: int
    row_level_caught: int
    row_level_recall: float
    missed: list[dict]
    unexpected: list[dict]

    def as_dict(self) -> dict:
        return {
            "defects_total": self.defects_total,
            "defects_caught": self.defects_caught,
            "fails_total": self.fails_total,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "row_level_applicable": self.row_level_applicable,
            "row_level_caught": self.row_level_caught,
            "row_level_recall": self.row_level_recall,
            "missed": self.missed,
            "unexpected": self.unexpected,
        }


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def load_defects(path: Path) -> list[Defect]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    defects = []
    for item in raw["defects"]:
        minimum = item.get("min_failed_rows")
        defects.append(
            Defect(
                defect_id=str(item["id"]),
                business_date=_as_date(item["business_date"]),
                table=str(item["table"]),
                check_id=str(item["check_id"]),
                defect_type=str(item["defect_type"]),
                description=str(item.get("description") or "").strip(),
                min_failed_rows=None if minimum is None else int(minimum),
            )
        )
    return defects


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def evaluate_results(results: list, defects: list[Defect]) -> Evaluation:
    """Score detection quality.

    A predicted positive is a check that failed on a business date.
    A ground-truth positive is one injected defect. The defect is caught when
    that check failed and, when ``min_failed_rows`` is set, the result counted
    at least that many offending rows.

    Precision uses the same caught set over all failed checks. A failed check
    whose key is not in the catalog is a false positive. A catalog key that
    failed the status test but missed the row minimum is a false negative and
    is not also counted as a true positive.
    """
    by_key = {(row.check_id, _as_date(row.business_date)): row for row in results}
    fail_keys = {key for key, row in by_key.items() if row.status == "fail"}

    missed: list[dict] = []
    caught_keys: set[tuple] = set()
    defect_keys = {(defect.check_id, defect.business_date) for defect in defects}
    row_applicable = 0
    row_caught = 0
    for defect in defects:
        key = (defect.check_id, defect.business_date)
        result = by_key.get(key)
        status_hit = result is not None and result.status == "fail"
        row_hit = True
        if defect.min_failed_rows is not None:
            row_applicable += 1
            observed = 0 if result is None else int(result.failed_row_count or 0)
            row_hit = observed >= defect.min_failed_rows
            if status_hit and row_hit:
                row_caught += 1
        if status_hit and row_hit:
            caught_keys.add(key)
        else:
            missed.append(
                {
                    "id": defect.defect_id,
                    "check_id": defect.check_id,
                    "business_date": defect.business_date.isoformat(),
                    "status": None if result is None else result.status,
                    "failed_row_count": None
                    if result is None
                    else int(result.failed_row_count or 0),
                    "min_failed_rows": defect.min_failed_rows,
                    "description": defect.description,
                }
            )

    unexpected = []
    for key in sorted(fail_keys - defect_keys, key=lambda item: (item[1].isoformat(), item[0])):
        result = by_key[key]
        unexpected.append(
            {
                "check_id": result.check_id,
                "business_date": _as_date(result.business_date).isoformat(),
                "table": result.table_name,
                "message": result.message,
                "failed_row_count": int(result.failed_row_count or 0),
            }
        )

    true_positives = len(caught_keys)
    false_positives = len(unexpected)
    false_negatives = len(missed)
    return Evaluation(
        defects_total=len(defects),
        defects_caught=true_positives,
        fails_total=len(fail_keys),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=_ratio(true_positives, true_positives + false_positives),
        recall=_ratio(true_positives, true_positives + false_negatives),
        row_level_applicable=row_applicable,
        row_level_caught=row_caught,
        row_level_recall=_ratio(row_caught, row_applicable),
        missed=missed,
        unexpected=unexpected,
    )
