"""Exact expansion, cost, and joint-prize mathematics for system entries."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb

from mark_six.domain.models import RuleVersion
from mark_six.mathematics.combinatorics import (
    PRIZE_PATTERN_BY_DIVISION,
    total_six_number_tickets,
)


def _choose(n: int, k: int) -> int:
    return comb(n, k) if 0 <= k <= n else 0


def _numbers(values: Iterable[int], pool_size: int, name: str) -> tuple[int, ...]:
    result = tuple(sorted(values))
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicate numbers")
    if any(number < 1 or number > pool_size for number in result):
        raise ValueError(f"{name} must be within 1..{pool_size}")
    return result


def multiple_combination_count(selection_count: int) -> int:
    """Return the number of ordinary combinations in a Multiple entry."""

    if selection_count < 7:
        raise ValueError("a Multiple entry requires at least 7 selections")
    return comb(selection_count, 6)


def banker_combination_count(banker_count: int, leg_count: int) -> int:
    """Return C(legs, 6-bankers) for a valid Banker entry shape."""

    if not 1 <= banker_count <= 5:
        raise ValueError("a Banker entry requires 1 to 5 bankers")
    required_legs = 6 - banker_count
    if leg_count <= required_legs:
        raise ValueError("a Banker entry must expand to more than one ordinary combination")
    return comb(leg_count, required_legs)


def iter_multiple_tickets(selections: Iterable[int], pool_size: int) -> Iterator[tuple[int, ...]]:
    """Yield a Multiple entry's unique tickets in stable lexicographic order."""

    normalized = _numbers(selections, pool_size, "selections")
    if len(normalized) > pool_size:
        raise ValueError("selection count exceeds the number pool")
    multiple_combination_count(len(normalized))
    yield from combinations(normalized, 6)


def iter_banker_tickets(
    bankers: Iterable[int], legs: Iterable[int], pool_size: int
) -> Iterator[tuple[int, ...]]:
    """Yield a Banker's unique tickets in stable lexicographic order."""

    normalized_bankers = _numbers(bankers, pool_size, "bankers")
    normalized_legs = _numbers(legs, pool_size, "legs")
    if set(normalized_bankers) & set(normalized_legs):
        raise ValueError("bankers and legs must be disjoint")
    if len(normalized_bankers) + len(normalized_legs) > pool_size:
        raise ValueError("bankers and legs exceed the number pool")
    banker_combination_count(len(normalized_bankers), len(normalized_legs))
    for selected_legs in combinations(normalized_legs, 6 - len(normalized_bankers)):
        yield tuple(sorted((*normalized_bankers, *selected_legs)))


def ticket_cost_cents(
    combination_count: int,
    rule: RuleVersion,
    *,
    entry_type: str,
    partial_unit: bool = False,
) -> int:
    """Return exact cents from combination count and the applicable stake."""

    if combination_count < 1:
        raise ValueError("combination_count must be positive")
    if entry_type not in {"single", "multiple", "banker"}:
        raise ValueError("entry_type must be single, multiple, or banker")
    if entry_type == "single" and combination_count != 1:
        raise ValueError("a Single entry contains exactly one combination")
    if partial_unit:
        if entry_type == "single":
            raise ValueError("partial units are not allowed for Single entries")
        if rule.partial_unit_stake_hkd_cents is None:
            raise ValueError("the rule version does not verify a partial unit stake")
        stake = rule.partial_unit_stake_hkd_cents
    else:
        stake = rule.unit_stake_hkd_cents
    return combination_count * stake


def first_division_probability(combination_count: int, pool_size: int) -> Fraction:
    """Return exact first-prize coverage without an independence assumption."""

    total = total_six_number_tickets(pool_size)
    if not 1 <= combination_count <= total:
        raise ValueError("combination_count must be within the ordinary-ticket universe")
    return Fraction(combination_count, total)


def multiple_first_division_probability(selection_count: int, pool_size: int) -> Fraction:
    """Return exact First Division coverage for a Multiple entry."""

    return first_division_probability(multiple_combination_count(selection_count), pool_size)


def banker_first_division_probability(
    banker_count: int, leg_count: int, pool_size: int
) -> Fraction:
    """Return exact First Division coverage for a Banker entry."""

    return first_division_probability(banker_combination_count(banker_count, leg_count), pool_size)


def multiple_ticket_cost_cents(
    selection_count: int, rule: RuleVersion, *, partial_unit: bool = False
) -> int:
    """Return a Multiple entry's exact cost under one rule version."""

    return ticket_cost_cents(
        multiple_combination_count(selection_count),
        rule,
        entry_type="multiple",
        partial_unit=partial_unit,
    )


def banker_ticket_cost_cents(
    banker_count: int,
    leg_count: int,
    rule: RuleVersion,
    *,
    partial_unit: bool = False,
) -> int:
    """Return a Banker entry's exact cost under one rule version."""

    return ticket_cost_cents(
        banker_combination_count(banker_count, leg_count),
        rule,
        entry_type="banker",
        partial_unit=partial_unit,
    )


@dataclass(frozen=True)
class PrizeVector:
    """Simultaneous eligible prizes across all combinations in one system entry."""

    division_counts: tuple[int, ...]
    no_prize_combinations: int

    def count(self, division: int) -> int:
        """Return the number of prizes in a one-based division."""

        if not 1 <= division <= len(self.division_counts):
            raise ValueError("division is outside this prize vector")
        return self.division_counts[division - 1]


def _to_prize_vector(
    pattern_counts: dict[object, int], total: int, prize_divisions: int
) -> PrizeVector:
    counts = tuple(
        pattern_counts.get(PRIZE_PATTERN_BY_DIVISION[division], 0)
        for division in range(1, prize_divisions + 1)
    )
    return PrizeVector(counts, total - sum(counts))


