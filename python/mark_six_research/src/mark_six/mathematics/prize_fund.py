"""Exact current-rule prize-fund and variable-prize arithmetic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from mark_six.mathematics.combinatorics import OutcomeOdds
from mark_six.mathematics.evidence import EvidenceType
from mark_six.mathematics.payouts import (
    CURRENT_FIXED_PRIZES_HKD_CENTS,
    expected_payout_hkd_cents,
)

Money = int | Fraction

PRIZE_FUND_SHARE = Fraction(54, 100)
LOTTERY_DUTY_SHARE = Fraction(25, 100)
LOTTERIES_FUND_SHARE = Fraction(15, 100)
HKJC_COMMISSION_SHARE = Fraction(6, 100)
FIRST_DIVISION_SHARE = Fraction(45, 100)
SECOND_DIVISION_SHARE = Fraction(15, 100)
THIRD_DIVISION_SHARE = Fraction(40, 100)
CURRENT_FIRST_DIVISION_MINIMUM_HKD_CENTS = 800_000_000


def _nonnegative_money(value: Money, name: str) -> Fraction:
    result = Fraction(value)
    if result < 0:
        raise ValueError(f"{name} cannot be negative")
    return result


def _winning_units(values: Mapping[int, Money], divisions: set[int]) -> dict[int, Fraction]:
    unknown = set(values) - divisions
    if unknown:
        raise ValueError(f"winning units include unavailable divisions: {sorted(unknown)}")
    return {
        division: _nonnegative_money(values.get(division, 0), f"Division {division} winning units")
        for division in divisions
    }


@dataclass(frozen=True)
class TurnoverAllocation:
    """Current official allocation of turnover, before prize calculations."""

    turnover_hkd_cents: Fraction
    prize_fund_hkd_cents: Fraction
    lottery_duty_hkd_cents: Fraction
    lotteries_fund_hkd_cents: Fraction
    hkjc_commission_hkd_cents: Fraction
    evidence_type: EvidenceType = EvidenceType.OFFICIAL_RULE_CALCULATION


def allocate_turnover(turnover_hkd_cents: Money) -> TurnoverAllocation:
    """Apply the current official 54/25/15/6 turnover percentages exactly."""

    turnover = _nonnegative_money(turnover_hkd_cents, "turnover")
    result = TurnoverAllocation(
        turnover_hkd_cents=turnover,
        prize_fund_hkd_cents=turnover * PRIZE_FUND_SHARE,
        lottery_duty_hkd_cents=turnover * LOTTERY_DUTY_SHARE,
        lotteries_fund_hkd_cents=turnover * LOTTERIES_FUND_SHARE,
        hkjc_commission_hkd_cents=turnover * HKJC_COMMISSION_SHARE,
    )
    assert (
        result.prize_fund_hkd_cents
        + result.lottery_duty_hkd_cents
        + result.lotteries_fund_hkd_cents
        + result.hkjc_commission_hkd_cents
        == turnover
    )
    return result


def current_fixed_prize_total(winning_units: Mapping[int, Money]) -> Fraction:
    """Return the exact amount payable to current fixed Divisions 4-7."""

    units = _winning_units(winning_units, set(CURRENT_FIXED_PRIZES_HKD_CENTS))
    return sum(
        (units[division] * amount for division, amount in CURRENT_FIXED_PRIZES_HKD_CENTS.items()),
        Fraction(),
    )


class ExceptionalPrizeFundingRequired(ValueError):
    """Raised when the standard formula crosses a formal exceptional-funding boundary."""


def current_snowball_deduction(
    prize_fund_hkd_cents: Money, fixed_prizes_hkd_cents: Money
) -> Fraction:
    """Apply the published Snowball Deduction formula effective 2024-05-21."""

    prize_fund = _nonnegative_money(prize_fund_hkd_cents, "prize fund")
    fixed = _nonnegative_money(fixed_prizes_hkd_cents, "fixed prizes")
    sixty_percent_prize_fund = Fraction(60, 100) * prize_fund
    if fixed > sixty_percent_prize_fund:
        raise ExceptionalPrizeFundingRequired(
            "fixed prizes exceed 60% of the Prize Fund; Lotteries Rule 3.16 exceptional "
            "Snowball funding/rateable-reduction mechanics are required"
        )
    base = sixty_percent_prize_fund - fixed
    deduction = (
        Fraction(9, 100) * (prize_fund - fixed - Fraction(55, 100) * base)
        + Fraction(55, 100) * base
    )
    assert deduction >= 0
    return deduction


@dataclass(frozen=True)
class CurrentDrawAllocation:
    """Standard current-draw allocation before minimum and no-winner adjustments."""

    turnover: TurnoverAllocation
    fixed_prizes_hkd_cents: Fraction
    snowball_deduction_hkd_cents: Fraction
    available_variable_pool_hkd_cents: Fraction
    division_funds_hkd_cents: Mapping[int, Fraction]
    evidence_type: EvidenceType = EvidenceType.OFFICIAL_RULE_CALCULATION


def current_draw_allocation(
    turnover_hkd_cents: Money, fixed_winning_units: Mapping[int, Money]
) -> CurrentDrawAllocation:
    """Reproduce the standard current Prize Fund and 45/15/40 allocation exactly."""

    turnover = allocate_turnover(turnover_hkd_cents)
    fixed = current_fixed_prize_total(fixed_winning_units)
    snowball = current_snowball_deduction(turnover.prize_fund_hkd_cents, fixed)
    available = turnover.prize_fund_hkd_cents - fixed - snowball
    funds = allocate_variable_pool(available)
    assert sum(funds.values(), Fraction()) == available
    return CurrentDrawAllocation(
        turnover=turnover,
        fixed_prizes_hkd_cents=fixed,
        snowball_deduction_hkd_cents=snowball,
        available_variable_pool_hkd_cents=available,
        division_funds_hkd_cents=funds,
    )


def allocate_variable_pool(
    available_prize_pool_hkd_cents: Money,
    *,
    first_division_allocation: Fraction = FIRST_DIVISION_SHARE,
    second_division_allocation: Fraction = SECOND_DIVISION_SHARE,
    third_division_allocation: Fraction = THIRD_DIVISION_SHARE,
) -> dict[int, Fraction]:
    """Allocate an explicit variable pool using explicit exact shares."""

    available = _nonnegative_money(available_prize_pool_hkd_cents, "available prize pool")
    shares = {
        1: Fraction(first_division_allocation),
        2: Fraction(second_division_allocation),
        3: Fraction(third_division_allocation),
    }
    if any(share < 0 for share in shares.values()) or sum(shares.values(), Fraction()) != 1:
        raise ValueError(
            "First, Second, and Third Division allocations must be nonnegative and sum to 1"
        )
    return {division: available * share for division, share in shares.items()}


@dataclass(frozen=True)
class FirstDivisionMinimumResult:
    """Exact top-up result without hiding an insufficient Snowball balance."""

    original_fund_hkd_cents: Fraction
    minimum_hkd_cents: Fraction
    snowball_top_up_hkd_cents: Fraction
    final_fund_hkd_cents: Fraction
    remaining_snowball_hkd_cents: Fraction
    unmet_minimum_hkd_cents: Fraction
    evidence_type: EvidenceType = EvidenceType.OFFICIAL_RULE_CALCULATION


def apply_first_division_minimum(
    first_division_fund_hkd_cents: Money,
    available_snowball_hkd_cents: Money,
    minimum_hkd_cents: Money = CURRENT_FIRST_DIVISION_MINIMUM_HKD_CENTS,
) -> FirstDivisionMinimumResult:
    """Apply the current HKD 8m First Division fund minimum as far as funds allow."""

    original = _nonnegative_money(first_division_fund_hkd_cents, "First Division fund")
    snowball = _nonnegative_money(available_snowball_hkd_cents, "available Snowball")
    minimum = _nonnegative_money(minimum_hkd_cents, "First Division minimum")
    required = max(minimum - original, Fraction())
    top_up = min(required, snowball)
    final = original + top_up
    return FirstDivisionMinimumResult(
        original_fund_hkd_cents=original,
        minimum_hkd_cents=minimum,
        snowball_top_up_hkd_cents=top_up,
        final_fund_hkd_cents=final,
        remaining_snowball_hkd_cents=snowball - top_up,
        unmet_minimum_hkd_cents=max(minimum - final, Fraction()),
    )


@dataclass(frozen=True)
class VariablePrizePoolInputs:
    """Explicit economic and prize-sharing inputs; none are predicted by this module."""

    available_prize_pool_hkd_cents: Money
    winning_units: Mapping[int, Money]
    first_division_allocation: Fraction = FIRST_DIVISION_SHARE
    second_division_allocation: Fraction = SECOND_DIVISION_SHARE
    third_division_allocation: Fraction = THIRD_DIVISION_SHARE
    carried_jackpot_hkd_cents: Money = 0
    snowball_contribution_hkd_cents: Money = 0
    special_jackpot_contribution_hkd_cents: Money = 0
    prize_pool_evidence: EvidenceType = EvidenceType.ECONOMIC_ASSUMPTION
    winning_units_evidence: EvidenceType = EvidenceType.BEHAVIORAL_ASSUMPTION


@dataclass(frozen=True)
class VariablePrizeSettlement:
    """Division funds, shared dividends, reallocations, and next-draw carry-forward."""

    division_funds_hkd_cents: Mapping[int, Fraction]
    dividends_per_unit_hkd_cents: Mapping[int, Fraction | None]
    winning_units: Mapping[int, Fraction]
    first_division_contributions_hkd_cents: Mapping[str, Fraction]
    third_division_reallocation_hkd_cents: Mapping[int, Fraction]
    carry_forward_to_first_next_draw_hkd_cents: Fraction
    calculation_evidence: EvidenceType = EvidenceType.OFFICIAL_RULE_CALCULATION
    prize_pool_evidence: EvidenceType = EvidenceType.ECONOMIC_ASSUMPTION
    winning_units_evidence: EvidenceType = EvidenceType.BEHAVIORAL_ASSUMPTION


@dataclass(frozen=True)
class PrizeShareResult:
    """Exact division sharing and optional official unit-stake rounding."""

    prize_fund_hkd_cents: Fraction
    winning_units: Fraction
    unrounded_dividend_per_unit_hkd_cents: Fraction
    dividend_per_unit_hkd_cents: Fraction
    total_paid_hkd_cents: Fraction
    rounding_surplus_hkd_cents: Fraction
    evidence_type: EvidenceType = EvidenceType.OFFICIAL_RULE_CALCULATION


def share_prize_fund(
    prize_fund_hkd_cents: Money,
    winning_units: Money,
    *,
    rounding_unit_hkd_cents: int | None = None,
) -> PrizeShareResult:
    """Divide a fund exactly and optionally apply Rule 3.17-style downward rounding."""

    fund = _nonnegative_money(prize_fund_hkd_cents, "prize fund")
    units = _nonnegative_money(winning_units, "winning units")
    if units == 0:
        raise ValueError("winning units must be positive to share a prize fund")
    if units < 1:
        raise ValueError(
            "a sole partial-unit winner requires the special Lotteries Rule 3.10 branch"
        )
    unrounded = fund / units
    if rounding_unit_hkd_cents is None:
        dividend = unrounded
    else:
        if rounding_unit_hkd_cents <= 0:
            raise ValueError("rounding unit must be positive")
        dividend = Fraction((unrounded // rounding_unit_hkd_cents) * rounding_unit_hkd_cents)
    total_paid = dividend * units
    return PrizeShareResult(
        prize_fund_hkd_cents=fund,
        winning_units=units,
        unrounded_dividend_per_unit_hkd_cents=unrounded,
        dividend_per_unit_hkd_cents=dividend,
        total_paid_hkd_cents=total_paid,
        rounding_surplus_hkd_cents=fund - total_paid,
    )


def settle_variable_prizes(inputs: VariablePrizePoolInputs) -> VariablePrizeSettlement:
    """Apply explicit contributions, prize sharing, and current no-winner rules exactly."""

    funds = allocate_variable_pool(
        inputs.available_prize_pool_hkd_cents,
        first_division_allocation=inputs.first_division_allocation,
        second_division_allocation=inputs.second_division_allocation,
        third_division_allocation=inputs.third_division_allocation,
    )
    contributions = {
        "carried_jackpot": _nonnegative_money(inputs.carried_jackpot_hkd_cents, "carried jackpot"),
        "snowball": _nonnegative_money(inputs.snowball_contribution_hkd_cents, "Snowball"),
        "special_jackpot": _nonnegative_money(
            inputs.special_jackpot_contribution_hkd_cents, "special jackpot"
        ),
    }
    funds[1] += sum(contributions.values(), Fraction())
    units = _winning_units(inputs.winning_units, {1, 2, 3})
    if any(0 < unit_count < 1 for unit_count in units.values()):
        raise ValueError(
            "a sole partial-unit winner requires the special Lotteries Rule 3.10 branch"
        )
    reallocation = {1: Fraction(), 2: Fraction()}
    carry_forward = Fraction()

    if units[3] == 0:
        third_fund = funds[3]
        funds[3] = Fraction()
        if units[1] > 0 and units[2] > 0:
            reallocation[1] = Fraction(75, 100) * third_fund
            reallocation[2] = Fraction(25, 100) * third_fund
            funds[1] += reallocation[1]
            funds[2] += reallocation[2]
        elif units[1] > 0:
            reallocation[1] = third_fund
            funds[1] += third_fund
        elif units[2] > 0:
            reallocation[2] = third_fund
            funds[2] += third_fund
        else:
            carry_forward += third_fund

    for division in (1, 2):
        if units[division] == 0:
            carry_forward += funds[division]
            funds[division] = Fraction()

    dividends = {
        division: (
            share_prize_fund(funds[division], units[division]).dividend_per_unit_hkd_cents
            if units[division] > 0
            else None
        )
        for division in (1, 2, 3)
    }
    return VariablePrizeSettlement(
        division_funds_hkd_cents=funds,
        dividends_per_unit_hkd_cents=dividends,
        winning_units=units,
        first_division_contributions_hkd_cents=contributions,
        third_division_reallocation_hkd_cents=reallocation,
        carry_forward_to_first_next_draw_hkd_cents=carry_forward,
        prize_pool_evidence=inputs.prize_pool_evidence,
        winning_units_evidence=inputs.winning_units_evidence,
    )


@dataclass(frozen=True)
class ExpectedValueBreakdown:
    """Expected payout per ordinary full-unit ticket, with evidence labels."""

    fixed_prize_contribution_hkd_cents: Fraction
    variable_prize_contribution_hkd_cents: Fraction
    total_expected_payout_hkd_cents: Fraction
    settlement: VariablePrizeSettlement
    fixed_evidence: EvidenceType = EvidenceType.OFFICIAL_RULE_CALCULATION
    probability_evidence: EvidenceType = EvidenceType.EXACT_COMBINATORIAL_RESULT


def expected_value_from_explicit_pool(
    odds: tuple[OutcomeOdds, ...], inputs: VariablePrizePoolInputs
) -> ExpectedValueBreakdown:
    """Combine exact probabilities with explicit, labeled variable-payout inputs."""

    settlement = settle_variable_prizes(inputs)
    variable_dividends = {
        division: dividend
        for division, dividend in settlement.dividends_per_unit_hkd_cents.items()
        if dividend is not None
    }
    fixed = expected_payout_hkd_cents(odds, CURRENT_FIXED_PRIZES_HKD_CENTS)
    variable = expected_payout_hkd_cents(odds, variable_dividends)
    return ExpectedValueBreakdown(
        fixed_prize_contribution_hkd_cents=fixed,
        variable_prize_contribution_hkd_cents=variable,
        total_expected_payout_hkd_cents=fixed + variable,
        settlement=settlement,
    )
