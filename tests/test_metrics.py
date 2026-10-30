import math

import pytest

from rutanorte_dq.metrics import bin_edges, deviation_from_median, histogram, psi


def test_psi_is_zero_for_identical_mixes():
    assert psi([550, 250, 150, 50], [550, 250, 150, 50]) == pytest.approx(0.0, abs=1e-12)


def test_psi_detects_a_cash_shift():
    baseline = [550 * 14, 250 * 14, 150 * 14, 50 * 14]
    shifted = [100, 50, 50, 800]
    assert psi(baseline, shifted) > 0.2


def test_volume_deviation_uses_median():
    deviation, center = deviation_from_median(200, [1000] * 12 + [1005, 1015])
    assert center == 1000
    assert deviation == pytest.approx(0.8)


def test_histogram_puts_edge_values_in_the_lower_bin():
    edges = bin_edges([100, 250, 499, 1200, 3500, 9000], bins=3)
    assert edges[0] == -math.inf
    assert edges[-1] == math.inf
    counts = histogram([50, 100, 101, 250, 9000], edges)
    assert sum(counts) == 5
    assert counts[0] >= 1
