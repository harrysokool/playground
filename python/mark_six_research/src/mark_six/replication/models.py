"""Typed frozen configuration and run containers for Phase 7."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from mark_six.prediction.models import (
    CalibrationSpec,
    CandidateModel,
    InferenceSpec,
    SuccessCriteria,
)


class ReserveSpec(BaseModel):
    """Exact registered historical reserve boundary."""

    model_config = ConfigDict(extra="forbid")

    period_id: str
    pool_size: Literal[49]
    draw_count: Literal[676]
    first_draw_id: str
    first_draw_date: date
    final_draw_id: str
    final_draw_date: date


class ReplicationSimulationSpec(BaseModel):
    """Full-process fair calibration settings."""

    model_config = ConfigDict(extra="forbid")

    root_seed: int
    histories: int = Field(ge=500)
    total_draws: int = Field(ge=1)
    scored_draws: int = Field(ge=1)
    batch_size: int = Field(ge=1)


class StabilitySpec(BaseModel):
    """Fixed chronological block assignment."""

    model_config = ConfigDict(extra="forbid")

    blocks: Literal[4]
    draws_per_block: int = Field(ge=1)


class ReplicationSuccessCriteria(SuccessCriteria):
    """Phase 6 criteria plus a favorable confidence-interval requirement."""

    require_confidence_interval_lower_above_zero: Literal[True]


class ReplicationConfig(BaseModel):
    """Complete preregistered Phase 7 configuration."""

    model_config = ConfigDict(extra="forbid")

    analysis_version: str
    protocol_version: str
    baseline_commit: str = Field(min_length=40, max_length=40)
    dataset_id: str
    dataset_manifest_sha256: str = Field(min_length=64, max_length=64)
    phase6_manifest_path: str
    phase6_manifest_sha256: str = Field(min_length=64, max_length=64)
    phase6_config_path: str
    protocol_path: str
    reserve_manifest_path: str
    reserve_manifest_sha256: str = Field(min_length=64, max_length=64)
    initial_history_draws: Literal[2700]
    history_first_draw_id: str
    history_start_date: date
    initial_history_final_draw_id: str
    initial_history_final_date: date
    reserve: ReserveSpec
    models: list[CandidateModel] = Field(min_length=11, max_length=11)
    primary_metric: Literal["whole_set_log_probability_nats"]
    secondary_metrics: list[str] = Field(min_length=5, max_length=5)
    inference: InferenceSpec
    simulation: ReplicationSimulationSpec
    calibration: CalibrationSpec
    stability: StabilitySpec
    success_criteria: ReplicationSuccessCriteria

    @model_validator(mode="after")
    def registered_counts_and_family_match(self) -> ReplicationConfig:
        if self.initial_history_draws + self.reserve.draw_count != self.simulation.total_draws:
            raise ValueError("initial history plus reserve must equal simulated history length")
        if self.reserve.draw_count != self.simulation.scored_draws:
            raise ValueError("every reserve draw must be scored")
        if self.stability.blocks * self.stability.draws_per_block != self.reserve.draw_count:
            raise ValueError("fixed stability blocks must cover all reserve draws")
        if self.reserve.first_draw_date <= self.initial_history_final_date:
            raise ValueError("reserve must follow the initialization history")
        names = [model.name for model in self.models]
        if len(names) != len(set(names)) or names[0] != "uniform":
            raise ValueError("the frozen model family must be unique and start with uniform")
        if any("pair" in name or "2-26" in name for name in names):
            raise ValueError("pair-specific models are prohibited")
        return self


@dataclass(frozen=True)
class ReplicationRunResult:
    """High-level result paths and confirmatory conclusion."""

    report_path: Path
    manifest_path: Path
    output_directory: Path
    reserve_draws: int
    candidate_models: int
    simulation_histories: int
    selected_best_model: str
    successful_models: tuple[str, ...]
    phase6_conclusion_replicated: bool


def load_replication_config(path: Path) -> ReplicationConfig:
    """Load and strictly validate the frozen Phase 7 YAML."""

    with path.open(encoding="utf-8") as handle:
        raw: Any = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"replication configuration must be a mapping: {path}")
    return ReplicationConfig.model_validate(raw)
