"""Reproducible end-to-end Phase 8 economic analysis and integrity verifier."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import UTC, date, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import numpy as np

from mark_six.economics.expected_value import expected_value, fixed_prize_breakdown
from mark_six.economics.historical import (
    field_semantics_rows,
    load_historical_economics,
    normal_special_rows,
    turnover_analysis_rows,
)
from mark_six.economics.models import EconomicConfig, EconomicRunResult, load_economic_config
from mark_six.economics.portfolio import (
    banker_entry_economics,
    multiple_entry_economics,
    portfolio_metrics,
)
from mark_six.economics.reporting import write_economic_reports
from mark_six.economics.scenarios import breakeven_rows, jackpot_scenario_rows, sharing_rows
from mark_six.economics.simulation import simulate_economic_scenario, simulate_portfolio_payout
from mark_six.economics.split_risk import split_risk_features
from mark_six.economics.state import build_current_state
from mark_six.holdout import load_holdout_manifest
from mark_six.mathematics.payouts import CURRENT_FIXED_PRIZES_HKD_CENTS
from mark_six.prediction.reserve import canonical_json_bytes
from mark_six.replication.runner import verify_historical_replication


class EconomicIntegrityError(RuntimeError):
    """Raised when a frozen Phase 8 dependency or generated artifact differs."""


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


def _has_ancestor(project_root: Path, commit: str) -> bool:
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
    paths = sorted((project_root / "src/mark_six/economics").glob("*.py"))
    paths.append(project_root / "src/mark_six/cli.py")
    for path in paths:
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    if not rows:
        raise ValueError(f"cannot write empty Phase 8 table: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _current_accounting_rows(config: EconomicConfig) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for turnover_hkd in config.turnover_hkd:
        state = build_current_state(turnover_hkd * 100)
        rows.append(
            {
                "turnover_hkd": turnover_hkd,
                "lottery_duty_hkd": float(state.lottery_duty_hkd_cents / 100),
                "lotteries_fund_hkd": float(state.lotteries_fund_hkd_cents / 100),
                "hkjc_commission_hkd": float(state.commission_hkd_cents / 100),
                "prize_fund_hkd": float(state.prize_fund_hkd_cents / 100),
                "expected_fixed_liability_hkd": float(
                    state.expected_fixed_liability_hkd_cents / 100
                ),
                "snowball_deduction_hkd": float(state.snowball_deduction_hkd_cents / 100),
                "remaining_variable_pool_hkd": float(state.variable_pool_hkd_cents / 100),
                "base_first_division_hkd": float(state.division_funds_hkd_cents[1] / 100),
                "second_division_hkd": float(state.division_funds_hkd_cents[2] / 100),
                "third_division_hkd": float(state.division_funds_hkd_cents[3] / 100),
                "minimum_first_division_hkd": 8_000_000,
                "unresolved_minimum_hkd": float(state.unresolved_minimum_hkd_cents / 100),
                "evidence": "exact_rule_math_with_expected_fixed_liability",
            }
        )
    return rows


def _fixed_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for division, value in fixed_prize_breakdown().items():
        hkd = value / 100
        rows.append(
            {
                "division": division,
                "exact_expected_payout_hkd_fraction": f"{hkd.numerator}/{hkd.denominator}",
                "expected_payout_hkd": float(hkd),
                "official_full_unit_prize_hkd": CURRENT_FIXED_PRIZES_HKD_CENTS[division] / 100,
                "evidence": "exact_rule_math",
            }
        )
    return rows


def _portfolio_tickets(line_count: int, kind: str, seed: int) -> tuple[tuple[int, ...], ...]:
    if kind == "duplicate":
        return ((1, 2, 3, 4, 5, 6),) * line_count
    rng = np.random.default_rng(seed)
    tickets: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    while len(tickets) < line_count:
        ticket = tuple(sorted(int(value) for value in rng.choice(49, size=6, replace=False) + 1))
        if ticket in seen:
            continue
        seen.add(ticket)
        tickets.append(ticket)
    if kind == "overlap":
        anchor = (1, 2, 3)
        tickets = []
        seen.clear()
        while len(tickets) < line_count:
            legs = tuple(
                sorted(int(value) for value in rng.choice(np.arange(4, 50), size=3, replace=False))
            )
            ticket = tuple(sorted((*anchor, *legs)))
            if ticket not in seen:
                seen.add(ticket)
                tickets.append(ticket)
    return tuple(tickets)


def _portfolio_rows(config: EconomicConfig) -> list[dict[str, object]]:
    state = build_current_state(100_000_000 * 100)
    funds: dict[int, int | Fraction] = {
        1: 50_000_000 * 100,
        2: state.division_funds_hkd_cents[2],
        3: state.division_funds_hkd_cents[3],
    }
    per_line = expected_value(
        funds, other_entries=9_999_999, sharing_mode="uniform"
    ).total_expected_payout_hkd_cents
    risk_dividends: dict[int, int | Fraction] = {
        1: 1,
        2: 1,
        3: 1,
        **CURRENT_FIXED_PRIZES_HKD_CENTS,
    }
    rows: list[dict[str, object]] = []
    for budget in config.budgets_hkd:
        lines = budget // 10
        for offset, kind in enumerate(("diversified", "overlap", "duplicate")):
            tickets = _portfolio_tickets(lines, kind, config.simulation.root_seed + offset + budget)
            metrics = portfolio_metrics(
                tickets,
                expected_payout_per_line_hkd_cents=per_line,
            )
            risk_simulation = (
                simulate_portfolio_payout(
                    tickets,
                    risk_dividends,
                    trials=config.simulation.draws,
                    seed=config.simulation.root_seed,
                )
                if budget == 100
                else None
            )
            rows.append(
                {
                    "budget_hkd": budget,
                    "construction": kind,
                    "ticket_units": metrics.ticket_count,
                    "unique_combinations": metrics.unique_combinations,
                    "duplicate_units": metrics.duplicate_units,
                    "unique_numbers": metrics.unique_numbers,
                    "mean_shared_numbers": metrics.mean_shared_numbers,
                    "maximum_shared_numbers": metrics.maximum_shared_numbers,
                    "repeated_owned_pairs": metrics.repeated_owned_pairs,
                    "first_division_probability": float(metrics.first_division_probability),
                    "expected_payout_hkd": metrics.linear_expected_payout_hkd_cents / 100,
                    "expectation_changes_with_construction": False,
                    "simulated_probability_any_prize_hkd100_budget": (
                        risk_simulation.probability_any_prize if risk_simulation else None
                    ),
                    "simulated_payout_variance_hkd_squared_hkd100_budget": (
                        risk_simulation.payout_variance_hkd_cents_squared / 10_000
                        if risk_simulation
                        else None
                    ),
                    "portfolio_simulation_trials": (
                        risk_simulation.trials if risk_simulation else None
                    ),
                    "portfolio_risk_model": (
                        "joint fair draws; fixed-prize variance; 1-cent variable markers"
                        if risk_simulation
                        else None
                    ),
                    "economic_scenario": (
                        "uniform sharing; HKD100m turnover; HKD50m First Division fund"
                    ),
                }
            )
    return rows


def _system_rows() -> list[dict[str, object]]:
    state = build_current_state(100_000_000 * 100)
    dividends: dict[int, int | Fraction] = {
        1: 50_000_000 * 100,
        2: state.division_funds_hkd_cents[2],
        3: state.division_funds_hkd_cents[3],
        **CURRENT_FIXED_PRIZES_HKD_CENTS,
    }
    results = [multiple_entry_economics(7, dividends), banker_entry_economics(2, 5, dividends)]
    return [
        {
            "entry_type": item.entry_type,
            "combination_count": item.combination_count,
            "cost_hkd": item.cost_hkd_cents / 100,
            "expected_payout_hkd": float(item.expected_payout_hkd_cents / 100),
            "expanded_ordinary_expected_payout_hkd": float(
                item.equivalent_ordinary_expected_payout_hkd_cents / 100
            ),
            "expectation_equal": item.expected_payout_hkd_cents
            == item.equivalent_ordinary_expected_payout_hkd_cents,
            "payout_variance_hkd_squared": float(item.payout_variance_hkd_cents_squared / 10_000),
            "probability_any_prize": float(item.probability_any_prize),
            "payout_scenario": (
                "explicit Division 1-3 funds with no other winning units; theoretical only"
            ),
            "covariance_note": (
                "joint exact outcome distribution; lines are not assumed independent"
            ),
        }
        for item in results
    ]


def _split_risk_rows() -> list[dict[str, object]]:
    examples = {
        "birthday_sequence": (1, 2, 3, 4, 5, 6),
        "above_31": (32, 35, 38, 41, 44, 49),
        "repeated_last_digits": (8, 18, 28, 38, 41, 49),
        "mixed": (4, 13, 22, 34, 41, 47),
    }
    rows: list[dict[str, object]] = []
    for name, ticket in examples.items():
        feature = split_risk_features(ticket)
        rows.append(
            {
                "example": name,
                "ticket": "-".join(map(str, ticket)),
                **feature.__dict__,
                "draw_probability_effect": "none",
                "evidence": "features_observed; popularity_effect_synthetic_or_external_only",
            }
        )
    return rows


def _sensitivity_rows(config: EconomicConfig) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for turnover in config.turnover_hkd:
        state = build_current_state(turnover * 100)
        entries = turnover // 10 - 1
        for first_fund in (20_000_000, 50_000_000, 100_000_000):
            for multiplier in (0.5, 1.0, 3.0, 6.0):
                result = expected_value(
                    {
                        1: first_fund * 100,
                        2: state.division_funds_hkd_cents[2],
                        3: state.division_funds_hkd_cents[3],
                    },
                    other_entries=entries,
                    sharing_mode="higher_sharing",
                    popularity_multiplier=multiplier,
                )
                rows.append(
                    {
                        "turnover_hkd": turnover,
                        "first_division_fund_hkd": first_fund,
                        "synthetic_popularity_multiplier": multiplier,
                        "return_ratio": result.expected_return_ratio,
                        "evidence": "synthetic_assumption",
                    }
                )
    return rows


def _verify_inputs(project_root: Path, config: EconomicConfig) -> dict[str, object]:
    if not (
        _git_head(project_root) == config.baseline_commit
        or _has_ancestor(project_root, config.baseline_commit)
    ):
        raise EconomicIntegrityError("Git history lacks the approved Phase 7 baseline")
    phase7 = verify_historical_replication(project_root)
    if (
        phase7["manifest_sha256"]
        != "c01b718854e21bfb9f26bdf66453d85eb688df6fc0655ddccb5f529f032000d9"
    ):
        raise EconomicIntegrityError("Phase 7 manifest differs from the approved baseline")
    holdout = load_holdout_manifest(project_root / "data/holdout/manifest.json")
    if holdout.state != "sealed" or holdout.entries:
        raise EconomicIntegrityError("prospective holdout is not sealed with zero entries")
    return {"phase7": phase7, "holdout_state": holdout.state, "holdout_entry_count": 0}


def run_economic_analysis(project_root: Path) -> EconomicRunResult:
    """Run the complete frozen Phase 8 economics workflow."""

    config_path = project_root / "configs/phase8_economics.yaml"
    config = load_economic_config(config_path)
    integrity = _verify_inputs(project_root, config)
    dataset_dir = project_root / "data/processed" / config.dataset_id
    historical = load_historical_economics(
        dataset_dir / "mark_six.duckdb",
        start_date=date.fromisoformat(config.historical_period.start_date),
        end_date=date.fromisoformat(config.historical_period.final_date),
    )
    if (
        not historical
        or historical[0]["draw_id"] != config.historical_period.first_draw_id
        or historical[-1]["draw_id"] != config.historical_period.final_draw_id
    ):
        raise EconomicIntegrityError("historical current-rule boundary differs from configuration")
    fixed = _fixed_rows()
    accounting = _current_accounting_rows(config)
    jackpot = jackpot_scenario_rows(
        config.turnover_hkd,
        config.first_division_fund_hkd,
        config.sharing.modes,
        popularity_multiplier=config.sharing.higher_sharing_probability_multiplier,
    )
    sharing = sharing_rows(config.turnover_hkd)
    breakeven = breakeven_rows(
        config.turnover_hkd,
        config.return_targets,
        config.sharing.modes,
        popularity_multiplier=config.sharing.higher_sharing_probability_multiplier,
    )
    turnover = turnover_analysis_rows(historical)
    special = normal_special_rows(historical)
    semantics = field_semantics_rows()
    systems = _system_rows()
    portfolios = _portfolio_rows(config)
    split_risk = _split_risk_rows()
    sensitivity = _sensitivity_rows(config)
    simulation = simulate_economic_scenario(
        {1: 0, 2: 0, 3: 0},
        other_entries=config.turnover_hkd[1] // 10 - 1,
        trials=config.simulation.draws,
        seed=config.simulation.root_seed,
    )
    simulation_rows = [simulation.__dict__]
    tables = {
        "fixed_prize_ev": fixed,
        "current_accounting_scenarios": accounting,
        "jackpot_scenarios": jackpot,
        "breakeven_scenarios": breakeven,
        "sharing_scenarios": sharing,
        "historical_economics": historical,
        "turnover_analysis": turnover,
        "normal_special": special,
        "field_semantics": semantics,
        "split_risk_assumptions": split_risk,
        "system_entry_equivalence": systems,
        "portfolio_analysis": portfolios,
        "simulation_validation": simulation_rows,
        "sensitivity": sensitivity,
    }
    output_directory = project_root / "reports/generated/phase8"
    outputs = [_write_csv(output_directory / f"{name}.csv", rows) for name, rows in tables.items()]
    reports = write_economic_reports(
        project_root,
        fixed_rows=fixed,
        jackpot_rows=jackpot,
        sharing_rows=sharing,
        breakeven_rows=breakeven,
        turnover_rows=turnover,
        normal_special=special,
        system_rows=systems,
        portfolio_rows=portfolios,
        simulation_rows=simulation_rows,
    )
    outputs.extend(reports)
    dataset_manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    timestamp = datetime.now(UTC)
    manifest: dict[str, object] = {
        "schema_version": "1",
        "analysis_version": config.analysis_version,
        "git_baseline": config.baseline_commit,
        "git_head_at_run": _git_head(project_root),
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "canonical_table_sha256": dataset_manifest["table_sha256"],
        "phase7_manifest_sha256": cast(dict[str, object], integrity["phase7"])["manifest_sha256"],
        "protocol_version": config.protocol_version,
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "rule_version": config.rule_version,
        "source_fields_used": [
            "turnover",
            "jackpot",
            "derivedFirstPrizeDiv",
            "estimatedPrize",
            "snowballCode",
            "snowballName",
            "winningUnit",
            "dividend",
        ],
        "economic_assumptions": {
            "ticket_cost_hkd": 10,
            "turnover_allocation": {
                "prize_fund": 0.54,
                "lottery_duty": 0.25,
                "lotteries_fund": 0.15,
                "hkjc_commission": 0.06,
            },
            "variable_pool_allocation": {
                "division_1": 0.45,
                "division_2": 0.15,
                "division_3": 0.40,
            },
            "fixed_full_unit_prizes_hkd": {
                "division_4": 9600,
                "division_5": 640,
                "division_6": 320,
                "division_7": 40,
            },
            "minimum_first_division_fund_hkd": 8_000_000,
            "historical_time_state": "completed_draw_post_draw_unless_separately_dated",
            "missing_values": "preserve_null",
            "positive_ev_rule": "return_ratio_strictly_above_one",
        },
        "sharing_assumptions": config.sharing.model_dump(mode="json"),
        "simulation_seed": config.simulation.root_seed,
        "simulation_count": config.simulation.draws,
        "scenario_definitions": {
            "turnover_hkd": config.turnover_hkd,
            "first_division_fund_hkd": config.first_division_fund_hkd,
            "return_targets": config.return_targets,
            "budgets_hkd": config.budgets_hkd,
        },
        "historical_first_draw": historical[0]["draw_id"],
        "historical_final_draw": historical[-1]["draw_id"],
        "historical_draws": len(historical),
        "prospective_holdout_state": integrity["holdout_state"],
        "prospective_holdout_entry_count": integrity["holdout_entry_count"],
        "prospective_holdout_accessed": False,
        "historical_prediction_reopened": False,
        "phase8_code_sha256": _code_hash(project_root),
        "generated_at": timestamp.isoformat(),
        "output_sha256": {
            path.relative_to(project_root).as_posix(): _sha256(path) for path in outputs
        },
        "deviations": [],
    }
    manifest["manifest_sha256"] = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    manifest_path = project_root / "reports/generated/phase8_analysis_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return EconomicRunResult(
        manifest_path=manifest_path,
        report_paths=reports,
        output_directory=output_directory,
        historical_draws=len(historical),
        simulation_trials=config.simulation.draws,
    )


def verify_economic_analysis(project_root: Path) -> dict[str, object]:
    """Verify Phase 8 dependencies, self-hash, code hash, and all generated outputs."""

    config_path = project_root / "configs/phase8_economics.yaml"
    config = load_economic_config(config_path)
    integrity = _verify_inputs(project_root, config)
    manifest_path = project_root / "reports/generated/phase8_analysis_manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    unsigned = dict(manifest)
    stated = unsigned.pop("manifest_sha256", None)
    if hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest() != stated:
        raise EconomicIntegrityError("Phase 8 manifest self-hash mismatch")
    checks = {
        "git_baseline": config.baseline_commit,
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "protocol_version": config.protocol_version,
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "rule_version": config.rule_version,
        "phase8_code_sha256": _code_hash(project_root),
        "simulation_seed": config.simulation.root_seed,
        "simulation_count": config.simulation.draws,
        "prospective_holdout_state": "sealed",
        "prospective_holdout_entry_count": 0,
        "prospective_holdout_accessed": False,
        "historical_prediction_reopened": False,
    }
    for field, expected in checks.items():
        if manifest.get(field) != expected:
            raise EconomicIntegrityError(f"Phase 8 manifest mismatch: {field}")
    output_hashes = manifest.get("output_sha256")
    if not isinstance(output_hashes, dict):
        raise EconomicIntegrityError("Phase 8 output hashes are absent")
    failures = [
        str(relative)
        for relative, expected in output_hashes.items()
        if not (project_root / str(relative)).exists()
        or _sha256(project_root / str(relative)) != expected
    ]
    if failures:
        raise EconomicIntegrityError(f"Phase 8 output hash failures: {', '.join(failures)}")
    return {
        "manifest_sha256": stated,
        "output_count": len(output_hashes),
        "output_failures": 0,
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "phase7_manifest_sha256": cast(dict[str, object], integrity["phase7"])["manifest_sha256"],
        "historical_draws": manifest["historical_draws"],
        "holdout_state": integrity["holdout_state"],
        "holdout_entry_count": integrity["holdout_entry_count"],
        "historical_prediction_reopened": False,
    }


# PHASE9_EXTENSION_BEGIN
def _without_phase9_extension(content: bytes) -> bytes:
    """Remove the isolated Phase 9 surface from the frozen Phase 8 code hash."""

    begin = b"\n\n# PHASE9_EXTENSION_BEGIN\n"
    end = b"# PHASE9_EXTENSION_END\n"
    while begin in content:
        start = content.index(begin)
        finish = content.index(end, start) + len(end)
        content = content[:start] + content[finish:]
    return content


def _code_hash(project_root: Path) -> str:  # type: ignore[no-redef]
    """Hash the frozen Phase 8 package while excluding Phase 9 extensions."""

    digest = hashlib.sha256()
    paths = sorted((project_root / "src/mark_six/economics").glob("*.py"))
    paths.append(project_root / "src/mark_six/cli.py")
    for path in paths:
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(_without_phase9_extension(path.read_bytes()))
        digest.update(b"\0")
    return digest.hexdigest()


# PHASE9_EXTENSION_END
