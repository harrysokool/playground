"""Strict Phase 9 configuration, evidence, evaluation, and ticket records."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Confidence = Literal["Low", "Medium", "High"]
Decision = Literal["SKIP", "WATCH", "ECONOMICALLY_INTERESTING"]

CONFIDENCE_RANK: dict[Confidence, int] = {"Low": 0, "Medium": 1, "High": 2}


class TurnoverConfig(BaseModel):
    """Frozen, explainable turnover estimator."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    method: Literal["frozen_draw_class_median_plus_fund_response_v1"]
    normal_baseline_hkd: int = Field(gt=0)
    special_baseline_hkd: int = Field(gt=0)
    reference_first_division_fund_hkd: int = Field(gt=0)
    fund_response_hkd_per_hkd: float = Field(ge=0)
    lower_multiplier: float = Field(gt=0, le=1)
    upper_multiplier: float = Field(ge=1)
    floor_hkd: int = Field(gt=0)
    evidence_class: Literal["estimate_from_frozen_pre_holdout_history_plus_assumption"]


class SharingScenario(BaseModel):
    """One frozen First Division sharing sensitivity."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    name: Literal["lower_sharing", "uniform", "higher_sharing"]
    first_division_popularity_multiplier: float = Field(gt=0)
    evidence_class: Literal["behavioral_assumption", "exact_under_uniform_selection_assumption"]


class DecisionRules(BaseModel):
    """Conservative categories frozen before real-draw use."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    economically_interesting_minimum_worst_case_return_ratio: float = Field(gt=1)
    watch_minimum_best_case_return_ratio: float = Field(gt=0, le=1)
    minimum_confidence: Literal["Medium"]
    low_confidence_action: Literal["SKIP"]
    missing_evidence_action: Literal["fail_closed"]


class StorageConfig(BaseModel):
    """Immutable record locations."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    directory: str
    evidence_kind: Literal["evidence"]
    evaluation_kind: Literal["evaluation"]


class OutputConfig(BaseModel):
    """Generated Phase 9 outputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest: str
    reports: list[str]


class FinalSystemConfig(BaseModel):
    """Complete frozen Phase 9 configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    system_version: Literal["phase9-v1"]
    protocol_version: Literal["phase9-final-system-v1"]
    baseline_commit: str
    dataset_id: Literal["marksix-bc02467ec951c2d8"]
    dataset_manifest_sha256: str
    protocol_path: str
    rule_version: Literal["hkjc_mark_six_2024_05_21"]
    previous_manifest_sha256: dict[Literal["phase5", "phase6", "phase7", "phase8"], str]
    turnover: TurnoverConfig
    sharing_scenarios: list[SharingScenario]
    decision_rules: DecisionRules
    ticket_budgets_hkd: list[int]
    ticket_price_hkd_cents: Literal[1000]
    source_definitions: dict[str, str]
    storage: StorageConfig
    outputs: OutputConfig

    @model_validator(mode="after")
    def frozen_values_are_complete(self) -> FinalSystemConfig:
        if [item.name for item in self.sharing_scenarios] != [
            "lower_sharing",
            "uniform",
            "higher_sharing",
        ]:
            raise ValueError("Phase 9 sharing scenarios differ from the frozen order")
        if self.ticket_budgets_hkd != [100, 500, 1000]:
            raise ValueError("Phase 9 ticket budgets differ from the frozen values")
        if set(self.previous_manifest_sha256) != {"phase5", "phase6", "phase7", "phase8"}:
            raise ValueError("all previous manifest hashes are required")
        return self


class EvidenceSource(BaseModel):
    """One source demonstrably available before the evaluation cutoff."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    published_at: datetime
    retrieved_at: datetime
    evidence_class: Literal["official_pre_draw", "official_rule"]
    confidence: Confidence

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> EvidenceSource:
        if self.published_at.tzinfo is None or self.retrieved_at.tzinfo is None:
            raise ValueError("source timestamps must be timezone-aware")
        if self.published_at > self.retrieved_at:
            raise ValueError("source publication cannot follow retrieval")
        if self.evidence_class == "official_pre_draw" and not (
            self.url.startswith("https://hkjc.com/") or ".hkjc.com/" in self.url
        ):
            raise ValueError("draw-specific official evidence must use an HKJC HTTPS URL")
        return self


