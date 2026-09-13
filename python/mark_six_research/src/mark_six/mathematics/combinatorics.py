"""Closed-form Mark Six prize combinatorics using exact integer arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from math import comb

from mark_six.mathematics.evidence import EvidenceType


class MatchPattern(StrEnum):
    """Mutually exclusive outcomes for one six-number entry."""

    SIX_MAIN = "six_main"
    FIVE_MAIN_PLUS_EXTRA = "five_main_plus_extra"
    FIVE_MAIN = "five_main"
    FOUR_MAIN_PLUS_EXTRA = "four_main_plus_extra"
    FOUR_MAIN = "four_main"
    THREE_MAIN_PLUS_EXTRA = "three_main_plus_extra"
    THREE_MAIN = "three_main"
    FEWER_THAN_THREE_MAIN = "fewer_than_three_main"


PRIZE_PATTERN_BY_DIVISION = {
    1: MatchPattern.SIX_MAIN,
    2: MatchPattern.FIVE_MAIN_PLUS_EXTRA,
    3: MatchPattern.FIVE_MAIN,
    4: MatchPattern.FOUR_MAIN_PLUS_EXTRA,
    5: MatchPattern.FOUR_MAIN,
    6: MatchPattern.THREE_MAIN_PLUS_EXTRA,
    7: MatchPattern.THREE_MAIN,
}


@dataclass(frozen=True)
class OutcomeOdds:
    """Exact count, probability, reciprocal odds, and derivation for one outcome."""

    outcome: str
    winning_combinations: int
    probability: Fraction
    one_in: Fraction
    derivation: str
    evidence_type: EvidenceType = EvidenceType.EXACT_COMBINATORIAL_RESULT


def _validate_pool_size(pool_size: int) -> None:
    if pool_size < 7:
        raise ValueError("pool_size must be at least 7")


def total_six_number_tickets(pool_size: int) -> int:
    """Return C(N, 6), the total distinct ordinary tickets."""

    _validate_pool_size(pool_size)
    return comb(pool_size, 6)


def match_pattern_counts(pool_size: int) -> dict[MatchPattern, int]:
    """Count all fixed-draw ticket outcomes, including the Extra Number role."""

    _validate_pool_size(pool_size)
    total = total_six_number_tickets(pool_size)
    counts = {
        MatchPattern.SIX_MAIN: 1,
        MatchPattern.FIVE_MAIN_PLUS_EXTRA: 6,
        MatchPattern.FIVE_MAIN: 6 * (pool_size - 7),
        MatchPattern.FOUR_MAIN_PLUS_EXTRA: 15 * (pool_size - 7),
        MatchPattern.FOUR_MAIN: 15 * comb(pool_size - 7, 2),
        MatchPattern.THREE_MAIN_PLUS_EXTRA: 20 * comb(pool_size - 7, 2),
        MatchPattern.THREE_MAIN: 20 * comb(pool_size - 7, 3),
    }
    counts[MatchPattern.FEWER_THAN_THREE_MAIN] = total - sum(counts.values())
    return counts


def match_pattern_probabilities(pool_size: int) -> dict[MatchPattern, Fraction]:
    """Return exact probabilities for every mutually exclusive match pattern."""

    total = total_six_number_tickets(pool_size)
    return {
        pattern: Fraction(count, total)
        for pattern, count in match_pattern_counts(pool_size).items()
    }


def classify_ticket_outcome(
    ticket: tuple[int, ...], main_numbers: frozenset[int], extra_number: int
) -> MatchPattern:
    """Classify one validated ticket against one fair-draw result."""

    if len(ticket) != 6 or len(set(ticket)) != 6:
        raise ValueError("ticket must contain exactly six unique numbers")
    if len(main_numbers) != 6 or extra_number in main_numbers:
        raise ValueError("draw must contain six main numbers and one distinct Extra Number")
    main_matches = len(set(ticket) & main_numbers)
    has_extra = extra_number in ticket
    return {
        (6, False): MatchPattern.SIX_MAIN,
        (5, True): MatchPattern.FIVE_MAIN_PLUS_EXTRA,
        (5, False): MatchPattern.FIVE_MAIN,
        (4, True): MatchPattern.FOUR_MAIN_PLUS_EXTRA,
        (4, False): MatchPattern.FOUR_MAIN,
        (3, True): MatchPattern.THREE_MAIN_PLUS_EXTRA,
        (3, False): MatchPattern.THREE_MAIN,
    }.get((main_matches, has_extra), MatchPattern.FEWER_THAN_THREE_MAIN)


def probability_of_any_prize(pool_size: int, prize_divisions: int = 7) -> Fraction:
    """Return the exact probability that one ordinary ticket wins any division."""

    return 1 - prize_outcome_odds(pool_size, prize_divisions)[-1].probability


def _derivation(pool_size: int, division: int) -> str:
    outside = pool_size - 7
    return {
        1: "C(6,6) = 1",
        2: "C(6,5) * C(1,1) = 6",
        3: f"C(6,5) * C({outside},1)",
        4: f"C(6,4) * C(1,1) * C({outside},1)",
        5: f"C(6,4) * C({outside},2)",
        6: f"C(6,3) * C(1,1) * C({outside},2)",
        7: f"C(6,3) * C({outside},3)",
    }[division]


def prize_outcome_odds(pool_size: int, prize_divisions: int = 7) -> tuple[OutcomeOdds, ...]:
    """Return exact division and no-prize odds for a six- or seven-division game."""

    if prize_divisions not in {6, 7}:
        raise ValueError("prize_divisions must be 6 or 7")
    total = total_six_number_tickets(pool_size)
    patterns = match_pattern_counts(pool_size)
    outcomes: list[OutcomeOdds] = []
    winning_total = 0
    for division in range(1, prize_divisions + 1):
        count = patterns[PRIZE_PATTERN_BY_DIVISION[division]]
        winning_total += count
        outcomes.append(
            OutcomeOdds(
                outcome=f"division_{division}",
                winning_combinations=count,
                probability=Fraction(count, total),
                one_in=Fraction(total, count),
                derivation=_derivation(pool_size, division),
            )
        )
    no_prize = total - winning_total
    outcomes.append(
        OutcomeOdds(
            outcome="no_prize",
            winning_combinations=no_prize,
            probability=Fraction(no_prize, total),
            one_in=Fraction(total, no_prize),
            derivation=f"C({pool_size},6) minus all eligible prize combinations",
        )
    )
    assert sum((outcome.probability for outcome in outcomes), Fraction()) == 1
    return tuple(outcomes)
