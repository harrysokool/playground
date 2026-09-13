"""Exact payout-expectation primitives separated from prize probabilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from mark_six.mathematics.combinatorics import OutcomeOdds

CURRENT_FIXED_PRIZES_HKD_CENTS = {4: 960_000, 5: 64_000, 6: 32_000, 7: 4_000}


@dataclass(frozen=True)
class PayoutSchedule:
    """Separate known fixed dividends from variable pari-mutuel divisions."""

    fixed_prizes_hkd_cents: Mapping[int, int]
    variable_divisions: frozenset[int]

    def __post_init__(self) -> None:
        if set(self.fixed_prizes_hkd_cents) & self.variable_divisions:
            raise ValueError("a division cannot be both fixed and variable")
        if any(amount < 0 for amount in self.fixed_prizes_hkd_cents.values()):
            raise ValueError("fixed prizes cannot be negative")


CURRENT_PAYOUT_SCHEDULE = PayoutSchedule(
    fixed_prizes_hkd_cents=CURRENT_FIXED_PRIZES_HKD_CENTS,
    variable_divisions=frozenset({1, 2, 3}),
)


def expected_payout_hkd_cents(
    odds: tuple[OutcomeOdds, ...], dividends_hkd_cents: Mapping[int, int | Fraction]
) -> Fraction:
    """Return exact expectation for supplied per-unit dividends without estimating missing pools."""

    probabilities = {
        int(item.outcome.removeprefix("division_")): item.probability
        for item in odds
        if item.outcome.startswith("division_")
    }
    unknown = set(dividends_hkd_cents) - probabilities.keys()
    if unknown:
        raise ValueError(f"dividends include unavailable divisions: {sorted(unknown)}")
    if any(Fraction(amount) < 0 for amount in dividends_hkd_cents.values()):
        raise ValueError("dividends cannot be negative")
    return sum(
        (
            probabilities[division] * Fraction(amount)
            for division, amount in dividends_hkd_cents.items()
        ),
        Fraction(),
    )


def scale_dividend_for_stake(
    dividend_hkd_cents: int | Fraction, stake_hkd_cents: int, full_unit_hkd_cents: int
) -> Fraction:
    """Scale a full-unit dividend exactly for a partial unit without applying guessed rounding."""

    if stake_hkd_cents <= 0 or full_unit_hkd_cents <= 0:
        raise ValueError("stake amounts must be positive")
    if Fraction(dividend_hkd_cents) < 0:
        raise ValueError("dividend cannot be negative")
    if stake_hkd_cents > full_unit_hkd_cents:
        raise ValueError("stake cannot exceed the full unit")
    return Fraction(dividend_hkd_cents) * Fraction(stake_hkd_cents, full_unit_hkd_cents)
