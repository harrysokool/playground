from datetime import date, timedelta
from typing import cast

import numpy as np

from mark_six.statistics.metrics import (
    analyse_period,
    gap_rows,
    metric_context,
    omnibus_statistics,
    serial_rows,
)
from mark_six.statistics.models import DrawHistory
from mark_six.statistics.null_model import sample_fair_history


def _history(mains: np.ndarray, extras: np.ndarray, pool_size: int = 12) -> DrawHistory:
    draw_count = len(mains)
    return DrawHistory(
        period_id="synthetic",
        pool_size=pool_size,
        draw_ids=tuple(f"draw-{index}" for index in range(draw_count)),
        draw_dates=tuple(date(2020, 1, 1) + timedelta(days=index) for index in range(draw_count)),
        mains=np.asarray(mains, dtype=np.int64),
        extras=np.asarray(extras, dtype=np.int64),
    )


def test_strong_single_number_pair_and_odd_biases_are_detected() -> None:
    rng = np.random.default_rng(7)
    mains = []
    extras = []
    for _ in range(300):
        rest = rng.choice(np.arange(3, 13), size=4, replace=False)
        main = np.sort(np.concatenate((np.array([1, 2]), rest)))
        available = np.asarray([value for value in range(1, 13) if value not in main])
        mains.append(main)
        extras.append(int(rng.choice(available)))
    history = _history(np.asarray(mains), np.asarray(extras))
    analysis = analyse_period(history, metric_context(12))

    number_one = analysis.tables["number_frequencies"][0]
    pair_one_two = next(
        row
        for row in analysis.tables["pair_statistics"]
        if row["first_number"] == 1 and row["second_number"] == 2
    )
    assert cast(float, number_one["standardized_deviation"]) > 15
    assert cast(float, pair_one_two["standardized_deviation"]) > 20

    all_odd = np.tile(np.array([1, 3, 5, 7, 9, 11]), (100, 1))
    odd_history = _history(all_odd, np.full(100, 2))
    odd_statistics = omnibus_statistics(odd_history, metric_context(12))
    assert odd_statistics["odd_even"] > 100


def test_artificial_serial_dependence_is_detected() -> None:
    mains, extras = sample_fair_history(12, 150, np.random.default_rng(9))
    repeated_mains = np.repeat(mains, 2, axis=0)
    repeated_extras = np.repeat(extras, 2)
    history = _history(repeated_mains, repeated_extras)

    _rows, maximum = serial_rows(history)

    assert maximum > 0.4


def test_seeded_fair_synthetic_history_has_small_practical_effects() -> None:
    mains, extras = sample_fair_history(49, 5_000, np.random.default_rng(81))
    history = _history(mains, extras, pool_size=49)
    analysis = analyse_period(history, metric_context(49))

    assert analysis.effect_sizes["odd_even"] < 0.05
    assert analysis.effect_sizes["low_high"] < 0.05
    assert abs(analysis.effect_sizes["sum_distribution"]) < 0.05
    assert analysis.effect_sizes["temporal_stability"] < 0.05


def test_gap_table_uses_completed_interarrivals_and_warns_against_overdue_claims() -> None:
    mains = np.asarray(
        [[1, 2, 3, 4, 5, 6], [2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 5, 6]],
        dtype=np.int64,
    )
    history = _history(mains, np.asarray([7, 1, 7]), pool_size=7)

    rows, _maximum = gap_rows(history)
    number_one = rows[0]

    assert number_one["completed_gaps"] == 1
    assert number_one["observed_mean_interarrival_draws"] == 2
    assert "do not change" in str(number_one["gambler_fallacy_warning"])


def test_statistics_use_sets_and_make_no_physical_order_assumption() -> None:
    first = np.asarray(
        [[1, 2, 3, 4, 5, 6], [2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 6, 7]],
        dtype=np.int64,
    )
    second = first[:, ::-1]
    first_history = _history(np.sort(first, axis=1), np.asarray([7, 1, 5]), pool_size=7)
    second_history = _history(np.sort(second, axis=1), np.asarray([7, 1, 5]), pool_size=7)

    assert omnibus_statistics(first_history, metric_context(7)) == omnibus_statistics(
        second_history, metric_context(7)
    )
