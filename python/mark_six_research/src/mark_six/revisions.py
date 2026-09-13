"""Controlled requery and field-level source revision comparison."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from mark_six.collection import DateWindow, collect_historical, find_cached_window
from mark_six.provenance import sha256_bytes


@dataclass(frozen=True)
class DrawRevision:
    """Field groups that changed for one official draw."""

    source_draw_id: str
    changed_groups: tuple[str, ...]


@dataclass(frozen=True)
class RevisionComparison:
    """Comparison of an old cached range with one new immutable snapshot."""

    old_snapshot_id: str
    new_snapshot_id: str
    old_content_sha256: str
    new_content_sha256: str
    raw_changed: bool
    draw_revisions: tuple[DrawRevision, ...]
    added_draw_ids: tuple[str, ...]
    removed_draw_ids: tuple[str, ...]
    record_path: Path


def _draw_map(content: bytes) -> dict[str, dict[str, Any]]:
    root = json.loads(content)
    items = root["data"]["lotteryDraws"]
    return {str(item["id"]): item for item in items}


def _changed_groups(old: dict[str, Any], new: dict[str, Any]) -> tuple[str, ...]:
    groups = {
        "draw_identity_and_dates": ("year", "no", "openDate", "closeDate", "drawDate", "status"),
        "draw_numbers": ("drawResult",),
        "special_draw_metadata": ("snowballCode", "snowballName_en", "snowballName_ch"),
    }
    changed = [
        name
        for name, fields in groups.items()
        if any(old.get(field) != new.get(field) for field in fields)
    ]
    old_pool = old.get("lotteryPool", {})
    new_pool = new.get("lotteryPool", {})
    pool_groups = {
        "turnover": ("totalInvestment",),
        "jackpot_fields": ("jackpot", "estimatedPrize", "derivedFirstPrizeDiv"),
        "stake_and_pool_status": ("unitBet", "sell", "status"),
        "prizes_and_winning_units": ("lotteryPrizes",),
    }
    changed.extend(
        name
        for name, fields in pool_groups.items()
        if any(old_pool.get(field) != new_pool.get(field) for field in fields)
    )
    return tuple(changed)


def revision_check(
    *,
    project_root: Path,
    client: httpx.Client,
    start_date: date,
    end_date: date,
) -> RevisionComparison:
    """Requery one cached window once, preserve it, and record field-level differences."""

    window = DateWindow(start_date, end_date)
    old_cached = find_cached_window(project_root, window)
    if old_cached is None:
        raise FileNotFoundError("Revision checking requires an existing valid exact-range snapshot")
    _, old_metadata = old_cached
    old_content = (project_root / old_metadata.raw_path).read_bytes()
    new_item = collect_historical(
        project_root=project_root,
        client=client,
        start_date=start_date,
        end_date=end_date,
        window_days=(end_date - start_date).days + 1,
        delay_seconds=0,
        revision_check=True,
    )[0]
    new_content = new_item.raw_path.read_bytes()
    old_draws = _draw_map(old_content)
    new_draws = _draw_map(new_content)
    common = sorted(old_draws.keys() & new_draws.keys())
    changes = tuple(
        DrawRevision(source_draw_id=draw_id, changed_groups=groups)
        for draw_id in common
        if (groups := _changed_groups(old_draws[draw_id], new_draws[draw_id]))
    )
    record_dir = project_root / "data" / "interim" / "revision_checks"
    record_dir.mkdir(parents=True, exist_ok=True)
    record_path = record_dir / f"{new_item.metadata.snapshot_id.replace(':', '_')}.json"
    record = {
        "old_snapshot_id": old_metadata.snapshot_id,
        "new_snapshot_id": new_item.metadata.snapshot_id,
        "old_content_sha256": sha256_bytes(old_content),
        "new_content_sha256": sha256_bytes(new_content),
        "raw_changed": old_content != new_content,
        "draw_revisions": [asdict(item) for item in changes],
        "added_draw_ids": sorted(new_draws.keys() - old_draws.keys()),
        "removed_draw_ids": sorted(old_draws.keys() - new_draws.keys()),
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return RevisionComparison(
        old_snapshot_id=old_metadata.snapshot_id,
        new_snapshot_id=new_item.metadata.snapshot_id,
        old_content_sha256=sha256_bytes(old_content),
        new_content_sha256=sha256_bytes(new_content),
        raw_changed=old_content != new_content,
        draw_revisions=changes,
        added_draw_ids=tuple(sorted(new_draws.keys() - old_draws.keys())),
        removed_draw_ids=tuple(sorted(old_draws.keys() - new_draws.keys())),
        record_path=record_path,
    )
