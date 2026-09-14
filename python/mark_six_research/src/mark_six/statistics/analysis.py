"""End-to-end, provenance-bound Phase 5 randomness analysis."""

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
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from mark_six.holdout import load_holdout_manifest
from mark_six.statistics.metrics import analyse_period, metric_context
from mark_six.statistics.models import (
    AnalysisConfig,
    DrawHistory,
    PeriodAnalysis,
    PeriodSpec,
    load_analysis_config,
)
from mark_six.statistics.multiple_testing import benjamini_hochberg, holm
from mark_six.statistics.reporting import write_randomness_report
from mark_six.statistics.simulation_calibration import calibrate_period, derived_period_seeds


class AnalysisIntegrityError(RuntimeError):
    """Raised when the frozen dataset or holdout does not match the protocol."""


@dataclass(frozen=True)
class AnalysisRunResult:
    """Paths and high-level results from one complete Phase 5 run."""

    report_path: Path
    manifest_path: Path
    output_directory: Path
    included_draws: int
    excluded_draws: int
    individual_hypotheses: int
    omnibus_hypotheses: int
    raw_significant: int
    corrected_significant: int
    inconsistent_findings: tuple[str, ...]


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_analysis_inputs(project_root: Path, config: AnalysisConfig) -> dict[str, object]:
    """Verify the exact dataset publication and outcome-free holdout manifest."""

    dataset_directory = project_root / "data" / "processed" / config.dataset_id
    manifest_path = dataset_directory / "manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_version") != config.dataset_id:
        raise AnalysisIntegrityError("dataset ID does not match the Phase 5 protocol")
    stated_hash = manifest.get("manifest_sha256")
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    calculated_hash = hashlib.sha256(_json_bytes(unsigned)).hexdigest()
    if stated_hash != config.dataset_manifest_sha256 or calculated_hash != stated_hash:
        raise AnalysisIntegrityError("dataset manifest hash does not match the approved baseline")
    table_hashes = manifest.get("table_sha256")
    if not isinstance(table_hashes, dict) or len(table_hashes) != 7:
        raise AnalysisIntegrityError(
            "dataset manifest must identify exactly seven canonical tables"
        )
    verified_tables: dict[str, str] = {}
    for table_name, expected_hash in table_hashes.items():
        table_path = dataset_directory / f"{table_name}.parquet"
        actual_hash = _sha256(table_path)
        if actual_hash != expected_hash:
            raise AnalysisIntegrityError(f"canonical table hash mismatch: {table_name}")
        verified_tables[str(table_name)] = actual_hash
    holdout = load_holdout_manifest(project_root / "data" / "holdout" / "manifest.json")
    if holdout.state != "sealed" or holdout.entries:
        raise AnalysisIntegrityError("prospective holdout must remain sealed with zero entries")
    return {
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": calculated_hash,
        "canonical_table_sha256": verified_tables,
        "holdout_state": holdout.state,
        "holdout_entry_count": len(holdout.entries),
    }


def _history_for_period(
    spec: PeriodSpec,
    draw_rows: list[dict[str, Any]],
    numbers_by_draw: dict[str, dict[str, list[int]]],
) -> DrawHistory:
    selected = sorted(
        (row for row in draw_rows if spec.start <= row["draw_date"] <= spec.end),
        key=lambda row: (row["draw_date"], row["draw_id"]),
    )
    if not selected:
        raise AnalysisIntegrityError(f"analysis period contains no draws: {spec.period_id}")
    mains: list[list[int]] = []
    extras: list[int] = []
    for draw in selected:
        draw_id = str(draw["draw_id"])
        number_roles = numbers_by_draw.get(draw_id, {})
        main = sorted(number_roles.get("main", []))
        extra = number_roles.get("extra", [])
        if len(main) != 6 or len(set(main)) != 6 or len(extra) != 1:
            raise AnalysisIntegrityError(f"invalid number cardinality in {draw_id}")
        if any(number < 1 or number > spec.pool_size for number in [*main, extra[0]]):
            raise AnalysisIntegrityError(
                f"number outside preregistered pool {spec.pool_size} in {draw_id}"
            )
        if extra[0] in main:
            raise AnalysisIntegrityError(f"Extra Number duplicates a main number in {draw_id}")
        mains.append(main)
        extras.append(extra[0])
    return DrawHistory(
        period_id=spec.period_id,
        pool_size=spec.pool_size,
        draw_ids=tuple(str(row["draw_id"]) for row in selected),
        draw_dates=tuple(row["draw_date"] for row in selected),
        mains=np.asarray(mains, dtype=np.int64),
        extras=np.asarray(extras, dtype=np.int64),
    )


