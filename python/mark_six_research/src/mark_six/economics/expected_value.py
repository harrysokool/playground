"""Exact and scenario-conditional expected-value calculations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from mark_six.economics.sharing import (
    binomial_sharing,
    popularity_adjusted_probability,
)
from mark_six.mathematics.combinatorics import prize_outcome_odds
from mark_six.mathematics.payouts import CURRENT_FIXED_PRIZES_HKD_CENTS


@dataclass(frozen=True)
class EconomicMetrics:
    """Gross payout and net ticket economics in exact cents where possible."""

    fixed_expected_payout_hkd_cents: Fraction
    variable_expected_payout_hkd_cents: float
    total_expected_payout_hkd_cents: float
    expected_profit_hkd_cents: float
    expected_return_ratio: float
    house_disadvantage: float
    expected_value_percent: float


def fixed_prize_breakdown() -> dict[int, Fraction]:
    """Return exact Division 4--7 expected cents for one current full unit."""

    odds = {
        int(row.outcome.removeprefix("division_")): row.probability
        for row in prize_outcome_odds(49, 7)
        if row.outcome.startswith("division_")
    }
    return {
        division: odds[division] * prize
        for division, prize in CURRENT_FIXED_PRIZES_HKD_CENTS.items()
    }


def expected_value(
    division_funds_hkd_cents: Mapping[int, int | Fraction],
    *,
    other_entries: int,
    ticket_cost_hkd_cents: int = 1000,
    sharing_mode: str = "uniform",
    popularity_multiplier: float = 3.0,
) -> EconomicMetrics:
    """Compute one-ticket EV from explicit Division 1--3 funds and a sharing model."""

    if set(division_funds_hkd_cents) != {1, 2, 3}:
        raise ValueError("division funds must contain exactly Divisions 1, 2, and 3")
    if any(Fraction(value) < 0 for value in division_funds_hkd_cents.values()):
        raise ValueError("division funds cannot be negative")
    if ticket_cost_hkd_cents <= 0:
        raise ValueError("ticket cost must be positive")
    probabilities = {
        int(row.outcome.removeprefix("division_")): row.probability
        for row in prize_outcome_odds(49, 7)
        if row.outcome.startswith("division_")
    }
    variable = 0.0
    for division in (1, 2, 3):
        qualification = probabilities[division]
        if sharing_mode == "no_sharing":
            share = 1.0
        elif sharing_mode == "uniform":
            share = binomial_sharing(other_entries, qualification).expected_share
        elif sharing_mode == "higher_sharing":
            sharing_probability = qualification
            if division == 1:
                sharing_probability = Fraction.from_float(
                    popularity_adjusted_probability(qualification, popularity_multiplier)
                )
            share = binomial_sharing(other_entries, sharing_probability).expected_share
        else:
            raise ValueError("sharing_mode must be no_sharing, uniform, or higher_sharing")
        variable += float(qualification) * float(division_funds_hkd_cents[division]) * share
    fixed = sum(fixed_prize_breakdown().values(), Fraction())
    total = float(fixed) + variable
    profit = total - ticket_cost_hkd_cents
    ratio = total / ticket_cost_hkd_cents
    return EconomicMetrics(
        fixed_expected_payout_hkd_cents=fixed,
        variable_expected_payout_hkd_cents=variable,
        total_expected_payout_hkd_cents=total,
        expected_profit_hkd_cents=profit,
        expected_return_ratio=ratio,
        house_disadvantage=1.0 - ratio,
        expected_value_percent=100.0 * profit / ticket_cost_hkd_cents,
    )


def first_fund_for_return_target(
    target_return_ratio: float,
    second_and_third_funds_hkd_cents: Mapping[int, int | Fraction],
    *,
    other_entries: int,
    sharing_mode: str,
    ticket_cost_hkd_cents: int = 1000,
    popularity_multiplier: float = 3.0,
) -> float:
    """Solve the conditional First Division fund required for a target return."""

    if set(second_and_third_funds_hkd_cents) != {2, 3}:
        raise ValueError("funds must contain Divisions 2 and 3")
    base = expected_value(
        {1: 0, **second_and_third_funds_hkd_cents},
        other_entries=other_entries,
        ticket_cost_hkd_cents=ticket_cost_hkd_cents,
        sharing_mode=sharing_mode,
        popularity_multiplier=popularity_multiplier,
    )
    first_probability = prize_outcome_odds(49, 7)[0].probability
    if sharing_mode == "no_sharing":
        share = 1.0
    else:
        probability = first_probability
        if sharing_mode == "higher_sharing":
            probability = Fraction.from_float(
                popularity_adjusted_probability(first_probability, popularity_multiplier)
            )
        share = binomial_sharing(other_entries, probability).expected_share
    required = target_return_ratio * ticket_cost_hkd_cents - base.total_expected_payout_hkd_cents
    return max(0.0, required / (float(first_probability) * share))
