"""Outcome-free Phase 7 historical reserve manifest and access guard."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from mark_six.prediction.models import PredictionConfig


class ReserveIntegrityError(RuntimeError):
    """Raised when protected-reserve metadata or access is invalid."""


def canonical_json_bytes(value: object) -> bytes:
    """Serialize a manifest deterministically."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def reserve_manifest_path(project_root: Path, config: PredictionConfig) -> Path:
    """Return the tracked reserve-manifest path."""

    return project_root / config.reserve_manifest_path


def expected_reserve_manifest(project_root: Path, config: PredictionConfig) -> dict[str, object]:
    """Build reserve metadata without reading the draw-number table."""

    draws_path = project_root / "data" / "processed" / config.dataset_id / "draws.parquet"
    rows: list[dict[str, Any]] = pq.read_table(
        draws_path,
        columns=["draw_id", "draw_date", "rule_version_id", "status"],
    ).to_pylist()
    primary = sorted(
        (
            row
            for row in rows
            if row["status"] == "completed"
            and config.primary.start <= row["draw_date"] <= config.primary.end
        ),
        key=lambda row: (row["draw_date"], row["draw_id"]),
    )
    if len(primary) != config.primary.population_draws:
        raise ReserveIntegrityError(
            f"expected {config.primary.population_draws} primary rows, found {len(primary)}"
        )
    reserve = primary[config.primary.phase6_draws :]
    if len(reserve) != config.primary.reserve_draws:
        raise ReserveIntegrityError("protected reserve count differs from the protocol")
    manifest: dict[str, object] = {
        "schema_version": "1",
        "reserve_id": "phase7-historical-prediction-reserve-v1",
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "protocol_version": config.protocol_version,
        "split_rule": (
            "last 676 rows after ordering the completed 6/49 primary population by "
            "(draw_date, draw_id)"
        ),
        "outcomes_included": False,
        "phase6_row_count": config.primary.phase6_draws,
        "reserve_row_count": len(reserve),
        "entries": [
            {
                "draw_id": str(row["draw_id"]),
                "draw_date": row["draw_date"].isoformat(),
                "rule_version_id": str(row["rule_version_id"]),
                "reserve_status": "sealed_for_phase7",
            }
            for row in reserve
        ],
    }
    manifest["manifest_sha256"] = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    return manifest


def initialize_reserve_manifest(project_root: Path, config: PredictionConfig) -> Path:
    """Create or validate the deterministic outcome-free reserve manifest."""

    expected = expected_reserve_manifest(project_root, config)
    path = reserve_manifest_path(project_root, config)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != expected:
            raise ReserveIntegrityError(
                "existing protected reserve manifest does not match metadata"
            )
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(expected))
    return path


def load_and_verify_reserve(project_root: Path, config: PredictionConfig) -> dict[str, object]:
    """Verify self-hash, metadata, and absence of outcome fields."""

    path = reserve_manifest_path(project_root, config)
    if not path.exists():
        raise ReserveIntegrityError("protected reserve manifest is absent")
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    stated_hash = value.get("manifest_sha256")
    unsigned = dict(value)
    unsigned.pop("manifest_sha256", None)
    calculated = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
    if stated_hash != calculated:
        raise ReserveIntegrityError("protected reserve self-hash mismatch")
    prohibited = {"main", "mains", "numbers", "extra", "number_value", "outcome"}
    entries = value.get("entries")
    if not isinstance(entries, list) or len(entries) != config.primary.reserve_draws:
        raise ReserveIntegrityError("protected reserve entry count mismatch")
    for entry in entries:
        if not isinstance(entry, dict) or prohibited.intersection(entry):
            raise ReserveIntegrityError("protected reserve contains an outcome field")
    if value != expected_reserve_manifest(project_root, config):
        raise ReserveIntegrityError("protected reserve metadata no longer matches the dataset")
    return value


def protected_draw_ids(manifest: dict[str, object]) -> frozenset[str]:
    """Return protected IDs from a verified manifest."""

    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise ReserveIntegrityError("reserve entries must be a list")
    return frozenset(str(entry["draw_id"]) for entry in entries if isinstance(entry, dict))


def reject_protected_ids(draw_ids: set[str] | frozenset[str], protected: frozenset[str]) -> None:
    """Reject any attempt to score a protected reserve draw."""

    overlap = draw_ids.intersection(protected)
    if overlap:
        example = min(overlap)
        raise ReserveIntegrityError(f"Phase 6 outcome access denied for reserve draw {example}")
