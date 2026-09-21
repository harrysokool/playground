"""Full-process fair-history calibration for the frozen candidate family."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from mark_six.prediction.models import CandidateModel


def _required_float(value: float | None, name: str) -> float:
    if value is None:
        raise ValueError(f"missing frozen model parameter: {name}")
    return value


def _required_int(value: int | None, name: str) -> int:
    if value is None:
        raise ValueError(f"missing frozen model parameter: {name}")
    return value


def _esp6(weights: NDArray[np.float64]) -> NDArray[np.float64]:
    """Vectorized e_6 over leading history and model dimensions."""

    coefficients = np.zeros((*weights.shape[:-1], 7), dtype=np.float64)
    coefficients[..., 0] = 1.0
    for number_index in range(weights.shape[-1]):
        weight = weights[..., number_index]
        for order in range(6, 0, -1):
            coefficients[..., order] += weight * coefficients[..., order - 1]
    return coefficients[..., 6]


def _model_weights(
    models: list[CandidateModel],
    counts: NDArray[np.float64],
    rolling: dict[int, NDArray[np.float64]],
    exponential: dict[float, NDArray[np.float64]],
    last_seen: NDArray[np.int64],
    previous: NDArray[np.float64],
    draw_index: int,
) -> NDArray[np.float64]:
    values: list[NDArray[np.float64]] = []
    for model in models:
        if model.kind == "expanding_frequency":
            values.append(counts + _required_float(model.smoothing, "smoothing"))
        elif model.kind == "rolling_frequency":
            values.append(
                rolling[_required_int(model.window, "window")]
                + _required_float(model.smoothing, "smoothing")
            )
        elif model.kind == "exponential_frequency":
            values.append(
                exponential[_required_float(model.half_life, "half_life")]
                + _required_float(model.smoothing, "smoothing")
            )
        elif model.kind in {"gap_due", "recent_appearance"}:
            gaps = draw_index - last_seen
            decay = np.exp(-math.log(2.0) * gaps / _required_float(model.half_life, "half_life"))
            if model.kind == "gap_due":
                values.append(1.0 + _required_float(model.multiplier, "multiplier") * (1.0 - decay))
            else:
                values.append(1.0 + _required_float(model.multiplier, "multiplier") * decay)
        elif model.kind == "previous_draw_multiplier":
            values.append(
                np.where(
                    previous > 0,
                    _required_float(model.multiplier, "multiplier"),
                    1.0,
                )
            )
        else:
            raise ValueError(f"fair simulation does not expect model kind {model.kind}")
    return np.stack(values, axis=1)


def _simulate_batch(
    *,
    histories: int,
    draws: int,
    warmup: int,
    pool_size: int,
    models: list[CandidateModel],
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    random_scores = rng.random((histories, draws, pool_size))
    mains = np.argpartition(random_scores, 6, axis=2)[:, :, :6]
    del random_scores
    indicators = np.zeros((histories, draws, pool_size), dtype=np.float64)
    history_indices = np.arange(histories)[:, None, None]
    draw_indices = np.arange(draws)[None, :, None]
    indicators[history_indices, draw_indices, mains] = 1.0

    counts = np.zeros((histories, pool_size), dtype=np.float64)
    windows = sorted(
        {
            int(model.window)
            for model in models
            if model.kind == "rolling_frequency" and model.window is not None
        }
    )
    rolling = {window: np.zeros((histories, pool_size), dtype=np.float64) for window in windows}
    half_lives = sorted(
        {
            float(model.half_life)
            for model in models
            if model.kind == "exponential_frequency" and model.half_life is not None
        }
    )
    exponential = {
        half_life: np.zeros((histories, pool_size), dtype=np.float64) for half_life in half_lives
    }
    last_seen = np.full((histories, pool_size), -1, dtype=np.int64)
    previous = np.zeros((histories, pool_size), dtype=np.float64)

    def update(index: int) -> None:
        nonlocal previous
        current = indicators[:, index, :]
        counts[:] += current
        for window, values in rolling.items():
            values += current
            expired = index - window
            if expired >= 0:
                values -= indicators[:, expired, :]
        for half_life, values in exponential.items():
            values *= 2.0 ** (-1.0 / half_life)
            values += current
        last_seen[current.astype(bool)] = index
        previous = current

    for index in range(warmup):
        update(index)
    nonuniform = [model for model in models if model.kind != "uniform"]
    sums = np.zeros((histories, len(nonuniform)), dtype=np.float64)
    uniform_log_score = -math.log(math.comb(pool_size, 6))
    for index in range(warmup, draws):
        weights = _model_weights(
            nonuniform,
            counts,
            rolling,
            exponential,
            last_seen,
            previous,
            index,
        )
        normalizers = _esp6(weights)
        targets = np.broadcast_to(mains[:, index, None, :], (histories, len(nonuniform), 6))
        selected_weights = np.take_along_axis(weights, targets, axis=2)
        log_scores = np.sum(np.log(selected_weights), axis=2) - np.log(normalizers)
        sums += log_scores - uniform_log_score
        update(index)
    return sums / (draws - warmup)


def simulate_fair_process(
    *,
    models: list[CandidateModel],
    histories: int,
    draws: int,
    warmup: int,
    pool_size: int,
    seed: int,
    batch_size: int,
) -> tuple[tuple[str, ...], NDArray[np.float64]]:
    """Return each fair history's mean improvement for every non-uniform model."""

    if histories < 1 or batch_size < 1:
        raise ValueError("histories and batch size must be positive")
    rng = np.random.default_rng(seed)
    batches: list[NDArray[np.float64]] = []
    remaining = histories
    while remaining:
        size = min(batch_size, remaining)
        batches.append(
            _simulate_batch(
                histories=size,
                draws=draws,
                warmup=warmup,
                pool_size=pool_size,
                models=models,
                rng=rng,
            )
        )
        remaining -= size
    names = tuple(model.name for model in models if model.kind != "uniform")
    return names, np.concatenate(batches, axis=0)


