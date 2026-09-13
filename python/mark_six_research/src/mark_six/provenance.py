"""Immutable raw-response snapshotting and provenance verification."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field


class SnapshotMetadata(BaseModel):
    """Auditable metadata stored next to an exact raw HTTP response."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    snapshot_id: str
    source_id: str
    source_name: str
    url: str
    method: Literal["GET", "POST"]
    request_parameters: dict[str, str | int | bool | None] = Field(default_factory=dict)
    request_body_sha256: str | None = None
    request_body_path: str | None = None
    retrieved_at: datetime
    http_status: int
    content_type: str | None
    content_sha256: str
    byte_length: int = Field(ge=0)
    raw_path: str
    parser_version: str


def sha256_bytes(content: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    return hashlib.sha256(content).hexdigest()


def _extension_for(content_type: str | None) -> str:
    if not content_type:
        return ".bin"
    media_type = content_type.partition(";")[0].strip().lower()
    return {
        "application/json": ".json",
        "application/pdf": ".pdf",
        "text/html": ".html",
        "text/plain": ".txt",
    }.get(media_type, ".bin")


def store_http_snapshot(
    *,
    project_root: Path,
    source_id: str,
    source_name: str,
    response: httpx.Response,
    parser_version: str,
    request_parameters: dict[str, str | int | bool | None] | None = None,
    request_body: bytes | None = None,
    retrieved_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Store exact response bytes and deterministic metadata side by side.

    The raw response is never reformatted. Existing files are never overwritten; an identical
    timestamp/content collision fails explicitly.
    """

    retrieved = retrieved_at or datetime.now(UTC)
    if retrieved.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")

    content = response.content
    method = response.request.method
    if method not in {"GET", "POST"}:
        raise ValueError(f"Unsupported snapshot request method: {method}")
    digest = sha256_bytes(content)
    timestamp = retrieved.astimezone(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = project_root / "data" / "raw" / source_id / retrieved.strftime("%Y/%m")
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{timestamp}_{digest[:12]}"
    raw_path = directory / f"{stem}{_extension_for(response.headers.get('content-type'))}"
    metadata_path = directory / f"{stem}.metadata.json"
    request_path = directory / f"{stem}.request.json" if request_body is not None else None

    targets = [raw_path, metadata_path]
    if request_path is not None:
        targets.append(request_path)
    collisions = [path for path in targets if path.exists()]
    if collisions:
        raise FileExistsError(f"Snapshot target already exists: {collisions[0]}")

    raw_path.write_bytes(content)
    if request_path is not None and request_body is not None:
        request_path.write_bytes(request_body)

    relative_raw_path = raw_path.relative_to(project_root).as_posix()
    relative_request_path = (
        request_path.relative_to(project_root).as_posix() if request_path is not None else None
    )
    metadata = SnapshotMetadata(
        snapshot_id=f"{source_id}:{timestamp}:{digest[:12]}",
        source_id=source_id,
        source_name=source_name,
        url=str(response.request.url),
        method=cast("Literal['GET', 'POST']", method),
        request_parameters=request_parameters or {},
        request_body_sha256=sha256_bytes(request_body) if request_body is not None else None,
        request_body_path=relative_request_path,
        retrieved_at=retrieved,
        http_status=response.status_code,
        content_type=response.headers.get("content-type"),
        content_sha256=digest,
        byte_length=len(content),
        raw_path=relative_raw_path,
        parser_version=parser_version,
    )
    metadata_path.write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return raw_path, metadata_path


def load_snapshot_metadata(path: Path) -> SnapshotMetadata:
    """Load strictly validated sidecar metadata."""

    return SnapshotMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def verify_snapshot(project_root: Path, metadata: SnapshotMetadata) -> bool:
    """Verify that the recorded raw file exists and still matches its hash and size."""

    raw_path = project_root / metadata.raw_path
    if not raw_path.is_file():
        return False
    content = raw_path.read_bytes()
    return len(content) == metadata.byte_length and sha256_bytes(content) == metadata.content_sha256
