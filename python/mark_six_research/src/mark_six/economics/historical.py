"""Rule-aware, time-state-separated historical economic tables."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import cast

import duckdb
import numpy as np

from mark_six.economics.expected_value import fixed_prize_breakdown
from mark_six.mathematics.combinatorics import prize_outcome_odds


def _plain(value: object) -> object:
    if isinstance(value, (date, Decimal)):
        return value.isoformat() if isinstance(value, date) else float(value)
    return value


def load_historical_economics(
    database_path: Path, *, start_date: date, end_date: date
) -> list[dict[str, object]]:
    """Load eligible current-rule economics without crossing the development cutoff."""

    if start_date < date(2024, 5, 21):
        raise ValueError("exact Phase 8 accounting starts with the current-rule interval")
    if end_date > date(2026, 9, 12):
        raise ValueError("Phase 8 may not query after the approved development dataset")
    query = """
        SELECT
          d.draw_id, d.draw_number, d.draw_date, d.rule_version_id,
          d.turnover_hkd_cents, d.unit_stake_hkd_cents,
          d.reported_jackpot_hkd_cents,
          d.estimated_first_prize_hkd_cents,
          d.reported_derived_first_prize_hkd_cents,
          d.snowball_code, d.snowball_name_en, d.is_special_draw,
          max(CASE WHEN p.division_code='division_1' THEN p.winning_units END)
            AS division_1_winning_units,
          max(CASE WHEN p.division_code='division_1'
                   THEN p.prize_per_winning_unit_hkd_cents END)
            AS division_1_dividend_hkd_cents,
          max(CASE WHEN p.division_code='division_2' THEN p.winning_units END)
            AS division_2_winning_units,
          max(CASE WHEN p.division_code='division_2'
                   THEN p.prize_per_winning_unit_hkd_cents END)
            AS division_2_dividend_hkd_cents,
          max(CASE WHEN p.division_code='division_3' THEN p.winning_units END)
            AS division_3_winning_units,
          max(CASE WHEN p.division_code='division_3'
                   THEN p.prize_per_winning_unit_hkd_cents END)
            AS division_3_dividend_hkd_cents,
          sum(CASE WHEN p.division_code IN
                  ('division_4','division_5','division_6','division_7')
                   THEN p.total_division_payout_hkd_cents ELSE 0 END)
            AS realized_fixed_liability_hkd_cents
        FROM draws d
        LEFT JOIN prize_results p USING(draw_id)
        WHERE d.draw_date BETWEEN ? AND ?
          AND d.rule_version_id = 'hkjc_mark_six_2024_05_21'
        GROUP BY ALL
        ORDER BY d.draw_date, d.draw_id
    """
    with duckdb.connect(str(database_path), read_only=True) as connection:
        cursor = connection.execute(query, [start_date, end_date])
        names = [column[0] for column in cursor.description]
        raw_rows = cursor.fetchall()
    probabilities = {
        division: prize_outcome_odds(49, 7)[division - 1].probability for division in range(1, 8)
    }
    expected_fixed = sum(fixed_prize_breakdown().values(), Fraction())
    rows: list[dict[str, object]] = []
    for values in raw_rows:
        row = {name: _plain(value) for name, value in zip(names, values, strict=True)}
        turnover = row["turnover_hkd_cents"]
        stake = row["unit_stake_hkd_cents"]
        row["pre_draw_values_verified"] = False
        row["source_time_state"] = "completed_draw_record_publication_time_unproven"
        row["derived_prize_fund_hkd_cents"] = (
            int(cast(int, turnover) * 54 // 100) if turnover is not None else None
        )
        row["derived_expected_fixed_liability_hkd_cents"] = (
            float(Fraction(cast(int, turnover), cast(int, stake)) * expected_fixed)
            if turnover is not None and stake is not None
            else None
        )
        ex_post = 0.0
        complete = True
        for division in range(1, 8):
            field = f"division_{division}_dividend_hkd_cents" if division <= 3 else None
            if field is None:
                dividend = {4: 960_000, 5: 64_000, 6: 32_000, 7: 4_000}[division]
            else:
                value = row[field]
                if value is None:
                    complete = False
                    break
                dividend = cast(int, value)
            ex_post += float(probabilities[division]) * dividend
        row["derived_ex_post_expected_payout_hkd_cents"] = ex_post if complete else None
        row["derived_ex_post_only"] = True
        rows.append(row)
    return rows


def turnover_analysis_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return descriptive correlations/regressions with no causal interpretation."""

    results: list[dict[str, object]] = []
    for field in (
        "reported_jackpot_hkd_cents",
        "reported_derived_first_prize_hkd_cents",
    ):
        pairs = [
            (float(cast(int, row["turnover_hkd_cents"])), float(cast(int, row[field])))
            for row in rows
            if row["turnover_hkd_cents"] is not None and row[field] is not None
        ]
        if len(pairs) < 3:
            results.append(
                {
                    "field": field,
                    "observations": len(pairs),
                    "correlation": None,
                    "slope": None,
                    "r_squared": None,
                }
            )
            continue
        x = np.asarray([pair[1] for pair in pairs], dtype=np.float64)
        y = np.asarray([pair[0] for pair in pairs], dtype=np.float64)
        slope, intercept = np.polyfit(x, y, 1)
        fitted = slope * x + intercept
        residual = float(np.sum((y - fitted) ** 2))
        total = float(np.sum((y - np.mean(y)) ** 2))
        results.append(
            {
                "field": field,
                "observations": len(pairs),
                "correlation": float(np.corrcoef(x, y)[0, 1]),
                "slope_turnover_per_field_hkd_cent": float(slope),
                "r_squared": 1.0 - residual / total if total else None,
                "interpretation": "descriptive_completed_draw_association_not_causal",
            }
        )
    return results


