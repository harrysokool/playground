import json
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from mark_six.prediction.reserve import canonical_json_bytes
from mark_six.replication.models import ReplicationConfig, ReserveSpec, load_replication_config
from mark_six.replication.reserve import (
    ReserveOpeningAuthorization,
    ReserveOpeningError,
    authorize_reserve_opening,
    load_authorized_replication_history,
)


def _synthetic_replication(tmp_path: Path) -> tuple[ReplicationConfig, dict[str, object]]:
    root = Path(__file__).parents[2]
    original = load_replication_config(root / "configs" / "phase7_replication.yaml")
    start = date(2010, 1, 1)
    first_reserve = start + timedelta(days=2700)
    final_reserve = start + timedelta(days=3375)
    config = original.model_copy(
        update={
            "dataset_id": "synthetic",
            "history_first_draw_id": "draw-0000",
            "history_start_date": start,
            "initial_history_final_draw_id": "draw-2699",
            "initial_history_final_date": start + timedelta(days=2699),
            "reserve": ReserveSpec(
                period_id="synthetic_reserve",
                pool_size=49,
                draw_count=676,
                first_draw_id="draw-2700",
                first_draw_date=first_reserve,
                final_draw_id="draw-3375",
                final_draw_date=final_reserve,
            ),
        }
    )
    dataset = tmp_path / "data" / "processed" / "synthetic"
    dataset.mkdir(parents=True)
    draws = [
        {
            "draw_id": f"draw-{index:04d}",
            "draw_date": start + timedelta(days=index),
            "status": "completed",
        }
        for index in range(3377)
    ]
    numbers = [
        {
            "draw_id": f"draw-{index:04d}",
            "number_role": "main",
            "number_value": ((index + offset) % 49) + 1,
        }
        for index in range(3377)
        for offset in range(6)
    ]
    pq.write_table(pa.Table.from_pylist(draws), dataset / "draws.parquet")
    pq.write_table(pa.Table.from_pylist(numbers), dataset / "draw_numbers.parquet")
    holdout = {
        "schema_version": "1",
        "policy_id": "prospective_312_after_2026_09_13",
        "cutoff_date": "2026-09-13",
        "target_eligible_draws": 312,
        "state": "sealed",
        "entries": [],
    }
    path = tmp_path / "data" / "holdout" / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(canonical_json_bytes(holdout))
    reserve: dict[str, object] = {
        "entries": [
            {
                "draw_id": f"draw-{index:04d}",
                "draw_date": (start + timedelta(days=index)).isoformat(),
            }
            for index in range(2700, 3376)
        ]
    }
    return config, reserve


def test_controlled_loader_scores_only_registered_reserve_and_stops_at_final(
    tmp_path: Path,
) -> None:
    config, reserve = _synthetic_replication(tmp_path)

    history, event = load_authorized_replication_history(
        tmp_path, config, reserve, authorize_reserve_opening(config)
    )

    assert history.draw_count == 3376
    assert history.draw_ids[2699:] == tuple(f"draw-{index:04d}" for index in range(2699, 3376))
    assert "draw-3376" not in history.draw_ids
    assert event.first_draw_id == "draw-2700"
    assert event.final_draw_id == "draw-3375"
    assert event.reserve_draw_count == 676
    assert event.prospective_holdout_accessed is False


def test_controlled_loader_rejects_mismatched_authorization(tmp_path: Path) -> None:
    config, reserve = _synthetic_replication(tmp_path)
    authorization = ReserveOpeningAuthorization(
        protocol_version="wrong",
        baseline_commit=config.baseline_commit,
        reserve_manifest_sha256=config.reserve_manifest_sha256,
    )

    with pytest.raises(ReserveOpeningError, match="does not match"):
        load_authorized_replication_history(tmp_path, config, reserve, authorization)


def test_controlled_loader_refuses_any_prospective_holdout_entry(tmp_path: Path) -> None:
    config, reserve = _synthetic_replication(tmp_path)
    path = tmp_path / "data" / "holdout" / "manifest.json"
    holdout = json.loads(path.read_text(encoding="utf-8"))
    holdout["entries"] = [
        {
            "source_draw_id": "future-1",
            "draw_date": "2026-09-15",
            "eligibility_status": "pending",
            "rule_version_id": None,
            "raw_snapshot_id": "not-read",
            "canonical_dataset_version": None,
            "sealed": True,
        }
    ]
    path.write_bytes(canonical_json_bytes(holdout))

    with pytest.raises(ReserveOpeningError, match="sealed with zero entries"):
        load_authorized_replication_history(
            tmp_path, config, reserve, authorize_reserve_opening(config)
        )