def load_development_histories(
    project_root: Path, config: AnalysisConfig
) -> tuple[list[DrawHistory], list[dict[str, object]], int]:
    """Load only the frozen development Parquet files and apply fixed period rules."""

    dataset_directory = project_root / "data" / "processed" / config.dataset_id
    draw_rows: list[dict[str, Any]] = pq.read_table(
        dataset_directory / "draws.parquet",
        columns=["draw_id", "draw_date", "status"],
    ).to_pylist()
    if any(row["draw_date"] > config.development_cutoff for row in draw_rows):
        raise AnalysisIntegrityError("development dataset crosses the sealed holdout cutoff")
    completed = [row for row in draw_rows if row["status"] == "completed"]
    number_rows: list[dict[str, Any]] = pq.read_table(
        dataset_directory / "draw_numbers.parquet",
        columns=["draw_id", "number_role", "number_value", "draw_position"],
    ).to_pylist()
    if any(row["draw_position"] is not None for row in number_rows):
        raise AnalysisIntegrityError(
            "Phase 5 does not consume physical position data; unexpected positions were present"
        )
    numbers_by_draw: dict[str, dict[str, list[int]]] = {}
    for row in number_rows:
        role_map = numbers_by_draw.setdefault(str(row["draw_id"]), {})
        role_map.setdefault(str(row["number_role"]), []).append(int(row["number_value"]))
    histories = [_history_for_period(spec, completed, numbers_by_draw) for spec in config.periods]
    included_ids = {draw_id for history in histories for draw_id in history.draw_ids}
    excluded_rows: list[dict[str, object]] = []
    for draw in sorted(completed, key=lambda row: (row["draw_date"], row["draw_id"])):
        draw_id = str(draw["draw_id"])
        if draw_id in included_ids:
            continue
        reason = "outside preregistered confirmatory periods"
        for exclusion in config.exclusions:
            if exclusion.start <= draw["draw_date"] <= exclusion.end:
                reason = exclusion.reason
                break
        excluded_rows.append(
            {
                "draw_id": draw_id,
                "draw_date": draw["draw_date"].isoformat(),
                "reason": reason,
            }
        )
    return histories, excluded_rows, len(completed)


def _apply_bh(rows: list[dict[str, object]], q: float, family_name: str) -> tuple[int, int]:
    raw = [cast(float, row["raw_p_value"]) for row in rows]
    adjusted, rejected = benjamini_hochberg(raw, q)
    for row, adjusted_p, reject in zip(rows, adjusted, rejected, strict=True):
        row["multiple_testing_family"] = family_name
        row["correction_method"] = "benjamini-hochberg"
        row["adjusted_p_value"] = adjusted_p
        row["corrected_significant"] = reject
    return sum(value < 0.05 for value in raw), sum(rejected)


