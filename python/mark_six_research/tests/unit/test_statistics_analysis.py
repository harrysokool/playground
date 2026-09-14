import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from mark_six.statistics.analysis import (
    AnalysisIntegrityError,
    _approved_baseline_available,
    _json_bytes,
    _mark_individual_practical_effects,
    load_development_histories,
    run_randomness_analysis,
)
from mark_six.statistics.models import load_analysis_config
from mark_six.statistics.null_model import sample_fair_history


def _write_synthetic_project(root: Path, *, physical_position: bool = False) -> None:
    dataset_id = "synthetic-dataset"
    dataset = root / "data" / "processed" / dataset_id
    dataset.mkdir(parents=True)
    mains, extras = sample_fair_history(7, 30, np.random.default_rng(12))
    draw_rows = []
    number_rows = []
    start = date(2020, 1, 1)
    for index, (main, extra) in enumerate(zip(mains, extras, strict=True)):
        draw_id = f"draw-{index}"
        draw_rows.append(
            {"draw_id": draw_id, "draw_date": start + timedelta(days=index), "status": "completed"}
        )
        for number in main:
            number_rows.append(
                {
                    "draw_id": draw_id,
                    "number_role": "main",
                    "number_value": int(number),
                    "draw_position": 1 if physical_position and index == 0 else None,
                }
            )
        number_rows.append(
            {
                "draw_id": draw_id,
                "number_role": "extra",
                "number_value": int(extra),
                "draw_position": None,
            }
        )
    draw_rows.append({"draw_id": "ambiguous", "draw_date": date(1996, 6, 1), "status": "completed"})
    for number in range(1, 7):
        number_rows.append(
            {
                "draw_id": "ambiguous",
                "number_role": "main",
                "number_value": number,
                "draw_position": None,
            }
        )
    number_rows.append(
        {"draw_id": "ambiguous", "number_role": "extra", "number_value": 7, "draw_position": None}
    )
    pq.write_table(pa.Table.from_pylist(draw_rows), dataset / "draws.parquet")
    pq.write_table(pa.Table.from_pylist(number_rows), dataset / "draw_numbers.parquet")
    for name in (
        "jackpot_events",
        "prize_results",
        "rule_versions",
        "source_records",
        "validation_issues",
    ):
        (dataset / f"{name}.parquet").write_bytes(name.encode())
    hashes = {
        path.stem: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in dataset.glob("*.parquet")
    }
    manifest: dict[str, object] = {"dataset_version": dataset_id, "table_sha256": hashes}
    manifest["manifest_sha256"] = hashlib.sha256(_json_bytes(manifest)).hexdigest()
    (dataset / "manifest.json").write_bytes(_json_bytes(manifest))

    config_directory = root / "configs"
    config_directory.mkdir()
    (config_directory / "phase5_statistics.yaml").write_text(
        """analysis_version: phase5-test
protocol_version: phase5-test-v1
dataset_id: synthetic-dataset
dataset_manifest_sha256: PLACEHOLDER
baseline_commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
development_cutoff: '2026-09-13'
root_seed: 77
simulations_per_period: 2
alpha: 0.05
fdr_q: 0.05
corrections: {individual_families: benjamini-hochberg, omnibus_family: holm}
periods:
  - {period_id: pool7, start: '2020-01-01', end: '2020-01-30', pool_size: 7}
exclusions:
  - {start: '1996-01-01', end: '1996-12-31', reason: unresolved pool transition}
low_definition: number <= floor(pool_size / 2)
stability_blocks: 3
practical_thresholds:
  individual_absolute_z: 3
  individual_relative_deviation: 0.1
  pair_triple_absolute_z: 3
  pair_triple_relative_deviation: 0.5
  categorical_cramers_v: 0.1
  sum_absolute_d: 0.1
  serial_absolute_r: 0.05
""".replace("PLACEHOLDER", str(manifest["manifest_sha256"])),
        encoding="utf-8",
    )
    holdout = root / "data" / "holdout"
    holdout.mkdir(parents=True)
    (holdout / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "policy_id": "prospective_312_after_2026_09_13",
                "cutoff_date": "2026-09-13",
                "target_eligible_draws": 312,
                "state": "sealed",
                "entries": [],
            }
        ),
        encoding="utf-8",
    )
    protocol = root / "docs" / "decisions"
    protocol.mkdir(parents=True)
    (protocol / "0005-randomness-testing-protocol.md").write_text(
        "frozen test protocol\n", encoding="utf-8"
    )


def test_rule_period_separation_excludes_ambiguous_1996_draw(tmp_path: Path) -> None:
    _write_synthetic_project(tmp_path)
    config = load_analysis_config(tmp_path / "configs" / "phase5_statistics.yaml")

    histories, excluded, total = load_development_histories(tmp_path, config)

    assert total == 31
    assert histories[0].draw_count == 30
    assert excluded == [
        {"draw_id": "ambiguous", "draw_date": "1996-06-01", "reason": "unresolved pool transition"}
    ]


def test_non_null_physical_position_is_rejected(tmp_path: Path) -> None:
    _write_synthetic_project(tmp_path, physical_position=True)
    config = load_analysis_config(tmp_path / "configs" / "phase5_statistics.yaml")

    with pytest.raises(AnalysisIntegrityError, match="physical position"):
        load_development_histories(tmp_path, config)


def test_analysis_manifest_is_reproducible_and_holdout_remains_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_synthetic_project(tmp_path)
    monkeypatch.setattr("mark_six.statistics.analysis._git_head", lambda _root: "a" * 40)
    monkeypatch.setattr("mark_six.statistics.analysis._phase5_code_hash", lambda _root: "b" * 64)
    timestamp = datetime(2026, 9, 14, tzinfo=UTC)

    first = run_randomness_analysis(tmp_path, generated_at=timestamp)
    first_bytes = first.manifest_path.read_bytes()
    second = run_randomness_analysis(tmp_path, generated_at=timestamp)

    assert second.manifest_path.read_bytes() == first_bytes
    manifest = json.loads(first_bytes)
    assert manifest["holdout_state"] == "sealed"
    assert manifest["holdout_entry_count"] == 0
    assert manifest["summary"]["excluded_draws"] == 1
    assert manifest["root_seed"] == 77


def test_corrected_individual_pair_is_included_in_meaningful_summary(tmp_path: Path) -> None:
    _write_synthetic_project(tmp_path)
    config = load_analysis_config(tmp_path / "configs" / "phase5_statistics.yaml")
    tables: dict[str, list[dict[str, object]]] = {
        "number_frequencies": [],
        "extra_number_frequencies": [],
        "pair_statistics": [
            {
                "period_id": "pool7",
                "first_number": 2,
                "second_number": 6,
                "standardized_deviation": -4.0,
                "relative_deviation": -0.60,
                "corrected_significant": True,
            }
        ],
    }

    findings = _mark_individual_practical_effects(tables, config)

    assert findings == ["pool7:pair=2-6"]
    assert tables["pair_statistics"][0]["meaningful_deviation"] is True


def test_phase5_descendant_retains_approved_phase4_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mark_six.statistics.analysis._git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(
        "mark_six.statistics.analysis._git_has_ancestor",
        lambda _root, commit: commit == "a" * 40,
    )

    assert _approved_baseline_available(tmp_path, "a" * 40)
