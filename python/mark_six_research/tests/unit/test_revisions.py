import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from mark_six.provenance import store_http_snapshot
from mark_six.revisions import revision_check
from mark_six.sources.hkjc import (
    ENDPOINT,
    PARSER_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    build_date_range_request,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "hkjc" / "current_sample.json"


def test_controlled_revision_preserves_snapshots_and_reports_field_groups(tmp_path: Path) -> None:
    start = end = date(2026, 9, 12)
    source_request = build_date_range_request(start, end)
    request = httpx.Request("POST", ENDPOINT, content=source_request.body)
    old = json.loads(FIXTURE.read_text(encoding="utf-8"))
    response = httpx.Response(200, json=old, request=request)
    store_http_snapshot(
        project_root=tmp_path,
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
        response=response,
        parser_version=PARSER_VERSION,
        request_parameters=source_request.parameters,
        request_body=source_request.body,
        retrieved_at=datetime(2026, 9, 12, 22, tzinfo=UTC),
    )
    changed = json.loads(FIXTURE.read_text(encoding="utf-8"))
    changed["data"]["lotteryDraws"][0]["lotteryPool"]["totalInvestment"] = "42599304"

    def respond(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=changed)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = revision_check(
            project_root=tmp_path,
            client=client,
            start_date=start,
            end_date=end,
        )

    assert result.raw_changed
    assert result.draw_revisions[0].source_draw_id == "202699N"
    assert result.draw_revisions[0].changed_groups == ("turnover",)
    assert result.record_path.is_file()
    assert len(list((tmp_path / "data" / "raw" / SOURCE_ID).glob("*/*/*.metadata.json"))) == 2
