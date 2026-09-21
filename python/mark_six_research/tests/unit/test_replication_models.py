from pathlib import Path

from mark_six.prediction.models import load_prediction_config
from mark_six.replication.models import load_replication_config


def test_phase7_family_and_parameters_are_identical_to_phase6() -> None:
    root = Path(__file__).parents[2]
    phase6 = load_prediction_config(root / "configs" / "phase6_prediction.yaml")
    phase7 = load_replication_config(root / "configs" / "phase7_replication.yaml")

    assert [model.model_dump() for model in phase7.models] == [
        model.model_dump() for model in phase6.models
    ]
    assert phase7.calibration == phase6.calibration
    assert len(phase7.models) == 11
    assert all("pair" not in model.name and "2-26" not in model.name for model in phase7.models)


def test_phase7_registered_counts_seeds_and_blocks_are_frozen() -> None:
    root = Path(__file__).parents[2]
    config = load_replication_config(root / "configs" / "phase7_replication.yaml")

    assert config.initial_history_draws == 2700
    assert config.reserve.draw_count == 676
    assert config.simulation.total_draws == 3376
    assert config.simulation.histories == 500
    assert config.simulation.root_seed == 2026091403
    assert config.inference.bootstrap_seed == 2026091404
    assert config.stability.blocks == 4
    assert config.stability.draws_per_block == 169
    assert config.success_criteria.require_confidence_interval_lower_above_zero is True


def test_controlled_reserve_opening_and_consumption_are_logged() -> None:
    root = Path(__file__).parents[2]
    log = (root / "docs" / "research_log.md").read_text(encoding="utf-8")

    assert "2026-09-14T08:59:48.738500+00:00" in log
    assert "exactly 676 main-number outcomes" in log
    assert "prospective holdout was not accessed" in log
    assert "reserve is now consumed" in log
