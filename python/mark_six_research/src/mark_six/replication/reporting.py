"""Deterministic reporting for the one-time Phase 7 replication."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from mark_six.replication.models import ReplicationConfig
from mark_six.replication.reserve import ReserveOpeningEvent


def _number(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def write_replication_report(
    *,
    report_path: Path,
    config: ReplicationConfig,
    integrity: dict[str, object],
    opening: ReserveOpeningEvent,
    summary_rows: list[dict[str, object]],
    inference_rows: list[dict[str, object]],
    simulation_rows: list[dict[str, object]],
    stability_rows: list[dict[str, object]],
    comparison_rows: list[dict[str, object]],
    criteria_rows: list[dict[str, object]],
    selected_best: str,
    phase6_conclusion_replicated: bool,
) -> None:
    """Write the fixed confirmatory report from computed result tables."""

    summaries = {str(row["model"]): row for row in summary_rows}
    inference = {str(row["model"]): row for row in inference_rows}
    blocks: dict[str, list[dict[str, object]]] = {}
    for row in stability_rows:
        blocks.setdefault(str(row["model"]), []).append(row)
    criteria = {str(row["model"]): row for row in criteria_rows}
    family = next(row for row in simulation_rows if row["scope"] == "family_selected_best")
    successful = [name for name, row in criteria.items() if bool(row["all_criteria_pass"])]
    corrected_rejections = sum(bool(row["holm_rejected"]) for row in inference_rows)
    uniform = summaries["uniform"]
    gap = summaries["gap_due"]
    rolling = summaries["rolling_frequency_250"]
    gap_hits_replicated = cast(float, gap["mean_top_six_hits"]) > cast(
        float, uniform["mean_top_six_hits"]
    )
    rolling_rank_replicated = cast(float, rolling["mean_observed_rank"]) < cast(
        float, uniform["mean_observed_rank"]
    )
    any_positive = any(
        cast(float, row["mean_log_score_difference_nats"]) > 0.0
        for row in summary_rows
        if row["model"] != "uniform"
    )
    conclusion = (
        "Phase 6's negative predictive conclusion replicated independently: every frozen "
        "non-uniform model again scored no better than uniform on the primary metric."
        if phase6_conclusion_replicated
        else "Phase 6's uniformly negative direction did not fully replicate, but no model is "
        "validated unless it passes every preregistered Phase 7 criterion."
    )
    lines = [
        "# Phase 7 Independent Historical Replication",
        "",
        f"**Protocol:** `{config.protocol_version}`  ",
        f"**Dataset:** `{config.dataset_id}`  ",
        f"**Reserve:** `{config.reserve.first_draw_id}` through `{config.reserve.final_draw_id}` "
        f"({config.reserve.draw_count} draws)  ",
        f"**Controlled opening:** `{opening.opened_at.isoformat()}`",
        "",
        "## Executive conclusion",
        "",
        conclusion,
        "",
        f"The selected-best Phase 7 model was `{selected_best}`. Models meeting every registered "
        f"success criterion: {', '.join(f'`{name}`' for name in successful) or 'none'}. "
        f"There were {corrected_rejections} Holm-corrected rejections, and the selected-best "
        f"family-wide fair-history p-value was {_number(family['simulation_p_value'])}.",
        "",
        "A positive secondary metric cannot rescue a failed primary result. The reserve has now "
        "been consumed once for this confirmatory analysis and must not be reused to develop or "
        "tune models. The prospective holdout remains sealed.",
        "",
        "## Integrity and opening boundary",
        "",
        f"- Approved Phase 6 commit: `{config.baseline_commit}`.",
        f"- Dataset manifest and seven canonical tables: verified "
        f"(`{integrity['dataset_manifest_sha256']}`).",
        f"- Retained source snapshots: {integrity['raw_snapshots']} verified with "
        f"{integrity['raw_integrity_failures']} failures.",
        "- Phase 5 analysis manifest: "
        f"`{cast(dict[str, object], integrity['phase5'])['manifest_sha256']}`.",
        "- Phase 6 analysis manifest: "
        f"`{cast(dict[str, object], integrity['phase6'])['manifest_sha256']}`.",
        f"- Metadata-only reserve manifest: `{config.reserve_manifest_sha256}`; outcomes stored in "
        "manifest: no.",
        f"- Prospective holdout: `{integrity['holdout_state']}` with "
        f"{integrity['holdout_entry_count']} entries; accessed: no.",
        f"- Opening source: `{opening.source_table}`; exactly "
        f"{opening.reserve_draw_count} registered "
        "main-number outcomes were joined.",
        "- Each forecast and its hash were constructed from prior completed draws before its "
        "target "
        "was scored and added to state.",
        "",
        "## Frozen primary and secondary results",
        "",
        f"Uniform whole-set mean log score: {_number(uniform['mean_whole_set_log_score_nats'])} "
        "nats/draw.",
        "",
        "| Model | Mean log score | Mean vs uniform | Cumulative vs uniform | 95% block interval | "
        "Raw p | Holm p | Brier skill | Top-six hits | Winner rank | ECE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in config.models:
        row = summaries[model.name]
        if model.kind == "uniform":
            interval = raw_p = holm_p = "baseline"
        else:
            test = inference[model.name]
            interval = (
                f"[{_number(test['bootstrap_lower_95'])}, {_number(test['bootstrap_upper_95'])}]"
            )
            raw_p = _number(test["raw_one_sided_p_value"])
            holm_p = _number(test["holm_adjusted_p_value"])
        lines.append(
            f"| `{model.name}` | {_number(row['mean_whole_set_log_score_nats'])} | "
            f"{_number(row['mean_log_score_difference_nats'])} | "
            f"{_number(row['total_log_score_difference_nats'])} | {interval} | {raw_p} | "
            f"{holm_p} | {_number(row['brier_skill_vs_uniform'])} | "
            f"{_number(row['mean_top_six_hits'])} | {_number(row['mean_observed_rank'])} | "
            f"{_number(row['calibration_ece'])} |"
        )
    lines.extend(
        [
            "",
            "## Preregistered decision",
            "",
            "| Model | Practical effect | Favorable CI | Holm | Family-wide | Calibration | "
            "Stability | All |",
            "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]
    )
    for model in config.models[1:]:
        row = criteria[model.name]
        cells = [
            row["effect_pass"],
            row["confidence_interval_pass"],
            row["holm_pass"],
            row["family_wide_pass"],
            row["calibration_pass"],
            row["stability_pass"],
            row["all_criteria_pass"],
        ]
        lines.append(
            f"| `{model.name}` | "
            + " | ".join("yes" if bool(value) else "no" for value in cells)
            + " |"
        )
    lines.extend(
        [
            "",
            "## Four fixed chronological blocks",
            "",
            "Every block contains exactly 169 reserve draws; boundaries were fixed before opening.",
            "",
            "| Model | Block 1 | Block 2 | Block 3 | Block 4 | Nonnegative blocks |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for model in config.models:
        model_blocks = sorted(blocks[model.name], key=lambda row: cast(int, row["block"]))
        values = [_number(row["mean_log_score_difference_nats"]) for row in model_blocks]
        lines.append(
            f"| `{model.name}` | {' | '.join(values)} | "
            f"{summaries[model.name]['nonnegative_stability_blocks']}/4 |"
        )
    lines.extend(
        [
            "",
            "## Registered Phase 6 secondary observations",
            "",
            f"- Gap due top-six hits: {_number(gap['mean_top_six_hits'])} versus uniform "
            f"{_number(uniform['mean_top_six_hits'])}; observation replicated: "
            f"{'yes' if gap_hits_replicated else 'no'}.",
            f"- Rolling-250 mean winner rank: {_number(rolling['mean_observed_rank'])} versus "
            f"uniform {_number(uniform['mean_observed_rank'])}; observation replicated: "
            f"{'yes' if rolling_rank_replicated else 'no'}.",
            "",
            "These checks remain secondary and have no special primary status.",
            "",
            "## Phase 6 versus Phase 7",
            "",
            "| Model | Phase 6 mean vs uniform | Phase 7 mean vs uniform | Same direction | "
            "Phase 6 Brier skill | Phase 7 Brier skill | Phase 6 top-six | Phase 7 top-six | "
            "Phase 6 rank | Phase 7 rank | Phase 6 ECE | Phase 7 ECE |",
            "|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in comparison_rows:
        lines.append(
            f"| `{row['model']}` | {_number(row['phase6_mean_log_improvement_nats'])} | "
            f"{_number(row['phase7_mean_log_improvement_nats'])} | "
            f"{'yes' if row['direction_consistent'] else 'no'} | "
            f"{_number(row['phase6_brier_skill'])} | {_number(row['phase7_brier_skill'])} | "
            f"{_number(row['phase6_mean_top_six_hits'])} | "
            f"{_number(row['phase7_mean_top_six_hits'])} | "
            f"{_number(row['phase6_mean_observed_rank'])} | "
            f"{_number(row['phase7_mean_observed_rank'])} | "
            f"{_number(row['phase6_calibration_ece'])} | "
            f"{_number(row['phase7_calibration_ece'])} |"
        )
    lines.extend(
        [
            "",
            "Phase 6 and Phase 7 were assessed independently and were not pooled for the "
            "confirmatory conclusion.",
            "",
            "## Interpretation and next boundary",
            "",
            "At least one non-uniform primary mean was positive: "
            f"{'yes' if any_positive else 'no'}. "
            "Any positive Phase 7 direction after a negative Phase 6 result is conflicting "
            "evidence, "
            "not automatic validation, unless every frozen criterion is satisfied.",
            "",
            "No new reserve-derived model, parameter, window, ensemble, pair hypothesis, machine-"
            "learning system, ticket strategy, or financial analysis was created. "
            "Historical-number "
            "prediction research should stop at this registered family after a negative or failed "
            "replication. The prospective holdout must remain untouched unless a separately "
            "approved, "
            "fully frozen Phase 8 protocol authorizes its eventual role.",
            "",
            "## Reproduction",
            "",
            "Run `mark-six replicate run`, then `mark-six replicate verify`. Use `mark-six "
            "replicate compare` for the independent Phase 6/Phase 7 comparison and `mark-six "
            "replicate report` "
            "to locate generated artifacts. Generated outputs are policy-ignored.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
