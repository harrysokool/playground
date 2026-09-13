from datetime import UTC, datetime
from pathlib import Path

import httpx

from mark_six.provenance import (
    load_snapshot_metadata,
    sha256_bytes,
    store_http_snapshot,
    verify_snapshot,
)


def test_snapshot_preserves_exact_bytes_and_auditable_metadata(tmp_path: Path) -> None:
    content = b'{"data":{"lotteryDraws":[]}}\n'
    body = b'{"operationName":"marksixResult"}'
    request = httpx.Request("POST", "https://example.test/graphql", content=body)
    response = httpx.Response(
        200,
        headers={"content-type": "application/json; charset=utf-8"},
        content=content,
        request=request,
    )

    raw_path, metadata_path = store_http_snapshot(
        project_root=tmp_path,
        source_id="source",
        source_name="Source",
        response=response,
        parser_version="parser-v1",
        request_parameters={"lastNDraw": 1},
        request_body=body,
        retrieved_at=datetime(2026, 9, 13, 8, 0, tzinfo=UTC),
    )
    metadata = load_snapshot_metadata(metadata_path)

    assert raw_path.read_bytes() == content
    assert metadata.content_sha256 == sha256_bytes(content)
    assert metadata.byte_length == len(content)
    assert metadata.request_body_sha256 == sha256_bytes(body)
    assert metadata.retrieved_at == datetime(2026, 9, 13, 8, 0, tzinfo=UTC)
    assert verify_snapshot(tmp_path, metadata)

    raw_path.write_bytes(b"changed")
    assert not verify_snapshot(tmp_path, metadata)
