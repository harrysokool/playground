import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from mark_six.domain.rules import CURRENT_RULES, RULES_1995_SAMPLE_PARTIAL
from mark_six.sources.hkjc_parser import HkjcParseError, parse_hkjc_payload

FIXTURES = Path(__file__).parents[1] / "fixtures" / "hkjc"


def test_parses_real_current_official_sample() -> None:
    draws = parse_hkjc_payload((FIXTURES / "current_sample.json").read_bytes(), CURRENT_RULES)

    assert [draw.source_draw_id for draw in draws] == ["202699N", "202696N"]
    assert draws[0].draw_number == "26/099"
    assert draws[0].draw_date == date(2026, 9, 12)
    assert draws[0].main_numbers == (9, 18, 24, 33, 40, 47)
    assert draws[0].extra_number == 11
    assert draws[0].turnover_hkd_cents == 4_259_930_300
    assert draws[1].snowball_code == "ANN"
    assert draws[1].prizes[0].source_winning_unit_amount == Decimal("35")
    assert draws[1].prizes[0].winning_units == Decimal("3.5")
    assert draws[1].prizes[0].dividend_hkd_cents == 6_337_661_000


def test_preserves_legitimate_missing_optional_fields() -> None:
    draws = parse_hkjc_payload(
        (FIXTURES / "legacy_missing_optional_sample.json").read_bytes(),
        RULES_1995_SAMPLE_PARTIAL,
    )

    draw = draws[0]
    assert draw.open_date is None
    assert draw.close_at is None
    assert draw.turnover_hkd_cents is None
    assert draw.reported_jackpot_hkd_cents is None
    assert draw.estimated_first_prize_hkd_cents is None
    assert draw.reported_derived_first_prize_hkd_cents is None


@pytest.mark.parametrize(
    "payload, message",
    [
        (b"not-json", "not valid"),
        (b'{"data": {}}', "lotteryDraws"),
        (b'{"data": {"lotteryDraws": {}}}', "must be an array"),
        (b'{"errors": [{"message": "no"}], "data": {}}', "contains errors"),
    ],
)
def test_rejects_malformed_source_structure(payload: bytes, message: str) -> None:
    with pytest.raises(HkjcParseError, match=message):
        parse_hkjc_payload(payload, CURRENT_RULES)


def test_rejects_missing_required_field() -> None:
    payload = json.loads((FIXTURES / "current_sample.json").read_text(encoding="utf-8"))
    del payload["data"]["lotteryDraws"][0]["drawDate"]

    with pytest.raises(HkjcParseError, match="drawDate"):
        parse_hkjc_payload(json.dumps(payload).encode(), CURRENT_RULES)
