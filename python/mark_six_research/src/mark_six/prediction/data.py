"""Guarded loading for Phase 6 chronological main-number histories."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

import duckdb

from mark_six.prediction.models import PeriodSpec, PredictionConfig, PredictionHistory
from mark_six.prediction.reserve import protected_draw_ids, reject_protected_ids


class PredictionDataError(RuntimeError):
    """Raised when a predictive-analysis history violates the frozen split."""


def _query_history(
    project_root: Path,
    config: PredictionConfig,
    spec: PeriodSpec,
    *,
    limit: int | None,
) -> list[dict[str, Any]]:
    dataset = project_root / "data" / "processed" / config.dataset_id
    draws_path = str(dataset / "draws.parquet")
    numbers_path = str(dataset / "draw_numbers.parquet")
    limit_clause = "" if limit is None else f"LIMIT {limit:d}"
    query = f"""
        WITH eligible AS (
            SELECT draw_id, draw_date
            FROM read_parquet(?)
            WHERE status = 'completed' AND draw_date BETWEEN ? AND ?
            ORDER BY draw_date, draw_id
            {limit_clause}
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
            [draws_path, spec.start.isoformat(), spec.end.isoformat(), numbers_path],
        ).fetchdf()
    finally:
        connection.close()
    return cast(list[dict[str, Any]], frame.to_dict(orient="records"))


def _rows_to_history(spec: PeriodSpec, rows: list[dict[str, Any]]) -> PredictionHistory:
    grouped: dict[tuple[date, str], list[int]] = {}
    for row in rows:
        raw_date = row["draw_date"]
        draw_date = raw_date.date() if isinstance(raw_date, datetime) else raw_date
        if not isinstance(draw_date, date):
            raise PredictionDataError("draw date is not date-like")
        key = (draw_date, str(row["draw_id"]))
        grouped.setdefault(key, []).append(int(row["number_value"]))
    ordered = sorted(grouped.items())
    if not ordered:
        raise PredictionDataError(f"no completed draws in {spec.period_id}")
    for (draw_date, draw_id), numbers in ordered:
        if len(numbers) != 6 or len(set(numbers)) != 6:
            raise PredictionDataError(f"invalid main-number cardinality in {draw_id}")
        if any(number < 1 or number > spec.pool_size for number in numbers):
            raise PredictionDataError(f"number outside pool on {draw_date}: {draw_id}")
    import numpy as np

    return PredictionHistory(
        period_id=spec.period_id,
        pool_size=spec.pool_size,
        draw_ids=tuple(draw_id for (_, draw_id), _ in ordered),
        draw_dates=tuple(draw_date for (draw_date, _), _ in ordered),
        mains=np.asarray([sorted(numbers) for _, numbers in ordered], dtype=np.int64),
    )


def load_primary_history(
    project_root: Path,
    config: PredictionConfig,
    reserve_manifest: dict[str, object],
) -> PredictionHistory:
    """Load only the first 2,700 primary outcomes through the SQL split guard."""

    rows = _query_history(project_root, config, config.primary, limit=config.primary.phase6_draws)
    history = _rows_to_history(config.primary, rows)
    if history.draw_count != config.primary.phase6_draws:
        raise PredictionDataError("Phase 6 primary outcome count mismatch")
    protected = protected_draw_ids(reserve_manifest)
    reject_protected_ids(frozenset(history.draw_ids), protected)
    return history


def load_secondary_history(
    project_root: Path, config: PredictionConfig, spec: PeriodSpec
) -> PredictionHistory:
    """Load one fixed older-pool replication period."""

    return _rows_to_history(spec, _query_history(project_root, config, spec, limit=None))
