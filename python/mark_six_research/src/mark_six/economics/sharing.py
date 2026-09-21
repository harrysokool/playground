"""Transparent prize-sharing distributions for independent player entries."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class SharingResult:
    """Conditional sharing for our qualifying unit and other full-unit entries."""

    other_entries: int
    other_entry_probability: float
    expected_other_winning_units: float
    expected_share: float
    sole_winner_probability: float
    share_with_one_probability: float
    share_with_multiple_probability: float


def binomial_sharing(
    other_entries: int, qualification_probability: int | float | Fraction
) -> SharingResult:
    """Return exact-binomial probabilities and E[1/(1+X)] using stable floats."""

    probability = float(qualification_probability)
    if other_entries < 0:
        raise ValueError("other_entries cannot be negative")
    if not 0.0 < probability <= 1.0:
        raise ValueError("qualification_probability must be in (0, 1]")
    if probability == 1.0:
        sole = float(other_entries == 0)
        one = float(other_entries == 1)
        share = 1.0 / (other_entries + 1)
    else:
        log_failure = math.log1p(-probability)
        sole = math.exp(other_entries * log_failure)
        one = (
            other_entries * probability * math.exp((other_entries - 1) * log_failure)
            if other_entries
            else 0.0
        )
        share = -math.expm1((other_entries + 1) * log_failure) / ((other_entries + 1) * probability)
    return SharingResult(
        other_entries=other_entries,
        other_entry_probability=probability,
        expected_other_winning_units=other_entries * probability,
        expected_share=share,
        sole_winner_probability=sole,
        share_with_one_probability=one,
        share_with_multiple_probability=max(0.0, 1.0 - sole - one),
    )


def poisson_sharing(expected_other_winners: float) -> SharingResult:
    """Return the Poisson approximation for comparison with the binomial benchmark."""

    if expected_other_winners < 0:
        raise ValueError("expected_other_winners cannot be negative")
    lam = expected_other_winners
    sole = math.exp(-lam)
    one = lam * sole
    share = (1.0 - sole) / lam if lam else 1.0
    return SharingResult(
        other_entries=0,
        other_entry_probability=0.0,
        expected_other_winning_units=lam,
        expected_share=share,
        sole_winner_probability=sole,
        share_with_one_probability=one,
        share_with_multiple_probability=max(0.0, 1.0 - sole - one),
    )


def popularity_adjusted_probability(uniform_probability: Fraction, multiplier: float) -> float:
    """Apply an explicit synthetic popularity multiplier without changing draw odds."""

    if multiplier <= 0:
        raise ValueError("popularity multiplier must be positive")
    return min(1.0, float(uniform_probability) * multiplier)
