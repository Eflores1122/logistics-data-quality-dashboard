"""Pure metric helpers for volume anomalies and population stability index."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def psi(
    expected_counts: Sequence[float], actual_counts: Sequence[float], eps: float = 1e-4
) -> float:
    """Population stability index. Proportions are floored with ``eps`` and renormalized."""
    if len(expected_counts) != len(actual_counts) or not expected_counts:
        raise ValueError("PSI inputs must be non-empty and the same length")
    expected = _shares(expected_counts, eps)
    actual = _shares(actual_counts, eps)
    return sum((a - e) * math.log(a / e) for e, a in zip(expected, actual, strict=True))


def _shares(counts: Sequence[float], eps: float) -> list[float]:
    adjusted = [max(float(c), 0.0) + eps for c in counts]
    total = sum(adjusted)
    return [c / total for c in adjusted]


def deviation_from_median(current: float, history: Sequence[float]) -> tuple[float, float]:
    """Return ``(absolute relative deviation, median)``.

    Deviation is ``abs(current / median - 1)``. A zero median yields a deviation
    of 0 when the current value is also 0, otherwise infinity.
    """
    if not history:
        raise ValueError("history must not be empty")
    center = float(statistics.median(history))
    if center == 0:
        return (0.0 if current == 0 else math.inf), center
    return abs(float(current) / center - 1.0), center


def quantile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("quantile of an empty series")
    if q <= 0:
        return float(sorted_values[0])
    if q >= 1:
        return float(sorted_values[-1])
    position = q * (len(sorted_values) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(sorted_values[low])
    weight = position - low
    return float(sorted_values[low]) * (1 - weight) + float(sorted_values[high]) * weight


def bin_edges(values: Sequence[float], bins: int) -> list[float]:
    """Return increasing cut points from ``-inf`` to ``inf`` using reference quantiles."""
    if bins < 1:
        raise ValueError("bins must be positive")
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return [float("-inf"), float("inf")]
    internal: list[float] = []
    for step in range(1, bins):
        cut = quantile(ordered, step / bins)
        if not internal or cut > internal[-1]:
            internal.append(cut)
    return [float("-inf"), *internal, float("inf")]


def histogram(values: Sequence[float], edges: Sequence[float]) -> list[int]:
    """Bin ``values`` into ``(-inf, e1], (e1, e2], ...``.

    ``edges`` must start at ``-inf`` and end at ``inf``. A value equal to an
    internal cut falls in the lower bin.
    """
    if len(edges) < 2:
        raise ValueError("edges must contain at least two cut points")
    counts = [0] * (len(edges) - 1)
    last = len(counts) - 1
    for value in values:
        number = float(value)
        placed = last
        for index in range(len(counts)):
            if number <= edges[index + 1]:
                placed = index
                break
        counts[placed] += 1
    return counts


def histogram_from_counts(
    value_counts: Sequence[tuple[float, int]], edges: Sequence[float]
) -> list[int]:
    expanded: list[float] = []
    for value, count in value_counts:
        expanded.extend([float(value)] * int(count))
    return histogram(expanded, edges)
