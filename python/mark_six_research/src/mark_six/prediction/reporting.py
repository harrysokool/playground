"""Markdown reporting for the preregistered Phase 6 analysis."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import cast

from mark_six.prediction.models import PredictionConfig


def _format(value: object, digits: int = 6) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def replication_models_to_report(
    rows: list[dict[str, object]],
) -> set[tuple[str, str]]:
    """Select uniform and the best non-uniform candidate in every replication period."""

    periods = {str(row["period_id"]) for row in rows}
    selected = {(period_id, "uniform") for period_id in periods}
    for period_id in periods:
        alternatives = [
            row for row in rows if row["period_id"] == period_id and row["model"] != "uniform"
        ]
        if alternatives:
            best = max(
                alternatives,
                key=lambda row: cast(float, row["mean_log_score_difference_nats"]),
            )
            selected.add((period_id, str(best["model"])))
    return selected


def write_prediction_report(
    *,
    report_path: Path,
    config: PredictionConfig,
    integrity: dict[str, object],
    primary_summary: list[dict[str, object]],
    inference_rows: list[dict[str, object]],
    simulation_rows: list[dict[str, object]],
    criteria_rows: list[dict[str, object]],
    replication_summary: list[dict[str, object]],
    primary_signal: bool,
    best_model: str,
) -> None:
    """Write the full report from computed tables, including a guarded conclusion."""

    summaries = {str(row["model"]): row for row in primary_summary}
    inference = {str(row["model"]): row for row in inference_rows}
    family_row = next(row for row in simulation_rows if row["scope"] == "family_selected_best")
    if primary_signal:
        conclusion = (
            f"The selected candidate `{best_model}` met every preregistered statistical, practical, "
            "calibration, and stability criterion on the Phase 6 development split. This is a historical "
            "predictive-signal finding that requires untouched Phase 7 confirmation; it is not a profit, "
            "ticket, or manipulation claim."
        )
    else:
        conclusion = (
            "No candidate met all preregistered Phase 6 criteria. The accessible historical record "
            "therefore supplies no validated out-of-sample predictive improvement over uniform 6/49 "
            "forecasting at the frozen thresholds."
        )
    lines = [
        "# Phase 6 Predictive-Signal Analysis",
        "",
        f"**Protocol:** `{config.protocol_version}`  ",
        f"**Dataset:** `{config.dataset_id}`  ",
        f"**Dataset manifest SHA-256:** `{config.dataset_manifest_sha256}`  ",
        f"**Phase 5 baseline:** `{config.baseline_commit}`",
        "",
        "## Executive conclusion",
        "",
        conclusion,
        "",
        "All scores are probabilities of the complete unordered six-number main outcome. Extra Numbers, prizes, payouts, returns, ticket construction, Banker and Multiple entries are outside scope. The Phase 5 pair 2-26 was not used as a model or parameter.",
        "",
        "## Integrity and chronology",
        "",
        f"- Canonical dataset manifest and seven Parquet hashes: verified (`{integrity['dataset_manifest_sha256']}`).",
        f"- Retained raw snapshots: {integrity['raw_snapshots']} verified, {integrity['raw_integrity_failures']} failures.",
        f"- Prospective holdout: `{integrity['holdout_state']}` with {integrity['holdout_entry_count']} entries.",
        f"- Phase 7 historical reserve: `{integrity['reserve_state']}` with {integrity['reserve_entry_count']} metadata-only entries; outcomes included: no.",
        f"- Primary 6/49 population: {config.primary.population_draws:,}; Phase 6 accessible: {config.primary.phase6_draws:,}; warm-up: {config.primary.warmup_draws:,}; scored: {config.primary.scored_draws:,}.",
        "- Every target forecast was constructed from prior completed draws, hashed against its cutoff draw, scored, and only then used to update model state.",
        "",
        "## Frozen model family",
        "",
        "The uniform baseline and ten generic alternatives were registered before outcome scoring. Product weights are normalized exactly with the sixth elementary symmetric polynomial; marginals use exact polynomial division, not subset enumeration or Monte Carlo.",
        "",
        "| Model | Mean log improvement (nats/draw) | 95% block interval | Holm p | Brier skill | ECE | Nonnegative blocks | Minimum block |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in config.models:
        summary = summaries[model.name]
        if model.kind == "uniform":
            interval = "baseline"
            adjusted = "baseline"
        else:
            row = inference[model.name]
            interval = (
                f"[{_format(row['bootstrap_lower_95'])}, {_format(row['bootstrap_upper_95'])}]"
            )
            adjusted = _format(row["holm_adjusted_p_value"])
        lines.append(
            f"| `{model.name}` | {_format(summary['mean_log_score_difference_nats'])} | "
            f"{interval} | {adjusted} | {_format(summary['brier_skill_vs_uniform'])} | "
            f"{_format(summary['calibration_ece'])} | "
            f"{summary['nonnegative_stability_blocks']}/{config.stability_blocks} | "
            f"{_format(summary['minimum_stability_block_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Family-wide fair-process calibration",
            "",
            f"The complete adaptive process was rerun on {family_row['simulation_histories']:,} seeded fair histories. The observed selected-best model was `{family_row['model']}` with mean improvement {_format(family_row['observed_mean_log_improvement_nats'])} nats/draw. The fair-history maximum met or exceeded it {family_row['exceedances']} times, giving family-wide p={_format(family_row['simulation_p_value'])}.",
            "",
            "## Conjunctive decision criteria",
            "",
            "| Model | Effect | Holm | Family calibration | ECE | Stability | All criteria |",
            "|---|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]
    )
    for row in criteria_rows:
        lines.append(
            f"| `{row['model']}` | {'yes' if row['effect_pass'] else 'no'} | "
            f"{'yes' if row['holm_pass'] else 'no'} | "
            f"{'yes' if row['family_wide_pass'] else 'no'} | "
            f"{'yes' if row['calibration_pass'] else 'no'} | "
            f"{'yes' if row['stability_pass'] else 'no'} | "
            f"{'yes' if row['all_criteria_pass'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "Only the selected-best candidate can satisfy the family-calibrated primary rule. Secondary metrics cannot rescue a failed primary result.",
            "",
            "## Older-pool replication",
            "",
            "The frozen formulas were applied after primary completion to the 6/45 and 6/47 periods, each after 100 warm-up draws. Calendar year 1996 remains excluded.",
            "",
            "| Period | Pool | Model | Scored draws | Mean log improvement | Brier skill | ECE |",
            "|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    replication_selection = replication_models_to_report(replication_summary)
    for row in replication_summary:
        if (str(row["period_id"]), str(row["model"])) in replication_selection:
            lines.append(
                f"| `{row['period_id']}` | {row['pool_size']} | `{row['model']}` | "
                f"{row['scored_draws']} | {_format(row['mean_log_score_difference_nats'])} | "
                f"{_format(row['brier_skill_vs_uniform'])} | {_format(row['calibration_ece'])} |"
            )
    lines.extend(
        [
            "",
            "Replication is descriptive and does not change the primary decision.",
            "",
            "## Limitations",
            "",
            "A proper score can detect probabilistic improvement but does not establish a physical mechanism. The candidate family is deliberately small and fixed; absence of evidence is not proof that every conceivable dependency is absent. Conversely, trying more models after seeing these results would invalidate the registered family correction. The protected 676-draw historical reserve and prospective holdout remain unopened for later phases.",
            "",
            "## Reproduction",
            "",
            "Run `mark-six predict run`, then `mark-six predict verify`. Supporting forecast, calibration, inference, stability, simulation, and replication tables are under `reports/generated/phase6/`; project policy keeps generated analysis artifacts out of Git.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
