from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from mark_six.final_system.evaluation import (
    EvaluationBlocked,
    build_evaluation_record,
    evaluate_predraw,
)
from mark_six.final_system.evidence import build_predraw_evidence
from mark_six.final_system.models import (
    EconomicEvaluation,
    EvidenceSource,
    FinalSystemConfig,
    PreDrawEvidence,
    PreDrawFacts,
    load_final_system_config,
)
from mark_six.final_system.storage import store_immutable_record, verify_immutable_record
from mark_six.final_system.tickets import (
    DuplicateTicketError,
    detect_duplicate_tickets,
    plan_tickets,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def config() -> FinalSystemConfig:
    return load_final_system_config(PROJECT_ROOT / "configs/phase9_final_system.yaml")


def _facts(
    first_fund_hkd: int,
    *,
    confidence: str = "High",
    exceptional: str = "none_known",
) -> PreDrawFacts:
    source = EvidenceSource.model_validate(
        {
            "source_id": "synthetic_official_draw_notice",
            "publisher": "SYNTHETIC HKJC FIXTURE",
            "url": "https://www.hkjc.com/synthetic-fixture-not-fetched",
            "published_at": datetime(2026, 9, 15, 2, tzinfo=UTC),
            "retrieved_at": datetime(2026, 9, 15, 3, tzinfo=UTC),
            "evidence_class": "official_pre_draw",
            "confidence": confidence,
        }
    )
    return PreDrawFacts.model_validate(
        {
            "draw_id": "hkjc:26/100",
            "draw_date": date(2026, 9, 16),
            "sales_close_at": datetime(2026, 9, 16, 13, tzinfo=UTC),
            "frozen_at": datetime(2026, 9, 15, 4, tzinfo=UTC),
            "draw_type": "normal",
            "ticket_price_hkd_cents": 1000,
            "official_first_division_fund_hkd_cents": first_fund_hkd * 100,
            "official_first_division_description": "official_estimated_first_division_fund",
            "known_carryover_hkd_cents": 0,
            "special_snowball_hkd_cents": 0,
            "exceptional_funding_status": exceptional,
            "sources": (source,),
        }
    )


def _evaluate(
    first_fund_hkd: int, config: FinalSystemConfig
) -> tuple[PreDrawEvidence, EconomicEvaluation]:
    evidence = build_predraw_evidence(_facts(first_fund_hkd), config)
    return evidence, evaluate_predraw(evidence, config)


def test_clear_negative_ev_produces_skip(config: FinalSystemConfig) -> None:
    _, result = _evaluate(8_000_000, config)
    assert result.decision == "SKIP"
    assert result.best_case_return_ratio < 0.95


def test_borderline_uncertainty_produces_watch(config: FinalSystemConfig) -> None:
    _, result = _evaluate(120_000_000, config)
    assert result.decision == "WATCH"
    assert result.worst_case_return_ratio < 1.02 <= result.best_case_return_ratio


def test_strong_conservative_scenario_is_interesting(config: FinalSystemConfig) -> None:
    _, result = _evaluate(500_000_000, config)
    assert result.decision == "ECONOMICALLY_INTERESTING"
    assert result.worst_case_return_ratio >= 1.02


def test_missing_or_uncertain_required_evidence_fails_closed(
    config: FinalSystemConfig,
) -> None:
    raw = _facts(120_000_000).model_dump()
    raw.pop("sources")
    with pytest.raises(ValidationError):
        PreDrawFacts.model_validate(raw)
    evidence = build_predraw_evidence(_facts(120_000_000, exceptional="uncertain"), config)
    with pytest.raises(EvaluationBlocked, match="exceptional funding"):
        evaluate_predraw(evidence, config)


def test_high_turnover_can_reduce_large_fund_value(config: FinalSystemConfig) -> None:
    _, result = _evaluate(150_000_000, config)
    assert result.turnover_sensitivity["upper"] < result.turnover_sensitivity["lower"]


def test_duplicate_tickets_are_detected() -> None:
    tickets = ((1, 2, 3, 4, 5, 6), (6, 5, 4, 3, 2, 1))
    with pytest.raises(DuplicateTicketError, match="duplicate ticket"):
        detect_duplicate_tickets(tickets)


@pytest.mark.parametrize("budget", [100, 500, 1000])
def test_uniform_budget_plans_are_exact_and_unique(budget: int) -> None:
    plan = plan_tickets(entry_type="uniform", budget_hkd=budget, seed=20260915)
    assert plan.combination_count == budget // 10
    assert plan.unique_combination_count == plan.combination_count
    assert plan.exact_cost_hkd_cents == budget * 100
    assert plan.duplicate_combination_count == 0


def test_multiple_and_banker_expand_with_exact_cost() -> None:
    multiple = plan_tickets(entry_type="multiple", budget_hkd=100, selections=(1, 2, 3, 4, 5, 6, 7))
    banker = plan_tickets(entry_type="banker", budget_hkd=100, bankers=(1, 2), legs=(3, 4, 5, 6, 7))
    assert (multiple.combination_count, multiple.exact_cost_hkd_cents) == (7, 7000)
    assert (banker.combination_count, banker.exact_cost_hkd_cents) == (5, 5000)
    assert "same draw probability" in multiple.draw_probability_statement


def test_tampered_turnover_forecast_is_blocked(config: FinalSystemConfig) -> None:
    evidence = build_predraw_evidence(_facts(120_000_000), config)
    raw = evidence.model_dump()
    raw["turnover_forecast"]["central_hkd"] += 1
    tampered = PreDrawEvidence.model_validate(raw)
    with pytest.raises(EvaluationBlocked, match="frozen explainable method"):
        evaluate_predraw(tampered, config)


def test_immutable_evidence_and_evaluation_records(
    tmp_path: Path, config: FinalSystemConfig
) -> None:
    evidence, evaluation = _evaluate(120_000_000, config)
    record = build_evaluation_record(
        evidence,
        evaluation,
        configuration_sha256="a" * 64,
        frozen_at=datetime(2026, 9, 15, 5, tzinfo=UTC),
    )
    path = store_immutable_record(
        tmp_path,
        record,
        draw_id=record.draw_id,
        frozen_at=record.frozen_at,
        kind="evaluation",
    )
    assert verify_immutable_record(path)
    assert record.outcome_comparison_status == "not_started"
    assert record.prospective_holdout_accessed is False
    with pytest.raises(FileExistsError):
        store_immutable_record(
            tmp_path,
            record,
            draw_id=record.draw_id,
            frozen_at=record.frozen_at,
            kind="evaluation",
        )


def test_evidence_must_be_frozen_before_sales_close() -> None:
    raw = _facts(120_000_000).model_dump()
    raw["frozen_at"] = raw["sales_close_at"]
    with pytest.raises(ValidationError, match="before sales close"):
        PreDrawFacts.model_validate(raw)
