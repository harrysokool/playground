"""Seeded Monte Carlo checks for the exact engine; never a prediction engine."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from math import sqrt
from random import Random

from mark_six.mathematics.combinatorics import (
    PRIZE_PATTERN_BY_DIVISION,
    MatchPattern,
    classify_ticket_outcome,
    prize_outcome_odds,
    total_six_number_tickets,
)
from mark_six.mathematics.evidence import EvidenceType


def generate_valid_ticket(pool_size: int, random_source: Random) -> tuple[int, ...]:
    """Generate one uniformly sampled, sorted six-number ticket."""

    total_six_number_tickets(pool_size)
    return tuple(sorted(random_source.sample(range(1, pool_size + 1), 6)))


def generate_fair_draw(pool_size: int, random_source: Random) -> tuple[frozenset[int], int]:
    """Generate six unordered main numbers followed by one distinct Extra Number."""

    total_six_number_tickets(pool_size)
    values = random_source.sample(range(1, pool_size + 1), 7)
    return frozenset(values[:6]), values[6]


@dataclass(frozen=True)
class SimulationComparison:
    """One simulation estimate compared with its exact probability."""

    outcome: str
    observed_count: int
    estimated_probability: Fraction
    exact_probability: Fraction
    absolute_error: Fraction
    tolerance: float
    within_tolerance: bool
    evidence_type: EvidenceType = EvidenceType.SIMULATION_ESTIMATE


@dataclass(frozen=True)
class SimulationResult:
    """Reproducible fixed-ticket simulation and exact comparison."""

    pool_size: int
    prize_divisions: int
    trials: int
    seed: int
    ticket: tuple[int, ...]
    comparisons: tuple[SimulationComparison, ...]
    evidence_type: EvidenceType = EvidenceType.SIMULATION_ESTIMATE


def _outcome_name(pattern: MatchPattern, prize_divisions: int) -> str:
    for division in range(1, prize_divisions + 1):
        if pattern == PRIZE_PATTERN_BY_DIVISION[division]:
            return f"division_{division}"
    return "no_prize"


def binomial_tolerance(probability: Fraction, trials: int, z_score: float = 6.0) -> float:
    """Return a conservative z-score sampling band plus one-count discretization."""

    if trials < 1:
        raise ValueError("trials must be positive")
    if z_score <= 0:
        raise ValueError("z_score must be positive")
    p = float(probability)
    return z_score * sqrt(p * (1.0 - p) / trials) + (1.0 / trials)


def simulate_ticket_outcomes(
    *,
    pool_size: int,
    prize_divisions: int = 7,
    trials: int,
    seed: int,
    ticket: tuple[int, ...] | None = None,
    tolerance_z_score: float = 6.0,
) -> SimulationResult:
    """Simulate fair draws solely to compare empirical and exact outcome probabilities."""

    if trials < 1:
        raise ValueError("trials must be positive")
    exact = prize_outcome_odds(pool_size, prize_divisions)
    random_source = Random(seed)
    selected_ticket = ticket or generate_valid_ticket(pool_size, random_source)
    if (
        len(selected_ticket) != 6
        or len(set(selected_ticket)) != 6
        or any(number < 1 or number > pool_size for number in selected_ticket)
    ):
        raise ValueError(f"ticket must contain six unique numbers within 1..{pool_size}")
    selected_ticket = tuple(sorted(selected_ticket))
    counts: Counter[str] = Counter()
    for _ in range(trials):
        main_numbers, extra_number = generate_fair_draw(pool_size, random_source)
        pattern = classify_ticket_outcome(selected_ticket, main_numbers, extra_number)
        counts[_outcome_name(pattern, prize_divisions)] += 1

    comparisons = []
    for item in exact:
        estimate = Fraction(counts[item.outcome], trials)
        absolute_error = abs(estimate - item.probability)
        tolerance = binomial_tolerance(item.probability, trials, tolerance_z_score)
        comparisons.append(
            SimulationComparison(
                outcome=item.outcome,
                observed_count=counts[item.outcome],
                estimated_probability=estimate,
                exact_probability=item.probability,
                absolute_error=absolute_error,
                tolerance=tolerance,
                within_tolerance=float(absolute_error) <= tolerance,
            )
        )
    assert sum(item.observed_count for item in comparisons) == trials
    return SimulationResult(
        pool_size=pool_size,
        prize_divisions=prize_divisions,
        trials=trials,
        seed=seed,
        ticket=selected_ticket,
        comparisons=tuple(comparisons),
    )
