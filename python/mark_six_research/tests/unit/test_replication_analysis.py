import hashlib
from pathlib import Path

from mark_six.prediction.reserve import canonical_json_bytes
from mark_six.replication.comparison import compare_phase6_phase7
from mark_six.replication.runner import _load_manifest


def _summary(model: str, mean: float, skill: float = 0.0) -> dict[str, object]:
    return {
        "model": model,
        "mean_log_score_difference_nats": mean,
        "brier_skill_vs_uniform": skill,
        "mean_top_six_hits": 0.7,
        "mean_observed_rank": 25.0,
        "calibration_ece": 0.01,
    }


def test_phase6_phase7_comparison_is_aligned_and_not_pooled() -> None:
    rows = compare_phase6_phase7(
        [_summary("uniform", 0.0), _summary("candidate", -0.02, -0.01)],
        [_summary("uniform", 0.0), _summary("candidate", 0.01, 0.02)],
    )

    candidate = rows[1]
    assert candidate["phase6_mean_log_improvement_nats"] == -0.02
    assert candidate["phase7_mean_log_improvement_nats"] == 0.01
    assert candidate["direction_consistent"] is False
    assert "pooled" not in candidate


def test_phase7_manifest_self_hash_verifies(tmp_path: Path) -> None:
    value: dict[str, object] = {"schema_version": "1", "output_sha256": {}}
    value["manifest_sha256"] = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
    path = tmp_path / "manifest.json"
    path.write_bytes(canonical_json_bytes(value))

    assert _load_manifest(path)["manifest_sha256"] == value["manifest_sha256"]
