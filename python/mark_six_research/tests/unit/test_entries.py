from collections import Counter
from collections.abc import Callable
from fractions import Fraction
from itertools import combinations
from math import comb

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mark_six.domain.rules import CURRENT_RULES, RULES_2002_PARTIAL
from mark_six.mathematics.entries import (
    banker_combination_count,
    banker_first_division_probability,
    banker_outcome_distribution,
    banker_prize_vector,
    banker_ticket_cost_cents,
    first_division_probability,
    iter_banker_tickets,
    iter_multiple_tickets,
    multiple_combination_count,
    multiple_first_division_probability,
    multiple_outcome_distribution,
    multiple_prize_vector,
    multiple_ticket_cost_cents,
    ticket_cost_cents,
)


def test_multiple_expansion_is_stable_unique_and_complete() -> None:
    tickets = list(iter_multiple_tickets([7, 1, 5, 3, 2, 6, 4], 49))

    assert len(tickets) == multiple_combination_count(7) == 7
    assert len(set(tickets)) == 7
    assert tickets == sorted(tickets)
    assert tickets[0] == (1, 2, 3, 4, 5, 6)


def test_banker_expansion_always_contains_bankers() -> None:
    tickets = list(iter_banker_tickets([2, 1], [7, 3, 6, 5, 4], 49))

    assert len(tickets) == banker_combination_count(2, 5) == 5
    assert len(set(tickets)) == 5
    assert tickets == sorted(tickets)
    assert all({1, 2}.issubset(ticket) for ticket in tickets)


def test_exact_costs_and_first_division_coverage() -> None:
    assert ticket_cost_cents(1, CURRENT_RULES, entry_type="single") == 1_000
    assert ticket_cost_cents(28, CURRENT_RULES, entry_type="multiple") == 28_000
    assert ticket_cost_cents(28, CURRENT_RULES, entry_type="multiple", partial_unit=True) == 14_000
    assert first_division_probability(28, 49) == Fraction(28, 13_983_816)
    assert multiple_ticket_cost_cents(8, CURRENT_RULES) == 28_000
    assert multiple_first_division_probability(8, 49) == Fraction(28, 13_983_816)
    assert banker_ticket_cost_cents(2, 5, CURRENT_RULES) == 5_000
    assert banker_first_division_probability(2, 5, 49) == Fraction(5, 13_983_816)


def test_partial_stake_requires_verified_eligible_entry() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ticket_cost_cents(2, CURRENT_RULES, entry_type="single")
    with pytest.raises(ValueError, match="Single"):
        ticket_cost_cents(1, CURRENT_RULES, entry_type="single", partial_unit=True)
    with pytest.raises(ValueError, match="does not verify"):
        ticket_cost_cents(7, RULES_2002_PARTIAL, entry_type="multiple", partial_unit=True)


def test_eight_number_multiple_has_known_simultaneous_prizes() -> None:
    vector = multiple_prize_vector(8, main_overlap=6, extra_selected=False)

    assert vector.count(1) == 1
    assert vector.count(3) == 12
    assert vector.count(5) == 15
    assert sum(vector.division_counts) == 28
    assert vector.no_prize_combinations == 0


def test_banker_prize_vector_matches_expanded_ticket_classification() -> None:
    bankers = {1, 2}
    legs = {3, 4, 5, 6, 7}
    main = {1, 2, 3, 4, 5, 8}
    extra = 6
    vector = banker_prize_vector(
        banker_count=2,
        leg_count=5,
        banker_main=2,
        banker_extra=False,
        leg_main=3,
        leg_extra=True,
    )
    brute_counts = [0] * 7
    no_prize = 0
    for ticket in iter_banker_tickets(bankers, legs, 49):
        matches = len(set(ticket) & main)
        has_extra = extra in ticket
        division = {
            (6, False): 1,
            (5, True): 2,
            (5, False): 3,
            (4, True): 4,
            (4, False): 5,
            (3, True): 6,
            (3, False): 7,
        }.get((matches, has_extra))
        if division is None:
            no_prize += 1
        else:
            brute_counts[division - 1] += 1

    assert vector.division_counts == tuple(brute_counts)
    assert vector.no_prize_combinations == no_prize


def test_joint_outcome_distributions_cover_every_draw_outcome() -> None:
    denominator = comb(49, 6) * 43

    assert sum(multiple_outcome_distribution(49, 8).values()) == denominator
    assert sum(banker_outcome_distribution(49, 2, 5).values()) == denominator


