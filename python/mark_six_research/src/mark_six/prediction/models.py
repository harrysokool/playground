"""Typed configuration and data containers for Phase 6."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PeriodSpec(BaseModel):
    """One chronological, pool-homogeneous period."""

    model_config = ConfigDict(extra="forbid")

    period_id: str
    start: date
    end: date
    pool_size: int = Field(ge=7)

    @model_validator(mode="after")
    def ordered_dates(self) -> PeriodSpec:
        if self.start > self.end:
            raise ValueError("period start must not follow period end")
        return self


class PrimarySpec(PeriodSpec):
    """Frozen primary population and split sizes."""

    population_draws: int = Field(ge=1)
    phase6_draws: int = Field(ge=1)
    reserve_draws: int = Field(ge=1)
    warmup_draws: int = Field(ge=1)
    scored_draws: int = Field(ge=1)

    @model_validator(mode="after")
    def counts_are_consistent(self) -> PrimarySpec:
        if self.phase6_draws + self.reserve_draws != self.population_draws:
            raise ValueError("Phase 6 and reserve counts must equal the primary population")
        if self.warmup_draws + self.scored_draws != self.phase6_draws:
            raise ValueError("warm-up and scored counts must equal the Phase 6 count")
        return self


class SecondarySpec(BaseModel):
    """Frozen historical replication periods."""

    model_config = ConfigDict(extra="forbid")

    warmup_draws: int = Field(ge=1)
    periods: list[PeriodSpec] = Field(min_length=1)


class ExclusionSpec(BaseModel):
    """One explicitly excluded date interval."""

    model_config = ConfigDict(extra="forbid")

    start: date
    end: date
    reason: str


ModelKind = Literal[
    "uniform",
    "expanding_frequency",
    "rolling_frequency",
    "exponential_frequency",
    "gap_due",
    "recent_appearance",
    "previous_draw_multiplier",
]


class CandidateModel(BaseModel):
    """One frozen candidate with no learned parameter."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: ModelKind
    version: str
    smoothing: float | None = Field(default=None, gt=0)
    window: int | None = Field(default=None, ge=1)
    half_life: float | None = Field(default=None, gt=0)
    multiplier: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def parameters_match_kind(self) -> CandidateModel:
        required: dict[str, tuple[str, ...]] = {
            "uniform": (),
            "expanding_frequency": ("smoothing",),
            "rolling_frequency": ("smoothing", "window"),
            "exponential_frequency": ("smoothing", "half_life"),
            "gap_due": ("half_life", "multiplier"),
            "recent_appearance": ("half_life", "multiplier"),
            "previous_draw_multiplier": ("multiplier",),
        }
        for field in required[self.kind]:
            if getattr(self, field) is None:
                raise ValueError(f"{self.kind} requires {field}")
        return self


class InferenceSpec(BaseModel):
    """Frozen paired inference settings."""

    model_config = ConfigDict(extra="forbid")

    alpha: float = Field(gt=0, lt=1)
    correction: Literal["holm"]
    bootstrap_seed: int
    bootstrap_replicates: int = Field(ge=1)
    moving_block_length: int = Field(ge=1)


class SimulationSpec(BaseModel):
    """Frozen full-process fair simulation settings."""

    model_config = ConfigDict(extra="forbid")

    root_seed: int
    histories: int = Field(ge=1)
    batch_size: int = Field(ge=1)


class CalibrationSpec(BaseModel):
    """Frozen marginal-calibration bins."""

    model_config = ConfigDict(extra="forbid")

    probability_edges: list[float] = Field(min_length=3)

    @model_validator(mode="after")
    def valid_edges(self) -> CalibrationSpec:
        edges = self.probability_edges
        if edges[0] != 0.0 or edges[-1] != 1.0:
            raise ValueError("calibration edges must span zero through one")
        if any(left >= right for left, right in pairwise(edges)):
            raise ValueError("calibration edges must be strictly increasing")
        return self


class SuccessCriteria(BaseModel):
    """Conjunctive primary interpretation thresholds."""

    model_config = ConfigDict(extra="forbid")

    minimum_mean_log_improvement_nats: float = Field(gt=0)
    maximum_adjusted_p_value: float = Field(gt=0, lt=1)
    maximum_family_wide_p_value: float = Field(gt=0, lt=1)
    maximum_ece: float = Field(gt=0)
    minimum_nonnegative_blocks: int = Field(ge=1)
    minimum_block_mean_log_improvement_nats: float = Field(lt=0)


class PredictionConfig(BaseModel):
    """Complete frozen Phase 6 configuration."""

    model_config = ConfigDict(extra="forbid")

    analysis_version: str
    protocol_version: str
    dataset_id: str
    dataset_manifest_sha256: str = Field(min_length=64, max_length=64)
    baseline_commit: str = Field(min_length=40, max_length=40)
    protocol_path: str
    reserve_manifest_path: str
    primary: PrimarySpec
    secondary: SecondarySpec
    excluded: ExclusionSpec
    models: list[CandidateModel] = Field(min_length=2)
    inference: InferenceSpec
    simulation: SimulationSpec
    calibration: CalibrationSpec
    stability_blocks: int = Field(ge=2)
    success_criteria: SuccessCriteria

    @model_validator(mode="after")
    def frozen_family_is_unique(self) -> PredictionConfig:
        names = [model.name for model in self.models]
        if len(names) != len(set(names)):
            raise ValueError("candidate model names must be unique")
        if names[0] != "uniform" or self.models[0].kind != "uniform":
            raise ValueError("uniform must be the first candidate")
        if any("pair" in name or "2-26" in name for name in names):
            raise ValueError("number-specific pair models are prohibited")
        return self


@dataclass(frozen=True)
class PredictionHistory:
    """Chronological main-number outcomes for a homogeneous pool."""

    period_id: str
    pool_size: int
    draw_ids: tuple[str, ...]
    draw_dates: tuple[date, ...]
    mains: NDArray[np.int64]

    @property
    def draw_count(self) -> int:
        return int(self.mains.shape[0])


@dataclass(frozen=True)
class WalkForwardResult:
    """Per-forecast rows and model-level summaries."""

    period_id: str
    pool_size: int
    warmup_draws: int
    forecast_rows: tuple[dict[str, object], ...]
    summary_rows: tuple[dict[str, object], ...]
    calibration_rows: tuple[dict[str, object], ...]
    stability_rows: tuple[dict[str, object], ...]


def load_prediction_config(path: Path) -> PredictionConfig:
    """Load and validate the frozen YAML configuration."""

    with path.open(encoding="utf-8") as handle:
        raw: Any = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"prediction configuration must be a mapping: {path}")
    return PredictionConfig.model_validate(raw)
