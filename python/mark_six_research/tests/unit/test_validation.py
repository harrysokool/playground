from datetime import date
from pathlib import Path

from mark_six.domain.models import ParsedDraw, RuleVersion
from mark_six.domain.rules import CURRENT_RULES, RULES_1995_SAMPLE_PARTIAL
from mark_six.domain.validation import validate_draw
from mark_six.sources.hkjc_parser import parse_hkjc_payload

FIXTURES = Path(__file__).parents[1] / "fixtures" / "hkjc"


def current_draw() -> ParsedDraw:
    return parse_hkjc_payload((FIXTURES / "current_sample.json").read_bytes(), CURRENT_RULES)[0]


def codes(draw: ParsedDraw, rule: RuleVersion) -> set[str]:
    return {issue.code for issue in validate_draw(draw, rule)}


def test_real_sample_passes_current_rule_validation() -> None:
    assert validate_draw(current_draw(), CURRENT_RULES) == []


def test_duplicate_main_numbers_are_rejected() -> None:
    draw = current_draw().model_copy(update={"main_numbers": (9, 9, 24, 33, 40, 47)})
    assert "duplicate_main_number" in codes(draw, CURRENT_RULES)


def test_invalid_extra_number_is_rejected() -> None:
    draw = current_draw().model_copy(update={"extra_number": 9})
    assert "extra_number_duplicates_main" in codes(draw, CURRENT_RULES)


def test_out_of_range_numbers_are_rejected() -> None:
    draw = current_draw().model_copy(update={"main_numbers": (9, 18, 24, 33, 40, 50)})
    assert "main_number_out_of_range" in codes(draw, CURRENT_RULES)


def test_negative_source_values_are_reported() -> None:
    draw = current_draw().model_copy(update={"turnover_hkd_cents": -1})
    assert "negative_money" in codes(draw, CURRENT_RULES)


def test_rule_linkage_must_match() -> None:
    assert "rule_version_mismatch" in codes(current_draw(), RULES_1995_SAMPLE_PARTIAL)


def test_range_validation_uses_rule_version_not_current_assumption() -> None:
    legacy_rule = RuleVersion(
        rule_version_id="test_pool_45",
        effective_from=date(1990, 1, 1),
        effective_to=date(1995, 12, 31),
        verification_status="partially_verified",
        number_min=1,
        number_max=45,
        main_numbers_drawn=6,
        extra_numbers_drawn=1,
        unit_stake_hkd_cents=400,
        prize_divisions=7,
    )
    draw = current_draw().model_copy(
        update={
            "draw_date": date(1995, 1, 3),
            "main_numbers": (9, 18, 24, 33, 40, 46),
            "unit_stake_hkd_cents": 400,
            "rule_version_id": legacy_rule.rule_version_id,
        }
    )

    assert "main_number_out_of_range" in codes(draw, legacy_rule)
    current_version = draw.model_copy(
        update={
            "draw_date": date(2026, 9, 12),
            "unit_stake_hkd_cents": 1_000,
            "rule_version_id": CURRENT_RULES.rule_version_id,
        }
    )
    assert "main_number_out_of_range" not in codes(current_version, CURRENT_RULES)
