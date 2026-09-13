from fractions import Fraction
from math import comb

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mark_six.mathematics.combinatorics import (
    MatchPattern,
    match_pattern_counts,
    match_pattern_probabilities,
    prize_outcome_odds,
    probability_of_any_prize,
    total_six_number_tickets,
)


def test_current_prize_counts_are_exact() -> None:
    odds = {item.outcome: item for item in prize_outcome_odds(49)}

    assert total_six_number_tickets(49) == 13_983_816
    assert {name: item.winning_combinations for name, item in odds.items()} == {
        "division_1": 1,
        "division_2": 6,
        "division_3": 252,
        "division_4": 630,
        "division_5": 12_915,
        "division_6": 17_220,
        "division_7": 229_600,
        "no_prize": 13_723_192,
    }
    assert odds["division_1"].probability == Fraction(1, 13_983_816)
    assert odds["division_1"].one_in == 13_983_816
    assert {name: item.probability for name, item in odds.items()} == {
        "division_1": Fraction(1, 13_983_816),
        "division_2": Fraction(1, 2_330_636),
        "division_3": Fraction(3, 166_474),
        "division_4": Fraction(15, 332_948),
        "division_5": Fraction(615, 665_896),
        "division_6": Fraction(205, 166_474),
        "division_7": Fraction(4_100, 249_711),
        "no_prize": Fraction(245_057, 249_711),
    }
    assert probability_of_any_prize(49) == Fraction(260_624, 13_983_816)


@pytest.mark.parametrize(
    ("pool_size", "total"),
    [(45, 8_145_060), (47, 10_737_573), (49, 13_983_816)],
)
def test_supported_pool_sizes_have_independently_known_totals(pool_size: int, total: int) -> None:
    assert total_six_number_tickets(pool_size) == total
    assert prize_outcome_odds(pool_size)[0].probability == Fraction(1, total)


@pytest.mark.parametrize(
    ("pool_size", "expected_counts"),
    [
        (45, (1, 6, 228, 570, 10_545, 14_060, 8_119_650)),
        (47, (1, 6, 240, 600, 11_700, 15_600, 10_709_426)),
        (49, (1, 6, 252, 630, 12_915, 17_220, 13_952_792)),
    ],
)
def test_six_division_historical_configuration_counts(
    pool_size: int, expected_counts: tuple[int, ...]
) -> None:
    odds = prize_outcome_odds(pool_size, prize_divisions=6)

    assert tuple(item.winning_combinations for item in odds) == expected_counts


@given(pool_size=st.integers(min_value=7, max_value=100))
def test_match_patterns_partition_ticket_universe(pool_size: int) -> None:
    counts = match_pattern_counts(pool_size)
    probabilities = match_pattern_probabilities(pool_size)

    assert sum(counts.values()) == comb(pool_size, 6)
    assert all(count >= 0 for count in counts.values())
    assert all(probability >= 0 for probability in probabilities.values())
    assert sum(probabilities.values(), Fraction()) == 1


def test_six_division_model_treats_three_main_only_as_no_prize() -> None:
    patterns = match_pattern_counts(47)
    odds = {item.outcome: item for item in prize_outcome_odds(47, prize_divisions=6)}
    seven_division = {item.outcome: item for item in prize_outcome_odds(47)}

    assert "division_7" not in odds
    assert (
        odds["no_prize"].winning_combinations
        == seven_division["no_prize"].winning_combinations + patterns[MatchPattern.THREE_MAIN]
    )
    assert sum((item.probability for item in odds.values()), Fraction()) == 1


def test_invalid_pool_and_division_models_are_rejected() -> None:
    with pytest.raises(ValueError):
        total_six_number_tickets(6)
    with pytest.raises(ValueError):
        prize_outcome_odds(49, prize_divisions=5)
