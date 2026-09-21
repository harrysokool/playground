"""Exact product-weighted sampling without replacement."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


def elementary_symmetric(weights: NDArray[np.float64], degree: int) -> NDArray[np.float64]:
    """Return coefficients e_0 through e_degree by exact dynamic programming."""

    if weights.ndim != 1:
        raise ValueError("weights must be one-dimensional")
    if degree < 0 or degree > len(weights):
        raise ValueError("degree must be between zero and the number of weights")
    if np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("weights must be finite and strictly positive")
    coefficients = np.zeros(degree + 1, dtype=np.float64)
    coefficients[0] = 1.0
    for index, weight in enumerate(weights):
        for order in range(min(degree, index + 1), 0, -1):
            coefficients[order] += weight * coefficients[order - 1]
    return coefficients


@dataclass(frozen=True)
class WeightedSubsetDistribution:
    """Distribution over unordered fixed-size subsets proportional to weight products."""

    weights: NDArray[np.float64]
    subset_size: int = 6

    def __post_init__(self) -> None:
        normalized = np.asarray(self.weights, dtype=np.float64)
        if normalized.ndim != 1:
            raise ValueError("weights must be one-dimensional")
        if self.subset_size < 1 or self.subset_size > len(normalized):
            raise ValueError("subset size must be within the pool")
        if np.any(~np.isfinite(normalized)) or np.any(normalized <= 0):
            raise ValueError("weights must be finite and strictly positive")
        object.__setattr__(self, "weights", normalized.copy())
        object.__setattr__(
            self, "_coefficients", elementary_symmetric(normalized, self.subset_size)
        )

    @property
    def normalizer(self) -> float:
        """Return e_k(weights), the exact finite normalizing sum."""

        coefficients = self.__dict__["_coefficients"]
        return float(coefficients[self.subset_size])

    def log_probability(self, subset: Iterable[int]) -> float:
        """Return the natural log probability of one 1-based unordered subset."""

        selected = tuple(int(value) for value in subset)
        if len(selected) != self.subset_size or len(set(selected)) != self.subset_size:
            raise ValueError("subset must contain the required number of unique values")
        if any(value < 1 or value > len(self.weights) for value in selected):
            raise ValueError("subset value outside the number pool")
        return float(
            sum(math.log(self.weights[value - 1]) for value in selected) - math.log(self.normalizer)
        )

    def probability(self, subset: Iterable[int]) -> float:
        """Return the probability of one 1-based unordered subset."""

        return math.exp(self.log_probability(subset))

    def marginals(self) -> NDArray[np.float64]:
        """Return exact inclusion probabilities for every number in O(Nk)."""

        coefficients = self.__dict__["_coefficients"]
        order = self.subset_size - 1
        values = np.empty(len(self.weights), dtype=np.float64)
        for index, weight in enumerate(self.weights):
            quotient = np.empty(order + 1, dtype=np.float64)
            quotient[0] = 1.0
            for degree in range(1, order + 1):
                quotient[degree] = coefficients[degree] - weight * quotient[degree - 1]
            values[index] = weight * quotient[order] / self.normalizer
        return values
