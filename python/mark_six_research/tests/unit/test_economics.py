"""Phase 8 exact economics, sharing, entry, portfolio, and isolation tests."""

from __future__ import annotations

import inspect
import math
from datetime import date
from fractions import Fraction
from pathlib import Path

import duckdb
import pytest

from mark_six.economics import analysis
from mark_six.economics.expected_value import (
    expected_value,
    first_fund_for_return_target,
    fixed_prize_breakdown,
)
from mark_six.economics.historical import load_historical_economics
from mark_six.economics.models import load_economic_config
from mark_six.economics.portfolio import (
    banker_entry_economics,
    multiple_entry_economics,
    portfolio_metrics,
)
from mark_six.economics.sharing import binomial_sharing, poisson_sharing
from mark_six.economics.simulation import simulate_economic_scenario, simulate_portfolio_payout
from mark_six.economics.split_risk import split_risk_features
from mark_six.economics.state import build_current_state
from mark_six.mathematics.payouts import CURRENT_FIXED_PRIZES_HKD_CENTS


def test_exact_fixed_prize_expected_value() -> None:
    breakdown = fixed_prize_breakdown()
    assert set(breakdown) == {4, 5, 6, 7}
    assert sum(breakdown.values(), Fraction()) == Fraction(7_400_000, 35_673)
    assert float(sum(breakdown.values(), Fraction()) / 100) == pytest.approx(2.074398)


def test_current_accounting_identity() -> None:
    state = build_current_state(10_000_000_000)
    assert (
        state.prize_fund_hkd_cents
        + state.lottery_duty_hkd_cents
        + state.lotteries_fund_hkd_cents
        + state.commission_hkd_cents
        == state.turnover_hkd_cents
    )
    assert (
        state.expected_fixed_liability_hkd_cents
        + state.snowball_deduction_hkd_cents
        + state.variable_pool_hkd_cents
        == state.prize_fund_hkd_cents
    )


def test_uniform_sharing_base_cases_and_multiple_winners() -> None:
    assert binomial_sharing(0, Fraction(1, 10)).expected_share == 1.0
    result = binomial_sharing(2, Fraction(1, 2))
    assert result.sole_winner_probability == pytest.approx(0.25)
    assert result.share_with_one_probability == pytest.approx(0.5)
    assert result.share_with_multiple_probability == pytest.approx(0.25)
    assert result.expected_share == pytest.approx(7 / 12)


def test_poisson_approximates_first_division_binomial() -> None:
    exact = binomial_sharing(9_999_999, Fraction(1, 13_983_816))
    approximate = poisson_sharing(exact.expected_other_winning_units)
    assert abs(exact.expected_share - approximate.expected_share) < 1e-8
    assert abs(exact.sole_winner_probability - approximate.sole_winner_probability) < 2e-8


def test_jackpot_is_monotone_with_fixed_turnover_and_sharing() -> None:
    state = build_current_state(10_000_000_000)
    low = expected_value(
        {
            1: 800_000_000,
            2: state.division_funds_hkd_cents[2],
            3: state.division_funds_hkd_cents[3],
        },
        other_entries=9_999_999,
    )
    high = expected_value(
        {
            1: 15_000_000_000,
            2: state.division_funds_hkd_cents[2],
            3: state.division_funds_hkd_cents[3],
        },
        other_entries=9_999_999,
    )
    assert high.expected_return_ratio > low.expected_return_ratio


def test_turnover_reduces_share_for_a_fixed_fund() -> None:
    probability = Fraction(1, 13_983_816)
    assert (
        binomial_sharing(4_999_999, probability).expected_share
        > binomial_sharing(19_999_999, probability).expected_share
    )


def test_popularity_sensitivity_changes_first_sharing_only() -> None:
    funds = {1: 0, 2: 100_000_000, 3: 100_000_000}
    uniform = expected_value(funds, other_entries=1_000_000, sharing_mode="uniform")
    higher = expected_value(funds, other_entries=1_000_000, sharing_mode="higher_sharing")
    assert higher.total_expected_payout_hkd_cents == pytest.approx(
        uniform.total_expected_payout_hkd_cents
    )


def test_break_even_solver_round_trip() -> None:
    state = build_current_state(10_000_000_000)
    lower = {2: state.division_funds_hkd_cents[2], 3: state.division_funds_hkd_cents[3]}
    first = first_fund_for_return_target(
        1.0, lower, other_entries=9_999_999, sharing_mode="uniform"
    )
    result = expected_value(
        {1: Fraction.from_float(first), **lower},
        other_entries=9_999_999,
        sharing_mode="uniform",
    )
    assert result.expected_return_ratio == pytest.approx(1.0)


