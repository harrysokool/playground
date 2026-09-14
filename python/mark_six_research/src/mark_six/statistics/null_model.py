"""Exact fair-draw expectations and deterministic null simulation."""

from __future__ import annotations

from functools import cache
from math import comb

import numpy as np
from numpy.typing import NDArray


def sample_fair_history(
    pool_size: int, draw_count: int, rng: np.random.Generator
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Sample independent six-main-plus-Extra draws without replacement."""

    if pool_size < 7 or draw_count < 1:
        raise ValueError("pool_size must be at least seven and draw_count positive")
    scores = rng.random((draw_count, pool_size))
    candidates = np.argpartition(scores, kth=6, axis=1)[:, :7]
    candidate_scores = np.take_along_axis(scores, candidates, axis=1)
    order = np.argsort(candidate_scores, axis=1)
    ordered = np.take_along_axis(candidates, order, axis=1).astype(np.int64) + 1
    mains = np.sort(ordered[:, :6], axis=1)
    extras = ordered[:, 6]
    return mains, extras


def inclusion_probability(pool_size: int, selected: int = 6) -> float:
    """Return one number's per-draw inclusion probability."""

    return selected / pool_size


def pair_probability(pool_size: int) -> float:
    """Return one pair's main-number co-appearance probability."""

    return comb(6, 2) / comb(pool_size, 2)


def triple_probability(pool_size: int) -> float:
    """Return one triple's main-number co-appearance probability."""

    return comb(6, 3) / comb(pool_size, 3)


def hypergeometric_composition_pmf(pool_size: int, target_count: int) -> NDArray[np.float64]:
    """Exact probabilities for selecting zero through six target-class numbers."""

    denominator = comb(pool_size, 6)
    values = [
        comb(target_count, count) * comb(pool_size - target_count, 6 - count) / denominator
        if count <= target_count and 6 - count <= pool_size - target_count
        else 0.0
        for count in range(7)
    ]
    return np.asarray(values, dtype=np.float64)


def overlap_pmf(pool_size: int) -> NDArray[np.float64]:
    """Exact overlap distribution for two independent six-number sets."""

    denominator = comb(pool_size, 6)
    return np.asarray(
        [comb(6, count) * comb(pool_size - 6, 6 - count) / denominator for count in range(7)],
        dtype=np.float64,
    )


def consecutive_pair_count_pmf(pool_size: int) -> NDArray[np.float64]:
    """Exact PMF for the number of adjacent selected pairs in a six-number set."""

    denominator = comb(pool_size, 6)
    counts: list[int] = []
    for adjacent_pairs in range(6):
        runs = 6 - adjacent_pairs
        counts.append(comb(5, runs - 1) * comb(pool_size - 5, runs))
    return np.asarray(counts, dtype=np.float64) / denominator


@cache
def run_of_three_probability(pool_size: int) -> float:
    """Exact probability that a six-number set contains a run of at least three."""

    states: dict[tuple[int, int, bool], int] = {(0, 0, False): 1}
    for _ in range(pool_size):
        next_states: dict[tuple[int, int, bool], int] = {}
        for (chosen, current_run, has_three), count in states.items():
            skip = (chosen, 0, has_three)
            next_states[skip] = next_states.get(skip, 0) + count
            if chosen < 6:
                new_run = current_run + 1
                take = (chosen + 1, new_run, has_three or new_run >= 3)
                next_states[take] = next_states.get(take, 0) + count
        states = next_states
    favorable = sum(
        count for (chosen, _run, has_three), count in states.items() if chosen == 6 and has_three
    )
    return favorable / comb(pool_size, 6)


@cache
def exact_sum_pmf(pool_size: int) -> tuple[int, NDArray[np.float64]]:
    """Return the minimum sum and exact PMF for a uniform six-number set."""

    maximum_sum = sum(range(pool_size - 5, pool_size + 1))
    ways = np.zeros((7, maximum_sum + 1), dtype=np.int64)
    ways[0, 0] = 1
    for value in range(1, pool_size + 1):
        for chosen in range(6, 0, -1):
            ways[chosen, value:] += ways[chosen - 1, :-value]
    minimum_sum = 21
    probabilities = ways[6, minimum_sum:].astype(np.float64) / comb(pool_size, 6)
    return minimum_sum, probabilities


def expected_sum(pool_size: int) -> float:
    """Exact expectation of the sum of six sampled pool values."""

    return 3.0 * (pool_size + 1)


def expected_sum_variance(pool_size: int) -> float:
    """Exact finite-population variance of one six-number sum."""

    population_variance = (pool_size**2 - 1) / 12
    return 6 * population_variance * (pool_size - 6) / (pool_size - 1)
