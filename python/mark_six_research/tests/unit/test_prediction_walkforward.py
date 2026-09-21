from datetime import date, timedelta
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from mark_six.prediction.models import (
    CandidateModel,
    PredictionHistory,
    load_prediction_config,
)
from mark_six.prediction.simulation import simulate_fair_process
from mark_six.prediction.walkforward import (
    forecast_sha256,
    forecast_weights_by_draw,
    run_walk_forward,
)


def _history(mains: list[list[int]], pool_size: int = 10) -> PredictionHistory:
    start = date(2020, 1, 1)
    return PredictionHistory(
        period_id="synthetic",
        pool_size=pool_size,
        draw_ids=tuple(f"draw-{index}" for index in range(len(mains))),
        draw_dates=tuple(start + timedelta(days=index) for index in range(len(mains))),
        mains=np.asarray(mains, dtype=np.int64),
    )


def _model(name: str, kind: str, **parameters: object) -> CandidateModel:
    return CandidateModel.model_validate(
        {"name": name, "kind": kind, "version": "v1", **parameters}
    )


def test_current_target_and_future_cannot_change_its_forecast() -> None:
    original = _history(
        [
            [1, 2, 3, 4, 5, 6],
            [2, 3, 4, 5, 6, 7],
            [3, 4, 5, 6, 7, 8],
            [4, 5, 6, 7, 8, 9],
            [1, 5, 6, 7, 9, 10],
        ]
    )
    changed = _history(
        [
            [1, 2, 3, 4, 5, 6],
            [2, 3, 4, 5, 6, 7],
            [3, 4, 5, 6, 7, 8],
            [1, 2, 3, 8, 9, 10],
            [1, 2, 3, 4, 9, 10],
        ]
    )
    models = [
        _model("expanding", "expanding_frequency", smoothing=1.0),
        _model("rolling", "rolling_frequency", window=2, smoothing=1.0),
        _model("ewm", "exponential_frequency", half_life=2.0, smoothing=1.0),
        _model("repeat", "previous_draw_multiplier", multiplier=1.2),
    ]

    original_forecasts = forecast_weights_by_draw(original, models, warmup_draws=3)
    changed_forecasts = forecast_weights_by_draw(changed, models, warmup_draws=3)

    for first, second in zip(original_forecasts[0], changed_forecasts[0], strict=True):
        assert first == pytest.approx(second)
    assert any(
        not np.allclose(first, second)
        for first, second in zip(original_forecasts[1], changed_forecasts[1], strict=True)
    )


def test_forecast_hash_is_deterministic_and_cutoff_bound() -> None:
    model = _model("uniform", "uniform")
    weights = np.ones(10)
    first = forecast_sha256(
        model=model,
        target_draw_id="target",
        cutoff_draw_id="cutoff",
        pool_size=10,
        weights=weights,
    )
    second = forecast_sha256(
        model=model,
        target_draw_id="target",
        cutoff_draw_id="cutoff",
        pool_size=10,
        weights=weights,
    )
    changed = forecast_sha256(
        model=model,
        target_draw_id="target",
        cutoff_draw_id="other",
        pool_size=10,
        weights=weights,
    )

    assert first == second
    assert len(first) == 64
    assert first != changed


def test_rolling_window_contains_prior_draws_only() -> None:
    history = _history(
        [
            [1, 2, 3, 4, 5, 6],
            [2, 3, 4, 5, 6, 7],
            [5, 6, 7, 8, 9, 10],
        ]
    )
    model = _model("rolling", "rolling_frequency", window=1, smoothing=1.0)

    weights = forecast_weights_by_draw(history, [model], warmup_draws=2)[0][0]

    assert weights == pytest.approx([1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0])


def test_planted_previous_draw_dependency_is_detected_by_frozen_repeat_model() -> None:
    repeated = [[1, 2, 3, 4, 5, 6] for _ in range(60)]
    history = _history(repeated)
    models = [
        _model("uniform", "uniform"),
        _model("repeat", "previous_draw_multiplier", multiplier=1.2),
    ]

    result = run_walk_forward(
        history, models, warmup_draws=10, calibration_edges=[0.0, 0.5, 1.0], stability_blocks=2
    )
    repeat = next(row for row in result.summary_rows if row["model"] == "repeat")

    assert cast(float, repeat["mean_log_score_difference_nats"]) > 0.4
    assert repeat["nonnegative_stability_blocks"] == 2


def test_scored_rows_are_strictly_ordered_and_bind_the_previous_cutoff() -> None:
    mains = [sorted({((index + offset) % 10) + 1 for offset in range(6)}) for index in range(12)]
    history = _history(mains)
    models = [
        _model("uniform", "uniform"),
        _model("repeat", "previous_draw_multiplier", multiplier=1.2),
    ]

    result = run_walk_forward(
        history, models, warmup_draws=4, calibration_edges=[0.0, 0.5, 1.0], stability_blocks=2
    )

    assert len(result.forecast_rows) == 8 * 2
    for offset in range(8):
        target_index = 4 + offset
        rows = result.forecast_rows[offset * 2 : (offset + 1) * 2]
        assert {row["target_draw_id"] for row in rows} == {history.draw_ids[target_index]}
        assert {row["cutoff_draw_id"] for row in rows} == {history.draw_ids[target_index - 1]}


def test_fair_process_has_no_systematic_repeat_advantage() -> None:
    models = [
        _model("uniform", "uniform"),
        _model("repeat", "previous_draw_multiplier", multiplier=1.2),
    ]

    names, means = simulate_fair_process(
        models=models,
        histories=120,
        draws=100,
        warmup=20,
        pool_size=10,
        seed=1234,
        batch_size=30,
    )

    assert names == ("repeat",)
    assert float(np.mean(means[:, 0])) < 0.0


def test_full_frozen_model_family_is_generic_and_pair_free() -> None:
    root = Path(__file__).parents[2]
    config = load_prediction_config(root / "configs" / "phase6_prediction.yaml")

    assert len(config.models) == 11
    assert config.models[0].name == "uniform"
    assert all("pair" not in model.name for model in config.models)
    assert all("2-26" not in model.name for model in config.models)
