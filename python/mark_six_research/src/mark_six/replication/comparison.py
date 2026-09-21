"""Independent Phase 6 versus Phase 7 model comparison."""

from __future__ import annotations

from typing import cast


def compare_phase6_phase7(
    phase6_rows: list[dict[str, object]], phase7_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Align frozen model summaries without pooling their scores."""

    phase6 = {str(row["model"]): row for row in phase6_rows}
    phase7 = {str(row["model"]): row for row in phase7_rows}
    if phase6.keys() != phase7.keys():
        raise ValueError("Phase 6 and Phase 7 model identities differ")
    rows: list[dict[str, object]] = []
    for name, earlier in phase6.items():
        later = phase7[name]
        phase6_delta = cast(float, earlier["mean_log_score_difference_nats"])
        phase7_delta = cast(float, later["mean_log_score_difference_nats"])
        rows.append(
            {
                "model": name,
                "phase6_mean_log_improvement_nats": phase6_delta,
                "phase7_mean_log_improvement_nats": phase7_delta,
                "direction_consistent": (phase6_delta >= 0) == (phase7_delta >= 0),
                "phase6_brier_skill": earlier["brier_skill_vs_uniform"],
                "phase7_brier_skill": later["brier_skill_vs_uniform"],
                "phase6_mean_top_six_hits": earlier["mean_top_six_hits"],
                "phase7_mean_top_six_hits": later["mean_top_six_hits"],
                "phase6_mean_observed_rank": earlier["mean_observed_rank"],
                "phase7_mean_observed_rank": later["mean_observed_rank"],
                "phase6_calibration_ece": earlier["calibration_ece"],
                "phase7_calibration_ece": later["calibration_ece"],
            }
        )
    return rows