def _mark_individual_practical_effects(
    tables: dict[str, list[dict[str, object]]], config: AnalysisConfig
) -> list[str]:
    """Apply the frozen individual effect thresholds and return disclosed deviations."""

    thresholds = config.practical_thresholds
    findings: list[str] = []
    for table_name in ("number_frequencies", "extra_number_frequencies"):
        for row in tables[table_name]:
            practical = bool(
                abs(cast(float, row["standardized_deviation"])) >= thresholds.individual_absolute_z
                and abs(cast(float, row["relative_deviation"]))
                >= thresholds.individual_relative_deviation
            )
            meaningful = bool(row["corrected_significant"] and practical)
            row["practical_effect"] = practical
            row["meaningful_deviation"] = meaningful
            if meaningful:
                role = "main" if table_name == "number_frequencies" else "extra"
                findings.append(f"{row['period_id']}:{role}_number={row['number']}")
    for row in tables["pair_statistics"]:
        practical = bool(
            abs(cast(float, row["standardized_deviation"])) >= thresholds.pair_triple_absolute_z
            and abs(cast(float, row["relative_deviation"]))
            >= thresholds.pair_triple_relative_deviation
        )
        meaningful = bool(row["corrected_significant"] and practical)
        row["practical_effect"] = practical
        row["meaningful_deviation"] = meaningful
        if meaningful:
            findings.append(f"{row['period_id']}:pair={row['first_number']}-{row['second_number']}")
    return findings


