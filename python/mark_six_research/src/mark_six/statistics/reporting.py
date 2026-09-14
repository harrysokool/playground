"""Generated Markdown reporting for the preregistered Phase 5 analysis."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import cast

from mark_six.statistics.models import AnalysisConfig, PeriodAnalysis

FAMILY_LABELS = {
    "main_frequency": "Main-number frequencies",
    "main_frequency_max": "Main-number maximum deviation",
    "extra_frequency": "Extra Number frequencies",
    "extra_frequency_max": "Extra Number maximum deviation",
    "odd_even": "Odd/even composition",
    "low_high": "Low/high composition",
    "sum_distribution": "Winning-number sums",
    "consecutive": "Within-draw consecutive behavior",
    "draw_overlap": "Consecutive-draw overlap",
    "gaps": "Appearance gaps",
    "pairs": "Pair frequencies",
    "triples": "Triple maximum",
    "serial_dependence": "Serial dependence",
    "temporal_stability": "Temporal stability",
}


def _format(value: object, digits: int = 6) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def _extreme(rows: list[dict[str, object]], field: str) -> dict[str, object]:
    return max(rows, key=lambda row: abs(cast(float, row[field])))


def write_randomness_report(
    *,
    report_path: Path,
    config: AnalysisConfig,
    analyses: list[PeriodAnalysis],
    calibration_rows: list[dict[str, object]],
    tables: dict[str, list[dict[str, object]]],
    summary: dict[str, object],
    integrity: dict[str, object],
) -> None:
    """Write the main report entirely from computed results."""

    calibration = {
        (str(row["period_id"]), str(row["test_family"])): row for row in calibration_rows
    }
    corrected = [row for row in calibration_rows if bool(row["corrected_significant"])]
    meaningful_omnibus = [row for row in calibration_rows if bool(row["meaningful_deviation"])]
    raw_only_omnibus = [
        row
        for row in calibration_rows
        if bool(row["raw_significant"]) and not bool(row["corrected_significant"])
    ]
    individual_rows = [
        row
        for name in ("number_frequencies", "extra_number_frequencies", "pair_statistics")
        for row in tables[name]
    ]
    corrected_individual = [row for row in individual_rows if bool(row["corrected_significant"])]
    meaningful_individual = [row for row in individual_rows if bool(row["meaningful_deviation"])]
    if meaningful_omnibus:
        conclusion = (
            "At least one preregistered omnibus result both survived Holm correction and crossed its "
            "predeclared practical-effect threshold. This is evidence of model tension requiring source, "
            "boundary, and mechanism investigation; it is not proof of manipulation or predictability."
        )
    elif meaningful_individual:
        conclusion = (
            "One preregistered individual comparison survived its BH correction and crossed the "
            "predeclared effect threshold, but no period-level omnibus test survived Holm correction. "
            "The matched-history family maximum shows that an extreme at least this large is not rare "
            "across the full search space. This isolated deviation warrants disclosure, not a claim of "
            "system-wide unfairness, manipulation, or predictability."
        )
    else:
        conclusion = (
            "No preregistered result both survived its correction and crossed its predeclared "
            "practical-effect threshold. The analysed record therefore provides no practically "
            "meaningful evidence inconsistent with the fair-draw null at the registered thresholds."
        )
    lines = [
        "# Phase 5 Randomness Analysis",
        "",
        f"**Protocol:** `{config.protocol_version}`  ",
        f"**Dataset:** `{config.dataset_id}`  ",
        f"**Dataset manifest SHA-256:** `{config.dataset_manifest_sha256}`  ",
        f"**Phase 4 baseline:** `{config.baseline_commit}`  ",
        f"**Simulation:** {config.simulations_per_period:,} matched fair histories per period; root seed `{config.root_seed}`",
        "",
        "## Executive conclusion",
        "",
        conclusion,
        "",
        "This analysis cannot prove that the lottery is random. A significant deviation would not by "
        "itself prove manipulation, and no high, low, hot, cold, paired, or overdue number becomes more "
        "likely in the next independent fair draw. No result in this report supplies evidence of useful "
        "future prediction.",
        "",
        "## Integrity and scope",
        "",
        f"- Canonical dataset and all seven Parquet hashes: verified (`{integrity['dataset_manifest_sha256']}`).",
        f"- Prospective holdout: `{integrity['holdout_state']}` with {integrity['holdout_entry_count']} entries; no holdout outcomes were accessed.",
        f"- Included completed draws: {summary['included_draws']:,}.",
        f"- Excluded completed draws: {summary['excluded_draws']:,}; all are outside the fixed periods, including the unresolved 1996 pool transition.",
        "- Physical draw-order tests: out of scope because the source arrays are sorted display values and physical positions are null.",
        "- Draw schedule gaps: not imputed; tests are indexed by observed completed draws.",
        "",
        "## Rule-aware analysis periods",
        "",
        "| Period | Pool | Draws | Protocol interval |",
        "|---|---:|---:|---|",
    ]
    period_specs = {period.period_id: period for period in config.periods}
    for analysis in analyses:
        spec = period_specs[analysis.period_id]
        lines.append(
            f"| `{analysis.period_id}` | {analysis.pool_size} | {analysis.draw_count:,} | "
            f"{spec.start.isoformat()} to {spec.end.isoformat()} |"
        )

    lines.extend(
        [
            "",
            "## Multiplicity summary",
            "",
            f"- Individual hypotheses: {summary['individual_hypotheses']:,} (BH within the three frozen families).",
            f"- Period-level omnibus hypotheses: {summary['omnibus_hypotheses']:,} (Holm across all omnibus tests).",
            f"- Total confirmatory hypotheses: {summary['total_confirmatory_hypotheses']:,}.",
            f"- Raw findings with `p < {config.alpha}`: {summary['raw_significant']:,}.",
            f"- Findings surviving their registered correction: {summary['corrected_significant']:,}.",
            f"- BH-corrected individual findings: {len(corrected_individual):,}; practically meaningful individual deviations: {len(meaningful_individual):,}.",
            f"- Holm-corrected omnibus findings: {len(corrected):,}; practically meaningful corrected omnibus deviations: {len(meaningful_omnibus):,}.",
            "",
            "Raw p-values are never interpreted alone for the large number, pair, or omnibus families.",
            "",
            "## Confirmatory results",
            "",
            "The table reports the preregistered statistic, its percentile among matched fair histories, "
            "the simulation p-value, Holm-adjusted p-value, and the prespecified effect flag.",
            "",
            "| Test | Period | Statistic | Sim percentile | Raw p | Holm p | Practical | Corrected |",
            "|---|---|---:|---:|---:|---:|:---:|:---:|",
        ]
    )
    for family in FAMILY_LABELS:
        for analysis in analyses:
            row = calibration[(analysis.period_id, family)]
            lines.append(
                f"| {FAMILY_LABELS[family]} | `{analysis.period_id}` | "
                f"{_format(row['observed_statistic'])} | {_format(row['simulated_percentile'], 5)}% | "
                f"{_format(row['raw_p_value'], 5)} | {_format(row['holm_adjusted_p_value'], 5)} | "
                f"{'yes' if row['practical_effect'] else 'no'} | "
                f"{'yes' if row['corrected_significant'] else 'no'} |"
            )

    lines.extend(["", "### Corrected individual findings", ""])
    if not corrected_individual:
        lines.append("None.")
    for row in corrected_individual:
        if "first_number" in row:
            pair_calibration = calibration[(str(row["period_id"]), "pairs")]
            lines.append(
                f"- Pair {row['first_number']}-{row['second_number']} in `{row['period_id']}`: "
                f"observed {row['observed_count']} versus expected {_format(row['expected_count'])}; "
                f"z={_format(row['standardized_deviation'])}, relative deviation="
                f"{_format(100 * cast(float, row['relative_deviation']), 5)}%, raw p="
                f"{_format(row['raw_p_value'], 5)}, BH p={_format(row['adjusted_p_value'], 5)}. "
                f"The preregistered period-wide pair maximum had simulation p="
                f"{_format(pair_calibration['raw_p_value'], 5)} and Holm p="
                f"{_format(pair_calibration['holm_adjusted_p_value'], 5)}; it did not reject."
            )
        else:
            lines.append(
                f"- Number {row['number']} in `{row['period_id']}`: observed "
                f"{row['observed_count']} versus expected {_format(row['expected_count'])}; "
                f"z={_format(row['standardized_deviation'])}, BH p="
                f"{_format(row['adjusted_p_value'], 5)}."
            )

    lines.extend(["", "### Raw-only omnibus tail observations", ""])
    if not raw_only_omnibus:
        lines.append("None.")
    for row in raw_only_omnibus:
        lines.append(
            f"- {FAMILY_LABELS[str(row['test_family'])]} in `{row['period_id']}`: "
            f"simulation percentile {_format(row['simulated_percentile'], 5)}%, raw p="
            f"{_format(row['raw_p_value'], 5)}, Holm p="
            f"{_format(row['holm_adjusted_p_value'], 5)}. This did not survive correction."
        )

    lines.extend(["", "## Effect-size and distribution details", ""])
    for analysis in analyses:
        main_rows = [
            row for row in tables["number_frequencies"] if row["period_id"] == analysis.period_id
        ]
        extra_rows = [
            row
            for row in tables["extra_number_frequencies"]
            if row["period_id"] == analysis.period_id
        ]
        pair_rows = [
            row for row in tables["pair_statistics"] if row["period_id"] == analysis.period_id
        ]
        triple_rows = [
            row for row in tables["triple_statistics"] if row["period_id"] == analysis.period_id
        ]
        main = _extreme(main_rows, "standardized_deviation")
        extra = _extreme(extra_rows, "standardized_deviation")
        pair = _extreme(pair_rows, "standardized_deviation")
        triple = triple_rows[0]
        description = analysis.descriptive
        lines.extend(
            [
                f"### `{analysis.period_id}`",
                "",
                f"- Main-number maximum: number {main['number']}, observed {_format(main['observed_count'])} versus expected {_format(main['expected_count'])}, z={_format(main['standardized_deviation'])}, relative deviation={_format(100 * cast(float, main['relative_deviation']), 5)}%, BH p={_format(main['adjusted_p_value'], 5)}.",
                f"- Extra maximum: number {extra['number']}, observed {_format(extra['observed_count'])} versus expected {_format(extra['expected_count'])}, z={_format(extra['standardized_deviation'])}, relative deviation={_format(100 * cast(float, extra['relative_deviation']), 5)}%, BH p={_format(extra['adjusted_p_value'], 5)}.",
                f"- Sum: mean {_format(description['observed_sum_mean'])} versus {_format(description['expected_sum_mean'])}; variance {_format(description['observed_sum_variance'])} versus {_format(description['expected_sum_variance'])}; standardized mean shift d={_format(analysis.effect_sizes['sum_distribution'])}.",
                f"- Strongest pair: {pair['first_number']}-{pair['second_number']}, observed {_format(pair['observed_count'])} versus expected {_format(pair['expected_count'])}, z={_format(pair['standardized_deviation'])}, BH p={_format(pair['adjusted_p_value'], 5)}.",
                f"- Strongest triple (descriptive member of the simulated maximum): {triple['first_number']}-{triple['second_number']}-{triple['third_number']}, observed {_format(triple['observed_count'])} versus expected {_format(triple['expected_count'])}, z={_format(triple['standardized_deviation'])}.",
                f"- Largest completed-gap relative mean deviation: {_format(100 * cast(float, description['largest_gap_relative_deviation']), 5)}%. Largest absolute registered serial correlation: {_format(description['largest_serial_absolute_r'])}.",
                f"- Cramer's V: odd/even {_format(analysis.effect_sizes['odd_even'])}, low/high {_format(analysis.effect_sizes['low_high'])}, overlap {_format(analysis.effect_sizes['draw_overlap'])}, temporal stability {_format(analysis.effect_sizes['temporal_stability'])}.",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation by test family",
            "",
            "- **Number and Extra frequencies:** global distribution tests and individual exact binomial tests are reported separately. No individual number is interpreted without BH correction and effect size.",
            "- **Odd/even and low/high:** expectations are exact hypergeometric distributions, not binomial approximations. Low is fixed as `number <= floor(N/2)`.",
            "- **Sums:** the full discrete sum distribution is derived by dynamic programming; extreme individual sums are not treated as suspicious.",
            "- **Consecutive values:** the null explicitly permits adjacent values and runs. Human visual salience is not evidence of bias.",
            "- **Draw overlap:** comparisons remain within compatible pool periods and use the exact overlap law.",
            "- **Gaps:** completed inter-arrival times have null mean `N/6`. Under independent draws, a long absence never makes a number due.",
            "- **Pairs:** all 3,247 pair hypotheses share one BH family; period maxima are separately calibrated against fair histories.",
            "- **Triples:** power is weak because expected counts per triple are small. Only the preregistered maximum statistic is inferential; displayed triples are descriptive.",
            "- **Serial dependence:** the maximum covers number-wise lag one, sum lag one, and odd-count lag one, preventing selective reporting.",
            "- **Temporal stability:** only three fixed contiguous blocks per period are tested; no breakpoint or rolling-window search was performed.",
            "",
            "## Confirmatory and exploratory findings",
            "",
            f"Confirmatory meaningful deviations: {', '.join(cast(list[str], summary['meaningful_deviations'])) if summary['meaningful_deviations'] else 'none'}.",
            "",
            "Exploratory findings: none were added. The analysis did not create alternative windows, "
            "splits, lags, subperiods, or tests after inspecting results.",
            "",
            "## Limitations",
            "",
            "The archive begins with the populated coverage available from the approved source, not the "
            "start of Mark Six. The exact 1996 pool transition remains unresolved and those draws are "
            "excluded. Statistical tests cannot authenticate physical draw machinery, and source arrays "
            "do not provide physical ball order. Monte Carlo p-values have resolution "
            f"`1/{config.simulations_per_period + 1}`. Multiple tests are dependent, and correction reduces but does not eliminate "
            "the possibility of chance findings. Historical consistency cannot establish future fairness.",
            "",
            "## Prediction boundary",
            "",
            "No result provides evidence of useful prediction. Under the fair null, each future draw is "
            "independent of historical frequencies, pairs, gaps, sums, or compositions. Phase 5 contains "
            "no number-selection strategy, machine learning, signal construction, or backtest.",
            "",
            "## Reproducible outputs",
            "",
            "Supporting CSV tables are under `reports/generated/phase5/`. The manifest "
            "`reports/generated/phase5_analysis_manifest.json` records hashes, periods, seeds, simulation "
            "counts, corrections, and output hashes. All result files are generated by code and should "
            "not be edited manually.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
