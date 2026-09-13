import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from mark_six.holdout import ensure_development_range, load_holdout_manifest


def test_development_cutoff_is_inclusive_and_crossing_is_rejected() -> None:
    ensure_development_range(date(2026, 9, 13), date(2026, 9, 13))
    with pytest.raises(PermissionError):
        ensure_development_range(date(2026, 9, 13), date(2026, 9, 14))


def test_holdout_entries_must_be_strictly_prospective(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "policy_id": "prospective_312_after_2026_09_13",
                "cutoff_date": "2026-09-13",
                "target_eligible_draws": 312,
                "state": "sealed",
                "entries": [
                    {
                        "source_draw_id": "not-future",
                        "draw_date": "2026-09-13",
                        "eligibility_status": "pending",
                        "rule_version_id": None,
                        "raw_snapshot_id": "sealed:not-future",
                        "canonical_dataset_version": None,
                        "sealed": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="strictly after"):
        load_holdout_manifest(path)


@pytest.mark.parametrize("outcome_field", ["main_numbers", "extra_number", "prizes", "turnover"])
def test_holdout_manifest_forbids_outcome_fields(tmp_path: Path, outcome_field: str) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "policy_id": "prospective_312_after_2026_09_13",
                "cutoff_date": "2026-09-13",
                "target_eligible_draws": 312,
                "state": "sealed",
                "entries": [
                    {
                        "source_draw_id": "future",
                        "draw_date": "2026-09-15",
                        "eligibility_status": "pending",
                        "rule_version_id": None,
                        "raw_snapshot_id": "sealed:future",
                        "canonical_dataset_version": None,
                        "sealed": True,
                        outcome_field: [1, 2, 3],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        load_holdout_manifest(path)
