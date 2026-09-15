"""Conservative pre-draw economic evaluation using the frozen Phase 8 engine."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from mark_six.economics.expected_value import expected_value, first_fund_for_return_target
from mark_six.economics.state import build_current_state
from mark_six.final_system.models import (
    CONFIDENCE_RANK,
    Decision,
    EconomicEvaluation,
    FinalSystemConfig,
    PreDrawEvidence,
    PreDrawFacts,
    ProspectiveEvaluationRecord,
    ScenarioResult,
    SharingScenario,
)
from mark_six.final_system.turnover import forecast_turnover
from mark_six.prediction.reserve import canonical_json_bytes


class EvaluationBlocked(RuntimeError):
    """Raised when required pre-draw evidence is missing or uncertain."""


TurnoverCase = Literal["lower", "central", "upper"]


def _sharing_parameters(scenario: SharingScenario) -> tuple[str, float]:
    if scenario.name == "uniform":
        return "uniform", 1.0
    return "higher_sharing", scenario.first_division_popularity_multiplier


def _one_scenario(
    evidence: PreDrawEvidence,
    turnover_case: TurnoverCase,
    turnover_hkd: int,
    sharing: SharingScenario,
) -> ScenarioResult:
    state = build_current_state(turnover_hkd * 100)
    mode, multiplier = _sharing_parameters(sharing)
    metrics = expected_value(
        {
            1: evidence.official_first_division_fund_hkd_cents,
            2: state.division_funds_hkd_cents[2],
            3: state.division_funds_hkd_cents[3],
        },
        other_entries=max(0, turnover_hkd // 10 - 1),
        ticket_cost_hkd_cents=evidence.ticket_price_hkd_cents,
        sharing_mode=mode,
        popularity_multiplier=multiplier,
    )
    return ScenarioResult(
        turnover_case=turnover_case,
        turnover_hkd=turnover_hkd,
        sharing_scenario=sharing.name,
        sharing_evidence_class=sharing.evidence_class,
        expected_payout_hkd=metrics.total_expected_payout_hkd_cents / 100,
        expected_profit_hkd=metrics.expected_profit_hkd_cents / 100,
        expected_return_ratio=metrics.expected_return_ratio,
        expected_return_percent=100 * metrics.expected_return_ratio,
    )


def evaluate_predraw(evidence: PreDrawEvidence, config: FinalSystemConfig) -> EconomicEvaluation:
    """Evaluate a complete record and classify it using the preregistered envelope."""

    if evidence.exceptional_funding_status != "none_known":
        raise EvaluationBlocked("exceptional funding is present or uncertain; evaluation blocked")
    if not evidence.sources:
        raise EvaluationBlocked("at least one dated official pre-draw source is required")
    if evidence.outcome_data_accessed:
        raise EvaluationBlocked("outcome-bearing evidence is forbidden")
    if evidence.ticket_price_hkd_cents != config.ticket_price_hkd_cents:
        raise EvaluationBlocked("ticket price differs from the frozen current rule")
    facts = PreDrawFacts.model_validate(
        evidence.model_dump(
            exclude={
                "schema_version",
                "record_type",
                "evidence_confidence",
                "turnover_forecast",
                "outcome_data_accessed",
            }
        )
    )
    if evidence.turnover_forecast != forecast_turnover(facts, config.turnover):
        raise EvaluationBlocked("turnover forecast differs from the frozen explainable method")

    turnover = evidence.turnover_forecast
    turnover_cases: tuple[tuple[TurnoverCase, int], ...] = (
        ("lower", turnover.lower_hkd),
        ("central", turnover.central_hkd),
        ("upper", turnover.upper_hkd),
    )
    scenarios = tuple(
        _one_scenario(evidence, case, amount, sharing)
        for case, amount in turnover_cases
        for sharing in config.sharing_scenarios
    )
    central = next(
        row
        for row in scenarios
        if row.turnover_case == "central" and row.sharing_scenario == "uniform"
    )
    worst = min(row.expected_return_ratio for row in scenarios)
    best = max(row.expected_return_ratio for row in scenarios)
    central_state = build_current_state(turnover.central_hkd * 100)
    break_even_cents = first_fund_for_return_target(
        1.0,
        {
            2: central_state.division_funds_hkd_cents[2],
            3: central_state.division_funds_hkd_cents[3],
        },
        other_entries=max(0, turnover.central_hkd // 10 - 1),
        sharing_mode="uniform",
        ticket_cost_hkd_cents=evidence.ticket_price_hkd_cents,
    )
    rules = config.decision_rules
    sufficient_confidence = (
        CONFIDENCE_RANK[evidence.evidence_confidence] >= CONFIDENCE_RANK[rules.minimum_confidence]
    )
    if not sufficient_confidence:
        decision: Decision = "SKIP"
        reason = "Material evidence confidence is Low; the system fails closed."
    elif worst >= rules.economically_interesting_minimum_worst_case_return_ratio:
        decision = "ECONOMICALLY_INTERESTING"
        reason = "Every frozen turnover and sharing scenario clears the conservative threshold."
    elif best >= rules.watch_minimum_best_case_return_ratio:
        decision = "WATCH"
        reason = (
            "The uncertainty envelope reaches the watch threshold but is not robustly positive."
        )
    else:
        decision = "SKIP"
        reason = "Even the most favorable frozen scenario remains below the watch threshold."
    turnover_sensitivity: dict[str, float] = {
        str(row.turnover_case): row.expected_return_ratio
        for row in scenarios
        if row.sharing_scenario == "uniform"
    }
    sharing_sensitivity: dict[str, float] = {
        str(row.sharing_scenario): row.expected_return_ratio
        for row in scenarios
        if row.turnover_case == "central"
    }
    return EconomicEvaluation(
        decision=decision,
        reason=reason,
        central_expected_payout_hkd=central.expected_payout_hkd,
        central_expected_profit_hkd=central.expected_profit_hkd,
        central_expected_return_percent=central.expected_return_percent,
        break_even_first_division_fund_hkd=break_even_cents / 100,
        break_even_distance_hkd=(evidence.official_first_division_fund_hkd_cents - break_even_cents)
        / 100,
        worst_case_return_ratio=worst,
        best_case_return_ratio=best,
        turnover_sensitivity=turnover_sensitivity,
        sharing_sensitivity=sharing_sensitivity,
        scenarios=scenarios,
    )


def build_evaluation_record(
    evidence: PreDrawEvidence,
    evaluation: EconomicEvaluation,
    *,
    configuration_sha256: str,
    frozen_at: datetime | None = None,
) -> ProspectiveEvaluationRecord:
    """Create an outcome-free, content-bound prospective record."""

    timestamp = frozen_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("evaluation frozen_at must be timezone-aware")
    evidence_hash = hashlib.sha256(
        canonical_json_bytes(evidence.model_dump(mode="json"))
    ).hexdigest()
    identifier_material = {
        "draw_id": evidence.draw_id,
        "frozen_at": timestamp.isoformat(),
        "evidence_sha256": evidence_hash,
        "configuration_sha256": configuration_sha256,
        "decision": evaluation.decision,
    }
    evaluation_id = (
        "phase9:" + hashlib.sha256(canonical_json_bytes(identifier_material)).hexdigest()[:20]
    )
    return ProspectiveEvaluationRecord(
        evaluation_id=evaluation_id,
        draw_id=evidence.draw_id,
        draw_date=evidence.draw_date,
        frozen_at=timestamp,
        evidence_sha256=evidence_hash,
        configuration_sha256=configuration_sha256,
        evaluation=evaluation,
    )
