"""Typed configuration and data containers for Phase 5 statistics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PeriodSpec(BaseModel):
    """One pool-homogeneous confirmatory period."""

    model_config = ConfigDict(extra="forbid")

    period_id: str
    start: date
    end: date
    pool_size: int = Field(ge=7)

    @model_validator(mode="after")
    def dates_are_ordered(self) -> PeriodSpec:
        if self.start > self.end:
            raise ValueError("period start must not follow period end")
        return self


class ExclusionSpec(BaseModel):
    """A date interval deliberately excluded from confirmatory analysis."""

    model_config = ConfigDict(extra="forbid")

    start: date
    end: date
    reason: str


class PracticalThresholds(BaseModel):
    """Effect-size thresholds frozen in the protocol."""

    model_config = ConfigDict(extra="forbid")

    individual_absolute_z: float = Field(gt=0)
    individual_relative_deviation: float = Field(gt=0)
    pair_triple_absolute_z: float = Field(gt=0)
    pair_triple_relative_deviation: float = Field(gt=0)
    categorical_cramers_v: float = Field(gt=0)
    sum_absolute_d: float = Field(gt=0)
    serial_absolute_r: float = Field(gt=0)


class AnalysisConfig(BaseModel):
    """Frozen Phase 5 analysis configuration."""

    model_config = ConfigDict(extra="forbid")

    analysis_version: str
    protocol_version: str
    dataset_id: str
    dataset_manifest_sha256: str = Field(min_length=64, max_length=64)
    baseline_commit: str = Field(min_length=40, max_length=40)
    development_cutoff: date
    root_seed: int
    simulations_per_period: int = Field(ge=1)
    alpha: float = Field(gt=0, lt=1)
    fdr_q: float = Field(gt=0, lt=1)
    corrections: dict[str, str]
    periods: list[PeriodSpec] = Field(min_length=1)
    exclusions: list[ExclusionSpec]
    low_definition: str
    stability_blocks: int = Field(ge=2)
    practical_thresholds: PracticalThresholds


@dataclass(frozen=True)
class DrawHistory:
    """Chronological draw arrays for one homogeneous number pool."""

    period_id: str
    pool_size: int
    draw_ids: tuple[str, ...]
    draw_dates: tuple[date, ...]
    mains: NDArray[np.int64]
    extras: NDArray[np.int64]

    @property
    def draw_count(self) -> int:
        return int(self.mains.shape[0])


@dataclass
class PeriodAnalysis:
    """Observed tables, fixed omnibus statistics, and effect summaries."""

    period_id: str
    pool_size: int
    draw_count: int
    tables: dict[str, list[dict[str, object]]]
    omnibus_statistics: dict[str, float]
    effect_sizes: dict[str, float]
    descriptive: dict[str, object]


def load_analysis_config(path: Path) -> AnalysisConfig:
    """Load the frozen YAML protocol configuration."""

    with path.open(encoding="utf-8") as config_file:
        raw: Any = yaml.safe_load(config_file)
    if not isinstance(raw, dict):
        raise ValueError(f"Analysis configuration must be a mapping: {path}")
    return AnalysisConfig.model_validate(raw)
