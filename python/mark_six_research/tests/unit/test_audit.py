from datetime import UTC, datetime
from pathlib import Path

import httpx

from mark_six.audit import audit_raw_acquisition, load_historical_audit
from mark_six.provenance import store_http_snapshot
from mark_six.sources.hkjc import (
    ENDPOINT,
    PARSER_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    build_date_range_request,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "hkjc" / "current_sample.json"


def _store(root: Path, timestamp: datetime) -> None:
    source_request = build_date_range_request(timestamp.date(), timestamp.date())
    request = httpx.Request("POST", ENDPOINT, content=source_request.body)
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=FIXTURE.read_bytes(),
        request=request,
    )
    store_http_snapshot(
        project_root=root,
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
        response=response,
        parser_version=PARSER_VERSION,
        request_parameters=source_request.parameters,
        request_body=source_request.body,
        retrieved_at=timestamp,
    )


def test_duplicate_observations_are_deduplicated_canonically(tmp_path: Path) -> None:
    _store(tmp_path, datetime(2026, 9, 11, 1, tzinfo=UTC))
    _store(tmp_path, datetime(2026, 9, 12, 1, tzinfo=UTC))

    audit = load_historical_audit(tmp_path, end_date=datetime(2026, 9, 13).date())
    raw = audit_raw_acquisition(tmp_path)

    assert len(audit.observations) == 4
    assert len(audit.canonical) == 2
    assert audit.exact_duplicate_observations == 2
    assert not audit.revisions
    assert raw.response_files == 2
    assert raw.metadata_sidecars == 2
    assert raw.request_sidecars == 2
    assert raw.duplicate_content_observations == 1
    assert raw.malformed_json == 0
    assert raw.unexpected_graphql_structures == 0
    assert raw.hash_failures == 0


def test_integrity_audit_reports_tampering(tmp_path: Path) -> None:
    _store(tmp_path, datetime(2026, 9, 11, 1, tzinfo=UTC))
    raw_path = next(
        path
        for path in (tmp_path / "data" / "raw" / SOURCE_ID).glob("*/*/*.json")
        if not path.name.endswith((".metadata.json", ".request.json"))
    )
    raw_path.write_bytes(b"changed")

    assert audit_raw_acquisition(tmp_path).hash_failures == 1
