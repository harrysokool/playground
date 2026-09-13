from datetime import UTC, date, datetime
from itertools import pairwise
from pathlib import Path

import httpx
import pytest
from hypothesis import given
from hypothesis import strategies as st

from mark_six.collection import (
    DateWindow,
    collect_historical,
    find_cached_window,
    iter_date_windows,
)
from mark_six.provenance import store_http_snapshot
from mark_six.sources.hkjc import (
    ENDPOINT,
    PARSER_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    build_date_range_request,
)

EMPTY = b'{"data":{"lotteryDraws":[]}}'


def store_window(
    root: Path,
    start: date,
    end: date,
    content: bytes = EMPTY,
    *,
    retrieved_at: datetime,
) -> None:
    source_request = build_date_range_request(start, end)
    request = httpx.Request("POST", ENDPOINT, content=source_request.body)
    response = httpx.Response(
        200, headers={"content-type": "application/json"}, content=content, request=request
    )
    store_http_snapshot(
        project_root=root,
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
        response=response,
        parser_version=PARSER_VERSION,
        request_parameters=source_request.parameters,
        request_body=source_request.body,
        retrieved_at=retrieved_at,
    )


@given(
    start=st.dates(min_value=date(1975, 1, 1), max_value=date(2026, 9, 13)),
    length=st.integers(min_value=0, max_value=365),
    width=st.integers(min_value=1, max_value=31),
)
def test_windows_cover_range_once_without_overlap(start: date, length: int, width: int) -> None:
    end = min(start.fromordinal(start.toordinal() + length), date(2026, 9, 13))
    windows = list(iter_date_windows(start, end, width))

    assert windows[0].start_date == start
    assert windows[-1].end_date == end
    assert all((window.end_date - window.start_date).days < width for window in windows)
    assert all(
        left.end_date.toordinal() + 1 == right.start_date.toordinal()
        for left, right in pairwise(windows)
    )


def test_partial_ingestion_resumes_and_reuses_valid_empty_cache(tmp_path: Path) -> None:
    store_window(
        tmp_path,
        date(2026, 1, 1),
        date(2026, 1, 2),
        retrieved_at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": {"lotteryDraws": []}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        items = collect_historical(
            project_root=tmp_path,
            client=client,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 4),
            window_days=2,
            delay_seconds=0,
        )

    assert [item.reused_cache for item in items] == [True, False]
    assert len(requests) == 1
    assert find_cached_window(tmp_path, DateWindow(date(2026, 1, 1), date(2026, 1, 2)))


def test_malformed_cache_is_not_reused(tmp_path: Path) -> None:
    store_window(
        tmp_path,
        date(2026, 1, 1),
        date(2026, 1, 1),
        b"not-json",
        retrieved_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    calls = 0

    def respond(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"data": {"lotteryDraws": []}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = collect_historical(
            project_root=tmp_path,
            client=client,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            delay_seconds=0,
        )

    assert calls == 1
    assert not result[0].reused_cache


def test_collection_rejects_holdout_before_network_access(tmp_path: Path) -> None:
    calls = 0

    def respond(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"data": {"lotteryDraws": []}})

    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        pytest.raises(PermissionError, match="cannot access draws after"),
    ):
        collect_historical(
            project_root=tmp_path,
            client=client,
            start_date=date(2026, 9, 13),
            end_date=date(2026, 9, 14),
        )
    assert calls == 0
