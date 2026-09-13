"""Reproducible canonical Parquet datasets, reports, and DuckDB views."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from mark_six.audit import (
    AuditIssue,
    HistoricalAudit,
    audit_raw_acquisition,
    load_historical_audit,
)
from mark_six.domain.rules import CURRENT_RULES, RULE_VERSIONS
from mark_six.holdout import DEVELOPMENT_CUTOFF, ensure_development_range
from mark_six.provenance import load_snapshot_metadata, sha256_bytes, verify_snapshot
from mark_six.sources.hkjc import PARSER_VERSION

SCHEMA_VERSION = "2"
VALIDATION_VERSION = "historical-validation-v1"
RULE_TIMELINE_VERSION = "2026-09-13-phase3"
DATASET_BUILDER_VERSION = "phase3-v2"


@dataclass(frozen=True)
class DatasetBuildResult:
    """Paths and identity of one canonical publication."""

    dataset_version: str
    dataset_dir: Path
    manifest_path: Path
    database_path: Path
    row_counts: dict[str, int]
    reused_existing: bool


class DatasetIntegrityError(RuntimeError):
    """Raised when canonical table relationships fail publication checks."""


def _draw_id(draw_number: str) -> str:
    return f"hkjc:{draw_number}"


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _issue_id(issue: AuditIssue, index: int) -> str:
    payload = {
        "check_code": issue.check_code,
        "classification": issue.classification,
        "draw": issue.source_draw_id,
        "field": issue.field_name,
        "message": issue.message,
        "source": issue.source_record_id,
        "index": index,
    }
    return f"issue:{sha256_bytes(_json_bytes(payload))[:20]}"


def _table(rows: list[dict[str, Any]], schema: pa.Schema) -> pa.Table:
    return pa.Table.from_pylist(rows, schema=schema)


def _canonical_rows(
    audit: HistoricalAudit, recorded_at: datetime
) -> dict[str, list[dict[str, Any]]]:
    draws_rows: list[dict[str, Any]] = []
    number_rows: list[dict[str, Any]] = []
    prize_rows: list[dict[str, Any]] = []
    jackpot_rows: list[dict[str, Any]] = []
    for observation in sorted(audit.canonical.values(), key=lambda item: item.draw.draw_date):
        draw = observation.draw
        canonical_id = _draw_id(draw.draw_number)
        special = draw.snowball_code is not None or draw.snowball_name_en is not None
        draws_rows.append(
            {
                "draw_id": canonical_id,
                "source_draw_id": draw.source_draw_id,
                "draw_number": draw.draw_number,
                "draw_date": draw.draw_date,
                "draw_at": None,
                "sales_open_date": draw.open_date,
                "sales_close_at": draw.close_at,
                "status": "completed" if draw.source_status == "Result" else "unknown",
                "source_status": draw.source_status,
                "rule_version_id": draw.rule_version_id,
                "turnover_hkd_cents": draw.turnover_hkd_cents,
                "reported_jackpot_hkd_cents": draw.reported_jackpot_hkd_cents,
                "estimated_first_prize_hkd_cents": draw.estimated_first_prize_hkd_cents,
                "reported_derived_first_prize_hkd_cents": (
                    draw.reported_derived_first_prize_hkd_cents
                ),
                "unit_stake_hkd_cents": draw.unit_stake_hkd_cents,
                "snowball_code": draw.snowball_code,
                "snowball_name_en": draw.snowball_name_en,
                "is_special_draw": special,
                "source_pool_sell": draw.pool_sell,
                "source_pool_status": draw.pool_status,
                "source_record_id": observation.source_record_id,
                "source_item_sha256": observation.item_sha256,
                "recorded_at": recorded_at,
            }
        )
        for position, number in enumerate(draw.main_numbers, start=1):
            number_rows.append(
                {
                    "draw_id": canonical_id,
                    "number_role": "main",
                    "draw_position": None,
                    "number_value": number,
                    "display_position": position,
                    "source_record_id": observation.source_record_id,
                }
            )
        number_rows.append(
            {
                "draw_id": canonical_id,
                "number_role": "extra",
                "draw_position": None,
                "number_value": draw.extra_number,
                "display_position": 1,
                "source_record_id": observation.source_record_id,
            }
        )
        for prize in draw.prizes:
            fixed = (
                prize.division >= 4
                if draw.rule_version_id == CURRENT_RULES.rule_version_id
                else None
            )
            prize_rows.append(
                {
                    "draw_id": canonical_id,
                    "division_code": f"division_{prize.division}",
                    "division_label": None,
                    "source_winning_unit_amount": prize.source_winning_unit_amount,
                    "winning_units": prize.winning_units,
                    "winning_tickets": None,
                    "prize_per_winning_unit_hkd_cents": prize.dividend_hkd_cents,
                    "total_division_payout_hkd_cents": None,
                    "is_fixed_prize": fixed,
                    "source_record_id": observation.source_record_id,
                }
            )
        if special:
            jackpot_rows.append(
                {
                    "jackpot_event_id": f"special:{draw.source_draw_id}",
                    "draw_id": canonical_id,
                    "event_type": "special_designation",
                    "event_at": None,
                    "published_at": None,
                    "amount_hkd_cents": None,
                    "from_draw_id": None,
                    "description": draw.snowball_name_en or draw.snowball_code,
                    "source_record_id": observation.source_record_id,
                }
            )

    rules_rows = [
        {
            "rule_version_id": rule.rule_version_id,
            "effective_from": rule.effective_from,
            "effective_to": rule.effective_to,
            "verification_status": rule.verification_status,
            "number_pool_min": rule.number_min,
            "number_pool_max": rule.number_max,
            "number_range_status": rule.number_range_status,
            "main_numbers_selected": rule.main_numbers_drawn,
            "extra_numbers_selected": rule.extra_numbers_drawn,
            "unit_stake_hkd_cents": rule.unit_stake_hkd_cents,
            "unit_stake_status": rule.unit_stake_status,
            "prize_division_count": rule.prize_divisions,
            "reported_prize_division_count": rule.reported_prize_division_count,
        }
        for rule in RULE_VERSIONS.values()
    ]
    validation_rows = [
        {
            "validation_issue_id": _issue_id(issue, index),
            "detected_at": recorded_at,
            "dataset_name": "historical_draws",
            "record_key": issue.source_draw_id,
            "field_name": issue.field_name,
            "check_code": issue.check_code,
            "classification": issue.classification,
            "severity": "error" if issue.classification == "confirmed_data_problem" else "warning",
            "observed_value": None,
            "message": issue.message,
            "source_record_id": issue.source_record_id,
            "status": "open",
        }
        for index, issue in enumerate(audit.issues)
    ]
    return {
        "draws": draws_rows,
        "draw_numbers": number_rows,
        "prize_results": prize_rows,
        "jackpot_events": jackpot_rows,
        "rule_versions": rules_rows,
        "validation_issues": validation_rows,
    }


def _source_rows(project_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((project_root / "data" / "raw").glob("*/*/*/*.metadata.json")):
        try:
            metadata = load_snapshot_metadata(path)
        except (OSError, ValueError):
            continue
        rows.append(
            {
                "source_record_id": metadata.snapshot_id,
                "source_name": metadata.source_id,
                "organization": "The Hong Kong Jockey Club",
                "url": metadata.url,
                "http_method": metadata.method,
                "request_parameters": json.dumps(metadata.request_parameters, sort_keys=True),
                "request_body_sha256": metadata.request_body_sha256,
                "request_body_path": metadata.request_body_path,
                "retrieval_method": "http",
                "retrieved_at": metadata.retrieved_at,
                "published_at": None,
                "http_status": metadata.http_status,
                "media_type": metadata.content_type,
                "content_sha256": metadata.content_sha256,
                "byte_length": metadata.byte_length,
                "raw_path": metadata.raw_path,
                "parser_version": metadata.parser_version,
                "terms_review_status": "pending",
                "hash_verified": verify_snapshot(project_root, metadata),
            }
        )
    return rows


def _schemas() -> dict[str, pa.Schema]:
    utc = pa.timestamp("us", tz="UTC")
    money = pa.int64()
    return {
        "draws": pa.schema(
            [
                ("draw_id", pa.string()),
                ("source_draw_id", pa.string()),
                ("draw_number", pa.string()),
                ("draw_date", pa.date32()),
                ("draw_at", utc),
                ("sales_open_date", pa.date32()),
                ("sales_close_at", utc),
                ("status", pa.string()),
                ("source_status", pa.string()),
                ("rule_version_id", pa.string()),
                ("turnover_hkd_cents", money),
                ("reported_jackpot_hkd_cents", money),
                ("estimated_first_prize_hkd_cents", money),
                ("reported_derived_first_prize_hkd_cents", money),
                ("unit_stake_hkd_cents", money),
                ("snowball_code", pa.string()),
                ("snowball_name_en", pa.string()),
                ("is_special_draw", pa.bool_()),
                ("source_pool_sell", pa.bool_()),
                ("source_pool_status", pa.string()),
                ("source_record_id", pa.string()),
                ("source_item_sha256", pa.string()),
                ("recorded_at", utc),
            ]
        ),
        "draw_numbers": pa.schema(
            [
                ("draw_id", pa.string()),
                ("number_role", pa.string()),
                ("draw_position", pa.int16()),
                ("number_value", pa.int16()),
                ("display_position", pa.int16()),
                ("source_record_id", pa.string()),
            ]
        ),
        "prize_results": pa.schema(
            [
                ("draw_id", pa.string()),
                ("division_code", pa.string()),
                ("division_label", pa.string()),
                ("source_winning_unit_amount", pa.decimal128(20, 4)),
                ("winning_units", pa.decimal128(20, 4)),
                ("winning_tickets", pa.int64()),
                ("prize_per_winning_unit_hkd_cents", money),
                ("total_division_payout_hkd_cents", money),
                ("is_fixed_prize", pa.bool_()),
                ("source_record_id", pa.string()),
            ]
        ),
        "jackpot_events": pa.schema(
            [
                ("jackpot_event_id", pa.string()),
                ("draw_id", pa.string()),
                ("event_type", pa.string()),
                ("event_at", utc),
                ("published_at", utc),
                ("amount_hkd_cents", money),
                ("from_draw_id", pa.string()),
                ("description", pa.string()),
                ("source_record_id", pa.string()),
            ]
        ),
        "rule_versions": pa.schema(
            [
                ("rule_version_id", pa.string()),
                ("effective_from", pa.date32()),
                ("effective_to", pa.date32()),
                ("verification_status", pa.string()),
                ("number_pool_min", pa.int16()),
                ("number_pool_max", pa.int16()),
                ("number_range_status", pa.string()),
                ("main_numbers_selected", pa.int16()),
                ("extra_numbers_selected", pa.int16()),
                ("unit_stake_hkd_cents", money),
                ("unit_stake_status", pa.string()),
                ("prize_division_count", pa.int16()),
                ("reported_prize_division_count", pa.int16()),
            ]
        ),
        "source_records": pa.schema(
            [
                ("source_record_id", pa.string()),
                ("source_name", pa.string()),
                ("organization", pa.string()),
                ("url", pa.string()),
                ("http_method", pa.string()),
                ("request_parameters", pa.string()),
                ("request_body_sha256", pa.string()),
                ("request_body_path", pa.string()),
                ("retrieval_method", pa.string()),
                ("retrieved_at", utc),
                ("published_at", utc),
                ("http_status", pa.int16()),
                ("media_type", pa.string()),
                ("content_sha256", pa.string()),
                ("byte_length", pa.int64()),
                ("raw_path", pa.string()),
                ("parser_version", pa.string()),
                ("terms_review_status", pa.string()),
                ("hash_verified", pa.bool_()),
            ]
        ),
        "validation_issues": pa.schema(
            [
                ("validation_issue_id", pa.string()),
                ("detected_at", utc),
                ("dataset_name", pa.string()),
                ("record_key", pa.string()),
                ("field_name", pa.string()),
                ("check_code", pa.string()),
                ("classification", pa.string()),
                ("severity", pa.string()),
                ("observed_value", pa.string()),
                ("message", pa.string()),
                ("source_record_id", pa.string()),
                ("status", pa.string()),
            ]
        ),
    }


def _build_spec(project_root: Path) -> dict[str, Any]:
    rule_path = project_root / "docs" / "rules_timeline.md"
    snapshot_manifest: list[dict[str, str]] = []
    for path in sorted((project_root / "data" / "raw").glob("*/*/*/*.metadata.json")):
        item = load_snapshot_metadata(path)
        snapshot_manifest.append(
            {
                "snapshot_id": item.snapshot_id,
                "source_id": item.source_id,
                "content_sha256": item.content_sha256,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "validation_version": VALIDATION_VERSION,
        "dataset_builder_version": DATASET_BUILDER_VERSION,
        "rule_timeline_version": RULE_TIMELINE_VERSION,
        "rule_timeline_sha256": _file_hash(rule_path),
        "development_cutoff": DEVELOPMENT_CUTOFF.isoformat(),
        "input_snapshot_count": len(snapshot_manifest),
        "raw_snapshot_manifest_sha256": sha256_bytes(_json_bytes(snapshot_manifest)),
        "input_snapshots": snapshot_manifest,
    }


def build_dataset(project_root: Path, *, end_date: date = DEVELOPMENT_CUTOFF) -> DatasetBuildResult:
    """Build or reuse one content-identified canonical dataset and DuckDB query layer."""

    ensure_development_range(end_date, end_date)
    audit = load_historical_audit(project_root, end_date=end_date)
    spec = _build_spec(project_root)
    dataset_version = f"marksix-{sha256_bytes(_json_bytes(spec))[:16]}"
    dataset_dir = project_root / "data" / "processed" / dataset_version
    manifest_path = dataset_dir / "manifest.json"
    database_path = dataset_dir / "mark_six.duckdb"
    if manifest_path.exists() and database_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return DatasetBuildResult(
            dataset_version=dataset_version,
            dataset_dir=dataset_dir,
            manifest_path=manifest_path,
            database_path=database_path,
            row_counts=existing_manifest["row_counts"],
            reused_existing=True,
        )

    dataset_dir.mkdir(parents=True, exist_ok=False)
    created_at = datetime.now(UTC)
    evidence_as_of = max(item.retrieved_at for item in audit.snapshot_metadata)
    rows = _canonical_rows(audit, evidence_as_of)
    rows["source_records"] = _source_rows(project_root)
    schemas = _schemas()
    table_hashes: dict[str, str] = {}
    row_counts: dict[str, int] = {}
    for name, schema in schemas.items():
        path = dataset_dir / f"{name}.parquet"
        table = _table(rows[name], schema)
        pq.write_table(table, path, compression="zstd", version="2.6")
        table_hashes[name] = _file_hash(path)
        row_counts[name] = table.num_rows

    create_duckdb_views(dataset_dir, database_path)
    integrity_failures = validate_dataset_relationships(database_path)
    if integrity_failures:
        raise DatasetIntegrityError(
            "Canonical publication checks failed: "
            + ", ".join(f"{name}={count}" for name, count in integrity_failures.items())
        )
    manifest: dict[str, Any] = {
        **spec,
        "dataset_version": dataset_version,
        "created_at": created_at.isoformat(),
        "git_commit": _git_commit(project_root),
        "row_counts": row_counts,
        "table_sha256": table_hashes,
        "duckdb_path": database_path.relative_to(project_root).as_posix(),
    }
    manifest["manifest_sha256"] = sha256_bytes(_json_bytes(manifest))
    manifest_path.write_bytes(_json_bytes(manifest))
    _write_reports(project_root, audit, manifest)
    return DatasetBuildResult(
        dataset_version=dataset_version,
        dataset_dir=dataset_dir,
        manifest_path=manifest_path,
        database_path=database_path,
        row_counts=row_counts,
        reused_existing=False,
    )


def _git_commit(project_root: Path) -> str | None:
    repository = project_root.parents[1]
    relative_project = project_root.relative_to(repository)
    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "ls-files",
            "--error-unmatch",
            str(relative_project / "pyproject.toml"),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if tracked.returncode != 0:
        return None
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def create_duckdb_views(dataset_dir: Path, database_path: Path) -> None:
    """Rebuild a local database whose views read the canonical Parquet files."""

    connection = duckdb.connect(str(database_path))
    try:
        for name in _schemas():
            parquet_path = (dataset_dir / f"{name}.parquet").resolve().as_posix()
            escaped_path = parquet_path.replace("'", "''")
            connection.execute(
                f"CREATE OR REPLACE VIEW \"{name}\" AS SELECT * FROM read_parquet('{escaped_path}')"
            )
    finally:
        connection.close()


def dataset_summary(database_path: Path) -> dict[str, Any]:
    """Return operational, non-pattern dataset quality counts from DuckDB."""

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        summary_row = connection.execute(
            "SELECT count(*), min(draw_date), max(draw_date) FROM draws"
        ).fetchone()
        assert summary_row is not None
        total, earliest, latest = summary_row
        missing_turnover_row = connection.execute(
            "SELECT count(*) FROM draws WHERE turnover_hkd_cents IS NULL"
        ).fetchone()
        assert missing_turnover_row is not None
        missing_turnover = missing_turnover_row[0]
        missing_stake_row = connection.execute(
            "SELECT count(*) FROM draws WHERE unit_stake_hkd_cents IS NULL"
        ).fetchone()
        assert missing_stake_row is not None
        missing_stake = missing_stake_row[0]
        missing_prizes_row = connection.execute(
            "SELECT count(*) FROM draws d WHERE NOT EXISTS "
            "(SELECT 1 FROM prize_results p WHERE p.draw_id = d.draw_id)"
        ).fetchone()
        assert missing_prizes_row is not None
        missing_prizes = missing_prizes_row[0]
        special_row = connection.execute(
            "SELECT count(*) FROM draws WHERE is_special_draw"
        ).fetchone()
        assert special_row is not None
        special = special_row[0]
        issues_row = connection.execute("SELECT count(*) FROM validation_issues").fetchone()
        assert issues_row is not None
        issues = issues_row[0]
        unresolved_row = connection.execute(
            "SELECT count(*) FROM validation_issues WHERE check_code = 'UNRESOLVED_RULE_ASSIGNMENT'"
        ).fetchone()
        assert unresolved_row is not None
        unresolved = unresolved_row[0]
        by_year = connection.execute(
            "SELECT year(draw_date), count(*) FROM draws GROUP BY 1 ORDER BY 1"
        ).fetchall()
    finally:
        connection.close()
    return {
        "total_draws": total,
        "earliest_draw_date": earliest.isoformat() if earliest else None,
        "latest_draw_date": latest.isoformat() if latest else None,
        "draws_by_year": {str(year): count for year, count in by_year},
        "missing_turnover": missing_turnover,
        "missing_stake": missing_stake,
        "missing_prize_information": missing_prizes,
        "special_draws": special,
        "validation_issues": issues,
        "unresolved_rule_assignments": unresolved,
    }


def validate_dataset_relationships(database_path: Path) -> dict[str, int]:
    """Return nonzero canonical relationship failures from the DuckDB query layer."""

    checks = {
        "duplicate_draw_ids": "SELECT count(*) - count(DISTINCT draw_id) FROM draws",
        "main_number_cardinality": (
            "SELECT count(*) FROM (SELECT draw_id FROM draw_numbers "
            "WHERE number_role = 'main' GROUP BY draw_id HAVING count(*) <> 6)"
        ),
        "extra_number_cardinality": (
            "SELECT count(*) FROM (SELECT draw_id FROM draw_numbers "
            "WHERE number_role = 'extra' GROUP BY draw_id HAVING count(*) <> 1)"
        ),
        "draws_without_main_numbers": (
            "SELECT count(*) FROM draws d WHERE NOT EXISTS "
            "(SELECT 1 FROM draw_numbers n WHERE n.draw_id=d.draw_id AND n.number_role='main')"
        ),
        "draws_without_extra_number": (
            "SELECT count(*) FROM draws d WHERE NOT EXISTS "
            "(SELECT 1 FROM draw_numbers n WHERE n.draw_id=d.draw_id AND n.number_role='extra')"
        ),
        "orphan_draw_numbers": (
            "SELECT count(*) FROM draw_numbers n LEFT JOIN draws d USING(draw_id) "
            "WHERE d.draw_id IS NULL"
        ),
        "orphan_prize_results": (
            "SELECT count(*) FROM prize_results p LEFT JOIN draws d USING(draw_id) "
            "WHERE d.draw_id IS NULL"
        ),
        "orphan_jackpot_events": (
            "SELECT count(*) FROM jackpot_events j LEFT JOIN draws d USING(draw_id) "
            "WHERE d.draw_id IS NULL"
        ),
        "duplicate_draw_number_rows": (
            "SELECT count(*) FROM (SELECT draw_id, number_role, number_value FROM draw_numbers "
            "GROUP BY ALL HAVING count(*) > 1)"
        ),
        "duplicate_prize_rows": (
            "SELECT count(*) FROM (SELECT draw_id, division_code FROM prize_results "
            "GROUP BY ALL HAVING count(*) > 1)"
        ),
        "missing_rule_links": (
            "SELECT count(*) FROM draws d LEFT JOIN rule_versions r USING(rule_version_id) "
            "WHERE r.rule_version_id IS NULL"
        ),
        "missing_source_links": (
            "SELECT count(*) FROM draws d LEFT JOIN source_records s USING(source_record_id) "
            "WHERE s.source_record_id IS NULL"
        ),
        "orphan_draw_number_sources": (
            "SELECT count(*) FROM draw_numbers n LEFT JOIN source_records s "
            "USING(source_record_id) "
            "WHERE s.source_record_id IS NULL"
        ),
        "orphan_prize_sources": (
            "SELECT count(*) FROM prize_results p LEFT JOIN source_records s "
            "USING(source_record_id) "
            "WHERE s.source_record_id IS NULL"
        ),
        "orphan_jackpot_sources": (
            "SELECT count(*) FROM jackpot_events j LEFT JOIN source_records s "
            "USING(source_record_id) "
            "WHERE s.source_record_id IS NULL"
        ),
        "impossible_numbers": (
            "SELECT count(*) FROM draw_numbers n JOIN draws d USING(draw_id) "
            "JOIN rule_versions r USING(rule_version_id) "
            "WHERE n.number_value < r.number_pool_min OR n.number_value > r.number_pool_max"
        ),
        "negative_draw_money": (
            "SELECT count(*) FROM draws WHERE turnover_hkd_cents < 0 "
            "OR reported_jackpot_hkd_cents < 0 OR estimated_first_prize_hkd_cents < 0 "
            "OR reported_derived_first_prize_hkd_cents < 0 OR unit_stake_hkd_cents < 0"
        ),
        "negative_prize_values": (
            "SELECT count(*) FROM prize_results WHERE source_winning_unit_amount < 0 "
            "OR winning_units < 0 OR prize_per_winning_unit_hkd_cents < 0"
        ),
    }
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        results = {
            name: int(connection.execute(query).fetchone()[0])  # type: ignore[index]
            for name, query in checks.items()
        }
    finally:
        connection.close()
    return {name: count for name, count in results.items() if count}


def latest_dataset_manifest(project_root: Path) -> Path:
    """Find the newest canonical manifest by its recorded creation time."""

    manifests = list((project_root / "data" / "processed").glob("marksix-*/manifest.json"))
    if not manifests:
        raise FileNotFoundError("No canonical dataset manifest exists; run build-dataset first")
    return max(
        manifests,
        key=lambda path: json.loads(path.read_text(encoding="utf-8"))["created_at"],
    )


def _write_reports(project_root: Path, audit: HistoricalAudit, manifest: dict[str, Any]) -> None:
    reports = project_root / "reports" / "generated"
    reports.mkdir(parents=True, exist_ok=True)
    draws = sorted(
        (item.draw for item in audit.canonical.values()), key=lambda item: item.draw_date
    )
    by_year = Counter(draw.draw_date.year for draw in draws)
    raw = audit_raw_acquisition(project_root)
    missing_numbers = [issue for issue in audit.issues if issue.check_code == "MISSING_DRAW_NUMBER"]
    unresolved = [
        issue for issue in audit.issues if issue.check_code == "UNRESOLVED_RULE_ASSIGNMENT"
    ]
    parse_failures = [issue for issue in audit.issues if issue.check_code == "DRAW_PARSE_FAILURE"]
    missing_prizes = [draw for draw in draws if not draw.prizes]
    quality = {
        "total_official_draws": len(draws),
        "earliest_draw_date": draws[0].draw_date.isoformat() if draws else None,
        "latest_draw_date": draws[-1].draw_date.isoformat() if draws else None,
        "duplicate_observations": audit.exact_duplicate_observations,
        "missing_draw_identifiers": len(missing_numbers),
        "missing_main_number_sets": len(parse_failures),
        "missing_extra_numbers": len(parse_failures),
        "missing_sales_open_date": sum(draw.open_date is None for draw in draws),
        "missing_sales_close_at": sum(draw.close_at is None for draw in draws),
        "missing_turnover": sum(draw.turnover_hkd_cents is None for draw in draws),
        "missing_reported_jackpot": sum(draw.reported_jackpot_hkd_cents is None for draw in draws),
        "missing_stake": sum(draw.unit_stake_hkd_cents is None for draw in draws),
        "missing_estimated_first_prize": sum(
            draw.estimated_first_prize_hkd_cents is None for draw in draws
        ),
        "missing_reported_derived_first_prize": sum(
            draw.reported_derived_first_prize_hkd_cents is None for draw in draws
        ),
        "missing_prize_divisions": len(missing_prizes),
        "validation_failures": sum(
            issue.classification == "confirmed_data_problem" for issue in audit.issues
        ),
        "unresolved_historical_rule_assignments": len(unresolved),
        "source_revisions": len(audit.revisions),
        "raw_result_snapshots": len(audit.snapshot_metadata),
        "raw_response_files": raw.response_files,
        "missing_metadata_sidecars": raw.missing_metadata_sidecars,
        "missing_request_sidecars": raw.missing_request_sidecars,
        "snapshot_hash_failures": len(audit.snapshot_hash_failures),
        "malformed_json_responses": raw.malformed_json,
        "unexpected_graphql_structures": raw.unexpected_graphql_structures,
        "http_failures": raw.http_failures,
    }
    coverage_lines = [
        "# Historical Coverage Report",
        "",
        "These are measured facts about the official structured endpoint, not the inception date",
        "of Mark Six.",
        "",
        "- Phase 3 sequential acquisition windows: **602**",
        f"- Preserved GraphQL responses including samples/requery: **{raw.response_files}**",
        f"- Structurally valid empty responses: **{raw.empty_responses}**",
        f"- Structurally valid nonempty responses: **{raw.nonempty_responses}**",
        f"- Official canonical draws: **{len(draws)}**",
        f"- Earliest: **{quality['earliest_draw_date']}**",
        f"- Latest development draw: **{quality['latest_draw_date']}**",
        f"- Missing identifiers within observed years: **{len(missing_numbers)}**",
        f"- Exact duplicate observations removed: **{audit.exact_duplicate_observations}**",
        f"- Conflicting source revisions: **{len(audit.revisions)}**",
        "",
        "## Draws by year",
        "",
        "| Year | Draws |",
        "|---:|---:|",
        *[f"| {year} | {count} |" for year, count in sorted(by_year.items())],
        "",
    ]
    (reports / "historical_coverage.md").write_text("\n".join(coverage_lines), encoding="utf-8")
    quality_lines = [
        "# Dataset Quality Report",
        "",
        "Official facts are preserved in source-qualified columns. Normalized values include HKD",
        "cents, civil dates, source-stake-scaled winning units, and rule IDs. Derived values are",
        "limited to stable IDs, completed/special flags, and designation events.",
        "Nulls and unresolved questions are not imputed.",
        "",
        "| Metric | Count/value |",
        "|---|---:|",
        *[f"| `{key}` | {value} |" for key, value in quality.items()],
        "",
    ]
    (reports / "dataset_quality.md").write_text("\n".join(quality_lines), encoding="utf-8")
    issue_counts = Counter((item.classification, item.check_code) for item in audit.issues)
    issue_lines = [
        "# Validation Issue Report",
        "",
        "All issue rows are retained in `validation_issues.parquet`.",
        "Warnings record expected historical behavior or unresolved research.",
        "Confirmed data problems would block a clean validation result.",
        "",
        "| Classification | Check | Count |",
        "|---|---|---:|",
        *[
            f"| `{classification}` | `{code}` | {count} |"
            for (classification, code), count in sorted(issue_counts.items())
        ],
        "",
    ]
    (reports / "validation_issues.md").write_text("\n".join(issue_lines), encoding="utf-8")
    rule_counts = Counter(draw.rule_version_id for draw in draws)
    rule_lines = [
        "# Rule Coverage Report",
        "",
        "| Rule version | Status | Draws |",
        "|---|---|---:|",
        *[
            f"| `{rule_id}` | `{RULE_VERSIONS[rule_id].verification_status}` | {count} |"
            for rule_id, count in sorted(rule_counts.items())
        ],
        "",
    ]
    (reports / "rule_coverage.md").write_text("\n".join(rule_lines), encoding="utf-8")
    revision_lines = [
        "# Source Revision Report",
        "",
        f"Distinct revised draws detected: **{len(audit.revisions)}**",
        "A controlled requery of 2026-09-08 through 2026-09-13 was byte-identical. Zero detected",
        "revisions does not establish that the source never revises.",
        "",
        "| Draw ID | Distinct item hashes | Source observations |",
        "|---|---:|---:|",
        *[
            f"| `{item.source_draw_id}` | {len(item.item_hashes)} | {len(item.source_record_ids)} |"
            for item in audit.revisions
        ],
        "",
    ]
    (reports / "source_revisions.md").write_text("\n".join(revision_lines), encoding="utf-8")
    (reports / "dataset_manifest.json").write_bytes(_json_bytes(manifest))
