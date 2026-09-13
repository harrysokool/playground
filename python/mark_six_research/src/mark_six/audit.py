"""Historical snapshot loading, deduplication, revision detection, and continuity checks."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, cast

from mark_six.domain.models import ParsedDraw, ValidationIssue
from mark_six.domain.rules import RULE_VERSIONS, rule_for_draw
from mark_six.domain.validation import validate_draw
from mark_six.provenance import (
    SnapshotMetadata,
    load_snapshot_metadata,
    sha256_bytes,
    verify_snapshot,
)
from mark_six.sources.hkjc import SOURCE_ID
from mark_six.sources.hkjc_parser import HkjcParseError, parse_hkjc_draw_with_rules

IssueClassification = Literal[
    "confirmed_data_problem",
    "expected_historical_behavior",
    "requires_rule_research",
    "requires_source_research",
]


@dataclass(frozen=True)
class AuditIssue:
    """A historical-quality issue with an explicit research classification."""

    check_code: str
    classification: IssueClassification
    message: str
    source_draw_id: str | None = None
    field_name: str | None = None
    source_record_id: str | None = None


@dataclass(frozen=True)
class DrawObservation:
    """One draw as observed in one immutable source snapshot."""

    draw: ParsedDraw
    source_record_id: str
    retrieved_at: datetime
    item_sha256: str
    raw_path: str


@dataclass(frozen=True)
class RevisionRecord:
    """Distinct official representations observed for the same draw ID."""

    source_draw_id: str
    item_hashes: tuple[str, ...]
    source_record_ids: tuple[str, ...]


@dataclass
class HistoricalAudit:
    """Complete audit result used to build canonical artifacts and reports."""

    observations: list[DrawObservation] = field(default_factory=list)
    canonical: dict[str, DrawObservation] = field(default_factory=dict)
    issues: list[AuditIssue] = field(default_factory=list)
    revisions: list[RevisionRecord] = field(default_factory=list)
    snapshot_metadata: list[SnapshotMetadata] = field(default_factory=list)
    empty_snapshot_ids: list[str] = field(default_factory=list)
    snapshot_hash_failures: list[str] = field(default_factory=list)

    @property
    def exact_duplicate_observations(self) -> int:
        """Count redundant identical observations beyond the first per draw and hash."""

        counts = Counter((item.draw.source_draw_id, item.item_sha256) for item in self.observations)
        return sum(count - 1 for count in counts.values())


@dataclass(frozen=True)
class RawAcquisitionAudit:
    """File- and response-level integrity counts for one snapshot source."""

    response_files: int
    metadata_sidecars: int
    request_sidecars: int
    missing_metadata_sidecars: int
    missing_request_sidecars: int
    hash_failures: int
    duplicate_request_observations: int
    duplicate_content_observations: int
    malformed_json: int
    unexpected_graphql_structures: int
    http_failures: int
    empty_responses: int
    nonempty_responses: int


def audit_raw_acquisition(project_root: Path) -> RawAcquisitionAudit:
    """Audit every preserved GraphQL response without parsing draw outcomes."""

    source_root = project_root / "data" / "raw" / SOURCE_ID
    metadata_paths = sorted(source_root.glob("*/*/*.metadata.json"))
    request_paths = sorted(source_root.glob("*/*/*.request.json"))
    response_paths = sorted(
        path
        for path in source_root.glob("*/*/*")
        if path.is_file()
        and not path.name.endswith(".metadata.json")
        and not path.name.endswith(".request.json")
    )
    metadata_by_raw: dict[str, SnapshotMetadata] = {}
    invalid_metadata = 0
    for path in metadata_paths:
        try:
            metadata = load_snapshot_metadata(path)
        except (OSError, ValueError):
            invalid_metadata += 1
            continue
        metadata_by_raw[metadata.raw_path] = metadata

    response_relatives = {path.relative_to(project_root).as_posix() for path in response_paths}
    missing_metadata = len(response_relatives - metadata_by_raw.keys()) + invalid_metadata
    request_relatives = {path.relative_to(project_root).as_posix() for path in request_paths}
    missing_request = 0
    hashes: Counter[str] = Counter()
    request_identities: Counter[tuple[object, ...]] = Counter()
    hash_failures = malformed = unexpected = http_failures = empty = nonempty = 0

    for metadata in metadata_by_raw.values():
        if (
            metadata.request_body_path is None
            or metadata.request_body_path not in request_relatives
        ):
            missing_request += 1
        if not verify_snapshot(project_root, metadata):
            hash_failures += 1
            continue
        hashes[metadata.content_sha256] += 1
        request_identities[
            (
                metadata.method,
                metadata.url,
                json.dumps(metadata.request_parameters, sort_keys=True),
                metadata.request_body_sha256,
            )
        ] += 1
        if metadata.http_status < 200 or metadata.http_status >= 300:
            http_failures += 1
        try:
            root = json.loads((project_root / metadata.raw_path).read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            malformed += 1
            continue
        if (
            not isinstance(root, dict)
            or root.get("errors")
            or not isinstance(root.get("data"), dict)
            or not isinstance(root["data"].get("lotteryDraws"), list)
        ):
            unexpected += 1
            continue
        if root["data"]["lotteryDraws"]:
            nonempty += 1
        else:
            empty += 1

    return RawAcquisitionAudit(
        response_files=len(response_paths),
        metadata_sidecars=len(metadata_paths),
        request_sidecars=len(request_paths),
        missing_metadata_sidecars=missing_metadata,
        missing_request_sidecars=missing_request,
        hash_failures=hash_failures,
        duplicate_request_observations=sum(count - 1 for count in request_identities.values()),
        duplicate_content_observations=sum(count - 1 for count in hashes.values()),
        malformed_json=malformed,
        unexpected_graphql_structures=unexpected,
        http_failures=http_failures,
        empty_responses=empty,
        nonempty_responses=nonempty,
    )


def _canonical_json_hash(item: object) -> str:
    return sha256_bytes(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )


def _source_id_hint(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    value = item.get("id")
    return value if isinstance(value, str) and value else None


def _load_snapshot_items(raw_path: Path) -> list[Any]:
    root = json.loads(raw_path.read_bytes())
    if (
        not isinstance(root, dict)
        or root.get("errors")
        or not isinstance(root.get("data"), dict)
        or not isinstance(root["data"].get("lotteryDraws"), list)
    ):
        raise HkjcParseError("snapshot does not contain data.lotteryDraws array")
    return cast("list[Any]", root["data"]["lotteryDraws"])


def _classification(issue: ValidationIssue) -> IssueClassification:
    if issue.code in {
        "duplicate_main_number",
        "extra_number_duplicates_main",
        "negative_money",
        "negative_winning_units",
        "negative_dividend",
        "duplicate_prize_division",
    }:
        return "confirmed_data_problem"
    if issue.code in {
        "rule_version_mismatch",
        "date_before_rule",
        "date_after_rule",
        "main_number_out_of_range",
        "extra_number_out_of_range",
        "unit_stake_mismatch",
    }:
        return "requires_rule_research"
    return "requires_source_research"


def load_historical_audit(project_root: Path, *, end_date: date) -> HistoricalAudit:
    """Load every verified official result snapshot and audit development-period observations."""

    audit = HistoricalAudit()
    metadata_root = project_root / "data" / "raw" / SOURCE_ID
    paths = sorted(metadata_root.glob("*/*/*.metadata.json"))
    grouped: dict[str, list[DrawObservation]] = defaultdict(list)
    for metadata_path in paths:
        try:
            metadata = load_snapshot_metadata(metadata_path)
        except (OSError, ValueError) as error:
            audit.issues.append(
                AuditIssue(
                    check_code="INVALID_SNAPSHOT_METADATA",
                    classification="confirmed_data_problem",
                    message=f"{metadata_path}: {error}",
                )
            )
            continue
        if metadata.source_id != SOURCE_ID:
            continue
        audit.snapshot_metadata.append(metadata)
        if not verify_snapshot(project_root, metadata):
            audit.snapshot_hash_failures.append(metadata.snapshot_id)
            audit.issues.append(
                AuditIssue(
                    check_code="SNAPSHOT_HASH_MISMATCH",
                    classification="confirmed_data_problem",
                    message="Raw snapshot does not match its recorded hash or size",
                    source_record_id=metadata.snapshot_id,
                )
            )
            continue
        raw_path = project_root / metadata.raw_path
        try:
            items = _load_snapshot_items(raw_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            audit.issues.append(
                AuditIssue(
                    check_code="MALFORMED_SNAPSHOT",
                    classification="confirmed_data_problem",
                    message=str(error),
                    source_record_id=metadata.snapshot_id,
                )
            )
            continue
        if not items:
            audit.empty_snapshot_ids.append(metadata.snapshot_id)
        for index, item in enumerate(items):
            source_id = _source_id_hint(item)
            try:
                draw = parse_hkjc_draw_with_rules(item, index, rule_for_draw)
            except (HkjcParseError, LookupError, ValueError) as error:
                audit.issues.append(
                    AuditIssue(
                        check_code="DRAW_PARSE_FAILURE",
                        classification=(
                            "requires_rule_research"
                            if isinstance(error, LookupError)
                            else "confirmed_data_problem"
                        ),
                        message=str(error),
                        source_draw_id=source_id,
                        source_record_id=metadata.snapshot_id,
                    )
                )
                continue
            if draw.draw_date > end_date:
                continue
            observation = DrawObservation(
                draw=draw,
                source_record_id=metadata.snapshot_id,
                retrieved_at=metadata.retrieved_at,
                item_sha256=_canonical_json_hash(item),
                raw_path=metadata.raw_path,
            )
            audit.observations.append(observation)
            grouped[draw.source_draw_id].append(observation)
            rule = RULE_VERSIONS[draw.rule_version_id]
            for issue in validate_draw(draw, rule):
                audit.issues.append(
                    AuditIssue(
                        check_code=issue.code.upper(),
                        classification=_classification(issue),
                        message=issue.message,
                        source_draw_id=draw.source_draw_id,
                        field_name=issue.field,
                        source_record_id=metadata.snapshot_id,
                    )
                )

    for source_draw_id, observations in grouped.items():
        ordered = sorted(observations, key=lambda item: (item.retrieved_at, item.source_record_id))
        audit.canonical[source_draw_id] = ordered[-1]
        item_hashes = tuple(sorted({item.item_sha256 for item in observations}))
        if len(item_hashes) > 1:
            audit.revisions.append(
                RevisionRecord(
                    source_draw_id=source_draw_id,
                    item_hashes=item_hashes,
                    source_record_ids=tuple(item.source_record_id for item in ordered),
                )
            )
            audit.issues.append(
                AuditIssue(
                    check_code="SOURCE_REVISION",
                    classification="requires_source_research",
                    message=f"Observed {len(item_hashes)} distinct source representations",
                    source_draw_id=source_draw_id,
                )
            )

    _add_continuity_issues(audit)
    return audit


def _add_continuity_issues(audit: HistoricalAudit) -> None:
    draws = sorted(
        (item.draw for item in audit.canonical.values()), key=lambda item: item.draw_date
    )
    by_date: dict[date, list[ParsedDraw]] = defaultdict(list)
    by_year: dict[int, list[int]] = defaultdict(list)
    for draw in draws:
        by_date[draw.draw_date].append(draw)
        by_year[draw.draw_date.year].append(int(draw.draw_number.split("/")[1]))
        rule = RULE_VERSIONS[draw.rule_version_id]
        if rule.number_range_status != "verified" or rule.unit_stake_status != "verified":
            audit.issues.append(
                AuditIssue(
                    check_code="UNRESOLVED_RULE_ASSIGNMENT",
                    classification="requires_rule_research",
                    message=f"Assigned partially verified rule {rule.rule_version_id}",
                    source_draw_id=draw.source_draw_id,
                    field_name="rule_version_id",
                )
            )
        expected = rule.reported_prize_division_count
        if expected is not None and len(draw.prizes) != expected:
            audit.issues.append(
                AuditIssue(
                    check_code="MISSING_REPORTED_PRIZE_DIVISIONS",
                    classification="requires_source_research",
                    message=f"Expected {expected} reported divisions, found {len(draw.prizes)}",
                    source_draw_id=draw.source_draw_id,
                    field_name="prizes",
                )
            )

    for draw_date, same_date in by_date.items():
        if len(same_date) > 1:
            audit.issues.append(
                AuditIssue(
                    check_code="DUPLICATE_DRAW_DATE",
                    classification="requires_rule_research",
                    message=f"{len(same_date)} draws share {draw_date.isoformat()}",
                )
            )
    for year, numbers in by_year.items():
        present = set(numbers)
        for missing in sorted(set(range(min(present), max(present) + 1)) - present):
            audit.issues.append(
                AuditIssue(
                    check_code="MISSING_DRAW_NUMBER",
                    classification="requires_source_research",
                    message=f"Draw {year % 100:02d}/{missing:03d} is absent within observed year",
                )
            )
    for previous, current in pairwise(draws):
        gap = (current.draw_date - previous.draw_date).days
        if gap > 14:
            expected_gap = (previous.source_draw_id, current.source_draw_id) in {
                ("2020008N", "2020009N"),
                ("2022001N", "2022002N"),
            }
            audit.issues.append(
                AuditIssue(
                    check_code="LONG_DATE_GAP",
                    classification=(
                        "expected_historical_behavior"
                        if expected_gap
                        else "requires_source_research"
                    ),
                    message=(
                        f"{gap}-day gap between {previous.draw_number} and {current.draw_number}; "
                        + (
                            "corroborated by official COVID-19 suspension/postponement notices"
                            if expected_gap
                            else "official schedule evidence still required"
                        )
                    ),
                    source_draw_id=current.source_draw_id,
                    field_name="draw_date",
                )
            )
