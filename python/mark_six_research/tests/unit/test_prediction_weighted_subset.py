import math
from itertools import combinations

import numpy as np
import pytest

from mark_six.prediction.weighted_subset import (
    WeightedSubsetDistribution,
    elementary_symmetric,
)


def test_normalizer_and_probabilities_match_brute_force_small_pool() -> None:
    weights = np.asarray([0.5, 1.0, 1.5, 2.0, 0.8, 1.2, 2.5, 0.7])
    subsets = list(combinations(range(1, 9), 3))
    brute_normalizer = sum(
        math.prod(weights[number - 1] for number in subset) for subset in subsets
    )
    distribution = WeightedSubsetDistribution(weights, subset_size=3)

    assert distribution.normalizer == pytest.approx(brute_normalizer, rel=1e-14)
    assert sum(distribution.probability(subset) for subset in subsets) == pytest.approx(1.0)


def test_exact_marginals_match_brute_force_and_sum_to_subset_size() -> None:
    weights = np.asarray([0.4, 0.9, 1.1, 1.7, 2.2, 0.6, 1.3])
    distribution = WeightedSubsetDistribution(weights, subset_size=3)
    marginals = distribution.marginals()
    brute = np.zeros(7)
    for subset in combinations(range(1, 8), 3):
        probability = distribution.probability(subset)
        for number in subset:
            brute[number - 1] += probability

    assert marginals == pytest.approx(brute, rel=1e-13, abs=1e-13)
    assert float(np.sum(marginals)) == pytest.approx(3.0, abs=1e-13)
    assert np.all((marginals >= 0.0) & (marginals <= 1.0))
    expected = math.prod(weights[number - 1] for number in (1, 3, 7)) / distribution.normalizer
    assert distribution.log_probability((1, 3, 7)) == pytest.approx(math.log(expected))


@pytest.mark.parametrize("pool_size", [7, 10, 45, 47, 49])
def test_unit_weights_are_uniform(pool_size: int) -> None:
    distribution = WeightedSubsetDistribution(np.ones(pool_size))

    assert distribution.normalizer == pytest.approx(math.comb(pool_size, 6))
    assert distribution.probability(range(1, 7)) == pytest.approx(
        1.0 / math.comb(pool_size, 6), rel=1e-14
    )
    assert distribution.marginals() == pytest.approx(np.full(pool_size, 6.0 / pool_size))


def test_common_weight_scaling_leaves_distribution_unchanged() -> None:
    weights = np.linspace(0.5, 2.0, 12)
    first = WeightedSubsetDistribution(weights)
    second = WeightedSubsetDistribution(weights * 37.5)

    assert first.probability((1, 3, 5, 7, 9, 11)) == pytest.approx(
        second.probability((1, 3, 5, 7, 9, 11)), rel=1e-13
    )
    assert first.marginals() == pytest.approx(second.marginals(), rel=1e-12)


def test_elementary_symmetric_rejects_nonpositive_weights() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        elementary_symmetric(np.asarray([1.0, 0.0, 2.0]), 2)


@pytest.mark.parametrize("subset", [(1, 2, 3, 4, 5, 5), (0, 1, 2, 3, 4, 5)])
def test_invalid_subsets_are_rejected(subset: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        WeightedSubsetDistribution(np.ones(10)).probability(subset)
