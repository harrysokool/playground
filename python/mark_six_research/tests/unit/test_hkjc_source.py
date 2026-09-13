from datetime import date

import pytest

from mark_six.sources.hkjc import build_date_range_request, build_recent_draw_request


def test_recent_request_is_deliberately_capped() -> None:
    assert build_recent_draw_request(5).parameters["lastNDraw"] == 5
    with pytest.raises(ValueError, match="between 1 and 10"):
        build_recent_draw_request(11)


def test_date_request_uses_source_specific_compact_dates() -> None:
    request = build_date_range_request(date(2024, 5, 21), date(2024, 5, 22))
    assert request.parameters["startDate"] == "20240521"
    assert request.parameters["endDate"] == "20240522"


def test_date_request_is_deliberately_narrow() -> None:
    with pytest.raises(ValueError, match="31 inclusive days"):
        build_date_range_request(date(2024, 1, 1), date(2024, 2, 2))
