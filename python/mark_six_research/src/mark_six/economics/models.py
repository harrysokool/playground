"""Validated Phase 8 configuration and run-result records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SimulationConfig(BaseModel):
    """Frozen deterministic simulation settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    root_seed: int
    draws: int = Field(gt=0)


class SharingConfig(BaseModel):
    """Registered sharing scenarios."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    modes: list[str]
    higher_sharing_probability_multiplier: float = Field(gt=0)
    use_exact_binomial: bool
    validate_poisson: bool

    @model_validator(mode="after")
    def modes_are_frozen(self) -> SharingConfig:
        if self.modes != ["no_sharing", "uniform", "higher_sharing"]:
            raise ValueError("Phase 8 sharing modes differ from the frozen protocol")
        return self


class HistoricalPeriod(BaseModel):
    """Eligible current-rule development interval."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    first_draw_id: str
    start_date: str
    final_draw_id: str
    final_date: str


class EconomicConfig(BaseModel):
    """Fields used by the Phase 8 analysis runner; extra protocol data remains forbidden."""

    model_config = ConfigDict(extra="allow", frozen=True)
    analysis_version: str
    protocol_version: str
    baseline_commit: str
    dataset_id: str
    dataset_manifest_sha256: str
    protocol_path: str
    rule_version: str
    historical_period: HistoricalPeriod
    turnover_hkd: list[int]
    first_division_fund_hkd: list[int]
    return_targets: list[float]
    sharing: SharingConfig
    budgets_hkd: list[int]
    simulation: SimulationConfig

    @model_validator(mode="after")
    def registered_values_are_unchanged(self) -> EconomicConfig:
        if self.turnover_hkd != [50_000_000, 100_000_000, 200_000_000]:
            raise ValueError("turnover grid differs from Decision 0008")
        if self.first_division_fund_hkd != [
            8_000_000,
            10_000_000,
            20_000_000,
            30_000_000,
            50_000_000,
            80_000_000,
            100_000_000,
            150_000_000,
        ]:
            raise ValueError("First Division grid differs from Decision 0008")
        if self.return_targets != [0.5, 0.75, 0.9, 1.0]:
            raise ValueError("return targets differ from Decision 0008")
        if self.budgets_hkd != [100, 500, 1000]:
            raise ValueError("budget grid differs from Decision 0008")
        if self.historical_period.final_date > "2026-09-12":
            raise ValueError("Phase 8 historical period crosses the development cutoff")
        return self


def load_economic_config(path: Path) -> EconomicConfig:
    """Load the frozen YAML configuration."""

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Phase 8 configuration must be a mapping")
    return EconomicConfig.model_validate(cast(dict[str, Any], raw))


@dataclass(frozen=True)
class EconomicRunResult:
    """High-level outputs from one reproducible Phase 8 run."""

    manifest_path: Path
    report_paths: tuple[Path, ...]
    output_directory: Path
    historical_draws: int
    simulation_trials: int
