"""Phase 9 report generation, manifest creation, and complete verification."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mark_six.economics.analysis import verify_economic_analysis
from mark_six.final_system.models import FinalSystemConfig, load_final_system_config
from mark_six.final_system.reporting import write_final_reports
from mark_six.holdout import load_holdout_manifest
from mark_six.prediction.analysis import _verify_phase5_outputs, verify_prediction_analysis
from mark_six.prediction.reserve import canonical_json_bytes
from mark_six.replication.runner import verify_historical_replication


class FinalSystemIntegrityError(RuntimeError):
    """Raised when Phase 9 or a frozen dependency fails verification."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(project_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _has_ancestor(project_root: Path, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def _phase9_cli_surface(content: bytes) -> bytes:
    begin = b"\n\n# PHASE9_EXTENSION_BEGIN\n"
    end = b"# PHASE9_EXTENSION_END\n"
    if begin not in content or end not in content:
        raise FinalSystemIntegrityError("Phase 9 CLI extension markers are absent")
    start = content.index(begin) + len(begin)
    finish = content.index(end, start)
    return content[start:finish]


def phase9_code_hash(project_root: Path) -> str:
    """Hash only the Phase 9 package and its isolated CLI extension."""

    digest = hashlib.sha256()
    for path in sorted((project_root / "src/mark_six/final_system").glob("*.py")):
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    cli = project_root / "src/mark_six/cli.py"
    digest.update(b"src/mark_six/cli.py:PHASE9")
    digest.update(b"\0")
    digest.update(_phase9_cli_surface(cli.read_bytes()))
    digest.update(b"\0")
    return digest.hexdigest()


def _load_config(project_root: Path) -> tuple[Path, FinalSystemConfig]:
    path = project_root / "configs/phase9_final_system.yaml"
    return path, load_final_system_config(path)


def verify_frozen_dependencies(
    project_root: Path, config: FinalSystemConfig
) -> dict[str, dict[str, object]]:
    """Verify Phases 5--8, canonical data, raw evidence, reserve, and holdout."""

    if not (
        _git_head(project_root) == config.baseline_commit
        or _has_ancestor(project_root, config.baseline_commit)
    ):
        raise FinalSystemIntegrityError("Git history lacks the approved Phase 8 baseline")
    phase5 = _verify_phase5_outputs(project_root)
    phase6 = verify_prediction_analysis(project_root)
    phase7 = verify_historical_replication(project_root)
    phase8 = verify_economic_analysis(project_root)
    results: dict[str, dict[str, object]] = {
        "phase5": phase5,
        "phase6": phase6,
        "phase7": phase7,
        "phase8": phase8,
    }
    expected_manifests: dict[str, str] = {
        str(phase): digest for phase, digest in config.previous_manifest_sha256.items()
    }
    for phase, result in results.items():
        if result.get("manifest_sha256") != expected_manifests.get(phase):
            raise FinalSystemIntegrityError(f"{phase} manifest differs from the approved baseline")
    holdout = load_holdout_manifest(project_root / "data/holdout/manifest.json")
    if holdout.state != "sealed" or holdout.entries:
        raise FinalSystemIntegrityError("prospective holdout must remain sealed with zero entries")
    if phase6.get("raw_snapshots") != 611 or phase6.get("canonical_table_count") != 7:
        raise FinalSystemIntegrityError("dataset or raw snapshot integrity differs from baseline")
    return results


