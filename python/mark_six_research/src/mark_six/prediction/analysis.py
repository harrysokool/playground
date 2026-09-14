"""End-to-end, provenance-bound Phase 6 predictive-signal analysis."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from mark_six.audit import audit_raw_acquisition
from mark_six.holdout import load_holdout_manifest
from mark_six.prediction.data import load_primary_history, load_secondary_history
from mark_six.prediction.inference import infer_candidates
from mark_six.prediction.models import PredictionConfig, load_prediction_config
from mark_six.prediction.reporting import write_prediction_report
from mark_six.prediction.reserve import (
    canonical_json_bytes,
    initialize_reserve_manifest,
    load_and_verify_reserve,
)
from mark_six.prediction.simulation import calibration_rows, simulate_fair_process
from mark_six.prediction.walkforward import run_walk_forward
from mark_six.provenance import load_snapshot_metadata, verify_snapshot


class PredictionIntegrityError(RuntimeError):
    """Raised when frozen inputs or generated outputs fail integrity checks."""


@dataclass(frozen=True)
class PredictionRunResult:
    """High-level paths and outcome of a complete Phase 6 run."""

    report_path: Path
    manifest_path: Path
    output_directory: Path
    primary_scored_draws: int
    candidate_models: int
    simulation_histories: int
    selected_best_model: str
    primary_signal: bool


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    paths = sorted((project_root / "src" / "mark_six" / "prediction").glob("*.py"))
    paths.append(project_root / "src" / "mark_six" / "cli.py")
    for path in paths:
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _verify_self_hashed_manifest(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    stated = value.get("manifest_sha256")
    unsigned = dict(value)
    unsigned.pop("manifest_sha256", None)
    if stated != hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest():
        raise PredictionIntegrityError(f"manifest self-hash mismatch: {path}")
    return value


def _verify_phase5_outputs(project_root: Path) -> dict[str, object]:
    path = project_root / "reports" / "generated" / "phase5_analysis_manifest.json"
    manifest = _verify_self_hashed_manifest(path)
    failures: list[str] = []
    outputs = manifest.get("output_sha256")
    if not isinstance(outputs, dict):
        raise PredictionIntegrityError("Phase 5 manifest output hashes are absent")
    for relative, expected in outputs.items():
        output = project_root / str(relative)
        if not output.exists() or _sha256(output) != expected:
            failures.append(str(relative))
    if failures:
        raise PredictionIntegrityError(f"Phase 5 output hash failures: {', '.join(failures)}")
    return {
        "manifest_path": path.relative_to(project_root).as_posix(),
        "manifest_sha256": manifest["manifest_sha256"],
        "output_count": len(outputs),
        "output_failures": 0,
    }


def verify_prediction_inputs(
    project_root: Path, config: PredictionConfig, reserve: dict[str, object]
) -> dict[str, object]:
    """Verify dataset, raw evidence, Phase 5 artifacts, reserve, and holdout."""

    dataset_directory = project_root / "data" / "processed" / config.dataset_id
    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset_manifest: dict[str, Any] = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    unsigned = dict(dataset_manifest)
    stated = unsigned.pop("manifest_sha256", None)
    calculated = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
    if (
        dataset_manifest.get("dataset_version") != config.dataset_id
        or stated != config.dataset_manifest_sha256
        or calculated != stated
    ):
        raise PredictionIntegrityError("dataset identity or manifest hash mismatch")
    table_hashes = dataset_manifest.get("table_sha256")
    if not isinstance(table_hashes, dict) or len(table_hashes) != 7:
        raise PredictionIntegrityError("dataset must contain exactly seven canonical tables")
    verified_tables: dict[str, str] = {}
    for name, expected in table_hashes.items():
        path = dataset_directory / f"{name}.parquet"
        actual = _sha256(path)
        if actual != expected:
            raise PredictionIntegrityError(f"canonical Parquet hash mismatch: {name}")
        verified_tables[str(name)] = actual
    acquisition = audit_raw_acquisition(project_root)
    acquisition_failures = sum(
        (
            acquisition.missing_metadata_sidecars,
            acquisition.missing_request_sidecars,
            acquisition.hash_failures,
            acquisition.malformed_json,
            acquisition.unexpected_graphql_structures,
            acquisition.http_failures,
        )
    )
    metadata_paths = sorted((project_root / "data" / "raw").glob("*/*/*/*.metadata.json"))
    snapshot_failures = 0
    for metadata_path in metadata_paths:
        try:
            metadata = load_snapshot_metadata(metadata_path)
        except (OSError, ValueError):
            snapshot_failures += 1
            continue
        if not verify_snapshot(project_root, metadata):
            snapshot_failures += 1
    raw_failures = acquisition_failures + snapshot_failures
    if len(metadata_paths) != 611 or raw_failures:
        raise PredictionIntegrityError("retained raw snapshot integrity differs from baseline")
    holdout = load_holdout_manifest(project_root / "data" / "holdout" / "manifest.json")
    if holdout.state != "sealed" or holdout.entries:
        raise PredictionIntegrityError("prospective holdout must remain sealed with zero entries")
    if not (
        _git_head(project_root) == config.baseline_commit
        or _git_has_ancestor(project_root, config.baseline_commit)
    ):
        raise PredictionIntegrityError("Git history does not contain the approved Phase 5 baseline")
    phase5 = _verify_phase5_outputs(project_root)
    return {
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": calculated,
        "canonical_table_sha256": verified_tables,
        "raw_snapshots": len(metadata_paths),
        "raw_integrity_failures": raw_failures,
        "holdout_state": holdout.state,
        "holdout_entry_count": len(holdout.entries),
        "reserve_state": "sealed_for_phase7",
        "reserve_entry_count": len(cast(list[object], reserve["entries"])),
        "reserve_manifest_sha256": reserve["manifest_sha256"],
        "phase5": phase5,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty Phase 6 table: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _differences(rows: tuple[dict[str, object], ...]) -> dict[str, np.ndarray[Any, Any]]:
    names = list(dict.fromkeys(str(row["model"]) for row in rows if row["model"] != "uniform"))
    return {
        name: np.asarray(
            [cast(float, row["log_score_difference_nats"]) for row in rows if row["model"] == name],
            dtype=np.float64,
        )
        for name in names
    }


def _criteria_rows(
    config: PredictionConfig,
    summary_rows: list[dict[str, object]],
    inference_rows: list[dict[str, object]],
    family_p: float,
    best_model: str,
) -> list[dict[str, object]]:
    summaries = {str(row["model"]): row for row in summary_rows}
    inference = {str(row["model"]): row for row in inference_rows}
    threshold = config.success_criteria
    rows: list[dict[str, object]] = []
    for model in config.models[1:]:
        summary = summaries[model.name]
        test = inference[model.name]
        effect = (
            cast(float, summary["mean_log_score_difference_nats"])
            >= threshold.minimum_mean_log_improvement_nats
        )
        holm_pass = cast(float, test["holm_adjusted_p_value"]) < threshold.maximum_adjusted_p_value
        family_pass = model.name == best_model and family_p < threshold.maximum_family_wide_p_value
        calibration_pass = cast(float, summary["calibration_ece"]) <= threshold.maximum_ece
        stability_pass = (
            cast(int, summary["nonnegative_stability_blocks"])
            >= threshold.minimum_nonnegative_blocks
            and cast(float, summary["minimum_stability_block_mean"])
            >= threshold.minimum_block_mean_log_improvement_nats
        )
        rows.append(
            {
                "model": model.name,
                "effect_pass": effect,
                "holm_pass": holm_pass,
                "family_wide_pass": family_pass,
                "calibration_pass": calibration_pass,
                "stability_pass": stability_pass,
                "all_criteria_pass": all(
                    (effect, holm_pass, family_pass, calibration_pass, stability_pass)
                ),
            }
        )
    return rows


def run_predictive_analysis(
    project_root: Path,
    *,
    simulation_histories: int | None = None,
    generated_at: datetime | None = None,
) -> PredictionRunResult:
    """Run the complete frozen Phase 6 workflow without touching reserve outcomes."""

    config_path = project_root / "configs" / "phase6_prediction.yaml"
    config = load_prediction_config(config_path)
    initialize_reserve_manifest(project_root, config)
    reserve = load_and_verify_reserve(project_root, config)
    integrity = verify_prediction_inputs(project_root, config, reserve)

    primary_history = load_primary_history(project_root, config, reserve)
    primary = run_walk_forward(
        primary_history,
        config.models,
        config.primary.warmup_draws,
        config.calibration.probability_edges,
        config.stability_blocks,
    )
    differences = _differences(primary.forecast_rows)
    inference_rows = infer_candidates(
        differences,
        replicates=config.inference.bootstrap_replicates,
        block_length=config.inference.moving_block_length,
        seed=config.inference.bootstrap_seed,
        alpha=config.inference.alpha,
    )
    actual_simulations = (
        config.simulation.histories if simulation_histories is None else simulation_histories
    )
    if actual_simulations < 1:
        raise ValueError("simulation histories must be positive")
    names, simulated_means = simulate_fair_process(
        models=config.models,
        histories=actual_simulations,
        draws=config.primary.phase6_draws,
        warmup=config.primary.warmup_draws,
        pool_size=config.primary.pool_size,
        seed=config.simulation.root_seed,
        batch_size=config.simulation.batch_size,
    )
    observed_means = {
        str(row["model"]): cast(float, row["mean_log_score_difference_nats"])
        for row in primary.summary_rows
        if row["model"] != "uniform"
    }
    simulation_rows, family_p, family_exceedances = calibration_rows(
        names, simulated_means, observed_means
    )
    best_model = max(names, key=observed_means.__getitem__)
    primary_summary = list(primary.summary_rows)
    criteria_rows = _criteria_rows(config, primary_summary, inference_rows, family_p, best_model)
    primary_signal = any(bool(row["all_criteria_pass"]) for row in criteria_rows)

    replications = [
        run_walk_forward(
            load_secondary_history(project_root, config, spec),
            config.models,
            config.secondary.warmup_draws,
            config.calibration.probability_edges,
            config.stability_blocks,
        )
        for spec in config.secondary.periods
    ]
    replication_forecasts = [row for result in replications for row in result.forecast_rows]
    replication_summary = [row for result in replications for row in result.summary_rows]
    replication_calibration = [row for result in replications for row in result.calibration_rows]
    replication_stability = [row for result in replications for row in result.stability_rows]

    output_directory = project_root / "reports" / "generated" / "phase6"
    fair_mean_rows = [
        {
            "simulation_index": history_index + 1,
            "model": name,
            "mean_log_score_difference_nats": float(simulated_means[history_index, model_index]),
        }
        for history_index in range(actual_simulations)
        for model_index, name in enumerate(names)
    ]
    tables: dict[str, list[dict[str, object]]] = {
        "primary_forecasts": list(primary.forecast_rows),
        "primary_model_summary": primary_summary,
        "primary_calibration": list(primary.calibration_rows),
        "primary_stability": list(primary.stability_rows),
        "paired_inference": inference_rows,
        "fair_process_calibration": simulation_rows,
        "fair_process_means": fair_mean_rows,
        "decision_criteria": criteria_rows,
        "replication_forecasts": replication_forecasts,
        "replication_model_summary": replication_summary,
        "replication_calibration": replication_calibration,
        "replication_stability": replication_stability,
    }
    output_paths: list[Path] = []
    for name, rows in tables.items():
        path = output_directory / f"{name}.csv"
        _write_csv(path, rows)
        output_paths.append(path)
    report_path = project_root / "reports" / "generated" / "predictive_signal_analysis.md"
    write_prediction_report(
        report_path=report_path,
        config=config,
        integrity=integrity,
        primary_summary=primary_summary,
        inference_rows=inference_rows,
        simulation_rows=simulation_rows,
        criteria_rows=criteria_rows,
        replication_summary=replication_summary,
        primary_signal=primary_signal,
        best_model=best_model,
    )
    output_paths.append(report_path)

    deviations = []
    if actual_simulations != config.simulation.histories:
        deviations.append(
            f"simulation_histories override: {actual_simulations} instead of "
            f"{config.simulation.histories}"
        )
    manifest: dict[str, object] = {
        "schema_version": "1",
        "analysis_version": config.analysis_version,
        "protocol_version": config.protocol_version,
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "canonical_table_sha256": integrity["canonical_table_sha256"],
        "phase5_baseline_commit": config.baseline_commit,
        "git_head_at_run": _git_head(project_root),
        "phase6_code_sha256": _code_hash(project_root),
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "reserve_manifest_path": config.reserve_manifest_path,
        "reserve_manifest_sha256": integrity["reserve_manifest_sha256"],
        "reserve_entry_count": integrity["reserve_entry_count"],
        "reserve_outcomes_accessed": False,
        "prospective_holdout_state": integrity["holdout_state"],
        "prospective_holdout_entry_count": integrity["holdout_entry_count"],
        "raw_snapshots": integrity["raw_snapshots"],
        "raw_integrity_failures": integrity["raw_integrity_failures"],
        "phase5_analysis": integrity["phase5"],
        "primary": {
            "population_draws": config.primary.population_draws,
            "accessible_draws": primary_history.draw_count,
            "warmup_draws": config.primary.warmup_draws,
            "scored_draws": config.primary.scored_draws,
            "first_accessible_draw_id": primary_history.draw_ids[0],
            "last_accessible_draw_id": primary_history.draw_ids[-1],
        },
        "candidate_count_including_uniform": len(config.models),
        "bootstrap_seed": config.inference.bootstrap_seed,
        "bootstrap_replicates": config.inference.bootstrap_replicates,
        "moving_block_length": config.inference.moving_block_length,
        "simulation_root_seed": config.simulation.root_seed,
        "simulation_histories": actual_simulations,
        "family_wide_exceedances": family_exceedances,
        "family_wide_p_value": family_p,
        "selected_best_model": best_model,
        "primary_signal": primary_signal,
        "deviations": deviations,
        "output_sha256": {
            path.relative_to(project_root).as_posix(): _sha256(path) for path in output_paths
        },
    }
    manifest["manifest_sha256"] = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    manifest_path = project_root / "reports" / "generated" / "phase6_analysis_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return PredictionRunResult(
        report_path=report_path,
        manifest_path=manifest_path,
        output_directory=output_directory,
        primary_scored_draws=config.primary.scored_draws,
        candidate_models=len(config.models),
        simulation_histories=actual_simulations,
        selected_best_model=best_model,
        primary_signal=primary_signal,
    )


def verify_prediction_analysis(project_root: Path) -> dict[str, object]:
    """Recompute all Phase 6 input, source, reserve, and generated-output hashes."""

    config_path = project_root / "configs" / "phase6_prediction.yaml"
    config = load_prediction_config(config_path)
    reserve = load_and_verify_reserve(project_root, config)
    integrity = verify_prediction_inputs(project_root, config, reserve)
    manifest_path = project_root / "reports" / "generated" / "phase6_analysis_manifest.json"
    manifest = _verify_self_hashed_manifest(manifest_path)
    checks = {
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "phase6_code_sha256": _code_hash(project_root),
        "reserve_manifest_sha256": reserve["manifest_sha256"],
    }
    for field, actual in checks.items():
        if manifest.get(field) != actual:
            raise PredictionIntegrityError(f"Phase 6 manifest mismatch: {field}")
    outputs = manifest.get("output_sha256")
    if not isinstance(outputs, dict):
        raise PredictionIntegrityError("Phase 6 output hashes are absent")
    failures = [
        str(relative)
        for relative, expected in outputs.items()
        if not (project_root / str(relative)).exists()
        or _sha256(project_root / str(relative)) != expected
    ]
    if failures:
        raise PredictionIntegrityError(f"Phase 6 output hash failures: {', '.join(failures)}")
    return {
        "manifest_sha256": manifest["manifest_sha256"],
        "output_count": len(outputs),
        "output_failures": 0,
        "dataset_manifest_sha256": integrity["dataset_manifest_sha256"],
        "canonical_table_count": len(
            cast(dict[object, object], integrity["canonical_table_sha256"])
        ),
        "raw_snapshots": integrity["raw_snapshots"],
        "holdout_state": integrity["holdout_state"],
        "holdout_entry_count": integrity["holdout_entry_count"],
        "reserve_state": integrity["reserve_state"],
        "reserve_entry_count": integrity["reserve_entry_count"],
        "reserve_outcomes_accessed": manifest["reserve_outcomes_accessed"],
        "deviations": manifest["deviations"],
    }