def _dividends() -> dict[int, int | Fraction]:
    return {1: 5_000_000_000, 2: 100_000_000, 3: 10_000_000, **CURRENT_FIXED_PRIZES_HKD_CENTS}


def test_multiple_entry_equals_expanded_lines_and_has_joint_variance() -> None:
    result = multiple_entry_economics(7, _dividends())
    assert result.combination_count == 7
    assert result.expected_payout_hkd_cents == result.equivalent_ordinary_expected_payout_hkd_cents
    assert result.payout_variance_hkd_cents_squared > 0


def test_banker_entry_equals_expanded_lines_and_has_joint_variance() -> None:
    result = banker_entry_economics(2, 5, _dividends())
    assert result.combination_count == 5
    assert result.expected_payout_hkd_cents == result.equivalent_ordinary_expected_payout_hkd_cents
    assert result.payout_variance_hkd_cents_squared > 0


def test_portfolio_duplicate_detection_and_linear_expectation() -> None:
    tickets = ((1, 2, 3, 4, 5, 6), (1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12))
    result = portfolio_metrics(tickets, expected_payout_per_line_hkd_cents=250.0)
    assert result.unique_combinations == 2
    assert result.duplicate_units == 1
    assert result.linear_expected_payout_hkd_cents == 750.0
    assert result.first_division_probability == Fraction(2, 13_983_816)


def test_split_risk_features_do_not_score_draw_probability() -> None:
    features = split_risk_features((1, 2, 3, 4, 5, 6))
    assert features.birthday_range_count == 6
    assert features.consecutive_pairs == 5
    assert features.arithmetic_sequence


def test_simulation_is_reproducible_and_uses_analytical_target() -> None:
    first = simulate_economic_scenario({1: 0, 2: 0, 3: 0}, other_entries=10, trials=20_000, seed=7)
    second = simulate_economic_scenario({1: 0, 2: 0, 3: 0}, other_entries=10, trials=20_000, seed=7)
    assert first == second
    assert math.isfinite(first.exact_expected_payout_hkd_cents)


def test_portfolio_simulation_is_reproducible_and_counts_owned_units() -> None:
    tickets = ((1, 2, 3, 4, 5, 6), (1, 2, 3, 4, 5, 6))
    first = simulate_portfolio_payout(
        tickets, CURRENT_FIXED_PRIZES_HKD_CENTS, trials=2_000, seed=9, batch_size=500
    )
    second = simulate_portfolio_payout(
        tickets, CURRENT_FIXED_PRIZES_HKD_CENTS, trials=2_000, seed=9, batch_size=500
    )
    assert first == second
    assert first.mean_payout_hkd_cents >= 0


def test_missing_source_fields_are_preserved_and_rule_interval_is_enforced(tmp_path: Path) -> None:
    database = tmp_path / "economics.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """CREATE TABLE draws AS SELECT
            'hkjc:24/058'::VARCHAR draw_id, '202458N'::VARCHAR source_draw_id,
            '24/058'::VARCHAR draw_number, DATE '2024-05-21' draw_date,
            'hkjc_mark_six_2024_05_21'::VARCHAR rule_version_id,
            NULL::BIGINT turnover_hkd_cents, 1000::BIGINT unit_stake_hkd_cents,
            NULL::BIGINT reported_jackpot_hkd_cents,
            NULL::BIGINT estimated_first_prize_hkd_cents,
            NULL::BIGINT reported_derived_first_prize_hkd_cents,
            NULL::VARCHAR snowball_code, NULL::VARCHAR snowball_name_en,
            false::BOOLEAN is_special_draw"""
        )
        connection.execute(
            """CREATE TABLE prize_results(
            draw_id VARCHAR, division_code VARCHAR, winning_units DECIMAL(20,4),
            prize_per_winning_unit_hkd_cents BIGINT,
            total_division_payout_hkd_cents BIGINT)"""
        )
    rows = load_historical_economics(
        database, start_date=date(2024, 5, 21), end_date=date(2024, 5, 21)
    )
    assert rows[0]["reported_jackpot_hkd_cents"] is None
    assert rows[0]["derived_prize_fund_hkd_cents"] is None
    with pytest.raises(ValueError, match="current-rule interval"):
        load_historical_economics(
            database, start_date=date(2024, 5, 20), end_date=date(2024, 5, 21)
        )


def test_phase8_cutoff_holdout_and_prediction_family_isolation() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_economic_config(root / "configs/phase8_economics.yaml")
    assert config.historical_period.final_date == "2026-09-12"
    source = inspect.getsource(analysis)
    assert "mark_six.prediction.models" not in source
    assert "run_predictive_analysis" not in source
