"""Source-neutral records used by the Phase 2 parser and validator."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RuleVersion(BaseModel):
    """A dated, evidence-backed set of draw constraints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_version_id: str = Field(min_length=1)
    effective_from: date | None
    effective_to: date | None
    verification_status: Literal["partially_verified", "verified"]
    number_min: int
    number_max: int
    number_range_status: Literal["verified", "conservative_upper_bound"] = "verified"
    main_numbers_drawn: int = Field(gt=0)
    extra_numbers_drawn: int = Field(ge=0)
    unit_stake_hkd_cents: int = Field(gt=0)
    unit_stake_status: Literal["verified", "source_observed"] = "verified"
    partial_unit_stake_hkd_cents: int | None = Field(default=None, gt=0)
    prize_divisions: int = Field(gt=0)
    reported_prize_division_count: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def interval_is_ordered(self) -> RuleVersion:
        """Reject an inverted effective interval."""

        if self.number_max < self.number_min:
            raise ValueError("number_max must not be below number_min")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("effective_to must not precede effective_from")
        return self


class ParsedPrize(BaseModel):
    """One source-reported prize division for a draw."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    division: int
    source_winning_unit_amount: Decimal
    winning_units: Decimal
    dividend_hkd_cents: int | None


class ParsedDraw(BaseModel):
    """A lossless-enough normalized view of one official GraphQL draw."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_draw_id: str = Field(min_length=1)
    draw_number: str = Field(min_length=1)
    draw_date: date
    open_date: date | None
    close_at: datetime | None
    source_status: str = Field(min_length=1)
    snowball_code: str | None
    snowball_name_en: str | None
    pool_sell: bool | None
    pool_status: str | None
    turnover_hkd_cents: int | None
    reported_jackpot_hkd_cents: int | None
    unit_stake_hkd_cents: int
    estimated_first_prize_hkd_cents: int | None
    reported_derived_first_prize_hkd_cents: int | None
    main_numbers: tuple[int, ...]
    extra_number: int
    prizes: tuple[ParsedPrize, ...]
    rule_version_id: str = Field(min_length=1)


class ValidationIssue(BaseModel):
    """A deterministic, machine-readable validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"
