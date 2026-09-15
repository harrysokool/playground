"""Reusable pre-draw economic state and current-rule accounting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from mark_six.mathematics.combinatorics import prize_outcome_odds
from mark_six.mathematics.payouts import CURRENT_FIXED_PRIZES_HKD_CENTS, expected_payout_hkd_cents
from mark_six.mathematics.prize_fund import (
    CURRENT_FIRST_DIVISION_MINIMUM_HKD_CENTS,
    allocate_turnover,
    allocate_variable_pool,
    apply_first_division_minimum,
    current_snowball_deduction,
)


@dataclass(frozen=True)
class EconomicState:
    """One current-rule draw state using no future winning-number information."""

    turnover_hkd_cents: int
    ticket_cost_hkd_cents: int
    expected_full_unit_entries: Fraction
    prize_fund_hkd_cents: Fraction
    lottery_duty_hkd_cents: Fraction
    lotteries_fund_hkd_cents: Fraction
    commission_hkd_cents: Fraction
    expected_fixed_liability_hkd_cents: Fraction
    snowball_deduction_hkd_cents: Fraction
    variable_pool_hkd_cents: Fraction
    division_funds_hkd_cents: Mapping[int, Fraction]
    advertised_first_division_fund_hkd_cents: int | None
    carried_first_division_hkd_cents: Fraction
    special_snowball_hkd_cents: Fraction
    minimum_top_up_hkd_cents: Fraction
    unresolved_minimum_hkd_cents: Fraction
    rule_version: str = "hkjc_mark_six_2024_05_21"


def build_current_state(
    turnover_hkd_cents: int,
    *,
    ticket_cost_hkd_cents: int = 1000,
    available_snowball_hkd_cents: int = 0,
    carried_first_division_hkd_cents: int = 0,
    special_snowball_hkd_cents: int = 0,
    advertised_first_division_fund_hkd_cents: int | None = None,
) -> EconomicState:
    """Apply exact current accounting using expected fixed liabilities before the draw."""

    if turnover_hkd_cents < 0 or ticket_cost_hkd_cents <= 0:
        raise ValueError("turnover must be nonnegative and ticket cost positive")
    if (
        min(
            available_snowball_hkd_cents,
            carried_first_division_hkd_cents,
            special_snowball_hkd_cents,
        )
        < 0
    ):
        raise ValueError("Snowball and carry inputs cannot be negative")
    if (
        advertised_first_division_fund_hkd_cents is not None
        and advertised_first_division_fund_hkd_cents < 0
    ):
        raise ValueError("advertised First Division fund cannot be negative")
    entries = Fraction(turnover_hkd_cents, ticket_cost_hkd_cents)
    odds = prize_outcome_odds(49, 7)
    fixed_per_entry = expected_payout_hkd_cents(odds, CURRENT_FIXED_PRIZES_HKD_CENTS)
    expected_fixed = entries * fixed_per_entry
    allocation = allocate_turnover(turnover_hkd_cents)
    deduction = current_snowball_deduction(allocation.prize_fund_hkd_cents, expected_fixed)
    variable_pool = allocation.prize_fund_hkd_cents - expected_fixed - deduction
    funds = allocate_variable_pool(variable_pool)
    carried = Fraction(carried_first_division_hkd_cents)
    special = Fraction(special_snowball_hkd_cents)
    funds[1] += carried + special
    minimum = apply_first_division_minimum(
        funds[1], available_snowball_hkd_cents, CURRENT_FIRST_DIVISION_MINIMUM_HKD_CENTS
    )
    funds[1] = minimum.final_fund_hkd_cents
    return EconomicState(
        turnover_hkd_cents=turnover_hkd_cents,
        ticket_cost_hkd_cents=ticket_cost_hkd_cents,
        expected_full_unit_entries=entries,
        prize_fund_hkd_cents=allocation.prize_fund_hkd_cents,
        lottery_duty_hkd_cents=allocation.lottery_duty_hkd_cents,
        lotteries_fund_hkd_cents=allocation.lotteries_fund_hkd_cents,
        commission_hkd_cents=allocation.hkjc_commission_hkd_cents,
        expected_fixed_liability_hkd_cents=expected_fixed,
        snowball_deduction_hkd_cents=deduction,
        variable_pool_hkd_cents=variable_pool,
        division_funds_hkd_cents=MappingProxyType(funds),
        advertised_first_division_fund_hkd_cents=advertised_first_division_fund_hkd_cents,
        carried_first_division_hkd_cents=carried,
        special_snowball_hkd_cents=special,
        minimum_top_up_hkd_cents=minimum.snowball_top_up_hkd_cents,
        unresolved_minimum_hkd_cents=minimum.unmet_minimum_hkd_cents,
    )
