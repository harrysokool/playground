"""Prospective holdout policy and development-data access guard."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEVELOPMENT_CUTOFF = date(2026, 9, 13)
HOLDOUT_TARGET_DRAWS = 312


class HoldoutEntry(BaseModel):
    """Outcome-free metadata allowed in the sealed holdout manifest."""

    model_config = ConfigDict(extra="forbid")

    source_draw_id: str
    draw_date: date
    eligibility_status: Literal["pending", "eligible", "ineligible"]
    rule_version_id: str | None
    raw_snapshot_id: str
    canonical_dataset_version: str | None
    sealed: Literal[True] = True

    @model_validator(mode="after")
    def is_prospective(self) -> HoldoutEntry:
        """Reject development-period records from the prospective holdout."""

        if self.draw_date <= DEVELOPMENT_CUTOFF:
            raise ValueError("holdout entries must be strictly after 2026-09-13")
        return self


class HoldoutManifest(BaseModel):
    """Manifest schema that deliberately has no number or prize fields."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    policy_id: Literal["prospective_312_after_2026_09_13"]
    cutoff_date: date = DEVELOPMENT_CUTOFF
    target_eligible_draws: Literal[312] = 312
    state: Literal["sealed", "unsealed"] = "sealed"
    entries: list[HoldoutEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def does_not_exceed_target(self) -> HoldoutManifest:
        """Keep the count-based holdout fixed at the preregistered size."""

        if len(self.entries) > HOLDOUT_TARGET_DRAWS:
            raise ValueError("holdout manifest cannot exceed 312 entries")
        return self


def load_holdout_manifest(path: Path) -> HoldoutManifest:
    """Load the strict outcome-free manifest."""

    return HoldoutManifest.model_validate_json(path.read_text(encoding="utf-8"))


def ensure_development_range(start_date: date, end_date: date) -> None:
    """Prevent ordinary collection/build paths from crossing into the holdout."""

    if start_date > end_date:
        raise ValueError("start_date must not follow end_date")
    if end_date > DEVELOPMENT_CUTOFF:
        raise PermissionError(
            "Development commands cannot access draws after 2026-09-13; "
            "use the future integrity-only sealed holdout path"
        )
