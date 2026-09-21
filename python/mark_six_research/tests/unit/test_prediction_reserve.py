import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from mark_six.prediction.data import load_primary_history
from mark_six.prediction.models import PredictionConfig
from mark_six.prediction.reserve import (
    ReserveIntegrityError,
    canonical_json_bytes,
    protected_draw_ids,
    reject_protected_ids,
)


def test_tracked_phase7_reserve_is_metadata_only_and_self_hashed() -> None:
    root = Path(__file__).parents[2]
    path = root / "data" / "reserves" / "phase7_historical_reserve.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    stated = manifest.pop("manifest_sha256")

    assert hashlib.sha256(canonical_json_bytes(manifest)).hexdigest() == stated
    assert manifest["outcomes_included"] is False
    assert manifest["reserve_row_count"] == 676
    assert len(manifest["entries"]) == 676
    prohibited = {"main", "mains", "numbers", "extra", "number_value", "outcome"}
    assert all(not prohibited.intersection(entry) for entry in manifest["entries"])


def test_reserve_guard_rejects_protected_draw_id() -> None:
    manifest: dict[str, object] = {"entries": [{"draw_id": "reserve-1"}]}
    protected = protected_draw_ids(manifest)

    reject_protected_ids({"development-1"}, protected)
    with pytest.raises(ReserveIntegrityError, match="access denied"):
        reject_protected_ids({"development-1", "reserve-1"}, protected)


def test_primary_loader_returns_only_pre_reserve_outcomes(tmp_path: Path) -> None:
    dataset = tmp_path / "data" / "processed" / "synthetic"
    dataset.mkdir(parents=True)
    start = date(2020, 1, 1)
    draws = [
        {
            "draw_id": f"draw-{index}",
            "draw_date": start + timedelta(days=index),
            "rule_version_id": "synthetic-rule",
            "status": "completed",
        }
        for index in range(10)
    ]
    numbers = [
        {
            "draw_id": f"draw-{index}",
            "number_role": "main",
            "number_value": number,
        }
        for index in range(10)
        for number in range(1, 7)
    ]
    pq.write_table(pa.Table.from_pylist(draws), dataset / "draws.parquet")
    pq.write_table(pa.Table.from_pylist(numbers), dataset / "draw_numbers.parquet")
    config = PredictionConfig.model_validate(
        {
            "analysis_version": "test",
            "protocol_version": "test",
            "dataset_id": "synthetic",
            "dataset_manifest_sha256": "a" * 64,
            "baseline_commit": "b" * 40,
            "protocol_path": "protocol.md",
            "reserve_manifest_path": "reserve.json",
            "primary": {
                "period_id": "primary",
                "start": "2020-01-01",
                "end": "2020-01-10",
                "pool_size": 7,
                "population_draws": 10,
                "phase6_draws": 6,
                "reserve_draws": 4,
                "warmup_draws": 2,
                "scored_draws": 4,
            },
            "secondary": {
                "warmup_draws": 2,
                "periods": [
                    {
                        "period_id": "older",
                        "start": "2019-01-01",
                        "end": "2019-01-10",
                        "pool_size": 7,
                    }
                ],
            },
            "excluded": {
                "start": "1996-01-01",
                "end": "1996-12-31",
                "reason": "transition",
            },
            "models": [
                {"name": "uniform", "kind": "uniform", "version": "v1"},
                {
                    "name": "repeat",
                    "kind": "previous_draw_multiplier",
                    "version": "v1",
                    "multiplier": 1.2,
                },
            ],
            "inference": {
                "alpha": 0.05,
                "correction": "holm",
                "bootstrap_seed": 1,
                "bootstrap_replicates": 10,
                "moving_block_length": 2,
            },
            "simulation": {"root_seed": 2, "histories": 10, "batch_size": 5},
            "calibration": {"probability_edges": [0.0, 0.5, 1.0]},
            "stability_blocks": 2,
            "success_criteria": {
                "minimum_mean_log_improvement_nats": 0.001,
                "maximum_adjusted_p_value": 0.05,
                "maximum_family_wide_p_value": 0.05,
                "maximum_ece": 0.025,
                "minimum_nonnegative_blocks": 1,
                "minimum_block_mean_log_improvement_nats": -0.005,
            },
        }
    )
    reserve: dict[str, object] = {
        "entries": [{"draw_id": f"draw-{index}"} for index in range(6, 10)]
    }

    history = load_primary_history(tmp_path, config, reserve)

    assert history.draw_count == 6
    assert history.draw_ids == tuple(f"draw-{index}" for index in range(6))
    assert all(type(draw_date) is date for draw_date in history.draw_dates)
