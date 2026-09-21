"""Controlled end-to-end runner for Phase 7 historical replication."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from mark_six.prediction.analysis import (
    PredictionIntegrityError,
    _sha256,
    verify_prediction_analysis,
    verify_prediction_inputs,
)
from mark_six.prediction.inference import infer_candidates
from mark_six.prediction.models import load_prediction_config
from mark_six.prediction.reserve import canonical_json_bytes, load_and_verify_reserve
from mark_six.prediction.simulation import calibration_rows, simulate_fair_process
from mark_six.prediction.walkforward import run_walk_forward
from mark_six.replication.comparison import compare_phase6_phase7
from mark_six.replication.models import (
    ReplicationConfig,
    ReplicationRunResult,
    load_replication_config,
)
from mark_six.replication.reporting import write_replication_report
from mark_six.replication.reserve import (
    authorize_reserve_opening,
    load_authorized_replication_history,
)


class ReplicationIntegrityError(RuntimeError):
    """Raised when a Phase 7 frozen input or generated output differs."""


def _git_head(project_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_has_ancestor(project_root: Path, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def _code_hash(project_root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted((project_root / "src" / "mark_six" / "replication").glob("*.py"))
    paths.append(project_root / "src" / "mark_six" / "cli.py")
    for path in paths:
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    stated = value.get("manifest_sha256")
    unsigned = dict(value)
    unsigned.pop("manifest_sha256", None)
    if stated != hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest():
        raise ReplicationIntegrityError(f"manifest self-hash mismatch: {path}")
    return value


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty Phase 7 table: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _read_summary(path: Path) -> list[dict[str, object]]:
    numeric = {
        "pool_size",
        "warmup_draws",
        "scored_draws",
        "mean_log_score_difference_nats",
        "total_log_score_difference_nats",
        "mean_marginal_brier_score",
        "brier_skill_vs_uniform",
        "mean_top_six_hits",
        "mean_observed_rank",
        "calibration_ece",
        "nonnegative_stability_blocks",
        "minimum_stability_block_mean",
    }
    with path.open(encoding="utf-8", newline="") as handle:
        rows: list[dict[str, object]] = []
        for raw in csv.DictReader(handle):
            row: dict[str, object] = dict(raw)
            for field in numeric:
                if field in row:
                    row[field] = float(cast(str, row[field]))
            rows.append(row)
    return rows


def _assert_frozen_family(config: ReplicationConfig, phase6_path: Path) -> None:
    phase6 = load_prediction_config(phase6_path)
    current = [model.model_dump(mode="json", exclude_none=True) for model in config.models]
    previous = [model.model_dump(mode="json", exclude_none=True) for model in phase6.models]
    if current != previous:
        raise ReplicationIntegrityError("Phase 7 model family or parameters differ from Phase 6")
    if config.calibration.model_dump(mode="json") != phase6.calibration.model_dump(mode="json"):
        raise ReplicationIntegrityError("Phase 7 calibration bins differ from Phase 6")
    previous_criteria = phase6.success_criteria.model_dump(mode="json")
    current_criteria = config.success_criteria.model_dump(mode="json")
    current_criteria.pop("require_confidence_interval_lower_above_zero")
    if current_criteria != previous_criteria:
        raise ReplicationIntegrityError("Phase 7 numeric success thresholds differ from Phase 6")


def verify_replication_inputs(
    project_root: Path, config: ReplicationConfig
) -> tuple[dict[str, object], dict[str, object]]:
    """Verify every frozen dependency without accessing reserve outcomes."""

    if not (
        _git_head(project_root) == config.baseline_commit
        or _git_has_ancestor(project_root, config.baseline_commit)
    ):
        raise ReplicationIntegrityError("Git history does not contain the approved Phase 6 commit")
    phase6_config_path = project_root / config.phase6_config_path
    _assert_frozen_family(config, phase6_config_path)
    phase6_config = load_prediction_config(phase6_config_path)
    reserve = load_and_verify_reserve(project_root, phase6_config)
    if reserve.get("manifest_sha256") != config.reserve_manifest_sha256:
        raise ReplicationIntegrityError("reserve manifest differs from frozen Phase 7 hash")
    try:
        integrity = verify_prediction_inputs(project_root, phase6_config, reserve)
        phase6 = verify_prediction_analysis(project_root)
    except PredictionIntegrityError as error:
        raise ReplicationIntegrityError(str(error)) from error
    if phase6.get("manifest_sha256") != config.phase6_manifest_sha256:
        raise ReplicationIntegrityError("Phase 6 manifest differs from frozen Phase 7 hash")
    integrity["phase6"] = phase6
    return integrity, reserve


def _differences(rows: tuple[dict[str, object], ...]) -> dict[str, np.ndarray[Any, Any]]:
    names = list(dict.fromkeys(str(row["model"]) for row in rows if row["model"] != "uniform"))
    return {
        name: np.asarray(
            [cast(float, row["log_score_difference_nats"]) for row in rows if row["model"] == name],
            dtype=np.float64,
        )
        for name in names
    }


def _summary_with_mean_scores(
    rows: list[dict[str, object]], forecasts: tuple[dict[str, object], ...]
) -> list[dict[str, object]]:
    by_model: dict[str, list[float]] = {}
    for row in forecasts:
        by_model.setdefault(str(row["model"]), []).append(
            cast(float, row["whole_set_log_score_nats"])
        )
    return [
        dict(row, mean_whole_set_log_score_nats=float(np.mean(by_model[str(row["model"])])))
        for row in rows
    ]


def _criteria_rows(
    config: ReplicationConfig,
    summaries: list[dict[str, object]],
    inference_rows: list[dict[str, object]],
    family_p: float,
    selected_best: str,
) -> list[dict[str, object]]:
    summary = {str(row["model"]): row for row in summaries}
    inference = {str(row["model"]): row for row in inference_rows}
    threshold = config.success_criteria
    rows: list[dict[str, object]] = []
    for model in config.models[1:]:
        result = summary[model.name]
        test = inference[model.name]
        effect = (
            cast(float, result["mean_log_score_difference_nats"])
            >= threshold.minimum_mean_log_improvement_nats
        )
        interval = cast(float, test["bootstrap_lower_95"]) > 0.0
        holm_pass = cast(float, test["holm_adjusted_p_value"]) < threshold.maximum_adjusted_p_value
        family_pass = (
            model.name == selected_best and family_p < threshold.maximum_family_wide_p_value
        )
        calibration_pass = cast(float, result["calibration_ece"]) <= threshold.maximum_ece
        stability_pass = (
            cast(int, result["nonnegative_stability_blocks"])
            >= threshold.minimum_nonnegative_blocks
            and cast(float, result["minimum_stability_block_mean"])
            >= threshold.minimum_block_mean_log_improvement_nats
        )
        rows.append(
            {
                "model": model.name,
                "effect_pass": effect,
                "confidence_interval_pass": interval,
                "holm_pass": holm_pass,
                "family_wide_pass": family_pass,
                "calibration_pass": calibration_pass,
                "stability_pass": stability_pass,
                "all_criteria_pass": all(
                    (effect, interval, holm_pass, family_pass, calibration_pass, stability_pass)
                ),
            }
        )
    return rows


def run_historical_replication(
    project_root: Path,
    *,
    generated_at: datetime | None = None,
) -> ReplicationRunResult:
    """Open exactly the registered reserve and run the frozen model family once."""

    config_path = project_root / "configs" / "phase7_replication.yaml"
    config = load_replication_config(config_path)
    integrity, reserve = verify_replication_inputs(project_root, config)
    timestamp = generated_at or datetime.now(UTC)
    history, opening = load_authorized_replication_history(
        project_root,
        config,
        reserve,
        authorize_reserve_opening(config),
        opened_at=timestamp,
    )
    result = run_walk_forward(
        history,
        config.models,
        config.initial_history_draws,
        config.calibration.probability_edges,
        config.stability.blocks,
    )
    if len(result.forecast_rows) != config.reserve.draw_count * len(config.models):
        raise ReplicationIntegrityError("Phase 7 did not score every model on every reserve draw")
    inference_rows = infer_candidates(
        _differences(result.forecast_rows),
        replicates=config.inference.bootstrap_replicates,
        block_length=config.inference.moving_block_length,
        seed=config.inference.bootstrap_seed,
        alpha=config.inference.alpha,
    )
    names, simulated_means = simulate_fair_process(
        models=config.models,
        histories=config.simulation.histories,
        draws=config.simulation.total_draws,
        warmup=config.initial_history_draws,
        pool_size=config.reserve.pool_size,
        seed=config.simulation.root_seed,
        batch_size=config.simulation.batch_size,
    )
    summaries = _summary_with_mean_scores(list(result.summary_rows), result.forecast_rows)
    observed = {
        str(row["model"]): cast(float, row["mean_log_score_difference_nats"])
        for row in summaries
        if row["model"] != "uniform"
    }
    simulation_rows, family_p, family_exceedances = calibration_rows(
        names, simulated_means, observed
    )
    selected_best = max(names, key=observed.__getitem__)
    criteria_rows = _criteria_rows(config, summaries, inference_rows, family_p, selected_best)
    successful = tuple(str(row["model"]) for row in criteria_rows if bool(row["all_criteria_pass"]))
    phase6_rows = _read_summary(
        project_root / "reports" / "generated" / "phase6" / "primary_model_summary.csv"
    )
    comparison_rows = compare_phase6_phase7(phase6_rows, summaries)
    phase6_conclusion_replicated = all(value <= 0.0 for value in observed.values())

    output_directory = project_root / "reports" / "generated" / "phase7"
    fair_mean_rows = [
        {
            "simulation_index": history_index + 1,
            "model": name,
            "mean_log_score_difference_nats": float(simulated_means[history_index, model_index]),
        }
        for history_index in range(config.simulation.histories)
        for model_index, name in enumerate(names)
    ]
    opening_rows: list[dict[str, object]] = [
        {
            "opened_at": opening.opened_at.isoformat(),
            "protocol_version": opening.protocol_version,
            "reserve_manifest_sha256": opening.reserve_manifest_sha256,
            "source_table": opening.source_table,
            "first_draw_id": opening.first_draw_id,
            "final_draw_id": opening.final_draw_id,
            "reserve_draw_count": opening.reserve_draw_count,
            "prospective_holdout_accessed": opening.prospective_holdout_accessed,
        }
    ]
    tables: dict[str, list[dict[str, object]]] = {
        "reserve_forecasts": list(result.forecast_rows),
        "model_summary": summaries,
        "paired_inference": inference_rows,
        "calibration": list(result.calibration_rows),
        "stability": list(result.stability_rows),
        "fair_process_calibration": simulation_rows,
        "fair_process_means": fair_mean_rows,
        "phase6_phase7_comparison": comparison_rows,
        "decision_criteria": criteria_rows,
        "reserve_opening": opening_rows,
    }
    output_paths: list[Path] = []
    for name, rows in tables.items():
        path = output_directory / f"{name}.csv"
        _write_csv(path, rows)
        output_paths.append(path)
    report_path = project_root / "reports" / "generated" / "historical_replication.md"
    write_replication_report(
        report_path=report_path,
        config=config,
        integrity=integrity,
        opening=opening,
        summary_rows=summaries,
        inference_rows=inference_rows,
        simulation_rows=simulation_rows,
        stability_rows=list(result.stability_rows),
        comparison_rows=comparison_rows,
        criteria_rows=criteria_rows,
        selected_best=selected_best,
        phase6_conclusion_replicated=phase6_conclusion_replicated,
    )
    output_paths.append(report_path)
    manifest: dict[str, object] = {
        "schema_version": "1",
        "analysis_version": config.analysis_version,
        "phase6_commit": config.baseline_commit,
        "git_head_at_run": _git_head(project_root),
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "canonical_table_sha256": integrity["canonical_table_sha256"],
        "phase5_analysis": integrity["phase5"],
        "phase6_analysis_manifest_sha256": config.phase6_manifest_sha256,
        "reserve_manifest_sha256": config.reserve_manifest_sha256,
        "protocol_version": config.protocol_version,
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "phase7_code_sha256": _code_hash(project_root),
        "generated_at": timestamp.isoformat(),
        "reserve_opening": opening_rows[0],
        "candidate_models": [
            model.model_dump(mode="json", exclude_none=True) for model in config.models
        ],
        "primary_metric": config.primary_metric,
        "secondary_metrics": config.secondary_metrics,
        "inference_method": "paired circular moving-block bootstrap",
        "correction_method": config.inference.correction,
        "bootstrap_seed": config.inference.bootstrap_seed,
        "bootstrap_replicates": config.inference.bootstrap_replicates,
        "moving_block_length": config.inference.moving_block_length,
        "simulation_seed": config.simulation.root_seed,
        "simulation_count": config.simulation.histories,
        "reserve_first_draw": config.reserve.first_draw_id,
        "reserve_final_draw": config.reserve.final_draw_id,
        "reserve_size": config.reserve.draw_count,
        "initial_history_draws": config.initial_history_draws,
        "stability_blocks": config.stability.blocks,
        "draws_per_stability_block": config.stability.draws_per_block,
        "selected_best_model": selected_best,
        "family_wide_exceedances": family_exceedances,
        "family_wide_p_value": family_p,
        "corrected_rejections": sum(bool(row["holm_rejected"]) for row in inference_rows),
        "successful_models": list(successful),
        "phase6_conclusion_replicated": phase6_conclusion_replicated,
        "prospective_holdout_state": integrity["holdout_state"],
        "prospective_holdout_entry_count": integrity["holdout_entry_count"],
        "prospective_holdout_accessed": False,
        "deviations": [],
        "output_sha256": {
            path.relative_to(project_root).as_posix(): _sha256(path) for path in output_paths
        },
    }
    manifest["manifest_sha256"] = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    manifest_path = project_root / "reports" / "generated" / "phase7_analysis_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return ReplicationRunResult(
        report_path=report_path,
        manifest_path=manifest_path,
        output_directory=output_directory,
        reserve_draws=config.reserve.draw_count,
        candidate_models=len(config.models),
        simulation_histories=config.simulation.histories,
        selected_best_model=selected_best,
        successful_models=successful,
        phase6_conclusion_replicated=phase6_conclusion_replicated,
    )


def verify_historical_replication(project_root: Path) -> dict[str, object]:
    """Verify Phase 7 inputs, manifest self-hash, code, and every output hash."""

    config_path = project_root / "configs" / "phase7_replication.yaml"
    config = load_replication_config(config_path)
    integrity, _ = verify_replication_inputs(project_root, config)
    path = project_root / "reports" / "generated" / "phase7_analysis_manifest.json"
    manifest = _load_manifest(path)
    checks = {
        "phase6_commit": config.baseline_commit,
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "phase6_analysis_manifest_sha256": config.phase6_manifest_sha256,
        "reserve_manifest_sha256": config.reserve_manifest_sha256,
        "protocol_version": config.protocol_version,
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "phase7_code_sha256": _code_hash(project_root),
        "reserve_first_draw": config.reserve.first_draw_id,
        "reserve_final_draw": config.reserve.final_draw_id,
        "reserve_size": config.reserve.draw_count,
        "simulation_seed": config.simulation.root_seed,
        "simulation_count": config.simulation.histories,
    }
    for field, expected in checks.items():
        if manifest.get(field) != expected:
            raise ReplicationIntegrityError(f"Phase 7 manifest mismatch: {field}")
    outputs = manifest.get("output_sha256")
    if not isinstance(outputs, dict):
        raise ReplicationIntegrityError("Phase 7 output hashes are absent")
    failures = [
        str(relative)
        for relative, expected in outputs.items()
        if not (project_root / str(relative)).exists()
        or _sha256(project_root / str(relative)) != expected
    ]
    if failures:
        raise ReplicationIntegrityError(f"Phase 7 output hash failures: {', '.join(failures)}")
    opening = cast(dict[str, object], manifest["reserve_opening"])
    if opening.get("prospective_holdout_accessed") is not False:
        raise ReplicationIntegrityError("Phase 7 manifest does not preserve holdout isolation")
    return {
        "manifest_sha256": manifest["manifest_sha256"],
        "output_count": len(outputs),
        "output_failures": 0,
        "dataset_manifest_sha256": integrity["dataset_manifest_sha256"],
        "canonical_table_count": len(
            cast(dict[object, object], integrity["canonical_table_sha256"])
        ),
        "raw_snapshots": integrity["raw_snapshots"],
        "phase6_manifest_sha256": config.phase6_manifest_sha256,
        "reserve_manifest_sha256": config.reserve_manifest_sha256,
        "reserve_entry_count": config.reserve.draw_count,
        "holdout_state": integrity["holdout_state"],
        "holdout_entry_count": integrity["holdout_entry_count"],
        "reserve_opened_at": opening["opened_at"],
        "selected_best_model": manifest["selected_best_model"],
        "successful_models": manifest["successful_models"],
        "phase6_conclusion_replicated": manifest["phase6_conclusion_replicated"],
        "deviations": manifest["deviations"],
    }


# PHASE8_EXTENSION_BEGIN
def _without_phase8_extension(content: bytes) -> bytes:
    """Remove isolated post-Phase 7 extensions from the frozen Phase 7 hash."""

    for phase in (b"PHASE8", b"PHASE9"):
        begin = b"\n\n# " + phase + b"_EXTENSION_BEGIN\n"
        end = b"# " + phase + b"_EXTENSION_END\n"
        while begin in content:
            start = content.index(begin)
            finish = content.index(end, start) + len(end)
            content = content[:start] + content[finish:]
    return content


def _code_hash(project_root: Path) -> str:  # type: ignore[no-redef]
    """Hash Phase 7 code while excluding the explicitly marked Phase 8 surface."""

    digest = hashlib.sha256()
    paths = sorted((project_root / "src" / "mark_six" / "replication").glob("*.py"))
    paths.append(project_root / "src" / "mark_six" / "cli.py")
    for path in paths:
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(_without_phase8_extension(path.read_bytes()))
        digest.update(b"\0")
    return digest.hexdigest()


# PHASE8_EXTENSION_END