def _practical_flag(analysis: PeriodAnalysis, family: str, config: AnalysisConfig) -> bool:
    thresholds = config.practical_thresholds
    effect = analysis.effect_sizes[family]
    if family in {"main_frequency", "main_frequency_max"}:
        return bool(
            cast(float, analysis.descriptive["largest_main_absolute_z"])
            >= thresholds.individual_absolute_z
            and effect >= thresholds.individual_relative_deviation
        )
    if family in {"extra_frequency", "extra_frequency_max"}:
        return bool(
            cast(float, analysis.descriptive["largest_extra_absolute_z"])
            >= thresholds.individual_absolute_z
            and effect >= thresholds.individual_relative_deviation
        )
    if family in {"odd_even", "low_high", "draw_overlap", "temporal_stability"}:
        return effect >= thresholds.categorical_cramers_v
    if family == "sum_distribution":
        return abs(effect) >= thresholds.sum_absolute_d
    if family in {"pairs", "triples"}:
        return bool(
            analysis.omnibus_statistics[family] >= thresholds.pair_triple_absolute_z
            and effect >= thresholds.pair_triple_relative_deviation
        )
    if family == "serial_dependence":
        return effect >= thresholds.serial_absolute_r
    if family == "gaps":
        return effect >= thresholds.individual_relative_deviation
    return analysis.omnibus_statistics[family] >= thresholds.individual_absolute_z


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"cannot write empty statistical table: {path.name}")
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _phase5_code_hash(project_root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted((project_root / "src" / "mark_six" / "statistics").glob("*.py"))
    paths.append(project_root / "src" / "mark_six" / "cli.py")
    for path in paths:
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_head(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_has_ancestor(project_root: Path, commit: str) -> bool:
    """Return whether the approved baseline is retained in current Git history."""

    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _approved_baseline_available(project_root: Path, baseline_commit: str) -> bool:
    """Accept the baseline itself or a descendant containing the Phase 5 implementation."""

    return _git_head(project_root) == baseline_commit or _git_has_ancestor(
        project_root, baseline_commit
    )


def run_randomness_analysis(
    project_root: Path,
    *,
    seed: int | None = None,
    simulations: int | None = None,
    generated_at: datetime | None = None,
) -> AnalysisRunResult:
    """Run the frozen confirmatory analysis and write reproducible generated outputs."""

    config_path = project_root / "configs" / "phase5_statistics.yaml"
    protocol_path = project_root / "docs" / "decisions" / "0005-randomness-testing-protocol.md"
    config = load_analysis_config(config_path)
    actual_seed = config.root_seed if seed is None else seed
    actual_simulations = config.simulations_per_period if simulations is None else simulations
    if actual_simulations < 1:
        raise ValueError("simulations must be positive")
    integrity = verify_analysis_inputs(project_root, config)
    if not _approved_baseline_available(project_root, config.baseline_commit):
        raise AnalysisIntegrityError("Git history no longer contains the approved Phase 4 baseline")
    histories, excluded_rows, total_completed = load_development_histories(project_root, config)
    contexts = {history.period_id: metric_context(history.pool_size) for history in histories}
    analyses = [analyse_period(history, contexts[history.period_id]) for history in histories]

    table_names = next(iter(analyses)).tables.keys()
    tables = {
        name: [row for analysis in analyses for row in analysis.tables[name]]
        for name in table_names
    }
    raw_significant = 0
    corrected_significant = 0
    for table_name, family_name in (
        ("number_frequencies", "main-number frequencies"),
        ("extra_number_frequencies", "Extra Number frequencies"),
        ("pair_statistics", "unordered main-number pairs"),
    ):
        raw_count, corrected_count = _apply_bh(tables[table_name], config.fdr_q, family_name)
        raw_significant += raw_count
        corrected_significant += corrected_count
    individual_raw_significant = raw_significant
    individual_corrected_significant = corrected_significant
    individual_findings = _mark_individual_practical_effects(tables, config)

    seeds = derived_period_seeds(actual_seed, len(histories))
    calibrations = []
    for history, analysis, period_seed in zip(histories, analyses, seeds, strict=True):
        calibrations.extend(
            calibrate_period(
                history,
                contexts[history.period_id],
                analysis.omnibus_statistics,
                actual_simulations,
                period_seed,
            )
        )
    adjusted, rejected = holm([result.raw_p_value for result in calibrations], config.alpha)
    analysis_by_period = {analysis.period_id: analysis for analysis in analyses}
    calibration_rows: list[dict[str, object]] = []
    inconsistent = list(individual_findings)
    for result, adjusted_p, reject in zip(calibrations, adjusted, rejected, strict=True):
        analysis = analysis_by_period[result.period_id]
        practical = _practical_flag(analysis, result.test_family, config)
        meaningful = bool(reject and practical)
        if meaningful:
            inconsistent.append(f"{result.period_id}:{result.test_family}")
        calibration_rows.append(
            {
                "period_id": result.period_id,
                "test_family": result.test_family,
                "observed_statistic": result.observed_statistic,
                "simulation_count": result.simulation_count,
                "period_seed": seeds[
                    [item.period_id for item in histories].index(result.period_id)
                ],
                "exceedances": result.exceedances,
                "raw_p_value": result.raw_p_value,
                "holm_adjusted_p_value": adjusted_p,
                "raw_significant": result.raw_p_value < config.alpha,
                "corrected_significant": reject,
                "effect_size": analysis.effect_sizes[result.test_family],
                "practical_effect": practical,
                "meaningful_deviation": meaningful,
                "simulated_percentile": result.simulated_percentile,
                "null_mean": result.null_mean,
                "null_standard_deviation": result.null_standard_deviation,
                "null_quantile_95": result.null_quantile_95,
                "null_quantile_99": result.null_quantile_99,
            }
        )
    raw_significant += sum(bool(row["raw_significant"]) for row in calibration_rows)
    corrected_significant += sum(bool(row["corrected_significant"]) for row in calibration_rows)
    omnibus_raw_significant = raw_significant - individual_raw_significant
    omnibus_corrected_significant = corrected_significant - individual_corrected_significant

    multiple_testing_rows: list[dict[str, object]] = []
    for table_name in (
        "number_frequencies",
        "extra_number_frequencies",
        "pair_statistics",
    ):
        for row in tables[table_name]:
            multiple_testing_rows.append(
                {
                    "family": row["multiple_testing_family"],
                    "period_id": row["period_id"],
                    "hypothesis": (
                        f"number={row['number']}"
                        if "number" in row
                        else f"pair={row['first_number']}-{row['second_number']}"
                    ),
                    "raw_p_value": row["raw_p_value"],
                    "adjusted_p_value": row["adjusted_p_value"],
                    "correction_method": row["correction_method"],
                    "corrected_significant": row["corrected_significant"],
                    "practical_effect": row["practical_effect"],
                    "meaningful_deviation": row["meaningful_deviation"],
                }
            )
    for row in calibration_rows:
        multiple_testing_rows.append(
            {
                "family": "period-level omnibus tests",
                "period_id": row["period_id"],
                "hypothesis": row["test_family"],
                "raw_p_value": row["raw_p_value"],
                "adjusted_p_value": row["holm_adjusted_p_value"],
                "correction_method": "holm",
                "corrected_significant": row["corrected_significant"],
                "practical_effect": row["practical_effect"],
                "meaningful_deviation": row["meaningful_deviation"],
            }
        )

    period_rows = [
        {
            "period_id": analysis.period_id,
            "pool_size": analysis.pool_size,
            "draw_count": analysis.draw_count,
            **analysis.descriptive,
        }
        for analysis in analyses
    ]
    output_directory = project_root / "reports" / "generated" / "phase5"
    output_directory.mkdir(parents=True, exist_ok=True)
    tables["excluded_draws"] = excluded_rows
    tables["period_summary"] = period_rows
    tables["simulation_calibration"] = calibration_rows
    tables["multiple_testing"] = multiple_testing_rows
    output_paths: list[Path] = []
    for name, rows in tables.items():
        path = output_directory / f"{name}.csv"
        _write_csv(path, rows)
        output_paths.append(path)

    individual_hypotheses = (
        len(tables["number_frequencies"])
        + len(tables["extra_number_frequencies"])
        + len(tables["pair_statistics"])
    )
    omnibus_hypotheses = len(calibration_rows)
    summary: dict[str, object] = {
        "included_draws": sum(history.draw_count for history in histories),
        "excluded_draws": len(excluded_rows),
        "total_completed_development_draws": total_completed,
        "individual_hypotheses": individual_hypotheses,
        "omnibus_hypotheses": omnibus_hypotheses,
        "total_confirmatory_hypotheses": individual_hypotheses + omnibus_hypotheses,
        "raw_significant": raw_significant,
        "corrected_significant": corrected_significant,
        "individual_raw_significant": individual_raw_significant,
        "individual_corrected_significant": individual_corrected_significant,
        "omnibus_raw_significant": omnibus_raw_significant,
        "omnibus_corrected_significant": omnibus_corrected_significant,
        "meaningful_deviations": inconsistent,
        "predictive_evidence": False,
        "exploratory_findings": [],
    }
    report_path = project_root / "reports" / "generated" / "randomness_analysis.md"
    write_randomness_report(
        report_path=report_path,
        config=config,
        analyses=analyses,
        calibration_rows=calibration_rows,
        tables=tables,
        summary=summary,
        integrity=integrity,
    )
    output_paths.append(report_path)

    manifest: dict[str, object] = {
        "schema_version": "1",
        "analysis_version": config.analysis_version,
        "protocol_version": config.protocol_version,
        "protocol_sha256": _sha256(protocol_path),
        "configuration_sha256": _sha256(config_path),
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "canonical_table_sha256": integrity["canonical_table_sha256"],
        "phase4_baseline_commit": config.baseline_commit,
        "git_head": _git_head(project_root),
        "phase5_code_sha256": _phase5_code_hash(project_root),
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "root_seed": actual_seed,
        "period_seeds": {
            history.period_id: period_seed
            for history, period_seed in zip(histories, seeds, strict=True)
        },
        "simulations_per_period": actual_simulations,
        "multiple_testing": config.corrections,
        "alpha": config.alpha,
        "fdr_q": config.fdr_q,
        "periods": period_rows,
        "excluded_draw_count": len(excluded_rows),
        "holdout_state": integrity["holdout_state"],
        "holdout_entry_count": integrity["holdout_entry_count"],
        "summary": summary,
        "output_sha256": {
            path.relative_to(project_root).as_posix(): _sha256(path) for path in output_paths
        },
    }
    manifest["manifest_sha256"] = hashlib.sha256(_json_bytes(manifest)).hexdigest()
    manifest_path = project_root / "reports" / "generated" / "phase5_analysis_manifest.json"
    manifest_path.write_bytes(_json_bytes(manifest))
    return AnalysisRunResult(
        report_path=report_path,
        manifest_path=manifest_path,
        output_directory=output_directory,
        included_draws=cast(int, summary["included_draws"]),
        excluded_draws=len(excluded_rows),
        individual_hypotheses=individual_hypotheses,
        omnibus_hypotheses=omnibus_hypotheses,
        raw_significant=raw_significant,
        corrected_significant=corrected_significant,
        inconsistent_findings=tuple(inconsistent),
    )