def _brute_vector(tickets: list[tuple[int, ...]], main: set[int], extra: int) -> tuple[int, ...]:
    counts = [0] * 7
    no_prize = 0
    for ticket in tickets:
        matches = len(set(ticket) & main)
        division = {
            (6, False): 1,
            (5, True): 2,
            (5, False): 3,
            (4, True): 4,
            (4, False): 5,
            (3, True): 6,
            (3, False): 7,
        }.get((matches, extra in ticket))
        if division is None:
            no_prize += 1
        else:
            counts[division - 1] += 1
    return (*counts, no_prize)


def test_closed_form_system_distributions_match_exhaustive_small_pool() -> None:
    pool = range(1, 9)
    multiple_tickets = list(iter_multiple_tickets(range(1, 8), 8))
    banker_tickets = list(iter_banker_tickets([1, 2], [3, 4, 5, 6, 7], 8))
    brute_multiple: Counter[tuple[int, ...]] = Counter()
    brute_banker: Counter[tuple[int, ...]] = Counter()
    for main_tuple in combinations(pool, 6):
        main = set(main_tuple)
        for extra in set(pool) - main:
            brute_multiple[_brute_vector(multiple_tickets, main, extra)] += 1
            brute_banker[_brute_vector(banker_tickets, main, extra)] += 1

    exact_multiple = {
        (*vector.division_counts, vector.no_prize_combinations): count
        for vector, count in multiple_outcome_distribution(8, 7).items()
    }
    exact_banker = {
        (*vector.division_counts, vector.no_prize_combinations): count
        for vector, count in banker_outcome_distribution(8, 2, 5).items()
    }
    assert exact_multiple == dict(brute_multiple)
    assert exact_banker == dict(brute_banker)


def test_current_maximum_entry_counts_match_official_chance_table() -> None:
    maximum_multiple = multiple_combination_count(49)
    assert maximum_multiple == 13_983_816
    assert (
        ticket_cost_cents(maximum_multiple, CURRENT_RULES, entry_type="multiple") == 13_983_816_000
    )
    assert (
        ticket_cost_cents(
            maximum_multiple,
            CURRENT_RULES,
            entry_type="multiple",
            partial_unit=True,
        )
        == 6_991_908_000
    )
    assert banker_combination_count(1, 48) == 1_712_304
    assert banker_combination_count(2, 47) == 178_365
    assert banker_combination_count(3, 46) == 15_180
    assert banker_combination_count(4, 45) == 990
    assert banker_combination_count(5, 44) == 44


@given(selection_count=st.integers(min_value=7, max_value=13))
def test_multiple_expansion_properties(selection_count: int) -> None:
    tickets = list(iter_multiple_tickets(range(1, selection_count + 1), selection_count))

    assert len(tickets) == comb(selection_count, 6)
    assert len(tickets) == len(set(tickets))
    assert all(len(ticket) == len(set(ticket)) == 6 for ticket in tickets)
    assert all(all(1 <= number <= selection_count for number in ticket) for ticket in tickets)


@given(
    banker_count=st.integers(min_value=1, max_value=5),
    extra_legs=st.integers(min_value=1, max_value=5),
)
def test_banker_expansion_properties(banker_count: int, extra_legs: int) -> None:
    leg_count = 6 - banker_count + extra_legs
    pool_size = banker_count + leg_count
    bankers = range(1, banker_count + 1)
    legs = range(banker_count + 1, pool_size + 1)
    tickets = list(iter_banker_tickets(bankers, legs, pool_size))

    assert len(tickets) == comb(leg_count, 6 - banker_count)
    assert len(tickets) == len(set(tickets))
    assert all(len(ticket) == len(set(ticket)) == 6 for ticket in tickets)
    assert all(set(bankers).issubset(ticket) for ticket in tickets)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: list(iter_multiple_tickets([1, 2, 3, 4, 5, 6], 49)),
        lambda: list(iter_multiple_tickets([1, 2, 3, 4, 5, 6, 6], 49)),
        lambda: list(iter_banker_tickets([1, 2], [2, 3, 4, 5, 6], 49)),
        lambda: banker_combination_count(0, 7),
    ],
)
def test_invalid_system_entries_are_rejected(operation: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        operation()
