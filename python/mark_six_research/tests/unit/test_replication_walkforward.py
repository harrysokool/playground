from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from mark_six.prediction.models import PredictionHistory
from mark_six.prediction.walkforward import forecast_weights_by_draw, run_walk_forward
from mark_six.replication.models import load_replication_config


def _history(changed: bool = False) -> PredictionHistory:
    start = date(2010, 1, 1)
    mains = [[((index + offset) % 49) + 1 for offset in range(6)] for index in range(2702)]
    if changed:
        mains[2700] = [40, 41, 42, 43, 44, 45]
        mains[2701] = [1, 8, 16, 24, 32, 49]
    return PredictionHistory(
        period_id="synthetic_phase7",
        pool_size=49,
        draw_ids=tuple(f"draw-{index}" for index in range(2702)),
        draw_dates=tuple(start + timedelta(days=index) for index in range(2702)),
        mains=np.asarray(mains, dtype=np.int64),
    )


def test_target_and_future_reserve_mutation_cannot_change_first_forecast() -> None:
    root = Path(__file__).parents[2]
    models = load_replication_config(root / "configs" / "phase7_replication.yaml").models

    original = forecast_weights_by_draw(_history(), models, warmup_draws=2700)
    changed = forecast_weights_by_draw(_history(changed=True), models, warmup_draws=2700)

    for first, second in zip(original[0], changed[0], strict=True):
        assert first == pytest.approx(second)
    assert any(
        not np.allclose(first, second)
        for first, second in zip(original[1], changed[1], strict=True)
    )


def test_fixed_phase7_blocks_have_exact_registered_size() -> None:
    root = Path(__file__).parents[2]
    config = load_replication_config(root / "configs" / "phase7_replication.yaml")
    repeated = np.tile(np.arange(1, 7, dtype=np.int64), (3376, 1))
    start = date(2010, 1, 1)
    history = PredictionHistory(
        period_id="synthetic_phase7",
        pool_size=49,
        draw_ids=tuple(f"draw-{index}" for index in range(3376)),
        draw_dates=tuple(start + timedelta(days=index) for index in range(3376)),
        mains=repeated,
    )

    result = run_walk_forward(
        history,
        config.models[:2],
        warmup_draws=2700,
        calibration_edges=config.calibration.probability_edges,
        stability_blocks=config.stability.blocks,
    )

    assert {row["draw_count"] for row in result.stability_rows} == {169}
    assert {row["block"] for row in result.stability_rows} == {1, 2, 3, 4}
