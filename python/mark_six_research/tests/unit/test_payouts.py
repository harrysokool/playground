from fractions import Fraction

import pytest

from mark_six.mathematics.combinatorics import prize_outcome_odds
from mark_six.mathematics.payouts import (
    CURRENT_FIXED_PRIZES_HKD_CENTS,
    CURRENT_PAYOUT_SCHEDULE,
    PayoutSchedule,
    expected_payout_hkd_cents,
    scale_dividend_for_stake,
)


def test_current_schedule_separates_fixed_and_variable_divisions() -> None:
    assert CURRENT_PAYOUT_SCHEDULE.variable_divisions == {1, 2, 3}
    assert CURRENT_FIXED_PRIZES_HKD_CENTS == {4: 960_000, 5: 64_000, 6: 32_000, 7: 4_000}


def test_expected_fixed_payout_uses_exact_fractions() -> None:
    odds = prize_outcome_odds(49)
    expected = expected_payout_hkd_cents(odds, CURRENT_FIXED_PRIZES_HKD_CENTS)

    manual = sum(
        (
            next(item.probability for item in odds if item.outcome == f"division_{division}")
            * cents
            for division, cents in CURRENT_FIXED_PRIZES_HKD_CENTS.items()
        ),
        Fraction(),
    )
    assert expected == manual


def test_partial_dividend_scaling_does_not_round() -> None:
    assert scale_dividend_for_stake(101, 500, 1_000) == Fraction(101, 2)


def test_invalid_payout_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        PayoutSchedule({1: 10}, frozenset({1}))
    with pytest.raises(ValueError):
        expected_payout_hkd_cents(prize_outcome_odds(49), {8: 10})
    with pytest.raises(ValueError):
        scale_dividend_for_stake(-1, 500, 1_000)
