"""Conservative access to the official HKJC Mark Six GraphQL result source."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

import httpx

SOURCE_ID = "hkjc_marksix_graphql"
SOURCE_NAME = "HKJC Mark Six results GraphQL"
ENDPOINT = "https://info.cld.hkjc.com/graphql/base/"
PARSER_VERSION = "hkjc-marksix-graphql-v1"

# HKJC's endpoint allowlists the exact operation document used by the official results site.
_FRAGMENT = (
    "fragment lotteryDrawsFragment on LotteryDraw {\n    id\n    year\n"
    "    no\n    openDate\n    closeDate\n    drawDate\n    status\n"
    "    snowballCode\n    snowballName_en\n    snowballName_ch\n"
    "    lotteryPool {\n      sell\n      status\n      totalInvestment\n"
    "      jackpot\n      unitBet\n      estimatedPrize\n"
    "      derivedFirstPrizeDiv\n      lotteryPrizes {\n        type\n"
    "        winningUnit\n        dividend\n      }\n    }\n"
    "    drawResult {\n      drawnNo\n      xDrawnNo\n    }\n  }"
)
QUERY = (
    "\n        " + _FRAGMENT + "\n        query marksixResult("
    "$lastNDraw: Int, $startDate: String, $endDate: String, "
    "$drawType: LotteryDrawType) {\n            lotteryDraws("
    "lastNDraw: $lastNDraw, startDate: $startDate, endDate: $endDate, "
    "drawType: $drawType) {\n              ...lotteryDrawsFragment\n"
    "            }\n        }\n    "
)

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://bet.hkjc.com",
    "Referer": "https://bet.hkjc.com/en/marksix/results",
    "User-Agent": "mark-six-research/0.1 (small reproducibility sample)",
}


@dataclass(frozen=True)
class HkjcRequest:
    """Exact request bytes plus separately searchable parameters."""

    body: bytes
    parameters: dict[str, str | int | bool | None]


def build_recent_draw_request(last_n: int = 5) -> HkjcRequest:
    """Build an allowlisted recent-draw request, capped for Phase 2 sampling."""

    if not 1 <= last_n <= 10:
        raise ValueError("Phase 2 sample size must be between 1 and 10 draws")
    variables: dict[str, str | int | bool | None] = {
        "lastNDraw": last_n,
        "drawType": "All",
    }
    payload = {
        "operationName": "marksixResult",
        "query": QUERY,
        "variables": variables,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return HkjcRequest(body=body, parameters=variables)


def build_date_range_request(start_date: date, end_date: date) -> HkjcRequest:
    """Build a narrow date-range request for source-coverage research."""

    if end_date < start_date:
        raise ValueError("end_date must not precede start_date")
    if (end_date - start_date).days >= 31:
        raise ValueError("Date-range requests are limited to 31 inclusive days")
    variables: dict[str, str | int | bool | None] = {
        "startDate": start_date.strftime("%Y%m%d"),
        "endDate": end_date.strftime("%Y%m%d"),
        "drawType": "All",
    }
    payload = {
        "operationName": "marksixResult",
        "query": QUERY,
        "variables": variables,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return HkjcRequest(body=body, parameters=variables)


def fetch_recent_draws(client: httpx.Client, last_n: int = 5) -> tuple[httpx.Response, HkjcRequest]:
    """Perform one official recent-results request without retries or pagination."""

    request = build_recent_draw_request(last_n)
    response = client.post(ENDPOINT, content=request.body, headers=HEADERS)
    return response, request


def fetch_draw_date_range(
    client: httpx.Client, start_date: date, end_date: date
) -> tuple[httpx.Response, HkjcRequest]:
    """Perform one official narrow date-range request without retries or pagination."""

    request = build_date_range_request(start_date, end_date)
    response = client.post(ENDPOINT, content=request.body, headers=HEADERS)
    return response, request
