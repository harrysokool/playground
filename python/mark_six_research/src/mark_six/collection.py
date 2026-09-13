"""Conservative, resumable collection of official historical draw windows."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx

from mark_six.holdout import ensure_development_range
from mark_six.provenance import (
    SnapshotMetadata,
    load_snapshot_metadata,
    store_http_snapshot,
    verify_snapshot,
)
from mark_six.sources.hkjc import (
    PARSER_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    build_date_range_request,
    fetch_draw_date_range,
)


@dataclass(frozen=True)
class DateWindow:
    """Inclusive source request window."""

    start_date: date
    end_date: date


@dataclass(frozen=True)
class CollectionItem:
    """One cached or newly retrieved request result."""

    window: DateWindow
    raw_path: Path
    metadata_path: Path
    metadata: SnapshotMetadata
    reused_cache: bool


def iter_date_windows(
    start_date: date, end_date: date, window_days: int = 31
) -> Iterator[DateWindow]:
    """Yield nonoverlapping inclusive windows without crossing the requested dates."""

    if start_date > end_date:
        raise ValueError("start_date must not follow end_date")
    if not 1 <= window_days <= 31:
        raise ValueError("window_days must be between 1 and 31")
    current = start_date
    while current <= end_date:
        window_end = min(current + timedelta(days=window_days - 1), end_date)
        yield DateWindow(current, window_end)
        current = window_end + timedelta(days=1)


def _response_has_expected_shape(content: bytes) -> bool:
    try:
        root = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(root, dict)
        and not root.get("errors")
        and isinstance(root.get("data"), dict)
        and isinstance(root["data"].get("lotteryDraws"), list)
    )


def find_cached_window(
    project_root: Path,
    window: DateWindow,
) -> tuple[Path, SnapshotMetadata] | None:
    """Return the newest verified exact-range snapshot, if one exists."""

    request = build_date_range_request(window.start_date, window.end_date)
    source_root = project_root / "data" / "raw" / SOURCE_ID
    matches: list[tuple[Path, SnapshotMetadata]] = []
    for path in source_root.glob("*/*/*.metadata.json"):
        try:
            metadata = load_snapshot_metadata(path)
        except (OSError, ValueError):
            continue
        if (
            metadata.source_id == SOURCE_ID
            and metadata.http_status == 200
            and metadata.request_parameters == request.parameters
            and verify_snapshot(project_root, metadata)
            and _response_has_expected_shape((project_root / metadata.raw_path).read_bytes())
        ):
            matches.append((path, metadata))
    if not matches:
        return None
    return max(matches, key=lambda item: item[1].retrieved_at)


def collect_historical(
    *,
    project_root: Path,
    client: httpx.Client,
    start_date: date,
    end_date: date,
    window_days: int = 31,
    delay_seconds: float = 1.0,
    revision_check: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    on_item: Callable[[CollectionItem], None] | None = None,
) -> list[CollectionItem]:
    """Collect sequential windows, reusing valid cache entries unless revision checking."""

    ensure_development_range(start_date, end_date)
    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative")
    items: list[CollectionItem] = []
    made_request = False
    for window in iter_date_windows(start_date, end_date, window_days):
        cached = None if revision_check else find_cached_window(project_root, window)
        if cached is not None:
            metadata_path, metadata = cached
            item = CollectionItem(
                window=window,
                raw_path=project_root / metadata.raw_path,
                metadata_path=metadata_path,
                metadata=metadata,
                reused_cache=True,
            )
            items.append(item)
            if on_item is not None:
                on_item(item)
            continue

        if made_request and delay_seconds:
            sleep(delay_seconds)
        response, request = fetch_draw_date_range(client, window.start_date, window.end_date)
        made_request = True
        raw_path, metadata_path = store_http_snapshot(
            project_root=project_root,
            source_id=SOURCE_ID,
            source_name=SOURCE_NAME,
            response=response,
            parser_version=PARSER_VERSION,
            request_parameters=request.parameters,
            request_body=request.body,
        )
        metadata = load_snapshot_metadata(metadata_path)
        response.raise_for_status()
        if not _response_has_expected_shape(response.content):
            raise RuntimeError(
                f"Unexpected HKJC response structure for {window.start_date}..{window.end_date}; "
                f"preserved as {raw_path.relative_to(project_root)}"
            )
        item = CollectionItem(
            window=window,
            raw_path=raw_path,
            metadata_path=metadata_path,
            metadata=metadata,
            reused_cache=False,
        )
        items.append(item)
        if on_item is not None:
            on_item(item)
    return items
