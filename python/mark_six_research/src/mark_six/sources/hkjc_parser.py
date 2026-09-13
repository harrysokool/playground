"""Strict parser for sampled official HKJC Mark Six GraphQL responses."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from mark_six.domain.models import ParsedDraw, ParsedPrize, RuleVersion

_SOURCE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[+-]\d{2}:\d{2})?$")


class HkjcParseError(ValueError):
    """Raised when an official response does not match the reviewed source contract."""


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HkjcParseError(f"{path} must be an object")
    return value


def _list(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise HkjcParseError(f"{path} must be an array")
    return value


def _required_text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HkjcParseError(f"{path} must be a non-empty string")
    return value


def _required_scalar_text(value: object, path: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise HkjcParseError(f"{path} must be a non-empty string or integer")
    text = str(value)
    if not text:
        raise HkjcParseError(f"{path} must not be empty")
    return text


def _optional_text(value: object, path: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise HkjcParseError(f"{path} must be a string or null")
    return value


def _optional_bool(value: object, path: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise HkjcParseError(f"{path} must be a boolean or null")
    return value


def _decimal(value: object, path: str) -> Decimal:
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise HkjcParseError(f"{path} must be a decimal string or integer")
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise HkjcParseError(f"{path} is not a decimal") from error


def _optional_money_cents(value: object, path: str) -> int | None:
    if value is None or value == "":
        return None
    amount = _decimal(value, path) * 100
    integral = amount.to_integral_value()
    if amount != integral:
        raise HkjcParseError(f"{path} has precision finer than one cent")
    return int(integral)


def _required_date(value: object, path: str) -> date:
    text = _required_text(value, path)
    if _SOURCE_DATE.fullmatch(text) is None:
        raise HkjcParseError(f"{path} is not an ISO date with an optional offset")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as error:
        raise HkjcParseError(f"{path} is not an ISO date") from error


def _optional_date(value: object, path: str) -> date | None:
    text = _optional_text(value, path)
    return None if text is None else _required_date(text, path)


def _optional_datetime(value: object, path: str) -> datetime | None:
    text = _optional_text(value, path)
    if text is None:
        return None
    try:
        result = datetime.fromisoformat(text)
    except ValueError as error:
        raise HkjcParseError(f"{path} is not an ISO datetime") from error
    if result.tzinfo is None:
        raise HkjcParseError(f"{path} must include a timezone offset")
    return result


def parse_hkjc_draw(item: object, index: int, rule: RuleVersion) -> ParsedDraw:
    path = f"data.lotteryDraws[{index}]"
    draw = _mapping(item, path)
    pool = _mapping(draw.get("lotteryPool"), f"{path}.lotteryPool")
    result = _mapping(draw.get("drawResult"), f"{path}.drawResult")

    unit_hkd = _decimal(pool.get("unitBet"), f"{path}.lotteryPool.unitBet")
    unit_cents = _optional_money_cents(pool.get("unitBet"), f"{path}.lotteryPool.unitBet")
    if unit_cents is None or unit_hkd <= 0:
        raise HkjcParseError(f"{path}.lotteryPool.unitBet must be positive")

    main_values = _list(result.get("drawnNo"), f"{path}.drawResult.drawnNo")
    try:
        main_numbers = tuple(
            int(_required_scalar_text(value, f"{path}.drawResult.drawnNo")) for value in main_values
        )
        extra_number = int(
            _required_scalar_text(result.get("xDrawnNo"), f"{path}.drawResult.xDrawnNo")
        )
    except ValueError as error:
        raise HkjcParseError(f"{path}.drawResult contains a non-integer number") from error

    prizes: list[ParsedPrize] = []
    prize_items = _list(pool.get("lotteryPrizes"), f"{path}.lotteryPool.lotteryPrizes")
    for prize_index, prize_item in enumerate(prize_items):
        prize_path = f"{path}.lotteryPool.lotteryPrizes[{prize_index}]"
        prize = _mapping(prize_item, prize_path)
        try:
            division = int(_required_scalar_text(prize.get("type"), f"{prize_path}.type"))
        except ValueError as error:
            raise HkjcParseError(f"{prize_path}.type must be an integer string") from error
        source_units = _decimal(prize.get("winningUnit"), f"{prize_path}.winningUnit")
        prizes.append(
            ParsedPrize(
                division=division,
                source_winning_unit_amount=source_units,
                winning_units=source_units / unit_hkd,
                dividend_hkd_cents=_optional_money_cents(
                    prize.get("dividend"), f"{prize_path}.dividend"
                ),
            )
        )

    year = _required_scalar_text(draw.get("year"), f"{path}.year")
    number = _required_scalar_text(draw.get("no"), f"{path}.no")
    if len(year) != 4 or not year.isdecimal() or not number.isdecimal():
        raise HkjcParseError(f"{path}.year and .no must be numeric source identifiers")
    return ParsedDraw(
        source_draw_id=_required_text(draw.get("id"), f"{path}.id"),
        draw_number=f"{year[-2:]}/{number.zfill(3)}",
        draw_date=_required_date(draw.get("drawDate"), f"{path}.drawDate"),
        open_date=_optional_date(draw.get("openDate"), f"{path}.openDate"),
        close_at=_optional_datetime(draw.get("closeDate"), f"{path}.closeDate"),
        source_status=_required_text(draw.get("status"), f"{path}.status"),
        snowball_code=_optional_text(draw.get("snowballCode"), f"{path}.snowballCode"),
        snowball_name_en=_optional_text(draw.get("snowballName_en"), f"{path}.snowballName_en"),
        pool_sell=_optional_bool(pool.get("sell"), f"{path}.lotteryPool.sell"),
        pool_status=_optional_text(pool.get("status"), f"{path}.lotteryPool.status"),
        turnover_hkd_cents=_optional_money_cents(
            pool.get("totalInvestment"), f"{path}.lotteryPool.totalInvestment"
        ),
        reported_jackpot_hkd_cents=_optional_money_cents(
            pool.get("jackpot"), f"{path}.lotteryPool.jackpot"
        ),
        unit_stake_hkd_cents=unit_cents,
        estimated_first_prize_hkd_cents=_optional_money_cents(
            pool.get("estimatedPrize"), f"{path}.lotteryPool.estimatedPrize"
        ),
        reported_derived_first_prize_hkd_cents=_optional_money_cents(
            pool.get("derivedFirstPrizeDiv"), f"{path}.lotteryPool.derivedFirstPrizeDiv"
        ),
        main_numbers=main_numbers,
        extra_number=extra_number,
        prizes=tuple(prizes),
        rule_version_id=rule.rule_version_id,
    )


def parse_hkjc_payload(payload: bytes, rule: RuleVersion) -> list[ParsedDraw]:
    """Parse an exact official response without filling absent optional values."""

    try:
        root = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HkjcParseError("response is not valid UTF-8 JSON") from error
    root_mapping = _mapping(root, "response")
    if root_mapping.get("errors"):
        raise HkjcParseError("GraphQL response contains errors")
    data = _mapping(root_mapping.get("data"), "data")
    draws = _list(data.get("lotteryDraws"), "data.lotteryDraws")
    return [parse_hkjc_draw(item, index, rule) for index, item in enumerate(draws)]


def parse_hkjc_payload_with_rules(
    payload: bytes,
    resolver: Callable[[date, int], RuleVersion],
) -> list[ParsedDraw]:
    """Parse a mixed-period response using source date and stake to select each rule."""

    try:
        root = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HkjcParseError("response is not valid UTF-8 JSON") from error
    root_mapping = _mapping(root, "response")
    if root_mapping.get("errors"):
        raise HkjcParseError("GraphQL response contains errors")
    data = _mapping(root_mapping.get("data"), "data")
    items = _list(data.get("lotteryDraws"), "data.lotteryDraws")
    parsed: list[ParsedDraw] = []
    for index, item in enumerate(items):
        parsed.append(parse_hkjc_draw_with_rules(item, index, resolver))
    return parsed


def parse_hkjc_draw_with_rules(
    item: object,
    index: int,
    resolver: Callable[[date, int], RuleVersion],
) -> ParsedDraw:
    """Parse one draw after resolving rules from only its source date and stake."""

    path = f"data.lotteryDraws[{index}]"
    source = _mapping(item, path)
    pool = _mapping(source.get("lotteryPool"), f"{path}.lotteryPool")
    draw_date = _required_date(source.get("drawDate"), f"{path}.drawDate")
    stake = _optional_money_cents(pool.get("unitBet"), f"{path}.lotteryPool.unitBet")
    if stake is None:
        raise HkjcParseError(f"{path}.lotteryPool.unitBet is required for rule assignment")
    return parse_hkjc_draw(item, index, resolver(draw_date, stake))
