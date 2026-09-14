"""Paired sequential inference for Phase 6 log-score differences."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from mark_six.statistics.multiple_testing import holm


@dataclass(frozen=True)
class BootstrapResult:
    """One candidate's fixed moving-block bootstrap result."""

    observed_mean: float
    lower_95: float
    upper_95: float
    exceedances: int
    raw_p_value: float


def moving_block_bootstrap(
    differences: NDArray[np.float64],
    *,
    replicates: int,
    block_length: int,
    rng: np.random.Generator,
) -> BootstrapResult:
    """Run the preregistered circular moving-block bootstrap."""

    values = np.asarray(differences, dtype=np.float64)
    if values.ndim != 1 or len(values) < 2:
        raise ValueError("paired differences must be a one-dimensional series")
    if replicates < 1 or block_length < 1:
        raise ValueError("replicates and block length must be positive")
    count = len(values)
    blocks_needed = (count + block_length - 1) // block_length
    starts = rng.integers(0, count, size=(replicates, blocks_needed), endpoint=False)
    offsets = np.arange(block_length, dtype=np.int64)
    indices = (starts[..., None] + offsets) % count
    indices = indices.reshape(replicates, -1)[:, :count]
    sampled_means = np.mean(values[indices], axis=1)
    observed = float(np.mean(values))
    centered_means = sampled_means - observed
    exceedances = int(np.count_nonzero(centered_means >= observed))
    raw_p = (1.0 + exceedances) / (replicates + 1.0)
    lower, upper = np.quantile(sampled_means, [0.025, 0.975])
    return BootstrapResult(
        observed_mean=observed,
        lower_95=float(lower),
        upper_95=float(upper),
        exceedances=exceedances,
        raw_p_value=float(raw_p),
    )


def infer_candidates(
    differences_by_model: dict[str, NDArray[np.float64]],
    *,
    replicates: int,
    block_length: int,
    seed: int,
    alpha: float,
) -> list[dict[str, object]]:
    """Bootstrap every non-uniform candidate and apply Holm correction once."""

    rng = np.random.default_rng(seed)
    names = list(differences_by_model)
    results = [
        moving_block_bootstrap(
            differences_by_model[name],
            replicates=replicates,
            block_length=block_length,
            rng=rng,
        )
        for name in names
    ]
    adjusted, rejected = holm([result.raw_p_value for result in results], alpha)
    return [
        {
            "model": name,
            "observed_mean_log_improvement_nats": result.observed_mean,
            "bootstrap_lower_95": result.lower_95,
            "bootstrap_upper_95": result.upper_95,
            "bootstrap_replicates": replicates,
            "moving_block_length": block_length,
            "null_exceedances": result.exceedances,
            "raw_one_sided_p_value": result.raw_p_value,
            "holm_adjusted_p_value": adjusted_p,
            "holm_rejected": reject,
        }
        for name, result, adjusted_p, reject in zip(names, results, adjusted, rejected, strict=True)
    ]
