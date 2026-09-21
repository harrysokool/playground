"""Frozen Phase 8 jackpot, sharing, break-even, and sensitivity grids."""

from __future__ import annotations

from fractions import Fraction

from mark_six.economics.expected_value import expected_value, first_fund_for_return_target
from mark_six.economics.sharing import binomial_sharing, poisson_sharing
from mark_six.economics.state import build_current_state
from mark_six.mathematics.combinatorics import prize_outcome_odds


def jackpot_scenario_rows(
    turnover_hkd_values: list[int],
    first_fund_hkd_values: list[int],
    sharing_modes: list[str],
    *,
    popularity_multiplier: float,
) -> list[dict[str, object]]:
    """Evaluate the registered grid using current turnover-derived Division 2/3 funds."""

    rows: list[dict[str, object]] = []
    for turnover_hkd in turnover_hkd_values:
        state = build_current_state(turnover_hkd * 100)
        other_entries = max(0, int(state.expected_full_unit_entries) - 1)
        for first_hkd in first_fund_hkd_values:
            funds: dict[int, int | Fraction] = {
                1: first_hkd * 100,
                2: state.division_funds_hkd_cents[2],
                3: state.division_funds_hkd_cents[3],
            }
            for mode in sharing_modes:
                metrics = expected_value(
                    funds,
                    other_entries=other_entries,
                    sharing_mode=mode,
                    popularity_multiplier=popularity_multiplier,
                )
                rows.append(
                    {
                        "turnover_hkd": turnover_hkd,
                        "full_unit_equivalent_entries": other_entries + 1,
                        "first_division_fund_hkd": first_hkd,
                        "sharing_mode": mode,
                        "fixed_expected_payout_hkd": float(
                            metrics.fixed_expected_payout_hkd_cents / 100
                        ),
                        "variable_expected_payout_hkd": metrics.variable_expected_payout_hkd_cents
                        / 100,
                        "total_expected_payout_hkd": metrics.total_expected_payout_hkd_cents / 100,
                        "expected_profit_hkd": metrics.expected_profit_hkd_cents / 100,
                        "return_ratio": metrics.expected_return_ratio,
                        "expected_value_percent": metrics.expected_value_percent,
                    }
                )
    return rows


def breakeven_rows(
    turnover_hkd_values: list[int],
    return_targets: list[float],
    sharing_modes: list[str],
    *,
    popularity_multiplier: float,
) -> list[dict[str, object]]:
    """Solve registered conditional First Division fund thresholds."""

    rows: list[dict[str, object]] = []
    for turnover_hkd in turnover_hkd_values:
        state = build_current_state(turnover_hkd * 100)
        other_entries = max(0, int(state.expected_full_unit_entries) - 1)
        lower_funds = {2: state.division_funds_hkd_cents[2], 3: state.division_funds_hkd_cents[3]}
        for target in return_targets:
            for mode in sharing_modes:
                required_cents = first_fund_for_return_target(
                    target,
                    lower_funds,
                    other_entries=other_entries,
                    sharing_mode=mode,
                    popularity_multiplier=popularity_multiplier,
                )
                rows.append(
                    {
                        "turnover_hkd": turnover_hkd,
                        "sharing_mode": mode,
                        "target_return_ratio": target,
                        "required_first_division_fund_hkd": required_cents / 100,
                    }
                )
    return rows


def sharing_rows(turnover_hkd_values: list[int]) -> list[dict[str, object]]:
    """Compare exact binomial and Poisson First Division sharing benchmarks."""

    first_probability = prize_outcome_odds(49, 7)[0].probability
    rows: list[dict[str, object]] = []
    for turnover_hkd in turnover_hkd_values:
        entries = turnover_hkd * 100 // 1000
        exact = binomial_sharing(entries - 1, first_probability)
        poisson = poisson_sharing(exact.expected_other_winning_units)
        rows.append(
            {
                "turnover_hkd": turnover_hkd,
                "full_unit_equivalent_entries": entries,
                "expected_other_first_winners": exact.expected_other_winning_units,
                "sole_winner_probability": exact.sole_winner_probability,
                "share_with_one_probability": exact.share_with_one_probability,
                "share_with_multiple_probability": exact.share_with_multiple_probability,
                "expected_first_fund_share": exact.expected_share,
                "poisson_expected_share": poisson.expected_share,
                "absolute_approximation_error": abs(exact.expected_share - poisson.expected_share),
            }
        )
    return rows
