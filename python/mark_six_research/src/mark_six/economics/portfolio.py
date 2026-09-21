"""Entry-package equivalence and fixed-budget portfolio diagnostics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from mark_six.mathematics.combinatorics import (
    prize_outcome_odds,
    probability_of_any_prize,
    total_six_number_tickets,
)
from mark_six.mathematics.entries import (
    PrizeVector,
    banker_combination_count,
    banker_outcome_distribution,
    multiple_combination_count,
    multiple_outcome_distribution,
)

Ticket = tuple[int, ...]


@dataclass(frozen=True)
class PortfolioMetrics:
    """Coverage and overlap diagnostics for owned ordinary combinations."""

    ticket_count: int
    unique_combinations: int
    duplicate_units: int
    unique_numbers: int
    mean_shared_numbers: float
    maximum_shared_numbers: int
    repeated_owned_pairs: int
    first_division_probability: Fraction
    linear_expected_payout_hkd_cents: float


@dataclass(frozen=True)
class SystemEntryEconomics:
    """Exact economics including covariance across a packaged entry's lines."""

    entry_type: str
    combination_count: int
    cost_hkd_cents: int
    expected_payout_hkd_cents: Fraction
    equivalent_ordinary_expected_payout_hkd_cents: Fraction
    payout_variance_hkd_cents_squared: Fraction
    probability_any_prize: Fraction


def _ticket(ticket: Ticket) -> Ticket:
    normalized = tuple(sorted(ticket))
    if len(normalized) != 6 or len(set(normalized)) != 6:
        raise ValueError("each ticket must contain six unique numbers")
    if normalized[0] < 1 or normalized[-1] > 49:
        raise ValueError("ticket numbers must be within 1..49")
    return normalized


def portfolio_metrics(
    tickets: tuple[Ticket, ...], *, expected_payout_per_line_hkd_cents: float
) -> PortfolioMetrics:
    """Measure duplicates, overlaps, coverage, and linear expected payout."""

    if not tickets:
        raise ValueError("portfolio cannot be empty")
    normalized = tuple(_ticket(ticket) for ticket in tickets)
    counts = Counter(normalized)
    overlaps = [len(set(left) & set(right)) for left, right in combinations(normalized, 2)]
    owned_pairs = Counter(pair for ticket in normalized for pair in combinations(ticket, 2))
    repeated_pairs = sum(count - 1 for count in owned_pairs.values() if count > 1)
    unique = len(counts)
    return PortfolioMetrics(
        ticket_count=len(normalized),
        unique_combinations=unique,
        duplicate_units=len(normalized) - unique,
        unique_numbers=len(set().union(*map(set, normalized))),
        mean_shared_numbers=sum(overlaps) / len(overlaps) if overlaps else 0.0,
        maximum_shared_numbers=max(overlaps, default=0),
        repeated_owned_pairs=repeated_pairs,
        first_division_probability=Fraction(unique, total_six_number_tickets(49)),
        linear_expected_payout_hkd_cents=len(normalized) * expected_payout_per_line_hkd_cents,
    )


def _system_entry_economics(
    entry_type: str,
    combination_count: int,
    distribution: Mapping[PrizeVector, int],
    dividends_hkd_cents: Mapping[int, int | Fraction],
    *,
    ticket_cost_hkd_cents: int = 1000,
) -> SystemEntryEconomics:
    sample_space = total_six_number_tickets(49) * 43
    payouts = {
        vector: sum(
            (
                Fraction(vector.count(division)) * Fraction(amount)
                for division, amount in dividends_hkd_cents.items()
            ),
            Fraction(),
        )
        for vector in distribution
    }
    mean = sum(
        (Fraction(ways, sample_space) * payouts[vector] for vector, ways in distribution.items()),
        Fraction(),
    )
    second = sum(
        (
            Fraction(ways, sample_space) * payouts[vector] ** 2
            for vector, ways in distribution.items()
        ),
        Fraction(),
    )
    any_probability = sum(
        (
            Fraction(ways, sample_space)
            for vector, ways in distribution.items()
            if vector.no_prize_combinations < combination_count
        ),
        Fraction(),
    )
    single_mean = sum(
        (
            row.probability * Fraction(dividends_hkd_cents.get(division, 0))
            for division, row in enumerate(prize_outcome_odds(49, 7)[:7], start=1)
        ),
        Fraction(),
    )
    equivalent = combination_count * single_mean
    assert mean == equivalent
    return SystemEntryEconomics(
        entry_type=entry_type,
        combination_count=combination_count,
        cost_hkd_cents=combination_count * ticket_cost_hkd_cents,
        expected_payout_hkd_cents=mean,
        equivalent_ordinary_expected_payout_hkd_cents=equivalent,
        payout_variance_hkd_cents_squared=second - mean**2,
        probability_any_prize=any_probability,
    )


def multiple_entry_economics(
    selection_count: int, dividends_hkd_cents: Mapping[int, int | Fraction]
) -> SystemEntryEconomics:
    """Return exact Multiple economics and expanded-line equivalence."""

    count = multiple_combination_count(selection_count)
    return _system_entry_economics(
        "multiple", count, multiple_outcome_distribution(49, selection_count), dividends_hkd_cents
    )


def banker_entry_economics(
    banker_count: int,
    leg_count: int,
    dividends_hkd_cents: Mapping[int, int | Fraction],
) -> SystemEntryEconomics:
    """Return exact Banker economics and expanded-line equivalence."""

    count = banker_combination_count(banker_count, leg_count)
    return _system_entry_economics(
        "banker",
        count,
        banker_outcome_distribution(49, banker_count, leg_count),
        dividends_hkd_cents,
    )


def ordinary_any_prize_probability() -> Fraction:
    """Expose the exact one-line any-prize probability for portfolio reporting."""

    return probability_of_any_prize(49, 7)
