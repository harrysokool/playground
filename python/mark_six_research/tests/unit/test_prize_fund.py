from fractions import Fraction

import pytest

from mark_six.mathematics.combinatorics import prize_outcome_odds
from mark_six.mathematics.evidence import EvidenceType
from mark_six.mathematics.prize_fund import (
    ExceptionalPrizeFundingRequired,
    VariablePrizePoolInputs,
    allocate_turnover,
    allocate_variable_pool,
    apply_first_division_minimum,
    current_draw_allocation,
    current_fixed_prize_total,
    current_snowball_deduction,
    expected_value_from_explicit_pool,
    settle_variable_prizes,
    share_prize_fund,
)


def test_current_turnover_shares_are_exact_and_exhaustive() -> None:
    allocation = allocate_turnover(100)

    assert allocation.prize_fund_hkd_cents == 54
    assert allocation.lottery_duty_hkd_cents == 25
    assert allocation.lotteries_fund_hkd_cents == 15
    assert allocation.hkjc_commission_hkd_cents == 6
    assert allocation.evidence_type == EvidenceType.OFFICIAL_RULE_CALCULATION


def test_fixed_prize_liability_uses_winning_units_and_exact_cents() -> None:
    assert current_fixed_prize_total({4: 2, 5: 3, 6: 4, 7: 5}) == 2_260_000
    assert current_fixed_prize_total({4: Fraction(1, 2)}) == 480_000


def test_published_snowball_formula_and_variable_allocations() -> None:
    deduction = current_snowball_deduction(10_000_000, 1_000_000)
    funds = allocate_variable_pool(5_687_500)

    assert deduction == 3_312_500
    assert funds == {1: 2_559_375, 2: 853_125, 3: 2_275_000}
    assert sum(funds.values(), Fraction()) == 5_687_500


def test_current_draw_allocation_keeps_every_prize_fund_component_separate() -> None:
    result = current_draw_allocation(100_000_000, {})

    assert result.turnover.prize_fund_hkd_cents == 54_000_000
    assert result.fixed_prizes_hkd_cents == 0
    assert result.snowball_deduction_hkd_cents == 21_076_200
    assert result.available_variable_pool_hkd_cents == 32_923_800
    assert result.division_funds_hkd_cents == {
        1: 14_815_710,
        2: 4_938_570,
        3: 13_169_520,
    }


def test_standard_snowball_formula_rejects_exceptional_fixed_prize_state() -> None:
    with pytest.raises(ExceptionalPrizeFundingRequired, match=r"Rule 3\.16"):
        current_snowball_deduction(1_000, 601)


def test_first_division_minimum_exposes_top_up_and_unmet_shortfall() -> None:
    funded = apply_first_division_minimum(500_000_000, 400_000_000)
    short = apply_first_division_minimum(500_000_000, 100_000_000)

    assert funded.snowball_top_up_hkd_cents == 300_000_000
    assert funded.final_fund_hkd_cents == 800_000_000
    assert funded.remaining_snowball_hkd_cents == 100_000_000
    assert funded.unmet_minimum_hkd_cents == 0
    assert short.final_fund_hkd_cents == 600_000_000
    assert short.unmet_minimum_hkd_cents == 200_000_000


def test_variable_pool_sharing_keeps_contributions_separate() -> None:
    settlement = settle_variable_prizes(
        VariablePrizePoolInputs(
            available_prize_pool_hkd_cents=1_000,
            winning_units={1: 2, 2: 3, 3: 4},
            carried_jackpot_hkd_cents=100,
            snowball_contribution_hkd_cents=50,
            special_jackpot_contribution_hkd_cents=25,
        )
    )

    assert settlement.first_division_contributions_hkd_cents == {
        "carried_jackpot": 100,
        "snowball": 50,
        "special_jackpot": 25,
    }
    assert settlement.division_funds_hkd_cents == {1: 625, 2: 150, 3: 400}
    assert settlement.dividends_per_unit_hkd_cents == {
        1: Fraction(625, 2),
        2: 50,
        3: 100,
    }
    assert settlement.prize_pool_evidence == EvidenceType.ECONOMIC_ASSUMPTION
    assert settlement.winning_units_evidence == EvidenceType.BEHAVIORAL_ASSUMPTION


def test_no_third_division_winner_reallocates_75_25() -> None:
    settlement = settle_variable_prizes(
        VariablePrizePoolInputs(
            available_prize_pool_hkd_cents=1_000,
            winning_units={1: 1, 2: 1, 3: 0},
        )
    )

    assert settlement.division_funds_hkd_cents == {1: 750, 2: 250, 3: 0}
    assert settlement.third_division_reallocation_hkd_cents == {1: 300, 2: 100}
    assert settlement.carry_forward_to_first_next_draw_hkd_cents == 0


def test_prize_sharing_and_rounding_are_exact() -> None:
    unrounded = share_prize_fund(10_005, 2)
    rounded = share_prize_fund(10_005, 2, rounding_unit_hkd_cents=1_000)

    assert unrounded.dividend_per_unit_hkd_cents == Fraction(10_005, 2)
    assert unrounded.rounding_surplus_hkd_cents == 0
    assert rounded.dividend_per_unit_hkd_cents == 5_000
    assert rounded.total_paid_hkd_cents == 10_000
    assert rounded.rounding_surplus_hkd_cents == 5


def test_sole_partial_unit_requires_special_rule_branch() -> None:
    with pytest.raises(ValueError, match="sole partial"):
        share_prize_fund(10_000, Fraction(1, 2))
    with pytest.raises(ValueError, match="sole partial"):
        settle_variable_prizes(
            VariablePrizePoolInputs(
                available_prize_pool_hkd_cents=10_000,
                winning_units={1: Fraction(1, 2)},
            )
        )


def test_no_variable_winners_carries_all_funds_to_next_first_division() -> None:
    settlement = settle_variable_prizes(
        VariablePrizePoolInputs(
            available_prize_pool_hkd_cents=1_000,
            winning_units={},
            carried_jackpot_hkd_cents=200,
        )
    )

    assert settlement.division_funds_hkd_cents == {1: 0, 2: 0, 3: 0}
    assert settlement.carry_forward_to_first_next_draw_hkd_cents == 1_200
    assert all(value is None for value in settlement.dividends_per_unit_hkd_cents.values())


def test_expected_value_breakdown_does_not_predict_winning_units() -> None:
    odds = prize_outcome_odds(49)
    result = expected_value_from_explicit_pool(
        odds,
        VariablePrizePoolInputs(
            available_prize_pool_hkd_cents=1_000_000,
            winning_units={1: 2, 2: 4, 3: 8},
        ),
    )
    total = 13_983_816
    independent_fixed = Fraction(
        630 * 960_000 + 12_915 * 64_000 + 17_220 * 32_000 + 229_600 * 4_000,
        total,
    )
    independent_variable = (
        Fraction(450_000, 2 * total)
        + Fraction(6 * 150_000, 4 * total)
        + Fraction(252 * 400_000, 8 * total)
    )

    assert result.fixed_prize_contribution_hkd_cents == independent_fixed
    assert result.variable_prize_contribution_hkd_cents == independent_variable
    assert result.total_expected_payout_hkd_cents == independent_fixed + independent_variable


def test_invalid_economic_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        allocate_variable_pool(100, first_division_allocation=Fraction(1, 2))
    with pytest.raises(ValueError, match="negative"):
        allocate_turnover(-1)
    with pytest.raises(ValueError, match="unavailable"):
        current_fixed_prize_total({3: 1})
