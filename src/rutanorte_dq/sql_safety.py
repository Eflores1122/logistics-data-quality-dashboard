"""Identifier quoting for SQL assembled from the declarative suite."""

from __future__ import annotations

import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_METRIC = re.compile(r"^(count\(\*\)|sum\([A-Za-z_][A-Za-z0-9_]*\))$")


def quote_ident(name: str) -> str:
    if not isinstance(name, str) or not _IDENT.match(name):
        raise ValueError(f"Refusing unsafe SQL identifier: {name!r}")
    return f'"{name}"'


def validate_metric_expression(expression: str) -> str:
    compact = expression.replace(" ", "")
    if not _METRIC.match(compact):
        raise ValueError(f"Metric expressions must be count(*) or sum(column). Got {expression!r}.")
    return compact
