"""Fair-history calibration for the preregistered omnibus statistics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mark_six.statistics.metrics import MetricContext, omnibus_statistics
from mark_six.statistics.models import DrawHistory
from mark_six.statistics.null_model import sample_fair_history


@dataclass(frozen=True)
class CalibrationResult:
    """One observed statistic positioned in a simulated null distribution."""

    period_id: str
    test_family: str
    observed_statistic: float
    simulation_count: int
    exceedances: int
    raw_p_value: float
    simulated_percentile: float
    null_mean: float
    null_standard_deviation: float
    null_quantile_95: float
    null_quantile_99: float


def calibrate_period(
    history: DrawHistory,
    context: MetricContext,
    observed: dict[str, float],
    simulations: int,
    seed: int,
) -> list[CalibrationResult]:
    """Generate matched fair histories and calibrate all fixed statistics together."""

    if simulations < 1:
        raise ValueError("simulations must be positive")
    rng = np.random.default_rng(seed)
    values = {name: np.empty(simulations, dtype=np.float64) for name in observed}
    for simulation_index in range(simulations):
        mains, extras = sample_fair_history(history.pool_size, history.draw_count, rng)
        simulated = DrawHistory(
            period_id=history.period_id,
            pool_size=history.pool_size,
            draw_ids=history.draw_ids,
            draw_dates=history.draw_dates,
            mains=mains,
            extras=extras,
        )
        statistics = omnibus_statistics(simulated, context)
        for name, statistic in statistics.items():
            values[name][simulation_index] = statistic
    results: list[CalibrationResult] = []
    for name, observed_statistic in observed.items():
        null_values = values[name]
        exceedances = int(np.count_nonzero(null_values >= observed_statistic))
        results.append(
            CalibrationResult(
                period_id=history.period_id,
                test_family=name,
                observed_statistic=observed_statistic,
                simulation_count=simulations,
                exceedances=exceedances,
                raw_p_value=(1 + exceedances) / (1 + simulations),
                simulated_percentile=(
                    100
                    * (
                        np.count_nonzero(null_values < observed_statistic)
                        + 0.5 * np.count_nonzero(null_values == observed_statistic)
                    )
                    / simulations
                ),
                null_mean=float(np.mean(null_values)),
                null_standard_deviation=float(np.std(null_values, ddof=1)),
                null_quantile_95=float(np.quantile(null_values, 0.95)),
                null_quantile_99=float(np.quantile(null_values, 0.99)),
            )
        )
    return results


def derived_period_seeds(root_seed: int, period_count: int) -> list[int]:
    """Derive stable, independent integer seeds in fixed period order."""

    children = np.random.SeedSequence(root_seed).spawn(period_count)
    return [int(child.generate_state(1, dtype=np.uint32)[0]) for child in children]
