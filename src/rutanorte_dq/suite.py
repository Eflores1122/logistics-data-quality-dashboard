"""Load the declarative YAML check suite."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

from rutanorte_dq.sql_safety import quote_ident, validate_metric_expression

CHECK_TYPES = {
    "completeness",
    "uniqueness",
    "validity",
    "accepted_values",
    "referential_integrity",
    "freshness",
    "volume_anomaly",
    "distribution_drift",
    "golden_reconciliation",
}
SEVERITIES = {"critical", "high", "medium", "low"}
SCOPES = {"partition", "table"}
LAYERS = {"extract", "warehouse", "mart"}


@dataclass(frozen=True)
class MetricSpec:
    name: str
    expression: str
    tolerance_abs: float | None = None
    tolerance_pct: float | None = None


@dataclass(frozen=True)
class CheckSpec:
    id: str
    type: str
    severity: str
    description: str
    scope: str = "partition"
    column: str | None = None
    columns: tuple[str, ...] = ()
    max_null_rate: float | None = None
    max_invalid_rate: float | None = None
    format: str | None = None
    values: tuple[str, ...] = ()
    references_table: str | None = None
    references_column: str | None = None
    timestamp_column: str | None = None
    deadline_hours: int | None = None
    window_days: int | None = None
    max_deviation_pct: float | None = None
    threshold: float | None = None
    bins: int | None = None
    numeric: bool = False
    golden_path: str | None = None
    metrics: tuple[MetricSpec, ...] = ()


@dataclass(frozen=True)
class TableSpec:
    name: str
    business_date_column: str | None
    key: str | None
    checks: tuple[CheckSpec, ...]


@dataclass(frozen=True)
class LineageNode:
    id: str
    label: str
    layer: str


@dataclass(frozen=True)
class LineageEdge:
    source: str
    target: str


@dataclass(frozen=True)
class Suite:
    name: str
    description: str
    as_of: date
    pass_score: float
    fail_on_critical: bool
    severity_weights: dict[str, float]
    nodes: tuple[LineageNode, ...]
    lineage: tuple[LineageEdge, ...]
    tables: tuple[TableSpec, ...]
    path: Path | None = None
    root: Path | None = field(default=None)

    def check_ids(self) -> set[str]:
        return {check.id for table in self.tables for check in table.checks}


def _as_date(value, label: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"{label} must be a date, got {value!r}")


def _require_ident(value: str | None, label: str) -> str:
    if not value:
        raise ValueError(f"{label} is required")
    quote_ident(value)
    return value


def _check_from_yaml(raw: dict, table_name: str) -> CheckSpec:
    check_type = raw.get("type")
    if check_type not in CHECK_TYPES:
        raise ValueError(f"Unknown check type {check_type!r} on {table_name}")
    severity = raw.get("severity", "medium")
    if severity not in SEVERITIES:
        raise ValueError(f"Unknown severity {severity!r} on check {raw.get('id')}")
    scope = raw.get("scope", "partition")
    if scope not in SCOPES:
        raise ValueError(f"Unknown scope {scope!r} on check {raw.get('id')}")
    columns = tuple(raw.get("columns") or ())
    for column in columns:
        _require_ident(column, f"{raw.get('id')}.columns")
    if raw.get("column"):
        _require_ident(raw["column"], f"{raw.get('id')}.column")
    metrics = []
    for metric in raw.get("metrics") or []:
        expression = validate_metric_expression(metric["expression"])
        metrics.append(
            MetricSpec(
                name=str(metric["name"]),
                expression=expression,
                tolerance_abs=(
                    float(metric["tolerance_abs"]) if "tolerance_abs" in metric else None
                ),
                tolerance_pct=(
                    float(metric["tolerance_pct"]) if "tolerance_pct" in metric else None
                ),
            )
        )
    references = raw.get("references") or {}
    if references:
        _require_ident(references.get("table"), f"{raw.get('id')}.references.table")
        _require_ident(references.get("column"), f"{raw.get('id')}.references.column")
    return CheckSpec(
        id=str(raw["id"]),
        type=check_type,
        severity=severity,
        description=str(raw.get("description") or "").strip(),
        scope=scope,
        column=raw.get("column"),
        columns=columns,
        max_null_rate=(float(raw["max_null_rate"]) if "max_null_rate" in raw else None),
        max_invalid_rate=(float(raw["max_invalid_rate"]) if "max_invalid_rate" in raw else None),
        format=raw.get("format"),
        values=tuple(str(item) for item in (raw.get("values") or [])),
        references_table=references.get("table"),
        references_column=references.get("column"),
        timestamp_column=raw.get("timestamp_column"),
        deadline_hours=(int(raw["deadline_hours"]) if "deadline_hours" in raw else None),
        window_days=(int(raw["window_days"]) if "window_days" in raw else None),
        max_deviation_pct=(float(raw["max_deviation_pct"]) if "max_deviation_pct" in raw else None),
        threshold=(float(raw["threshold"]) if "threshold" in raw else None),
        bins=(int(raw["bins"]) if "bins" in raw else None),
        numeric=bool(raw.get("numeric", False)),
        golden_path=raw.get("golden_path"),
        metrics=tuple(metrics),
    )


def load_suite(path: Path, root: Path | None = None) -> Suite:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    weights = {str(key): float(value) for key, value in raw["severity_weights"].items()}
    missing = SEVERITIES - set(weights)
    if missing:
        raise ValueError(f"severity_weights is missing {sorted(missing)}")
    nodes = tuple(
        LineageNode(
            id=str(item["id"]), label=str(item.get("label") or item["id"]), layer=str(item["layer"])
        )
        for item in raw.get("nodes") or []
    )
    for node in nodes:
        if node.layer not in LAYERS:
            raise ValueError(f"Unknown lineage layer {node.layer!r} on {node.id}")
    edges = tuple(
        LineageEdge(source=str(item["from"]), target=str(item["to"]))
        for item in raw.get("lineage") or []
    )
    tables = []
    seen_ids: set[str] = set()
    for table in raw["tables"]:
        name = _require_ident(table["name"], "table.name")
        date_column = table.get("business_date_column")
        if date_column:
            _require_ident(date_column, f"{name}.business_date_column")
        key = table.get("key")
        if key:
            _require_ident(key, f"{name}.key")
        checks = tuple(_check_from_yaml(item, name) for item in table["checks"])
        for check in checks:
            if check.id in seen_ids:
                raise ValueError(f"Duplicate check id {check.id}")
            seen_ids.add(check.id)
            if check.scope == "partition" and not date_column:
                raise ValueError(f"{check.id} is partition scoped but {name} has no business date")
        tables.append(
            TableSpec(
                name=name,
                business_date_column=date_column,
                key=key,
                checks=checks,
            )
        )
    sla = raw["sla"]
    return Suite(
        name=str(raw["suite"]),
        description=str(raw.get("description") or "").strip(),
        as_of=_as_date(raw["as_of"], "as_of"),
        pass_score=float(sla["pass_score"]),
        fail_on_critical=bool(sla.get("fail_on_critical", True)),
        severity_weights=weights,
        nodes=nodes,
        lineage=edges,
        tables=tuple(tables),
        path=path,
        root=root or path.resolve().parents[1],
    )
