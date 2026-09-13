import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx

from mark_six.dataset import build_dataset, dataset_summary, validate_dataset_relationships
from mark_six.provenance import store_http_snapshot
from mark_six.sources.hkjc import (
    ENDPOINT,
    PARSER_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    build_date_range_request,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "hkjc" / "current_sample.json"


def test_canonical_publication_builds_linked_parquet_and_duckdb(tmp_path: Path) -> None:
    rules_doc = tmp_path / "docs" / "rules_timeline.md"
    rules_doc.parent.mkdir()
    rules_doc.write_text("reviewed test rules\n", encoding="utf-8")
    start = end = datetime(2026, 9, 12).date()
    source_request = build_date_range_request(start, end)
    request = httpx.Request("POST", ENDPOINT, content=source_request.body)
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=FIXTURE.read_bytes(),
        request=request,
    )
    store_http_snapshot(
        project_root=tmp_path,
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
        response=response,
        parser_version=PARSER_VERSION,
        request_parameters=source_request.parameters,
        request_body=source_request.body,
        retrieved_at=datetime(2026, 9, 13, 1, tzinfo=UTC),
    )

    result = build_dataset(tmp_path)

    assert result.row_counts["draws"] == 2
    assert result.row_counts["draw_numbers"] == 14
    assert result.row_counts["prize_results"] == 14
    assert result.row_counts["jackpot_events"] == 1
    assert result.row_counts["source_records"] == 1
    assert validate_dataset_relationships(result.database_path) == {}
    assert dataset_summary(result.database_path)["missing_stake"] == 0
    with duckdb.connect(str(result.database_path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM draws").fetchone() == (2,)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["input_snapshot_count"] == 1
    assert len(manifest["raw_snapshot_manifest_sha256"]) == 64
    assert build_dataset(tmp_path).reused_existing
