"""In-memory check results shared by the engine, scorer, and evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class CheckResult:
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
    sample_rows: list[dict] = field(default_factory=list)

    @property
    def weight_key(self) -> str:
        return self.severity
