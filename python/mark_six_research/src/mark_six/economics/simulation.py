"""Deterministic economic simulation used only where exact formulas are insufficient."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from mark_six.economics.expected_value import expected_value
from mark_six.mathematics.combinatorics import prize_outcome_odds
from mark_six.mathematics.payouts import CURRENT_FIXED_PRIZES_HKD_CENTS


@dataclass(frozen=True)
class EconomicSimulationResult:
    """Seeded Monte Carlo comparison with the analytical scenario expectation."""

    seed: int
    trials: int
    simulated_expected_payout_hkd_cents: float
    exact_expected_payout_hkd_cents: float
    standard_error_hkd_cents: float
    within_three_standard_errors: bool


@dataclass(frozen=True)
class PortfolioSimulationResult:
    """Simulated joint payout distribution for explicitly owned ordinary lines."""

    seed: int
    trials: int
    mean_payout_hkd_cents: float
    payout_variance_hkd_cents_squared: float
    probability_any_prize: float


def simulate_economic_scenario(
    division_funds_hkd_cents: Mapping[int, int | Fraction],
    *,
    other_entries: int,
    sharing_mode: str = "uniform",
    popularity_multiplier: float = 3.0,
    trials: int = 500_000,
    seed: int = 2026091501,
) -> EconomicSimulationResult:
    """Simulate one ticket, competing winners, fixed prizes, and variable sharing."""

    if trials <= 0:
        raise ValueError("trials must be positive")
    odds = prize_outcome_odds(49, 7)
    probabilities = np.asarray([float(row.probability) for row in odds], dtype=np.float64)
    rng = np.random.default_rng(seed)
    categories = rng.choice(len(odds), size=trials, p=probabilities)
    payouts = np.zeros(trials, dtype=np.float64)
    for division, prize in CURRENT_FIXED_PRIZES_HKD_CENTS.items():
        payouts[categories == division - 1] = prize
    for division in (1, 2, 3):
        selected = categories == division - 1
        count = int(np.sum(selected))
        if not count:
            continue
        if sharing_mode == "no_sharing":
            others = np.zeros(count, dtype=np.int64)
        else:
            probability = float(odds[division - 1].probability)
            if sharing_mode == "higher_sharing":
                if division == 1:
                    probability = min(1.0, probability * popularity_multiplier)
            elif sharing_mode != "uniform":
                raise ValueError("unknown sharing mode")
            others = rng.binomial(other_entries, probability, size=count)
        payouts[selected] = float(division_funds_hkd_cents[division]) / (1 + others)
    analytical = expected_value(
        division_funds_hkd_cents,
        other_entries=other_entries,
        sharing_mode=sharing_mode,
        popularity_multiplier=popularity_multiplier,
    ).total_expected_payout_hkd_cents
    estimate = float(np.mean(payouts))
    standard_error = float(np.std(payouts, ddof=1) / np.sqrt(trials))
    return EconomicSimulationResult(
        seed=seed,
        trials=trials,
        simulated_expected_payout_hkd_cents=estimate,
        exact_expected_payout_hkd_cents=analytical,
        standard_error_hkd_cents=standard_error,
        within_three_standard_errors=abs(estimate - analytical) <= 3 * standard_error,
    )


def simulate_portfolio_payout(
    tickets: tuple[tuple[int, ...], ...],
    dividends_hkd_cents: Mapping[int, int | Fraction],
    *,
    trials: int,
    seed: int,
    batch_size: int = 5_000,
) -> PortfolioSimulationResult:
    """Simulate fair draws and all simultaneous prizes in an ordinary-line portfolio."""

    if not tickets or trials <= 0 or batch_size <= 0:
        raise ValueError("tickets, trials, and batch_size must be positive")
    normalized = tuple(tuple(sorted(ticket)) for ticket in tickets)
    if any(
        len(ticket) != 6 or len(set(ticket)) != 6 or ticket[0] < 1 or ticket[-1] > 49
        for ticket in normalized
    ):
        raise ValueError("each ticket must have six unique numbers from 1 through 49")
    rng = np.random.default_rng(seed)
    all_payouts: list[np.ndarray[tuple[int], np.dtype[np.float64]]] = []
    remaining = trials
    while remaining:
        size = min(batch_size, remaining)
        keys = rng.random((size, 49))
        selected = np.argpartition(keys, 7, axis=1)[:, :7]
        main = selected[:, :6]
        extra = selected[:, 6]
        main_mask = np.zeros((size, 49), dtype=np.bool_)
        main_mask[np.arange(size)[:, None], main] = True
        payouts = np.zeros(size, dtype=np.float64)
        for ticket in normalized:
            indices = np.asarray(ticket, dtype=np.int64) - 1
            matches = np.sum(main_mask[:, indices], axis=1)
            has_extra = np.isin(extra, indices)
            divisions = np.zeros(size, dtype=np.int8)
            divisions[matches == 6] = 1
            divisions[(matches == 5) & has_extra] = 2
            divisions[(matches == 5) & ~has_extra] = 3
            divisions[(matches == 4) & has_extra] = 4
            divisions[(matches == 4) & ~has_extra] = 5
            divisions[(matches == 3) & has_extra] = 6
            divisions[(matches == 3) & ~has_extra] = 7
            for division, dividend in dividends_hkd_cents.items():
                payouts[divisions == division] += float(dividend)
        all_payouts.append(payouts)
        remaining -= size
    combined = np.concatenate(all_payouts)
    return PortfolioSimulationResult(
        seed=seed,
        trials=trials,
        mean_payout_hkd_cents=float(np.mean(combined)),
        payout_variance_hkd_cents_squared=float(np.var(combined, ddof=1)),
        probability_any_prize=float(np.mean(combined > 0)),
    )