def calibration_rows(
    names: tuple[str, ...],
    simulated_means: NDArray[np.float64],
    observed_means: dict[str, float],
) -> tuple[list[dict[str, object]], float, int]:
    """Calibrate individual and selected-best means against complete fair processes."""

    histories = simulated_means.shape[0]
    rows: list[dict[str, object]] = []
    for index, name in enumerate(names):
        observed = observed_means[name]
        exceedances = int(np.count_nonzero(simulated_means[:, index] >= observed))
        rows.append(
            {
                "scope": "individual_model",
                "model": name,
                "observed_mean_log_improvement_nats": observed,
                "simulation_histories": histories,
                "exceedances": exceedances,
                "simulation_p_value": (1.0 + exceedances) / (histories + 1.0),
                "null_mean": float(np.mean(simulated_means[:, index])),
                "null_standard_deviation": float(np.std(simulated_means[:, index], ddof=1)),
                "null_quantile_95": float(np.quantile(simulated_means[:, index], 0.95)),
                "null_quantile_99": float(np.quantile(simulated_means[:, index], 0.99)),
            }
        )
    best_name = max(names, key=observed_means.__getitem__)
    observed_best = observed_means[best_name]
    simulated_best = np.max(simulated_means, axis=1)
    family_exceedances = int(np.count_nonzero(simulated_best >= observed_best))
    family_p = (1.0 + family_exceedances) / (histories + 1.0)
    rows.append(
        {
            "scope": "family_selected_best",
            "model": best_name,
            "observed_mean_log_improvement_nats": observed_best,
            "simulation_histories": histories,
            "exceedances": family_exceedances,
            "simulation_p_value": family_p,
            "null_mean": float(np.mean(simulated_best)),
            "null_standard_deviation": float(np.std(simulated_best, ddof=1)),
            "null_quantile_95": float(np.quantile(simulated_best, 0.95)),
            "null_quantile_99": float(np.quantile(simulated_best, 0.99)),
        }
    )
    return rows, float(family_p), family_exceedances