def normal_special_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Compare current-rule normal and source-designated special draws descriptively."""

    result: list[dict[str, object]] = []
    for special in (False, True):
        selected = [row for row in rows if bool(row["is_special_draw"]) is special]
        turnover = np.asarray(
            [
                float(cast(int, row["turnover_hkd_cents"])) / 100
                for row in selected
                if row["turnover_hkd_cents"] is not None
            ],
            dtype=np.float64,
        )
        winner_units = np.asarray(
            [
                float(cast(float, row["division_1_winning_units"]))
                for row in selected
                if row["division_1_winning_units"] is not None
            ],
            dtype=np.float64,
        )
        result.append(
            {
                "draw_type": "special" if special else "normal",
                "draws": len(selected),
                "turnover_observations": len(turnover),
                "mean_turnover_hkd": float(np.mean(turnover)) if len(turnover) else None,
                "median_turnover_hkd": float(np.median(turnover)) if len(turnover) else None,
                "mean_first_division_winning_units_ex_post": (
                    float(np.mean(winner_units)) if len(winner_units) else None
                ),
                "interpretation": "rule_aware_ex_post_descriptive_not_causal",
            }
        )
    return result


def field_semantics_rows() -> list[dict[str, object]]:
    """Record the bounded interpretation reached from official field reconciliation."""

    return [
        {
            "source_field": "jackpot",
            "observed_behavior": (
                "26/096 equals the HKD185m carried Snowball in the dated official notice; "
                "values vary on normal draws"
            ),
            "official_definition_found": (
                "draw-specific reconciliation only; no invariant GraphQL definition found"
            ),
            "confidence": "high_for_26/096_low_across_all_draws",
            "safe_for_economic_modeling": "source_reported_post_draw_or_dated_draw_specific_only",
        },
        {
            "source_field": "derivedFirstPrizeDiv",
            "observed_behavior": (
                "26/096 equals the officially advertised HKD228m estimated First Division "
                "fund and often equals the HKD8m minimum"
            ),
            "official_definition_found": (
                "draw-specific reconciliation; publication timing absent from completed record"
            ),
            "confidence": "high_for_26/096_medium_current_interval",
            "safe_for_economic_modeling": (
                "ex_post_descriptive; pre_draw_only_with_separate_dated_notice"
            ),
        },
        {
            "source_field": "estimatedPrize",
            "observed_behavior": "null in all completed canonical samples",
            "official_definition_found": (
                "label suggests estimate but no populated completed-draw evidence"
            ),
            "confidence": "high_that_canonical_completed_values_are_missing",
            "safe_for_economic_modeling": "no",
        },
        {
            "source_field": "snowballCode/snowballName",
            "observed_behavior": (
                "identifies official special Snowball designations including 26/096"
            ),
            "official_definition_found": "official notice corroborates named special draw",
            "confidence": "high_for_designation_not_amount",
            "safe_for_economic_modeling": "classification_only_unless_amount_has_separate_notice",
        },
    ]