def multiple_prize_vector(
    selection_count: int,
    main_overlap: int,
    extra_selected: bool,
    *,
    prize_divisions: int = 7,
) -> PrizeVector:
    """Count simultaneous prizes from overlap state without expanding the ticket."""

    total = multiple_combination_count(selection_count)
    extra = int(extra_selected)
    if not 0 <= main_overlap <= min(6, selection_count):
        raise ValueError("main_overlap is impossible")
    if main_overlap + extra > selection_count:
        raise ValueError("overlap state exceeds the selected set")
    other = selection_count - main_overlap - extra
    counts: dict[object, int] = {}
    for division, pattern in PRIZE_PATTERN_BY_DIVISION.items():
        main_matches = (6, 5, 5, 4, 4, 3, 3)[division - 1]
        needs_extra = division in {2, 4, 6}
        if needs_extra:
            count = extra * _choose(main_overlap, main_matches) * _choose(other, 5 - main_matches)
        else:
            count = _choose(main_overlap, main_matches) * _choose(other, 6 - main_matches)
        counts[pattern] = count
    return _to_prize_vector(counts, total, prize_divisions)


def banker_prize_vector(
    banker_count: int,
    leg_count: int,
    banker_main: int,
    banker_extra: bool,
    leg_main: int,
    leg_extra: bool,
    *,
    prize_divisions: int = 7,
) -> PrizeVector:
    """Count simultaneous Banker prizes from banker/leg overlap state exactly."""

    total = banker_combination_count(banker_count, leg_count)
    if banker_extra and leg_extra:
        raise ValueError("the Extra Number cannot be both a banker and a leg")
    if not 0 <= banker_main <= min(6, banker_count):
        raise ValueError("banker_main is impossible")
    if not 0 <= leg_main <= min(6 - banker_main, leg_count):
        raise ValueError("leg_main is impossible")
    if banker_main + int(banker_extra) > banker_count:
        raise ValueError("banker overlap exceeds banker count")
    if leg_main + int(leg_extra) > leg_count:
        raise ValueError("leg overlap exceeds leg count")
    legs_chosen = 6 - banker_count
    other_legs = leg_count - leg_main - int(leg_extra)
    counts: dict[object, int] = {}
    for division, pattern in PRIZE_PATTERN_BY_DIVISION.items():
        main_matches = (6, 5, 5, 4, 4, 3, 3)[division - 1]
        needs_extra = division in {2, 4, 6}
        main_legs_needed = main_matches - banker_main
        if banker_extra:
            extra_leg_needed = 0
            possible = needs_extra
        elif leg_extra:
            extra_leg_needed = int(needs_extra)
            possible = True
        else:
            extra_leg_needed = 0
            possible = not needs_extra
        other_needed = legs_chosen - main_legs_needed - extra_leg_needed
        count = (
            _choose(leg_main, main_legs_needed) * _choose(other_legs, other_needed)
            if possible
            else 0
        )
        counts[pattern] = count
    return _to_prize_vector(counts, total, prize_divisions)


def multiple_outcome_distribution(
    pool_size: int, selection_count: int, *, prize_divisions: int = 7
) -> dict[PrizeVector, int]:
    """Count draw outcomes producing each simultaneous Multiple prize vector."""

    if selection_count > pool_size:
        raise ValueError("selection count exceeds the number pool")
    multiple_combination_count(selection_count)
    outside = pool_size - selection_count
    result: Counter[PrizeVector] = Counter()
    for main_overlap in range(7):
        main_ways = _choose(selection_count, main_overlap) * _choose(outside, 6 - main_overlap)
        for extra_selected in (False, True):
            extra_ways = (
                selection_count - main_overlap if extra_selected else outside - (6 - main_overlap)
            )
            if main_ways and extra_ways > 0:
                vector = multiple_prize_vector(
                    selection_count,
                    main_overlap,
                    extra_selected,
                    prize_divisions=prize_divisions,
                )
                result[vector] += main_ways * extra_ways
    assert sum(result.values()) == comb(pool_size, 6) * (pool_size - 6)
    return dict(result)


def banker_outcome_distribution(
    pool_size: int,
    banker_count: int,
    leg_count: int,
    *,
    prize_divisions: int = 7,
) -> dict[PrizeVector, int]:
    """Count draw outcomes producing each simultaneous Banker prize vector."""

    banker_combination_count(banker_count, leg_count)
    outside = pool_size - banker_count - leg_count
    if outside < 0:
        raise ValueError("bankers and legs exceed the number pool")
    result: Counter[PrizeVector] = Counter()
    for banker_main in range(min(6, banker_count) + 1):
        for leg_main in range(min(6 - banker_main, leg_count) + 1):
            outside_main = 6 - banker_main - leg_main
            main_ways = (
                _choose(banker_count, banker_main)
                * _choose(leg_count, leg_main)
                * _choose(outside, outside_main)
            )
            if not main_ways:
                continue
            extra_groups = (
                (True, False, banker_count - banker_main),
                (False, True, leg_count - leg_main),
                (False, False, outside - outside_main),
            )
            for banker_extra, leg_extra, extra_ways in extra_groups:
                if extra_ways <= 0:
                    continue
                vector = banker_prize_vector(
                    banker_count,
                    leg_count,
                    banker_main,
                    banker_extra,
                    leg_main,
                    leg_extra,
                    prize_divisions=prize_divisions,
                )
                result[vector] += main_ways * extra_ways
    assert sum(result.values()) == comb(pool_size, 6) * (pool_size - 6)
    return dict(result)