class TurnoverForecast(BaseModel):
    """Pre-draw turnover estimate and explicit uncertainty range."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    method: Literal["frozen_draw_class_median_plus_fund_response_v1"]
    central_hkd: int = Field(gt=0)
    lower_hkd: int = Field(gt=0)
    upper_hkd: int = Field(gt=0)
    confidence: Confidence
    evidence_class: Literal["estimate_from_frozen_pre_holdout_history_plus_assumption"]
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def range_contains_central(self) -> TurnoverForecast:
        if not self.lower_hkd <= self.central_hkd <= self.upper_hkd:
            raise ValueError("turnover range must contain the central estimate")
        return self


class PreDrawFacts(BaseModel):
    """Official facts used to construct a complete pre-draw evidence record."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    draw_id: str = Field(pattern=r"^hkjc:\d{2}/\d{3}$")
    draw_date: date
    sales_close_at: datetime
    frozen_at: datetime
    draw_type: Literal["normal", "special"]
    ticket_price_hkd_cents: Literal[1000]
    official_first_division_fund_hkd_cents: int = Field(gt=0)
    official_first_division_description: Literal[
        "official_estimated_first_division_fund",
        "official_confirmed_first_division_fund_available_for_allocation",
    ]
    known_carryover_hkd_cents: int = Field(ge=0)
    special_snowball_hkd_cents: int = Field(ge=0)
    exceptional_funding_status: Literal["none_known", "present", "uncertain"]
    sources: tuple[EvidenceSource, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def timing_is_before_sales_close(self) -> PreDrawFacts:
        if self.frozen_at.tzinfo is None or self.sales_close_at.tzinfo is None:
            raise ValueError("freeze and sales-close timestamps must be timezone-aware")
        if self.frozen_at >= self.sales_close_at:
            raise ValueError("evidence must be frozen before sales close")
        if self.sales_close_at.date() != self.draw_date:
            raise ValueError("sales_close_at must fall on the stated draw date")
        if not any(source.evidence_class == "official_pre_draw" for source in self.sources):
            raise ValueError("a dated official pre-draw source is required")
        return self


class PreDrawEvidence(PreDrawFacts):
    """Complete evidence package frozen before a draw."""

    schema_version: Literal["1"] = "1"
    record_type: Literal["mark_six_pre_draw_evidence"] = "mark_six_pre_draw_evidence"
    evidence_confidence: Confidence
    turnover_forecast: TurnoverForecast
    outcome_data_accessed: Literal[False] = False

    @model_validator(mode="after")
    def is_strictly_predraw(self) -> PreDrawEvidence:
        if self.frozen_at.tzinfo is None:
            raise ValueError("frozen_at must be timezone-aware")
        for source in self.sources:
            if source.published_at > self.frozen_at or source.retrieved_at > self.frozen_at:
                raise ValueError("all evidence must be published and retrieved before frozen_at")
        lowest = min(
            [self.turnover_forecast.confidence, *(source.confidence for source in self.sources)],
            key=lambda value: CONFIDENCE_RANK[value],
        )
        if CONFIDENCE_RANK[self.evidence_confidence] > CONFIDENCE_RANK[lowest]:
            raise ValueError("overall confidence cannot exceed its weakest material evidence")
        return self


class ScenarioResult(BaseModel):
    """One turnover/sharing economic sensitivity."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    turnover_case: Literal["lower", "central", "upper"]
    turnover_hkd: int
    sharing_scenario: Literal["lower_sharing", "uniform", "higher_sharing"]
    sharing_evidence_class: str
    expected_payout_hkd: float
    expected_profit_hkd: float
    expected_return_ratio: float
    expected_return_percent: float


class EconomicEvaluation(BaseModel):
    """Decision and full scenario envelope frozen before outcome observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    decision: Decision
    reason: str
    central_expected_payout_hkd: float
    central_expected_profit_hkd: float
    central_expected_return_percent: float
    break_even_first_division_fund_hkd: float
    break_even_distance_hkd: float
    worst_case_return_ratio: float
    best_case_return_ratio: float
    turnover_sensitivity: dict[str, float]
    sharing_sensitivity: dict[str, float]
    scenarios: tuple[ScenarioResult, ...]


class ProspectiveEvaluationRecord(BaseModel):
    """Outcome-free record to be compared only under a separate future protocol."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1"] = "1"
    record_type: Literal["mark_six_prospective_evaluation"] = "mark_six_prospective_evaluation"
    evaluation_id: str
    draw_id: str
    draw_date: date
    frozen_at: datetime
    evidence_sha256: str
    configuration_sha256: str
    evaluation: EconomicEvaluation
    outcome_comparison_status: Literal["not_started"] = "not_started"
    outcome_data_accessed: Literal[False] = False
    prospective_holdout_accessed: Literal[False] = False


class TicketPlan(BaseModel):
    """Exact expanded combinations and cost for a fixed budget."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    entry_type: Literal["uniform", "multiple", "banker"]
    budget_hkd_cents: int
    exact_cost_hkd_cents: int
    unused_budget_hkd_cents: int
    combination_count: int
    unique_combination_count: int
    duplicate_combination_count: int
    combinations: tuple[tuple[int, int, int, int, int, int], ...]
    seed: int | None
    draw_probability_statement: str
    packaging_statement: str
    split_risk_note: str | None


def load_final_system_config(path: Path) -> FinalSystemConfig:
    """Load strict frozen Phase 9 configuration."""

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Phase 9 configuration must be a mapping")
    return FinalSystemConfig.model_validate(cast(dict[str, Any], raw))
