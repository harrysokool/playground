"""Strict sequential forecasts and preregistered scoring."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from itertools import pairwise
from typing import cast

import numpy as np
from numpy.typing import NDArray

from mark_six.prediction.models import (
    CandidateModel,
    PredictionHistory,
    WalkForwardResult,
)
from mark_six.prediction.weighted_subset import WeightedSubsetDistribution


def _required_float(value: float | None, name: str) -> float:
    if value is None:
        raise ValueError(f"missing frozen model parameter: {name}")
    return value


def _required_int(value: int | None, name: str) -> int:
    if value is None:
        raise ValueError(f"missing frozen model parameter: {name}")
    return value


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def forecast_sha256(
    *,
    model: CandidateModel,
    target_draw_id: str,
    cutoff_draw_id: str,
    pool_size: int,
    weights: NDArray[np.float64],
) -> str:
    """Bind one forecast to its exact pre-draw state without storing outcomes."""

    payload = {
        "model": model.name,
        "model_version": model.version,
        "target_draw_id": target_draw_id,
        "cutoff_draw_id": cutoff_draw_id,
        "pool_size": pool_size,
        "weights_hex": [float(value).hex() for value in weights],
    }
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


@dataclass
class SequentialState:
    """Sufficient information available strictly before the next draw."""

    pool_size: int
    counts: NDArray[np.float64] = field(init=False)
    last_seen: NDArray[np.int64] = field(init=False)
    previous: NDArray[np.float64] = field(init=False)
    indicators: list[NDArray[np.float64]] = field(default_factory=list)
    exponential: dict[float, NDArray[np.float64]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.counts = np.zeros(self.pool_size, dtype=np.float64)
        self.last_seen = np.full(self.pool_size, -1, dtype=np.int64)
        self.previous = np.zeros(self.pool_size, dtype=np.float64)

    @property
    def draw_index(self) -> int:
        return len(self.indicators)

    def enable_half_lives(self, models: list[CandidateModel]) -> None:
        """Create only the exponentially decayed states required by the model family."""

        half_lives = {
            float(model.half_life)
            for model in models
            if model.kind == "exponential_frequency" and model.half_life is not None
        }
        self.exponential = {
            half_life: np.zeros(self.pool_size, dtype=np.float64) for half_life in half_lives
        }

    def update(self, main_numbers: NDArray[np.int64]) -> None:
        """Reveal one completed outcome after all forecasts for it are fixed."""

        indicator = np.zeros(self.pool_size, dtype=np.float64)
        indicator[main_numbers - 1] = 1.0
        current_index = self.draw_index
        self.counts += indicator
        for half_life, values in self.exponential.items():
            decay = 2.0 ** (-1.0 / half_life)
            values *= decay
            values += indicator
        appeared = indicator.astype(bool)
        self.last_seen[appeared] = current_index
        self.previous = indicator
        self.indicators.append(indicator)

    def weights(self, model: CandidateModel) -> NDArray[np.float64]:
        """Return positive weights from state containing prior draws only."""

        if model.kind == "uniform":
            return np.ones(self.pool_size, dtype=np.float64)
        if model.kind == "expanding_frequency":
            return np.asarray(
                self.counts + _required_float(model.smoothing, "smoothing"),
                dtype=np.float64,
            )
        if model.kind == "rolling_frequency":
            window = _required_int(model.window, "window")
            recent = self.indicators[-window:]
            counts = (
                np.sum(np.stack(recent), axis=0)
                if recent
                else np.zeros(self.pool_size, dtype=np.float64)
            )
            return np.asarray(
                counts + _required_float(model.smoothing, "smoothing"),
                dtype=np.float64,
            )
        if model.kind == "exponential_frequency":
            half_life = _required_float(model.half_life, "half_life")
            return np.asarray(
                self.exponential[half_life] + _required_float(model.smoothing, "smoothing"),
                dtype=np.float64,
            )
        gaps = self.draw_index - self.last_seen
        if model.kind in {"gap_due", "recent_appearance"}:
            decay = np.exp(-math.log(2.0) * gaps / _required_float(model.half_life, "half_life"))
            if model.kind == "gap_due":
                return np.asarray(
                    1.0 + _required_float(model.multiplier, "multiplier") * (1.0 - decay),
                    dtype=np.float64,
                )
            return np.asarray(
                1.0 + _required_float(model.multiplier, "multiplier") * decay,
                dtype=np.float64,
            )
        if model.kind == "previous_draw_multiplier":
            return np.asarray(
                np.where(
                    self.previous > 0,
                    _required_float(model.multiplier, "multiplier"),
                    1.0,
                ),
                dtype=np.float64,
            )
        raise ValueError(f"unsupported model kind: {model.kind}")


def forecast_weights_by_draw(
    history: PredictionHistory,
    models: list[CandidateModel],
    warmup_draws: int,
) -> tuple[tuple[NDArray[np.float64], ...], ...]:
    """Expose deterministic pre-draw weights for leakage and synthetic tests."""

    if history.draw_count <= warmup_draws:
        raise ValueError("history must contain at least one scored draw")
    state = SequentialState(history.pool_size)
    state.enable_half_lives(models)
    for main in history.mains[:warmup_draws]:
        state.update(main)
    forecasts: list[tuple[NDArray[np.float64], ...]] = []
    for target in history.mains[warmup_draws:]:
        forecasts.append(tuple(state.weights(model) for model in models))
        state.update(target)
    return tuple(forecasts)


def _rank_metrics(marginals: NDArray[np.float64], target: NDArray[np.int64]) -> tuple[int, float]:
    numbers = np.arange(1, len(marginals) + 1, dtype=np.int64)
    order = np.lexsort((numbers, -marginals))
    ranks = np.empty(len(marginals), dtype=np.int64)
    ranks[order] = np.arange(1, len(marginals) + 1)
    top = set((order[:6] + 1).tolist())
    hits = len(top.intersection(target.tolist()))
    return hits, float(np.mean(ranks[target - 1]))


def _calibration_rows(
    *,
    period_id: str,
    model_name: str,
    probabilities: NDArray[np.float64],
    outcomes: NDArray[np.float64],
    edges: list[float],
) -> tuple[list[dict[str, object]], float]:
    flat_p = probabilities.reshape(-1)
    flat_y = outcomes.reshape(-1)
    indices = np.searchsorted(np.asarray(edges), flat_p, side="right") - 1
    indices = np.clip(indices, 0, len(edges) - 2)
    rows: list[dict[str, object]] = []
    weighted_error = 0.0
    for bin_index, (lower, upper) in enumerate(pairwise(edges)):
        selected = indices == bin_index
        count = int(np.count_nonzero(selected))
        mean_probability = float(np.mean(flat_p[selected])) if count else math.nan
        observed_rate = float(np.mean(flat_y[selected])) if count else math.nan
        if count:
            weighted_error += count * abs(mean_probability - observed_rate)
        rows.append(
            {
                "period_id": period_id,
                "model": model_name,
                "bin_index": bin_index + 1,
                "lower_bound": lower,
                "upper_bound": upper,
                "observation_count": count,
                "mean_probability": mean_probability,
                "observed_rate": observed_rate,
                "absolute_calibration_error": (
                    abs(mean_probability - observed_rate) if count else math.nan
                ),
            }
        )
    return rows, weighted_error / len(flat_p)


def run_walk_forward(
    history: PredictionHistory,
    models: list[CandidateModel],
    warmup_draws: int,
    calibration_edges: list[float],
    stability_blocks: int,
) -> WalkForwardResult:
    """Generate every forecast before revealing its target and compute fixed scores."""

    if history.draw_count <= warmup_draws:
        raise ValueError("history must contain at least one scored draw")
    state = SequentialState(history.pool_size)
    state.enable_half_lives(models)
    for main in history.mains[:warmup_draws]:
        state.update(main)
    scored_count = history.draw_count - warmup_draws
    uniform_log_score = -math.log(math.comb(history.pool_size, 6))
    rows: list[dict[str, object]] = []
    per_model: dict[str, dict[str, list[object]]] = {
        model.name: {
            "differences": [],
            "brier": [],
            "hits": [],
            "rank": [],
            "marginals": [],
            "outcomes": [],
        }
        for model in models
    }
    for index in range(warmup_draws, history.draw_count):
        cutoff_draw_id = history.draw_ids[index - 1]
        model_weights = tuple(state.weights(model) for model in models)
        forecast_hashes = tuple(
            forecast_sha256(
                model=model,
                target_draw_id=history.draw_ids[index],
                cutoff_draw_id=cutoff_draw_id,
                pool_size=history.pool_size,
                weights=weights,
            )
            for model, weights in zip(models, model_weights, strict=True)
        )
        # The target is joined only after every forecast and its hash are fixed.
        target = history.mains[index]
        target_indicator = np.zeros(history.pool_size, dtype=np.float64)
        target_indicator[target - 1] = 1.0
        for model, weights, forecast_hash in zip(
            models, model_weights, forecast_hashes, strict=True
        ):
            distribution = WeightedSubsetDistribution(weights)
            log_score = distribution.log_probability(target)
            marginals = distribution.marginals()
            brier = float(np.mean((marginals - target_indicator) ** 2))
            hits, mean_rank = _rank_metrics(marginals, target)
            difference = log_score - uniform_log_score
            rows.append(
                {
                    "period_id": history.period_id,
                    "pool_size": history.pool_size,
                    "model": model.name,
                    "model_version": model.version,
                    "target_draw_id": history.draw_ids[index],
                    "target_draw_date": history.draw_dates[index].isoformat(),
                    "cutoff_draw_id": cutoff_draw_id,
                    "forecast_sha256": forecast_hash,
                    "whole_set_log_score_nats": log_score,
                    "uniform_log_score_nats": uniform_log_score,
                    "log_score_difference_nats": difference,
                    "marginal_brier_score": brier,
                    "top_six_hits": hits,
                    "mean_observed_rank": mean_rank,
                }
            )
            bucket = per_model[model.name]
            bucket["differences"].append(difference)
            bucket["brier"].append(brier)
            bucket["hits"].append(hits)
            bucket["rank"].append(mean_rank)
            bucket["marginals"].append(marginals)
            bucket["outcomes"].append(target_indicator)
        state.update(target)

    uniform_brier = float(np.mean(np.asarray(cast(list[float], per_model["uniform"]["brier"]))))
    summary_rows: list[dict[str, object]] = []
    calibration_rows: list[dict[str, object]] = []
    stability_rows: list[dict[str, object]] = []
    for model in models:
        bucket = per_model[model.name]
        differences = np.asarray(bucket["differences"], dtype=np.float64)
        brier = float(np.mean(np.asarray(cast(list[float], bucket["brier"]))))
        model_calibration, ece = _calibration_rows(
            period_id=history.period_id,
            model_name=model.name,
            probabilities=np.asarray(bucket["marginals"], dtype=np.float64),
            outcomes=np.asarray(bucket["outcomes"], dtype=np.float64),
            edges=calibration_edges,
        )
        calibration_rows.extend(model_calibration)
        blocks = np.array_split(differences, stability_blocks)
        block_means = [float(np.mean(block)) for block in blocks]
        for block_index, block in enumerate(blocks, start=1):
            stability_rows.append(
                {
                    "period_id": history.period_id,
                    "model": model.name,
                    "block": block_index,
                    "draw_count": len(block),
                    "mean_log_score_difference_nats": float(np.mean(block)),
                }
            )
        summary_rows.append(
            {
                "period_id": history.period_id,
                "pool_size": history.pool_size,
                "model": model.name,
                "model_version": model.version,
                "warmup_draws": warmup_draws,
                "scored_draws": scored_count,
                "mean_log_score_difference_nats": float(np.mean(differences)),
                "total_log_score_difference_nats": float(np.sum(differences)),
                "mean_marginal_brier_score": brier,
                "brier_skill_vs_uniform": 1.0 - brier / uniform_brier,
                "mean_top_six_hits": float(np.mean(np.asarray(cast(list[int], bucket["hits"])))),
                "mean_observed_rank": float(np.mean(np.asarray(cast(list[float], bucket["rank"])))),
                "calibration_ece": ece,
                "nonnegative_stability_blocks": sum(value >= 0.0 for value in block_means),
                "minimum_stability_block_mean": min(block_means),
            }
        )
    return WalkForwardResult(
        period_id=history.period_id,
        pool_size=history.pool_size,
        warmup_draws=warmup_draws,
        forecast_rows=tuple(rows),
        summary_rows=tuple(summary_rows),
        calibration_rows=tuple(calibration_rows),
        stability_rows=tuple(stability_rows),
    )
