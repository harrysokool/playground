"""Observed and simulated statistics fixed by the Phase 5 protocol."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import sqrt
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy.stats import binomtest  # type: ignore[import-untyped]

from mark_six.statistics.models import DrawHistory, PeriodAnalysis
from mark_six.statistics.null_model import (
    consecutive_pair_count_pmf,
    exact_sum_pmf,
    expected_sum,
    expected_sum_variance,
    hypergeometric_composition_pmf,
    inclusion_probability,
    overlap_pmf,
    pair_probability,
    run_of_three_probability,
    triple_probability,
)

PAIR_COLUMNS = tuple(combinations(range(6), 2))
TRIPLE_COLUMNS = tuple(combinations(range(6), 3))


@dataclass(frozen=True)
class MetricContext:
    """Pool-specific exact distributions and combination lookups."""

    pool_size: int
    odd_pmf: NDArray[np.float64]
    low_pmf: NDArray[np.float64]
    overlap_distribution: NDArray[np.float64]
    consecutive_distribution: NDArray[np.float64]
    sum_minimum: int
    sum_distribution: NDArray[np.float64]
    pair_lookup: NDArray[np.int64]
    pair_values: tuple[tuple[int, int], ...]
    triple_lookup: NDArray[np.int64]
    triple_values: tuple[tuple[int, int, int], ...]


def metric_context(pool_size: int) -> MetricContext:
    """Build immutable lookup state for one number pool."""

    pair_values = tuple(combinations(range(1, pool_size + 1), 2))
    pair_lookup = np.full((pool_size + 1, pool_size + 1), -1, dtype=np.int64)
    for index, (first, second) in enumerate(pair_values):
        pair_lookup[first, second] = index
    triple_values = tuple(combinations(range(1, pool_size + 1), 3))
    triple_lookup = np.full((pool_size + 1, pool_size + 1, pool_size + 1), -1, dtype=np.int64)
    for index, (first, second, third) in enumerate(triple_values):
        triple_lookup[first, second, third] = index
    sum_minimum, sum_distribution = exact_sum_pmf(pool_size)
    return MetricContext(
        pool_size=pool_size,
        odd_pmf=hypergeometric_composition_pmf(pool_size, (pool_size + 1) // 2),
        low_pmf=hypergeometric_composition_pmf(pool_size, pool_size // 2),
        overlap_distribution=overlap_pmf(pool_size),
        consecutive_distribution=consecutive_pair_count_pmf(pool_size),
        sum_minimum=sum_minimum,
        sum_distribution=sum_distribution,
        pair_lookup=pair_lookup,
        pair_values=pair_values,
        triple_lookup=triple_lookup,
        triple_values=triple_values,
    )


def safe_binomial_z(observed: float, trials: int, probability: float) -> float:
    """Return a binomial standardized deviation, including degenerate protection."""

    variance = trials * probability * (1 - probability)
    return 0.0 if variance <= 0 else (observed - trials * probability) / sqrt(variance)


def wilson_interval(
    successes: int, trials: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError("successes and trials do not define a binomial sample")
    estimate = successes / trials
    denominator = 1 + z * z / trials
    centre = (estimate + z * z / (2 * trials)) / denominator
    half = z * sqrt(estimate * (1 - estimate) / trials + z * z / (4 * trials**2))
    return centre - half / denominator, centre + half / denominator


def _counts(mains: NDArray[np.int64], pool_size: int) -> NDArray[np.int64]:
    return np.bincount(mains.ravel(), minlength=pool_size + 1)[1:].astype(np.int64)


def _composition_counts(
    mains: NDArray[np.int64], predicate: NDArray[np.bool_]
) -> NDArray[np.int64]:
    per_draw = predicate.sum(axis=1)
    return np.bincount(per_draw, minlength=7).astype(np.int64)


def _pearson(observed: NDArray[np.int64], expected: NDArray[np.float64]) -> float:
    valid = expected > 0
    residual = observed[valid].astype(np.float64) - expected[valid]
    return float(np.sum(residual * residual / expected[valid]))


def _cramers_v(statistic: float, observations: int, dimensions: int = 6) -> float:
    return sqrt(statistic / (observations * dimensions)) if observations else 0.0


def _sum_cvm(sums: NDArray[np.int64], context: MetricContext) -> float:
    observed = np.bincount(
        sums - context.sum_minimum, minlength=len(context.sum_distribution)
    ).astype(np.float64)
    if len(observed) > len(context.sum_distribution):
        observed = observed[: len(context.sum_distribution)]
    observed_cdf = np.cumsum(observed / len(sums))
    expected_cdf = np.cumsum(context.sum_distribution)
    return float(np.sum((observed_cdf - expected_cdf) ** 2 * context.sum_distribution))


def consecutive_summaries(mains: NDArray[np.int64]) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
    """Return adjacent-pair counts and run-of-three indicators."""

    differences = np.diff(mains, axis=1)
    adjacent = (differences == 1).sum(axis=1).astype(np.int64)
    has_three = np.any((differences[:, :-1] == 1) & (differences[:, 1:] == 1), axis=1)
    return adjacent, has_three


def combination_counts(
    mains: NDArray[np.int64], context: MetricContext, order: int
) -> NDArray[np.int64]:
    """Count all observed unordered pairs or triples using lookup arrays."""

    if order == 2:
        indexes = [
            context.pair_lookup[mains[:, first], mains[:, second]] for first, second in PAIR_COLUMNS
        ]
        size = len(context.pair_values)
    elif order == 3:
        indexes = [
            context.triple_lookup[mains[:, first], mains[:, second], mains[:, third]]
            for first, second, third in TRIPLE_COLUMNS
        ]
        size = len(context.triple_values)
    else:
        raise ValueError("only pair and triple counts are supported")
    return np.bincount(np.concatenate(indexes), minlength=size).astype(np.int64)


def gap_rows(
    history: DrawHistory,
) -> tuple[list[dict[str, object]], float]:
    """Build per-number completed-gap summaries and the fixed global statistic."""

    rows: list[dict[str, object]] = []
    expected = history.pool_size / 6
    maximum_relative = 0.0
    for number in range(1, history.pool_size + 1):
        positions = np.flatnonzero(np.any(history.mains == number, axis=1))
        completed = np.diff(positions)
        mean_gap = float(np.mean(completed)) if len(completed) else float("nan")
        relative = (mean_gap - expected) / expected if len(completed) else float("nan")
        if np.isfinite(relative):
            maximum_relative = max(maximum_relative, abs(relative))
        absence_parts = [int(positions[0])] if len(positions) else [history.draw_count]
        if len(positions) > 1:
            absence_parts.extend((np.diff(positions) - 1).astype(int).tolist())
        if len(positions):
            absence_parts.append(history.draw_count - 1 - int(positions[-1]))
        rows.append(
            {
                "period_id": history.period_id,
                "pool_size": history.pool_size,
                "number": number,
                "appearances": len(positions),
                "completed_gaps": len(completed),
                "observed_mean_interarrival_draws": mean_gap,
                "expected_mean_interarrival_draws": expected,
                "relative_mean_gap_deviation": relative,
                "longest_absence_run": max(absence_parts),
                "gambler_fallacy_warning": "past gaps do not change the next-draw probability",
            }
        )
    return rows, maximum_relative


def lag_one_correlation(first: NDArray[np.float64], second: NDArray[np.float64]) -> float:
    """Return lag-one correlation, using zero for a degenerate series."""

    if len(first) < 3 or np.std(first[:-1]) == 0 or np.std(second[1:]) == 0:
        return 0.0
    return float(np.corrcoef(first[:-1], second[1:])[0, 1])


def serial_rows(history: DrawHistory) -> tuple[list[dict[str, object]], float]:
    """Return fixed per-number, sum, and odd-count lag-one correlations."""

    indicators = np.zeros((history.draw_count, history.pool_size), dtype=np.float64)
    row_index = np.repeat(np.arange(history.draw_count), 6)
    indicators[row_index, history.mains.ravel() - 1] = 1.0
    rows: list[dict[str, object]] = []
    correlations: list[float] = []
    for number in range(1, history.pool_size + 1):
        correlation = lag_one_correlation(indicators[:, number - 1], indicators[:, number - 1])
        correlations.append(correlation)
        rows.append(
            {
                "period_id": history.period_id,
                "series": f"number_{number}",
                "lag": 1,
                "correlation": correlation,
            }
        )
    sums = history.mains.sum(axis=1).astype(np.float64)
    odds = (history.mains % 2 == 1).sum(axis=1).astype(np.float64)
    for name, values in (("draw_sum", sums), ("odd_count", odds)):
        correlation = lag_one_correlation(values, values)
        correlations.append(correlation)
        rows.append(
            {
                "period_id": history.period_id,
                "series": name,
                "lag": 1,
                "correlation": correlation,
            }
        )
    return rows, max(abs(value) for value in correlations)


def stability_statistic(
    history: DrawHistory, blocks: int = 3
) -> tuple[float, float, list[dict[str, object]]]:
    """Return fixed contiguous-block number-frequency homogeneity statistics."""

    if history.draw_count < blocks:
        raise ValueError("draw count must be at least the number of stability blocks")
    indexes = np.array_split(np.arange(history.draw_count), blocks)
    table = np.stack([_counts(history.mains[index], history.pool_size) for index in indexes])
    block_totals = table.sum(axis=1).astype(np.float64)
    number_totals = table.sum(axis=0).astype(np.float64)
    expected = np.outer(block_totals, number_totals) / table.sum()
    valid = expected > 0
    statistic = float(np.sum((table[valid] - expected[valid]) ** 2 / expected[valid]))
    effect = sqrt(statistic / (table.sum() * min(blocks - 1, history.pool_size - 1)))
    rows = [
        {
            "period_id": history.period_id,
            "block": block + 1,
            "start_draw_id": history.draw_ids[int(index[0])],
            "end_draw_id": history.draw_ids[int(index[-1])],
            "draw_count": len(index),
            "pearson_component": float(
                np.sum(
                    (table[block][expected[block] > 0] - expected[block][expected[block] > 0]) ** 2
                    / expected[block][expected[block] > 0]
                )
            ),
        }
        for block, index in enumerate(indexes)
    ]
    return statistic, effect, rows


def omnibus_statistics(history: DrawHistory, context: MetricContext) -> dict[str, float]:
    """Compute the 12 fixed period-level statistics used for simulation calibration."""

    draw_count = history.draw_count
    main_counts = _counts(history.mains, history.pool_size)
    main_expected = np.full(history.pool_size, draw_count * 6 / history.pool_size)
    extra_counts = np.bincount(history.extras, minlength=history.pool_size + 1)[1:]
    extra_expected = np.full(history.pool_size, draw_count / history.pool_size)
    main_probability = inclusion_probability(history.pool_size)
    extra_probability = 1 / history.pool_size
    main_z = np.abs(
        (main_counts - draw_count * main_probability)
        / sqrt(draw_count * main_probability * (1 - main_probability))
    )
    extra_z = np.abs(
        (extra_counts - draw_count * extra_probability)
        / sqrt(draw_count * extra_probability * (1 - extra_probability))
    )
    odd_counts = _composition_counts(history.mains, history.mains % 2 == 1)
    low_counts = _composition_counts(history.mains, history.mains <= history.pool_size // 2)
    sums = history.mains.sum(axis=1)
    adjacent, has_three = consecutive_summaries(history.mains)
    consecutive_pmf = context.consecutive_distribution
    mean_expected = float(np.dot(np.arange(6), consecutive_pmf))
    mean_variance = float(np.dot((np.arange(6) - mean_expected) ** 2, consecutive_pmf))
    any_probability = 1 - consecutive_pmf[0]
    three_probability = run_of_three_probability(history.pool_size)
    consecutive_z = max(
        abs((float(np.mean(adjacent)) - mean_expected) / sqrt(mean_variance / draw_count)),
        abs(safe_binomial_z(float(np.count_nonzero(adjacent)), draw_count, any_probability)),
        abs(safe_binomial_z(float(np.count_nonzero(has_three)), draw_count, three_probability)),
    )
    overlaps = np.asarray(
        [
            len(set(history.mains[index - 1]) & set(history.mains[index]))
            for index in range(1, draw_count)
        ],
        dtype=np.int64,
    )
    overlap_counts = np.bincount(overlaps, minlength=7)
    _gap_table, gap_maximum = gap_rows(history)
    pair_counts = combination_counts(history.mains, context, 2)
    pair_p = pair_probability(history.pool_size)
    pair_z = np.abs((pair_counts - draw_count * pair_p) / sqrt(draw_count * pair_p * (1 - pair_p)))
    triple_counts = combination_counts(history.mains, context, 3)
    triple_p = triple_probability(history.pool_size)
    triple_z = np.abs(
        (triple_counts - draw_count * triple_p) / sqrt(draw_count * triple_p * (1 - triple_p))
    )
    _serial_table, serial_maximum = serial_rows(history)
    stability, _effect, _rows = stability_statistic(history)
    return {
        "main_frequency": _pearson(main_counts, main_expected),
        "main_frequency_max": float(np.max(main_z)),
        "extra_frequency": _pearson(extra_counts, extra_expected),
        "extra_frequency_max": float(np.max(extra_z)),
        "odd_even": _pearson(odd_counts, context.odd_pmf * draw_count),
        "low_high": _pearson(low_counts, context.low_pmf * draw_count),
        "sum_distribution": _sum_cvm(sums, context),
        "consecutive": consecutive_z,
        "draw_overlap": _pearson(overlap_counts, context.overlap_distribution * (draw_count - 1)),
        "gaps": gap_maximum,
        "pairs": float(np.max(pair_z)),
        "triples": float(np.max(triple_z)),
        "serial_dependence": serial_maximum,
        "temporal_stability": stability,
    }


def analyse_period(history: DrawHistory, context: MetricContext) -> PeriodAnalysis:
    """Create all preregistered observed tables for one period."""

    n = history.draw_count
    pool = history.pool_size
    main_p = inclusion_probability(pool)
    main_counts = _counts(history.mains, pool)
    main_rows: list[dict[str, object]] = []
    for number, count_value in enumerate(main_counts, start=1):
        count = int(count_value)
        expected = n * main_p
        low, high = wilson_interval(count, n)
        main_rows.append(
            {
                "period_id": history.period_id,
                "pool_size": pool,
                "number": number,
                "observed_count": count,
                "expected_count": expected,
                "observed_frequency": count / n,
                "expected_frequency": main_p,
                "absolute_deviation": count - expected,
                "relative_deviation": (count - expected) / expected,
                "standardized_deviation": safe_binomial_z(count, n, main_p),
                "confidence_low": low,
                "confidence_high": high,
                "raw_p_value": float(binomtest(count, n, main_p).pvalue),
            }
        )

    extra_p = 1 / pool
    extra_counts = np.bincount(history.extras, minlength=pool + 1)[1:].astype(np.int64)
    extra_rows: list[dict[str, object]] = []
    for number, count_value in enumerate(extra_counts, start=1):
        count = int(count_value)
        expected = n * extra_p
        low, high = wilson_interval(count, n)
        extra_rows.append(
            {
                "period_id": history.period_id,
                "pool_size": pool,
                "number": number,
                "observed_count": count,
                "expected_count": expected,
                "observed_frequency": count / n,
                "expected_frequency": extra_p,
                "absolute_deviation": count - expected,
                "relative_deviation": (count - expected) / expected,
                "standardized_deviation": safe_binomial_z(count, n, extra_p),
                "confidence_low": low,
                "confidence_high": high,
                "raw_p_value": float(binomtest(count, n, extra_p).pvalue),
            }
        )

    composition_rows: list[dict[str, object]] = []
    composition_effects: dict[str, float] = {}
    for name, predicate, pmf in (
        ("odd", history.mains % 2 == 1, context.odd_pmf),
        ("low", history.mains <= pool // 2, context.low_pmf),
    ):
        observed = _composition_counts(history.mains, predicate)
        statistic = _pearson(observed, pmf * n)
        composition_effects[name] = _cramers_v(statistic, n)
        for count in range(7):
            composition_rows.append(
                {
                    "period_id": history.period_id,
                    "composition": name,
                    "target_count": count,
                    "observed_draws": int(observed[count]),
                    "expected_draws": float(pmf[count] * n),
                    "observed_frequency": float(observed[count] / n),
                    "expected_frequency": float(pmf[count]),
                }
            )

    sums = history.mains.sum(axis=1)
    sum_observed_counts = np.bincount(
        sums - context.sum_minimum, minlength=len(context.sum_distribution)
    )[: len(context.sum_distribution)]
    sum_rows = [
        {
            "period_id": history.period_id,
            "sum": context.sum_minimum + index,
            "observed_draws": int(sum_observed_counts[index]),
            "expected_draws": float(probability * n),
            "observed_frequency": float(sum_observed_counts[index] / n),
            "expected_frequency": float(probability),
        }
        for index, probability in enumerate(context.sum_distribution)
    ]
    null_sum_mean = expected_sum(pool)
    null_sum_variance = expected_sum_variance(pool)
    observed_sum_mean = float(np.mean(sums))
    observed_sum_variance = float(np.var(sums, ddof=1))

    adjacent, has_three = consecutive_summaries(history.mains)
    consecutive_pmf = context.consecutive_distribution
    consecutive_rows = [
        {
            "period_id": history.period_id,
            "measure": "adjacent_pair_count",
            "value": count,
            "observed_draws": int(np.count_nonzero(adjacent == count)),
            "expected_draws": float(consecutive_pmf[count] * n),
        }
        for count in range(6)
    ]
    consecutive_rows.extend(
        [
            {
                "period_id": history.period_id,
                "measure": "at_least_one_consecutive_pair",
                "value": 1,
                "observed_draws": int(np.count_nonzero(adjacent)),
                "expected_draws": float((1 - consecutive_pmf[0]) * n),
            },
            {
                "period_id": history.period_id,
                "measure": "run_of_at_least_three",
                "value": 1,
                "observed_draws": int(np.count_nonzero(has_three)),
                "expected_draws": float(run_of_three_probability(pool) * n),
            },
        ]
    )

    overlaps = np.asarray(
        [len(set(history.mains[index - 1]) & set(history.mains[index])) for index in range(1, n)],
        dtype=np.int64,
    )
    overlap_counts = np.bincount(overlaps, minlength=7)
    overlap_rows = [
        {
            "period_id": history.period_id,
            "overlap_count": count,
            "observed_transitions": int(overlap_counts[count]),
            "expected_transitions": float(context.overlap_distribution[count] * (n - 1)),
            "observed_frequency": float(overlap_counts[count] / (n - 1)),
            "expected_frequency": float(context.overlap_distribution[count]),
        }
        for count in range(7)
    ]

    gaps, gap_maximum = gap_rows(history)
    pair_counts = combination_counts(history.mains, context, 2)
    pair_p = pair_probability(pool)
    pair_rows: list[dict[str, object]] = []
    for (first, second), count_value in zip(context.pair_values, pair_counts, strict=True):
        count = int(count_value)
        expected = n * pair_p
        pair_rows.append(
            {
                "period_id": history.period_id,
                "first_number": first,
                "second_number": second,
                "observed_count": count,
                "expected_count": expected,
                "relative_deviation": (count - expected) / expected,
                "standardized_deviation": safe_binomial_z(count, n, pair_p),
                "raw_p_value": float(binomtest(count, n, pair_p).pvalue),
            }
        )

    triple_counts = combination_counts(history.mains, context, 3)
    triple_p = triple_probability(pool)
    triple_expected = n * triple_p
    triple_z = np.asarray([safe_binomial_z(int(count), n, triple_p) for count in triple_counts])
    top_triple_indexes = np.argsort(np.abs(triple_z))[::-1][:20]
    triple_rows = [
        {
            "period_id": history.period_id,
            "rank_by_absolute_z": rank,
            "first_number": context.triple_values[int(index)][0],
            "second_number": context.triple_values[int(index)][1],
            "third_number": context.triple_values[int(index)][2],
            "observed_count": int(triple_counts[index]),
            "expected_count": triple_expected,
            "relative_deviation": (int(triple_counts[index]) - triple_expected) / triple_expected,
            "standardized_deviation": float(triple_z[index]),
            "individual_inference": "not_performed; preregistered maximum statistic only",
        }
        for rank, index in enumerate(top_triple_indexes, start=1)
    ]

    serial, serial_maximum = serial_rows(history)
    _stability, stability_effect, stability_rows = stability_statistic(history)
    statistics = omnibus_statistics(history, context)
    overlap_effect = _cramers_v(statistics["draw_overlap"], n - 1)
    descriptive: dict[str, object] = {
        "observed_sum_mean": observed_sum_mean,
        "expected_sum_mean": null_sum_mean,
        "observed_sum_variance": observed_sum_variance,
        "expected_sum_variance": null_sum_variance,
        "sum_quantile_05": float(np.quantile(sums, 0.05)),
        "sum_quantile_25": float(np.quantile(sums, 0.25)),
        "sum_quantile_50": float(np.quantile(sums, 0.50)),
        "sum_quantile_75": float(np.quantile(sums, 0.75)),
        "sum_quantile_95": float(np.quantile(sums, 0.95)),
        "largest_main_absolute_z": max(
            abs(cast(float, row["standardized_deviation"])) for row in main_rows
        ),
        "largest_extra_absolute_z": max(
            abs(cast(float, row["standardized_deviation"])) for row in extra_rows
        ),
        "largest_pair_absolute_z": statistics["pairs"],
        "largest_triple_absolute_z": statistics["triples"],
        "largest_gap_relative_deviation": gap_maximum,
        "largest_serial_absolute_r": serial_maximum,
    }
    effects = {
        "main_frequency": max(abs(cast(float, row["relative_deviation"])) for row in main_rows),
        "main_frequency_max": max(abs(cast(float, row["relative_deviation"])) for row in main_rows),
        "extra_frequency": max(abs(cast(float, row["relative_deviation"])) for row in extra_rows),
        "extra_frequency_max": max(
            abs(cast(float, row["relative_deviation"])) for row in extra_rows
        ),
        "odd_even": composition_effects["odd"],
        "low_high": composition_effects["low"],
        "sum_distribution": (observed_sum_mean - null_sum_mean) / sqrt(null_sum_variance),
        "consecutive": max(
            abs(cast(int, consecutive_rows[-2]["observed_draws"]) / n - (1 - consecutive_pmf[0])),
            abs(
                cast(int, consecutive_rows[-1]["observed_draws"]) / n
                - run_of_three_probability(pool)
            ),
        ),
        "draw_overlap": overlap_effect,
        "gaps": gap_maximum,
        "pairs": max(abs(cast(float, row["relative_deviation"])) for row in pair_rows),
        "triples": max(abs(cast(float, row["relative_deviation"])) for row in triple_rows),
        "serial_dependence": serial_maximum,
        "temporal_stability": stability_effect,
    }
    return PeriodAnalysis(
        period_id=history.period_id,
        pool_size=pool,
        draw_count=n,
        tables={
            "number_frequencies": main_rows,
            "extra_number_frequencies": extra_rows,
            "composition": composition_rows,
            "sum_distribution": sum_rows,
            "consecutive_behavior": consecutive_rows,
            "draw_overlap": overlap_rows,
            "gap_behavior": gaps,
            "pair_statistics": pair_rows,
            "triple_statistics": triple_rows,
            "serial_dependence": serial,
            "temporal_stability": stability_rows,
        },
        omnibus_statistics=statistics,
        effect_sizes=effects,
        descriptive=descriptive,
    )