def build_phase9_outputs(project_root: Path) -> Path:
    """Generate deterministic final reports and a self-hashed Phase 9 manifest."""

    config_path, config = _load_config(project_root)
    dependencies = verify_frozen_dependencies(project_root, config)
    holdout = load_holdout_manifest(project_root / "data/holdout/manifest.json")
    reports = write_final_reports(project_root, config)
    manifest: dict[str, object] = {
        "schema_version": "1",
        "system_version": config.system_version,
        "protocol_version": config.protocol_version,
        "baseline_commit": config.baseline_commit,
        "git_head_at_run": _git_head(project_root),
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "previous_manifest_sha256": config.previous_manifest_sha256,
        "decision_rules": config.decision_rules.model_dump(mode="json"),
        "turnover_method": config.turnover.model_dump(mode="json"),
        "sharing_scenarios": [item.model_dump(mode="json") for item in config.sharing_scenarios],
        "source_definitions": config.source_definitions,
        "ticket_budgets_hkd": config.ticket_budgets_hkd,
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "phase9_code_sha256": phase9_code_hash(project_root),
        "prospective_holdout_state": holdout.state,
        "prospective_holdout_entry_count": len(holdout.entries),
        "prospective_holdout_accessed": False,
        "historical_prediction_reopened": False,
        "prospective_evaluation_started": False,
        "generated_at": datetime.now(UTC).isoformat(),
        "output_sha256": {
            path.relative_to(project_root).as_posix(): _sha256(path) for path in reports
        },
        "dependency_output_counts": {
            phase: result.get("output_count") for phase, result in dependencies.items()
        },
    }
    manifest["manifest_sha256"] = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    path = project_root / config.outputs.manifest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(manifest))
    return path


def verify_phase9_outputs(project_root: Path) -> dict[str, object]:
    """Verify Phase 9 dependencies, manifest, code, configuration, and reports."""

    config_path, config = _load_config(project_root)
    dependencies = verify_frozen_dependencies(project_root, config)
    path = project_root / config.outputs.manifest
    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(manifest)
    stated = unsigned.pop("manifest_sha256", None)
    if hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest() != stated:
        raise FinalSystemIntegrityError("Phase 9 manifest self-hash mismatch")
    checks: dict[str, object] = {
        "system_version": config.system_version,
        "protocol_version": config.protocol_version,
        "baseline_commit": config.baseline_commit,
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "previous_manifest_sha256": config.previous_manifest_sha256,
        "decision_rules": config.decision_rules.model_dump(mode="json"),
        "turnover_method": config.turnover.model_dump(mode="json"),
        "sharing_scenarios": [item.model_dump(mode="json") for item in config.sharing_scenarios],
        "source_definitions": config.source_definitions,
        "protocol_sha256": _sha256(project_root / config.protocol_path),
        "configuration_sha256": _sha256(config_path),
        "phase9_code_sha256": phase9_code_hash(project_root),
        "prospective_holdout_state": "sealed",
        "prospective_holdout_entry_count": 0,
        "prospective_holdout_accessed": False,
        "historical_prediction_reopened": False,
        "prospective_evaluation_started": False,
    }
    for field, expected in checks.items():
        if manifest.get(field) != expected:
            raise FinalSystemIntegrityError(f"Phase 9 manifest mismatch: {field}")
    outputs = manifest.get("output_sha256")
    if not isinstance(outputs, dict):
        raise FinalSystemIntegrityError("Phase 9 output hashes are absent")
    failures = [
        str(relative)
        for relative, expected in outputs.items()
        if not (project_root / str(relative)).is_file()
        or _sha256(project_root / str(relative)) != expected
    ]
    if failures:
        raise FinalSystemIntegrityError(f"Phase 9 output hash failures: {', '.join(failures)}")
    return {
        "manifest_sha256": stated,
        "output_count": len(outputs),
        "output_failures": 0,
        "dataset_id": config.dataset_id,
        "dataset_manifest_sha256": config.dataset_manifest_sha256,
        "raw_snapshots": dependencies["phase6"]["raw_snapshots"],
        "canonical_table_count": dependencies["phase6"]["canonical_table_count"],
        "phase5_manifest_sha256": dependencies["phase5"]["manifest_sha256"],
        "phase6_manifest_sha256": dependencies["phase6"]["manifest_sha256"],
        "phase7_manifest_sha256": dependencies["phase7"]["manifest_sha256"],
        "phase8_manifest_sha256": dependencies["phase8"]["manifest_sha256"],
        "holdout_state": "sealed",
        "holdout_entry_count": 0,
        "holdout_accessed": False,
        "prospective_evaluation_started": False,
    }
