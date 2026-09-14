import numpy as np

from mark_six.prediction.inference import infer_candidates, moving_block_bootstrap


def test_moving_block_bootstrap_is_deterministic() -> None:
    differences = np.sin(np.arange(200) / 11.0).astype(np.float64) + 0.02

    first = moving_block_bootstrap(
        differences,
        replicates=200,
        block_length=10,
        rng=np.random.default_rng(9),
    )
    second = moving_block_bootstrap(
        differences,
        replicates=200,
        block_length=10,
        rng=np.random.default_rng(9),
    )

    assert first == second
    assert first.lower_95 < first.observed_mean < first.upper_95


def test_candidate_inference_applies_one_holm_family() -> None:
    differences = {
        "strong": np.full(100, 0.2),
        "null": np.tile(np.asarray([-0.1, 0.1]), 50),
    }

    rows = infer_candidates(
        differences,
        replicates=199,
        block_length=5,
        seed=5,
        alpha=0.05,
    )

    assert [row["model"] for row in rows] == ["strong", "null"]
    assert rows[0]["raw_one_sided_p_value"] == 0.005
    assert rows[0]["holm_adjusted_p_value"] == 0.01
    assert rows[0]["holm_rejected"] is True
    assert rows[1]["holm_rejected"] is False
