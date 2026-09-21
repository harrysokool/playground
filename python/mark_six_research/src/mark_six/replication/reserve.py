"""Explicitly authorized Phase 7 reserve-outcome loading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

import duckdb
import numpy as np

from mark_six.holdout import load_holdout_manifest
from mark_six.prediction.models import PredictionHistory
from mark_six.prediction.reserve import protected_draw_ids
from mark_six.replication.models import ReplicationConfig


class ReserveOpeningError(RuntimeError):
    """Raised when the one-time Phase 7 opening boundary is violated."""


@dataclass(frozen=True)
class ReserveOpeningAuthorization:
    """Explicit capability binding an opening to the frozen protocol and manifest."""

    protocol_version: str
    baseline_commit: str
    reserve_manifest_sha256: str
    purpose: str = "phase7_one_time_historical_replication"


@dataclass(frozen=True)
class ReserveOpeningEvent:
    """Auditable description of the controlled outcome join."""

    opened_at: datetime
    protocol_version: str
    reserve_manifest_sha256: str
    source_table: str
    first_draw_id: str
    final_draw_id: str
    reserve_draw_count: int
    prospective_holdout_accessed: bool = False


def authorize_reserve_opening(config: ReplicationConfig) -> ReserveOpeningAuthorization:
    """Issue the narrow capability used only by the Phase 7 runner."""

    return ReserveOpeningAuthorization(
        protocol_version=config.protocol_version,
        baseline_commit=config.baseline_commit,
        reserve_manifest_sha256=config.reserve_manifest_sha256,
    )


def _validate_authorization(
    config: ReplicationConfig, authorization: ReserveOpeningAuthorization
) -> None:
    if authorization.purpose != "phase7_one_time_historical_replication":
        raise ReserveOpeningError("reserve opening purpose is not authorized")
    if (
        authorization.protocol_version != config.protocol_version
        or authorization.baseline_commit != config.baseline_commit
        or authorization.reserve_manifest_sha256 != config.reserve_manifest_sha256
    ):
        raise ReserveOpeningError(
            "reserve opening authorization does not match the frozen protocol"
        )


def load_authorized_replication_history(
    project_root: Path,
    config: ReplicationConfig,
    reserve_manifest: dict[str, object],
    authorization: ReserveOpeningAuthorization,
    *,
    opened_at: datetime | None = None,
) -> tuple[PredictionHistory, ReserveOpeningEvent]:
    """Load exactly 2,700 initialization and 676 registered reserve outcomes."""

    _validate_authorization(config, authorization)
    holdout = load_holdout_manifest(project_root / "data" / "holdout" / "manifest.json")
    if holdout.state != "sealed" or holdout.entries:
        raise ReserveOpeningError("prospective holdout must remain sealed with zero entries")
    dataset = project_root / "data" / "processed" / config.dataset_id
    query = """
        WITH eligible AS (
            SELECT draw_id, draw_date
            FROM read_parquet(?)
            WHERE status = 'completed' AND draw_date BETWEEN ? AND ?
            ORDER BY draw_date, draw_id
        )
        SELECT e.draw_id, e.draw_date, n.number_value
        FROM eligible AS e
        JOIN read_parquet(?) AS n USING (draw_id)
        WHERE n.number_role = 'main'
        ORDER BY e.draw_date, e.draw_id, n.number_value
    """
    connection = duckdb.connect(":memory:")
    try:
        frame = connection.execute(
            query,
            [
                str(dataset / "draws.parquet"),
                config.history_start_date.isoformat(),
                config.reserve.final_draw_date.isoformat(),
                str(dataset / "draw_numbers.parquet"),
            ],
        ).fetchdf()
    finally:
        connection.close()
    rows = cast(list[dict[str, Any]], frame.to_dict(orient="records"))
    grouped: dict[tuple[date, str], list[int]] = {}
    for row in rows:
        raw_date = row["draw_date"]
        draw_date = raw_date.date() if isinstance(raw_date, datetime) else raw_date
        if not isinstance(draw_date, date):
            raise ReserveOpeningError("draw date is not date-like")
        grouped.setdefault((draw_date, str(row["draw_id"])), []).append(int(row["number_value"]))
    ordered = sorted(grouped.items())
    expected_total = config.initial_history_draws + config.reserve.draw_count
    if len(ordered) != expected_total:
        raise ReserveOpeningError(f"expected {expected_total} eligible draws, found {len(ordered)}")
    draw_ids = tuple(draw_id for (_, draw_id), _ in ordered)
    if (
        draw_ids[0] != config.history_first_draw_id
        or draw_ids[config.initial_history_draws - 1] != config.initial_history_final_draw_id
        or draw_ids[config.initial_history_draws] != config.reserve.first_draw_id
        or draw_ids[-1] != config.reserve.final_draw_id
    ):
        raise ReserveOpeningError("eligible history or reserve boundary differs from protocol")
    manifest_ids = tuple(
        str(entry["draw_id"])
        for entry in cast(list[dict[str, object]], reserve_manifest["entries"])
    )
    reserve_ids = draw_ids[config.initial_history_draws :]
    if reserve_ids != manifest_ids or frozenset(reserve_ids) != protected_draw_ids(
        reserve_manifest
    ):
        raise ReserveOpeningError("loaded reserve IDs differ from the metadata-only manifest")
    mains: list[list[int]] = []
    for (_, draw_id), values in ordered:
        if len(values) != 6 or len(set(values)) != 6:
            raise ReserveOpeningError(f"invalid main-number cardinality in {draw_id}")
        if any(value < 1 or value > config.reserve.pool_size for value in values):
            raise ReserveOpeningError(f"number outside 6/49 pool in {draw_id}")
        mains.append(sorted(values))
    history = PredictionHistory(
        period_id=config.reserve.period_id,
        pool_size=config.reserve.pool_size,
        draw_ids=draw_ids,
        draw_dates=tuple(draw_date for (draw_date, _), _ in ordered),
        mains=np.asarray(mains, dtype=np.int64),
    )
    event = ReserveOpeningEvent(
        opened_at=opened_at or datetime.now(UTC),
        protocol_version=config.protocol_version,
        reserve_manifest_sha256=config.reserve_manifest_sha256,
        source_table=f"data/processed/{config.dataset_id}/draw_numbers.parquet",
        first_draw_id=reserve_ids[0],
        final_draw_id=reserve_ids[-1],
        reserve_draw_count=len(reserve_ids),
    )
    return history, event
