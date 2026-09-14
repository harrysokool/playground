from itertools import combinations, pairwise
from math import comb

import numpy as np
import pytest

from mark_six.statistics.multiple_testing import benjamini_hochberg, holm
from mark_six.statistics.null_model import (
    consecutive_pair_count_pmf,
    exact_sum_pmf,
    expected_sum,
    expected_sum_variance,
    hypergeometric_composition_pmf,
    inclusion_probability,
    overlap_pmf,
    pair_probability,
    sample_fair_history,
    triple_probability,
)


def test_exact_frequency_pair_and_gap_expectations() -> None:
    assert inclusion_probability(45) == pytest.approx(6 / 45)
    assert pytest.approx(1 / 47) == 1 / 47  # Separate Extra Number expectation.
    assert 1 / inclusion_probability(49) == pytest.approx(49 / 6)  # Inter-arrival mean.
    assert pair_probability(49) == pytest.approx(comb(6, 2) / comb(49, 2))
    assert triple_probability(49) == pytest.approx(comb(6, 3) / comb(49, 3))


def test_odd_even_distribution_is_exact_hypergeometric() -> None:
    pool_size = 9
    expected = hypergeometric_composition_pmf(pool_size, 5)
    brute = np.zeros(7)
    tickets = list(combinations(range(1, pool_size + 1), 6))
    for ticket in tickets:
        brute[sum(number % 2 for number in ticket)] += 1
    brute /= len(tickets)

    np.testing.assert_allclose(expected, brute)
    assert expected.sum() == pytest.approx(1)


def test_overlap_distribution_matches_exact_enumeration() -> None:
    pool_size = 8
    reference = set(range(1, 7))
    observed = np.zeros(7)
    tickets = list(combinations(range(1, pool_size + 1), 6))
    for ticket in tickets:
        observed[len(reference & set(ticket))] += 1
    observed /= len(tickets)

    np.testing.assert_allclose(overlap_pmf(pool_size), observed)


def test_sum_distribution_reproduces_exact_moments() -> None:
    pool_size = 12
    minimum, probabilities = exact_sum_pmf(pool_size)
    values = np.arange(minimum, minimum + len(probabilities))
    mean = float(np.dot(values, probabilities))
    variance = float(np.dot((values - mean) ** 2, probabilities))

    assert probabilities.sum() == pytest.approx(1)
    assert mean == pytest.approx(expected_sum(pool_size))
    assert variance == pytest.approx(expected_sum_variance(pool_size))


def test_consecutive_distribution_matches_brute_force() -> None:
    pool_size = 10
    observed = np.zeros(6)
    tickets = list(combinations(range(1, pool_size + 1), 6))
    for ticket in tickets:
        observed[sum(second == first + 1 for first, second in pairwise(ticket))] += 1
    observed /= len(tickets)

    np.testing.assert_allclose(consecutive_pair_count_pmf(pool_size), observed)


def test_fair_simulation_is_seeded_and_never_reuses_extra_number() -> None:
    first_main, first_extra = sample_fair_history(49, 500, np.random.default_rng(20260914))
    second_main, second_extra = sample_fair_history(49, 500, np.random.default_rng(20260914))

    np.testing.assert_array_equal(first_main, second_main)
    np.testing.assert_array_equal(first_extra, second_extra)
    assert np.all(np.diff(first_main, axis=1) > 0)
    assert all(extra not in main for main, extra in zip(first_main, first_extra, strict=True))


def test_multiple_testing_corrections_known_case() -> None:
    p_values = [0.001, 0.01, 0.03, 0.20]

    bh_adjusted, bh_rejected = benjamini_hochberg(p_values, 0.05)
    holm_adjusted, holm_rejected = holm(p_values, 0.05)

    assert bh_adjusted == pytest.approx([0.004, 0.02, 0.04, 0.20])
    assert bh_rejected == [True, True, True, False]
    assert holm_adjusted == pytest.approx([0.004, 0.03, 0.06, 0.20])
    assert holm_rejected == [True, True, False, False]
