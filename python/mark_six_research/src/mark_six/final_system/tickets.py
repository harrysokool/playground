"""Non-predictive fixed-budget ticket construction and exact expansion."""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Iterable
from typing import Literal

from mark_six.economics.split_risk import split_risk_features
from mark_six.final_system.models import TicketPlan
from mark_six.mathematics.entries import iter_banker_tickets, iter_multiple_tickets

Ticket = tuple[int, int, int, int, int, int]


class DuplicateTicketError(ValueError):
    """Raised when a plan accidentally contains the same combination twice."""


def _ticket(values: Iterable[int]) -> Ticket:
    result = tuple(sorted(values))
    if len(result) != 6 or len(set(result)) != 6 or result[0] < 1 or result[-1] > 49:
        raise ValueError("each ticket must contain six unique values within 1..49")
    return result


def detect_duplicate_tickets(tickets: Iterable[Iterable[int]]) -> None:
    """Reject duplicate ordinary combinations after normalizing number order."""

    normalized = [_ticket(ticket) for ticket in tickets]
    duplicates = [ticket for ticket, count in Counter(normalized).items() if count > 1]
    if duplicates:
        raise DuplicateTicketError(f"duplicate ticket detected: {duplicates[0]}")


def _passes_optional_split_filter(ticket: Ticket) -> bool:
    features = split_risk_features(ticket)
    return not (
        features.birthday_range_count == 6
        or features.consecutive_pairs >= 2
        or features.repeated_last_digit_pairs >= 3
    )


def _uniform_tickets(line_count: int, seed: int, split_risk_filter: bool) -> tuple[Ticket, ...]:
    rng = random.Random(seed)
    tickets: list[Ticket] = []
    seen: set[Ticket] = set()
    while len(tickets) < line_count:
        ticket = _ticket(rng.sample(range(1, 50), 6))
        if ticket in seen or (split_risk_filter and not _passes_optional_split_filter(ticket)):
            continue
        seen.add(ticket)
        tickets.append(ticket)
    return tuple(tickets)


def plan_tickets(
    *,
    entry_type: Literal["uniform", "multiple", "banker"],
    budget_hkd: int,
    seed: int = 20260915,
    selections: Iterable[int] | None = None,
    bankers: Iterable[int] | None = None,
    legs: Iterable[int] | None = None,
    split_risk_filter: bool = False,
) -> TicketPlan:
    """Build a unique-line plan with exact cost and unspent budget."""

    budget_cents = budget_hkd * 100
    if budget_cents < 1000:
        raise ValueError("budget must fund at least one HKD 10 full-unit line")
    if entry_type == "uniform":
        tickets = _uniform_tickets(budget_cents // 1000, seed, split_risk_filter)
        used_seed: int | None = seed
    elif entry_type == "multiple":
        if selections is None:
            raise ValueError("Multiple planning requires selections")
        tickets = tuple(_ticket(ticket) for ticket in iter_multiple_tickets(selections, 49))
        used_seed = None
    else:
        if bankers is None or legs is None:
            raise ValueError("Banker planning requires bankers and legs")
        tickets = tuple(_ticket(ticket) for ticket in iter_banker_tickets(bankers, legs, 49))
        used_seed = None
    exact_cost = len(tickets) * 1000
    if exact_cost > budget_cents:
        raise ValueError(f"expanded entry costs HKD {exact_cost / 100:.2f}, above budget")
    detect_duplicate_tickets(tickets)
    split_note = (
        "Optional filtering used qualitative split-risk features. It is assumption-based because "
        "Hong Kong player-selection microdata are unavailable; it does not alter draw probability."
        if split_risk_filter
        else None
    )
    return TicketPlan(
        entry_type=entry_type,
        budget_hkd_cents=budget_cents,
        exact_cost_hkd_cents=exact_cost,
        unused_budget_hkd_cents=budget_cents - exact_cost,
        combination_count=len(tickets),
        unique_combination_count=len(set(tickets)),
        duplicate_combination_count=0,
        combinations=tickets,
        seed=used_seed,
        draw_probability_statement=(
            "Every valid six-number combination has exactly the same draw probability."
        ),
        packaging_statement=(
            "Multiple and Banker entries are their expanded ordinary combinations; packaging "
            "does not create additional expected value."
        ),
        split_risk_note=split_note,
    )
