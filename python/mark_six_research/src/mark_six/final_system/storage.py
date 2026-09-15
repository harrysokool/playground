"""Content-addressed, timestamped immutable storage for pre-draw records."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from mark_six.prediction.reserve import canonical_json_bytes


def record_sha256(record: BaseModel) -> str:
    """Hash one record's canonical JSON representation."""

    return hashlib.sha256(canonical_json_bytes(record.model_dump(mode="json"))).hexdigest()


def store_immutable_record(
    project_root: Path,
    record: BaseModel,
    *,
    draw_id: str,
    frozen_at: datetime,
    kind: str,
    storage_directory: str = "data/predraw",
) -> Path:
    """Write a new record once; never overwrite an existing record."""

    if kind not in {"evidence", "evaluation"}:
        raise ValueError("record kind must be evidence or evaluation")
    if frozen_at.tzinfo is None:
        raise ValueError("record timestamp must be timezone-aware")
    safe_draw_id = re.sub(r"[^A-Za-z0-9._-]", "_", draw_id)
    digest = record_sha256(record)
    timestamp = frozen_at.strftime("%Y%m%dT%H%M%S.%f%z")
    path = (
        project_root / storage_directory / safe_draw_id / kind / f"{timestamp}_{digest[:16]}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(record.model_dump(mode="json")))
    return path


def verify_immutable_record(path: Path) -> bool:
    """Check that a stored file's content hash matches its filename prefix."""

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path.stem.rsplit("_", 1)[-1] == digest[:16]
