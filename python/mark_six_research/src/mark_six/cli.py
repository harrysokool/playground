"""Command-line entry point for project operations."""

import json
import platform
from collections import Counter
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Annotated

import httpx
import typer

from mark_six import __version__
from mark_six.audit import audit_raw_acquisition, load_historical_audit
from mark_six.collection import CollectionItem, collect_historical
from mark_six.config import load_project_config
from mark_six.dataset import (
    build_dataset,
    dataset_summary,
    latest_dataset_manifest,
    validate_dataset_relationships,
)
from mark_six.domain.models import RuleVersion
from mark_six.domain.rules import CURRENT_RULES, RULE_VERSIONS
from mark_six.domain.validation import validate_draw
from mark_six.mathematics.combinatorics import (
    prize_outcome_odds,
    probability_of_any_prize,
    total_six_number_tickets,
)
from mark_six.mathematics.entries import (
    banker_combination_count,
    banker_first_division_probability,
    banker_ticket_cost_cents,
    multiple_combination_count,
    multiple_first_division_probability,
    multiple_ticket_cost_cents,
)
from mark_six.mathematics.reporting import (
    write_mathematics_reports,
    write_prize_probability_report,
)
from mark_six.mathematics.simulation import simulate_ticket_outcomes
from mark_six.prediction.analysis import run_predictive_analysis, verify_prediction_analysis
from mark_six.prediction.models import load_prediction_config
from mark_six.provenance import load_snapshot_metadata, store_http_snapshot, verify_snapshot
from mark_six.revisions import revision_check
from mark_six.sources.hkjc import (
    PARSER_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    fetch_draw_date_range,
    fetch_recent_draws,
)
from mark_six.sources.hkjc_parser import parse_hkjc_payload
from mark_six.statistics.analysis import run_randomness_analysis

app = typer.Typer(
    name="mark-six",
    help="Reproducible research tools for Hong Kong Mark Six.",
    no_args_is_help=True,
)
source_app = typer.Typer(help="Inspect approved external evidence sources.")
app.add_typer(source_app, name="source")
mathematics_app = typer.Typer(help="Generate exact, non-predictive mathematical results.")
app.add_typer(mathematics_app, name="mathematics")
statistics_app = typer.Typer(help="Run preregistered, non-predictive randomness tests.")
app.add_typer(statistics_app, name="stats")
prediction_app = typer.Typer(help="Run preregistered walk-forward predictive-signal tests.")
app.add_typer(prediction_app, name="predict")


@app.callback()
def main() -> None:
    """Run Mark Six research project commands."""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _rule(rule_version_id: str) -> RuleVersion:
    try:
        return RULE_VERSIONS[rule_version_id]
    except KeyError as error:
        choices = ", ".join(sorted(RULE_VERSIONS))
        raise typer.BadParameter(f"Unknown rule version; choose one of: {choices}") from error


@mathematics_app.command("prize-probabilities")
def prize_probabilities() -> None:
    """Generate exact current and historical-candidate prize probability tables."""

    project_root = _project_root()
    report_path = write_prize_probability_report(
        project_root / "reports" / "generated" / "prize_probabilities.md"
    )
    typer.echo(f"Report: {report_path.relative_to(project_root)}")


@mathematics_app.command("odds")
def mathematics_odds(
    pool_size: Annotated[int, typer.Option(min=7)] = 49,
    prize_divisions: Annotated[int, typer.Option(min=6, max=7)] = 7,
) -> None:
    """Show exact prize odds and the probability of any prize."""

    typer.echo(f"Total combinations: {total_six_number_tickets(pool_size)}")
    for item in prize_outcome_odds(pool_size, prize_divisions):
        typer.echo(
            f"{item.outcome}: count={item.winning_combinations} "
            f"probability={_fraction(item.probability)} one_in={_fraction(item.one_in)}"
        )
    any_prize = probability_of_any_prize(pool_size, prize_divisions)
    typer.echo(f"any_prize: probability={_fraction(any_prize)} one_in={_fraction(1 / any_prize)}")


@mathematics_app.command("first-division")
def mathematics_first_division(
    pool_size: Annotated[int, typer.Option(min=7)] = 49,
) -> None:
    """Show the exact First Division probability for one ordinary ticket."""

    total = total_six_number_tickets(pool_size)
    typer.echo(f"Pool size: {pool_size}")
    typer.echo(f"Total combinations: {total}")
    typer.echo(f"First Division probability: 1/{total}")


@mathematics_app.command("multiple")
def mathematics_multiple(
    selections: Annotated[int, typer.Option(min=7, max=49)],
    pool_size: Annotated[int, typer.Option(min=7, max=49)] = 49,
    partial_unit: bool = typer.Option(False, help="Use the verified partial unit where allowed."),
    rule_version_id: str = typer.Option(CURRENT_RULES.rule_version_id),
) -> None:
    """Inspect a Multiple entry's combinations, cost, and First Division coverage."""

    if selections > pool_size:
        raise typer.BadParameter("selections cannot exceed pool-size")
    rule = _rule(rule_version_id)
    count = multiple_combination_count(selections)
    cost = multiple_ticket_cost_cents(selections, rule, partial_unit=partial_unit)
    probability = multiple_first_division_probability(selections, pool_size)
    typer.echo(f"Rule version: {rule.rule_version_id}")
    typer.echo(f"Combinations: {count}")
    typer.echo(f"Cost cents: {cost}")
    typer.echo(f"First Division probability: {_fraction(probability)}")


@mathematics_app.command("banker")
def mathematics_banker(
    bankers: Annotated[int, typer.Option(min=1, max=5)],
    legs: Annotated[int, typer.Option(min=2, max=48)],
    pool_size: Annotated[int, typer.Option(min=7, max=49)] = 49,
    partial_unit: bool = typer.Option(False, help="Use the verified partial unit where allowed."),
    rule_version_id: str = typer.Option(CURRENT_RULES.rule_version_id),
) -> None:
    """Inspect a Banker entry's combinations, cost, and First Division coverage."""

    if bankers + legs > pool_size:
        raise typer.BadParameter("bankers plus legs cannot exceed pool-size")
    rule = _rule(rule_version_id)
    count = banker_combination_count(bankers, legs)
    cost = banker_ticket_cost_cents(bankers, legs, rule, partial_unit=partial_unit)
    probability = banker_first_division_probability(bankers, legs, pool_size)
    typer.echo(f"Rule version: {rule.rule_version_id}")
    typer.echo(f"Combinations: {count}")
    typer.echo(f"Cost cents: {cost}")
    typer.echo(f"First Division probability: {_fraction(probability)}")


@mathematics_app.command("simulate")
def mathematics_simulate(
    trials: Annotated[int, typer.Option(min=1, max=10_000_000)] = 100_000,
    seed: int = 20260913,
    pool_size: Annotated[int, typer.Option(min=7, max=49)] = 49,
    prize_divisions: Annotated[int, typer.Option(min=6, max=7)] = 7,
) -> None:
    """Run a seeded fair-draw simulation as an independent exact-math check."""

    result = simulate_ticket_outcomes(
        pool_size=pool_size,
        prize_divisions=prize_divisions,
        trials=trials,
        seed=seed,
        ticket=(1, 2, 3, 4, 5, 6),
    )
    typer.echo(f"Evidence: {result.evidence_type}")
    typer.echo(f"Trials: {result.trials}")
    typer.echo(f"Seed: {result.seed}")
    for item in result.comparisons:
        typer.echo(
            f"{item.outcome}: observed={item.observed_count} "
            f"estimated={_fraction(item.estimated_probability)} "
            f"exact={_fraction(item.exact_probability)} "
            f"within_tolerance={str(item.within_tolerance).lower()}"
        )


@mathematics_app.command("reports")
def mathematics_reports() -> None:
    """Generate all deterministic Phase 4 mathematics reports."""

    project_root = _project_root()
    for path in write_mathematics_reports(project_root):
        typer.echo(f"Report: {path.relative_to(project_root)}")


@statistics_app.command("run")
def statistics_run(
    seed: int | None = typer.Option(
        None, help="Deterministic root seed; default is preregistered."
    ),
    simulations: Annotated[
        int | None, typer.Option(min=1, help="Fair histories per period; default is preregistered.")
    ] = None,
) -> None:
    """Run the complete frozen Phase 5 analysis against development data only."""

    project_root = _project_root()
    result = run_randomness_analysis(project_root, seed=seed, simulations=simulations)
    typer.echo(f"Report: {result.report_path.relative_to(project_root)}")
    typer.echo(f"Manifest: {result.manifest_path.relative_to(project_root)}")
    typer.echo(f"Included draws: {result.included_draws}")
    typer.echo(f"Excluded draws: {result.excluded_draws}")
    typer.echo(
        f"Confirmatory hypotheses: {result.individual_hypotheses + result.omnibus_hypotheses}"
    )
    typer.echo(f"Raw significant findings: {result.raw_significant}")
    typer.echo(f"Corrected significant findings: {result.corrected_significant}")
    typer.echo(f"Meaningful fair-null deviations: {len(result.inconsistent_findings)}")


def _show_statistics_output(relative_path: str) -> None:
    project_root = _project_root()
    path = project_root / "reports" / "generated" / relative_path
    if not path.exists():
        raise typer.BadParameter("Phase 5 output is absent; run `mark-six stats run` first")
    typer.echo(f"Output: {path.relative_to(project_root)}")


@prediction_app.command("run")
def prediction_run() -> None:
    """Run the complete frozen Phase 6 analysis without reserve outcomes."""

    project_root = _project_root()
    result = run_predictive_analysis(project_root)
    typer.echo(f"Report: {result.report_path.relative_to(project_root)}")
    typer.echo(f"Manifest: {result.manifest_path.relative_to(project_root)}")
    typer.echo(f"Primary scored draws: {result.primary_scored_draws}")
    typer.echo(f"Candidate models: {result.candidate_models}")
    typer.echo(f"Fair histories: {result.simulation_histories}")
    typer.echo(f"Selected best model: {result.selected_best_model}")
    typer.echo(f"Primary predictive signal: {str(result.primary_signal).lower()}")


@prediction_app.command("models")
def prediction_models() -> None:
    """List the frozen Phase 6 candidates and parameters."""

    project_root = _project_root()
    config = load_prediction_config(project_root / "configs" / "phase6_prediction.yaml")
    typer.echo(f"Protocol: {config.protocol_version}")
    for model in config.models:
        parameters = model.model_dump(exclude_none=True)
        typer.echo(json.dumps(parameters, sort_keys=True))


@prediction_app.command("report")
def prediction_report() -> None:
    """Locate the generated Phase 6 report and manifest."""

    project_root = _project_root()
    for relative in ("predictive_signal_analysis.md", "phase6_analysis_manifest.json"):
        path = project_root / "reports" / "generated" / relative
        if not path.exists():
            raise typer.BadParameter("Phase 6 output is absent; run `mark-six predict run` first")
        typer.echo(f"Output: {path.relative_to(project_root)}")


@prediction_app.command("verify")
def prediction_verify() -> None:
    """Verify Phase 6 inputs, reserve guard, manifest, and output hashes."""

    result = verify_prediction_analysis(_project_root())
    for name, value in result.items():
        typer.echo(f"{name}: {value}")


@statistics_app.command("frequencies")
def statistics_frequencies() -> None:
    """Locate the generated main and Extra Number frequency tables."""

    _show_statistics_output("phase5/number_frequencies.csv")
    _show_statistics_output("phase5/extra_number_frequencies.csv")


@statistics_app.command("composition")
def statistics_composition() -> None:
    """Locate the generated odd/even and low/high table."""

    _show_statistics_output("phase5/composition.csv")


@statistics_app.command("overlap")
def statistics_overlap() -> None:
    """Locate the generated consecutive-draw overlap table."""

    _show_statistics_output("phase5/draw_overlap.csv")


@statistics_app.command("gaps")
def statistics_gaps() -> None:
    """Locate the generated number appearance-gap table."""

    _show_statistics_output("phase5/gap_behavior.csv")


@statistics_app.command("pairs")
def statistics_pairs() -> None:
    """Locate the corrected pair-frequency table."""

    _show_statistics_output("phase5/pair_statistics.csv")


@statistics_app.command("report")
def statistics_report() -> None:
    """Locate the generated main randomness report and analysis manifest."""

    _show_statistics_output("randomness_analysis.md")
    _show_statistics_output("phase5_analysis_manifest.json")


@app.command()
def info() -> None:
    """Show the installed project and environment status."""

    config = load_project_config()
    typer.echo(f"Project: {config.project_name}")
    typer.echo(f"Version: {__version__}")
    typer.echo(f"Python: {platform.python_version()}")
    typer.echo(f"Status: {config.status}")


@source_app.command("fetch-sample")
def fetch_sample(
    last_n: int = typer.Option(5, min=1, max=10, help="Small recent-draw sample size."),
) -> None:
    """Fetch and snapshot a small official HKJC results sample exactly once."""

    project_root = _project_root()
    with httpx.Client(timeout=20.0, follow_redirects=False) as client:
        response, request = fetch_recent_draws(client, last_n)
        raw_path, metadata_path = store_http_snapshot(
            project_root=project_root,
            source_id=SOURCE_ID,
            source_name=SOURCE_NAME,
            response=response,
            parser_version=PARSER_VERSION,
            request_parameters=request.parameters,
            request_body=request.body,
        )
    typer.echo(f"HTTP status: {response.status_code}")
    typer.echo(f"Raw response: {raw_path.relative_to(project_root)}")
    typer.echo(f"Metadata: {metadata_path.relative_to(project_root)}")
    response.raise_for_status()


@source_app.command("fetch-date-sample")
def fetch_date_sample(
    start_date: str = typer.Option(..., help="Inclusive ISO date."),
    end_date: str = typer.Option(..., help="Inclusive ISO date; at most 31 days later."),
) -> None:
    """Fetch and snapshot one narrow official HKJC date-range response."""

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    project_root = _project_root()
    with httpx.Client(timeout=20.0, follow_redirects=False) as client:
        response, request = fetch_draw_date_range(client, start, end)
        raw_path, metadata_path = store_http_snapshot(
            project_root=project_root,
            source_id=SOURCE_ID,
            source_name=SOURCE_NAME,
            response=response,
            parser_version=PARSER_VERSION,
            request_parameters=request.parameters,
            request_body=request.body,
        )
    typer.echo(f"HTTP status: {response.status_code}")
    typer.echo(f"Raw response: {raw_path.relative_to(project_root)}")
    typer.echo(f"Metadata: {metadata_path.relative_to(project_root)}")
    response.raise_for_status()


@source_app.command("inspect-snapshot")
def inspect_snapshot(
    metadata_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    rule_version_id: Annotated[
        str,
        typer.Option(help="Reviewed rule version used for parsing and validation."),
    ] = CURRENT_RULES.rule_version_id,
) -> None:
    """Verify, parse, and validate one preserved HKJC response snapshot."""

    project_root = _project_root()
    metadata = load_snapshot_metadata(metadata_path)
    if not verify_snapshot(project_root, metadata):
        typer.echo("Snapshot integrity: FAILED", err=True)
        raise typer.Exit(1)
    try:
        rule = RULE_VERSIONS[rule_version_id]
    except KeyError as error:
        choices = ", ".join(sorted(RULE_VERSIONS))
        raise typer.BadParameter(f"Unknown rule version; choose one of: {choices}") from error

    draws = parse_hkjc_payload((project_root / metadata.raw_path).read_bytes(), rule)
    issues = [issue for draw in draws for issue in validate_draw(draw, rule)]
    typer.echo("Snapshot integrity: OK")
    typer.echo(f"Parsed draws: {len(draws)}")
    typer.echo(f"Draw IDs: {', '.join(draw.source_draw_id for draw in draws) or '(none)'}")
    typer.echo(f"Validation issues: {len(issues)}")
    if issues:
        raise typer.Exit(1)


@app.command()
def ingest(
    start_date: Annotated[str, typer.Option(help="Inclusive development start date (YYYY-MM-DD).")],
    end_date: Annotated[str, typer.Option(help="Inclusive development end date (YYYY-MM-DD).")],
    window_days: Annotated[
        int, typer.Option(min=1, max=31, help="Inclusive days per sequential request.")
    ] = 31,
    delay_seconds: Annotated[
        float, typer.Option(min=0.0, help="Spacing between live requests.")
    ] = 1.0,
) -> None:
    """Conservatively collect official development-period history with cache reuse."""

    project_root = _project_root()

    def report(item: CollectionItem) -> None:
        action = "cached" if item.reused_cache else "fetched"
        typer.echo(f"{item.window.start_date}..{item.window.end_date}: {action}")

    with httpx.Client(timeout=20.0, follow_redirects=False) as client:
        items = collect_historical(
            project_root=project_root,
            client=client,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
            window_days=window_days,
            delay_seconds=delay_seconds,
            on_item=report,
        )
    reused = sum(item.reused_cache for item in items)
    typer.echo(f"Windows complete: {len(items)} ({reused} cached, {len(items) - reused} fetched)")


@app.command("verify-snapshots")
def verify_snapshots() -> None:
    """Verify every raw artifact that has a provenance metadata sidecar."""

    project_root = _project_root()
    checked = 0
    failures: list[str] = []
    for path in sorted((project_root / "data" / "raw").glob("*/*/*/*.metadata.json")):
        checked += 1
        try:
            metadata = load_snapshot_metadata(path)
        except (OSError, ValueError) as error:
            failures.append(f"{path}: {error}")
            continue
        if not verify_snapshot(project_root, metadata):
            failures.append(metadata.snapshot_id)
    typer.echo(f"Snapshots checked: {checked}")
    typer.echo(f"Integrity failures: {len(failures)}")
    for failure in failures:
        typer.echo(f"FAILED: {failure}", err=True)
    if failures:
        raise typer.Exit(1)


@app.command("audit-acquisition")
def audit_acquisition() -> None:
    """Report exact official GraphQL acquisition and integrity counts."""

    audit = audit_raw_acquisition(_project_root())
    for name, value in audit.__dict__.items():
        typer.echo(f"{name}: {value}")
    if any(
        (
            audit.missing_metadata_sidecars,
            audit.missing_request_sidecars,
            audit.hash_failures,
            audit.malformed_json,
            audit.unexpected_graphql_structures,
            audit.http_failures,
        )
    ):
        raise typer.Exit(1)


@app.command()
def coverage(
    end_date: Annotated[str, typer.Option(help="Development cutoff date.")] = "2026-09-13",
) -> None:
    """Report structural historical coverage without number-pattern analysis."""

    audit = load_historical_audit(_project_root(), end_date=date.fromisoformat(end_date))
    draws = sorted(
        (item.draw for item in audit.canonical.values()), key=lambda draw: draw.draw_date
    )
    typer.echo(f"Official draws: {len(draws)}")
    typer.echo(f"Earliest: {min((draw.draw_date for draw in draws), default=None)}")
    typer.echo(f"Latest: {max((draw.draw_date for draw in draws), default=None)}")
    typer.echo(f"Exact duplicate observations: {audit.exact_duplicate_observations}")
    typer.echo(f"Source revisions: {len(audit.revisions)}")
    typer.echo(f"Validation/research issues: {len(audit.issues)}")


@app.command()
def validate(
    end_date: Annotated[str, typer.Option(help="Development cutoff date.")] = "2026-09-13",
) -> None:
    """Run complete rule-aware and continuity validation over raw snapshots."""

    audit = load_historical_audit(_project_root(), end_date=date.fromisoformat(end_date))
    counts = Counter(issue.classification for issue in audit.issues)
    typer.echo(f"Canonical draws checked: {len(audit.canonical)}")
    for classification in (
        "confirmed_data_problem",
        "expected_historical_behavior",
        "requires_rule_research",
        "requires_source_research",
    ):
        typer.echo(f"{classification}: {counts[classification]}")
    if counts["confirmed_data_problem"]:
        raise typer.Exit(1)


@app.command("build-dataset")
def build_dataset_command() -> None:
    """Publish canonical Parquet tables, reports, manifest, and DuckDB views."""

    result = build_dataset(_project_root())
    action = "reused" if result.reused_existing else "built"
    typer.echo(f"Dataset: {result.dataset_version} ({action})")
    for name, count in sorted(result.row_counts.items()):
        typer.echo(f"{name}: {count}")
    typer.echo(f"Manifest: {result.manifest_path.relative_to(_project_root())}")
    typer.echo(f"DuckDB: {result.database_path.relative_to(_project_root())}")


@app.command("dataset-info")
def dataset_info() -> None:
    """Query operational counts from the newest canonical DuckDB database."""

    project_root = _project_root()
    manifest_path = latest_dataset_manifest(project_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    database_path = project_root / manifest["duckdb_path"]
    typer.echo(f"Dataset: {manifest['dataset_version']}")
    typer.echo(f"Manifest SHA-256: {manifest['manifest_sha256']}")
    typer.echo(json.dumps(dataset_summary(database_path), indent=2, sort_keys=True))


@app.command("validate-dataset")
def validate_dataset() -> None:
    """Independently check canonical relationships through DuckDB."""

    project_root = _project_root()
    manifest_path = latest_dataset_manifest(project_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = validate_dataset_relationships(project_root / manifest["duckdb_path"])
    typer.echo(f"Relationship failures: {sum(failures.values())}")
    for name, count in sorted(failures.items()):
        typer.echo(f"{name}: {count}")
    if failures:
        raise typer.Exit(1)


@source_app.command("revision-check")
def revision_check_command(
    start_date: Annotated[str, typer.Option(help="Existing exact-range start date.")],
    end_date: Annotated[str, typer.Option(help="Existing exact-range end date.")],
) -> None:
    """Requery one controlled cached range and record source-field differences."""

    project_root = _project_root()
    with httpx.Client(timeout=20.0, follow_redirects=False) as client:
        comparison = revision_check(
            project_root=project_root,
            client=client,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
        )
    typer.echo(f"Raw changed: {comparison.raw_changed}")
    typer.echo(f"Draw revisions: {len(comparison.draw_revisions)}")
    typer.echo(f"Added draws: {len(comparison.added_draw_ids)}")
    typer.echo(f"Removed draws: {len(comparison.removed_draw_ids)}")
    typer.echo(f"Record: {comparison.record_path.relative_to(project_root)}")


# PHASE7_EXTENSION_BEGIN
replication_app = typer.Typer(help="Run the one-time frozen historical replication.")
app.add_typer(replication_app, name="replicate")


@replication_app.command("run")
def replication_run() -> None:
    """Open and score exactly the registered Phase 7 reserve."""

    from mark_six.replication.runner import run_historical_replication

    project_root = _project_root()
    result = run_historical_replication(project_root)
    typer.echo(f"Report: {result.report_path.relative_to(project_root)}")
    typer.echo(f"Manifest: {result.manifest_path.relative_to(project_root)}")
    typer.echo(f"Reserve draws: {result.reserve_draws}")
    typer.echo(f"Candidate models: {result.candidate_models}")
    typer.echo(f"Fair histories: {result.simulation_histories}")
    typer.echo(f"Selected best model: {result.selected_best_model}")
    typer.echo(f"Successful models: {list(result.successful_models)}")
    typer.echo(f"Phase 6 conclusion replicated: {str(result.phase6_conclusion_replicated).lower()}")


@replication_app.command("verify")
def replication_verify() -> None:
    """Verify Phase 7 inputs, manifest, and generated output hashes."""

    from mark_six.replication.runner import verify_historical_replication

    for name, value in verify_historical_replication(_project_root()).items():
        typer.echo(f"{name}: {value}")


@replication_app.command("report")
def replication_report() -> None:
    """Locate the generated Phase 7 report and manifest."""

    project_root = _project_root()
    for relative in ("historical_replication.md", "phase7_analysis_manifest.json"):
        path = project_root / "reports" / "generated" / relative
        if not path.exists():
            raise typer.BadParameter("Phase 7 output is absent; run `mark-six replicate run` first")
        typer.echo(f"Output: {path.relative_to(project_root)}")


@replication_app.command("compare")
def replication_compare() -> None:
    """Locate the independent Phase 6 versus Phase 7 comparison."""

    project_root = _project_root()
    path = project_root / "reports" / "generated" / "phase7" / "phase6_phase7_comparison.csv"
    if not path.exists():
        raise typer.BadParameter("Phase 7 comparison is absent; run `mark-six replicate run` first")
    typer.echo(f"Output: {path.relative_to(project_root)}")


# PHASE7_EXTENSION_END


# PHASE8_EXTENSION_BEGIN
economics_app = typer.Typer(help="Analyze Mark Six economics without predicting winning numbers.")
app.add_typer(economics_app, name="economics")


@economics_app.command("expected-value")
def economics_expected_value(
    turnover_hkd: Annotated[int, typer.Option(min=1)] = 100_000_000,
    first_division_fund_hkd: Annotated[int, typer.Option(min=0)] = 50_000_000,
    sharing_mode: str = typer.Option("uniform"),
) -> None:
    """Calculate one full-unit ticket's conditional expected value."""

    from mark_six.economics.expected_value import expected_value
    from mark_six.economics.state import build_current_state

    state = build_current_state(turnover_hkd * 100)
    result = expected_value(
        {
            1: first_division_fund_hkd * 100,
            2: state.division_funds_hkd_cents[2],
            3: state.division_funds_hkd_cents[3],
        },
        other_entries=turnover_hkd // 10 - 1,
        sharing_mode=sharing_mode,
    )
    typer.echo(f"Ticket cost HKD: {state.ticket_cost_hkd_cents / 100:.2f}")
    typer.echo(f"Expected payout HKD: {result.total_expected_payout_hkd_cents / 100:.8f}")
    typer.echo(f"Expected profit HKD: {result.expected_profit_hkd_cents / 100:.8f}")
    typer.echo(f"Return ratio: {result.expected_return_ratio:.8f}")
    typer.echo(f"House disadvantage: {result.house_disadvantage:.8f}")
    typer.echo(f"Expected value percent: {result.expected_value_percent:.6f}")


@economics_app.command("breakeven")
def economics_breakeven(
    turnover_hkd: Annotated[int, typer.Option(min=1)] = 100_000_000,
    target_return: Annotated[float, typer.Option(min=0.0)] = 1.0,
    sharing_mode: str = typer.Option("uniform"),
) -> None:
    """Solve a conditional First Division fund threshold."""

    from mark_six.economics.expected_value import first_fund_for_return_target
    from mark_six.economics.state import build_current_state

    state = build_current_state(turnover_hkd * 100)
    required = first_fund_for_return_target(
        target_return,
        {2: state.division_funds_hkd_cents[2], 3: state.division_funds_hkd_cents[3]},
        other_entries=turnover_hkd // 10 - 1,
        sharing_mode=sharing_mode,
    )
    typer.echo(f"Conditional required First Division fund HKD: {required / 100:.2f}")


@economics_app.command("sharing")
def economics_sharing(
    turnover_hkd: Annotated[int, typer.Option(min=10)] = 100_000_000,
) -> None:
    """Show the exact-binomial uniform First Division sharing benchmark."""

    from mark_six.economics.sharing import binomial_sharing, poisson_sharing

    probability = Fraction(1, 13_983_816)
    result = binomial_sharing(turnover_hkd // 10 - 1, probability)
    approximation = poisson_sharing(result.expected_other_winning_units)
    typer.echo(f"Expected other winning units: {result.expected_other_winning_units:.8f}")
    typer.echo(f"Expected payout share: {result.expected_share:.8f}")
    typer.echo(f"Sole winner probability: {result.sole_winner_probability:.8f}")
    typer.echo(f"Share with one probability: {result.share_with_one_probability:.8f}")
    typer.echo(f"Share with multiple probability: {result.share_with_multiple_probability:.8f}")
    typer.echo(f"Poisson expected share: {approximation.expected_share:.8f}")


def _economic_dividends(
    turnover_hkd: int, first_division_fund_hkd: int
) -> dict[int, int | Fraction]:
    from mark_six.economics.state import build_current_state
    from mark_six.mathematics.payouts import CURRENT_FIXED_PRIZES_HKD_CENTS

    state = build_current_state(turnover_hkd * 100)
    return {
        1: first_division_fund_hkd * 100,
        2: state.division_funds_hkd_cents[2],
        3: state.division_funds_hkd_cents[3],
        **CURRENT_FIXED_PRIZES_HKD_CENTS,
    }


@economics_app.command("multiple")
def economics_multiple(
    selections: Annotated[int, typer.Option(min=7, max=12)] = 7,
    turnover_hkd: Annotated[int, typer.Option(min=1)] = 100_000_000,
    first_division_fund_hkd: Annotated[int, typer.Option(min=0)] = 50_000_000,
) -> None:
    """Compare a Multiple entry with its exact expanded ordinary lines."""

    from mark_six.economics.portfolio import multiple_entry_economics

    result = multiple_entry_economics(
        selections, _economic_dividends(turnover_hkd, first_division_fund_hkd)
    )
    typer.echo("Payout scenario: explicit variable funds with no other winning units")
    typer.echo(f"Combinations: {result.combination_count}")
    typer.echo(f"Cost HKD: {result.cost_hkd_cents / 100:.2f}")
    typer.echo(f"Expected payout HKD: {float(result.expected_payout_hkd_cents / 100):.8f}")
    equal = result.expected_payout_hkd_cents == result.equivalent_ordinary_expected_payout_hkd_cents
    typer.echo(f"Expanded expectation equal: {str(equal).lower()}")
    typer.echo(f"Probability any prize: {float(result.probability_any_prize):.8f}")


@economics_app.command("banker")
def economics_banker(
    bankers: Annotated[int, typer.Option(min=1, max=5)] = 2,
    legs: Annotated[int, typer.Option(min=2, max=12)] = 5,
    turnover_hkd: Annotated[int, typer.Option(min=1)] = 100_000_000,
    first_division_fund_hkd: Annotated[int, typer.Option(min=0)] = 50_000_000,
) -> None:
    """Compare a Banker entry with its exact expanded ordinary lines."""

    from mark_six.economics.portfolio import banker_entry_economics

    result = banker_entry_economics(
        bankers, legs, _economic_dividends(turnover_hkd, first_division_fund_hkd)
    )
    typer.echo("Payout scenario: explicit variable funds with no other winning units")
    typer.echo(f"Combinations: {result.combination_count}")
    typer.echo(f"Cost HKD: {result.cost_hkd_cents / 100:.2f}")
    typer.echo(f"Expected payout HKD: {float(result.expected_payout_hkd_cents / 100):.8f}")
    equal = result.expected_payout_hkd_cents == result.equivalent_ordinary_expected_payout_hkd_cents
    typer.echo(f"Expanded expectation equal: {str(equal).lower()}")
    typer.echo(f"Probability any prize: {float(result.probability_any_prize):.8f}")


@economics_app.command("portfolio")
def economics_portfolio(
    budget_hkd: Annotated[int, typer.Option(min=10)] = 100,
) -> None:
    """Compare deterministic unique and duplicate fixed-budget coverage."""

    from mark_six.economics.analysis import _portfolio_tickets
    from mark_six.economics.portfolio import portfolio_metrics

    lines = budget_hkd // 10
    for offset, kind in enumerate(("diversified", "overlap", "duplicate")):
        metrics = portfolio_metrics(
            _portfolio_tickets(lines, kind, 2026091501 + offset + budget_hkd),
            expected_payout_per_line_hkd_cents=0,
        )
        typer.echo(
            f"{kind}: lines={metrics.ticket_count} unique={metrics.unique_combinations} "
            f"duplicates={metrics.duplicate_units} number_coverage={metrics.unique_numbers} "
            f"first_probability={_fraction(metrics.first_division_probability)}"
        )


@economics_app.command("run")
def economics_run() -> None:
    """Run the complete frozen Phase 8 analysis."""

    from mark_six.economics.analysis import run_economic_analysis

    result = run_economic_analysis(_project_root())
    typer.echo(f"Manifest: {result.manifest_path.relative_to(_project_root())}")
    typer.echo(f"Historical draws: {result.historical_draws}")
    typer.echo(f"Simulation trials: {result.simulation_trials}")
    for path in result.report_paths:
        typer.echo(f"Report: {path.relative_to(_project_root())}")


@economics_app.command("reports")
def economics_reports() -> None:
    """Locate the generated Phase 8 reports."""

    for relative in (
        "jackpot_economics.md",
        "prize_sharing.md",
        "ticket_construction.md",
        "phase8_analysis_manifest.json",
    ):
        path = _project_root() / "reports/generated" / relative
        if not path.exists():
            raise typer.BadParameter("Phase 8 outputs are absent; run `mark-six economics run`")
        typer.echo(f"Output: {path.relative_to(_project_root())}")


@economics_app.command("verify")
def economics_verify() -> None:
    """Verify the Phase 8 manifest, outputs, frozen inputs, and holdout isolation."""

    from mark_six.economics.analysis import verify_economic_analysis

    for name, value in verify_economic_analysis(_project_root()).items():
        typer.echo(f"{name}: {value}")


# PHASE8_EXTENSION_END


# PHASE9_EXTENSION_BEGIN
@app.command("build-final-system")
def build_final_system() -> None:
    """Generate final Phase 9 reports and the self-verifying manifest."""

    from mark_six.final_system.runner import build_phase9_outputs

    project_root = _project_root()
    path = build_phase9_outputs(project_root)
    typer.echo(f"Manifest: {path.relative_to(project_root)}")
    typer.echo("Prospective evaluation started: false")


@app.command("current")
def current_draw(
    evidence_path: Annotated[
        Path, typer.Option("--evidence", exists=True, dir_okay=False, help="Frozen evidence JSON.")
    ],
) -> None:
    """Validate and display a supplied pre-draw evidence record without fetching outcomes."""

    from mark_six.final_system.evidence import load_predraw_evidence

    evidence = load_predraw_evidence(evidence_path)
    typer.echo(f"Draw: {evidence.draw_id}")
    typer.echo(f"Draw date: {evidence.draw_date.isoformat()}")
    typer.echo(f"Frozen at: {evidence.frozen_at.isoformat()}")
    typer.echo(f"Evidence confidence: {evidence.evidence_confidence}")
    typer.echo(
        "Turnover forecast HKD: "
        f"{evidence.turnover_forecast.lower_hkd:,}.."
        f"{evidence.turnover_forecast.central_hkd:,}.."
        f"{evidence.turnover_forecast.upper_hkd:,}"
    )
    typer.echo("Outcome data accessed: false")


@app.command("evaluate")
def evaluate_current_draw(
    evidence_path: Annotated[
        Path, typer.Option("--evidence", exists=True, dir_okay=False, help="Frozen evidence JSON.")
    ],
    store: bool = typer.Option(
        True, "--store/--no-store", help="Store immutable evidence and evaluation records."
    ),
) -> None:
    """Evaluate one complete pre-draw record under frozen Phase 9 rules."""

    import hashlib

    from mark_six.final_system.evaluation import build_evaluation_record, evaluate_predraw
    from mark_six.final_system.evidence import load_predraw_evidence
    from mark_six.final_system.models import load_final_system_config
    from mark_six.final_system.storage import store_immutable_record

    project_root = _project_root()
    config_path = project_root / "configs/phase9_final_system.yaml"
    config = load_final_system_config(config_path)
    evidence = load_predraw_evidence(evidence_path)
    evaluation = evaluate_predraw(evidence, config)
    record = build_evaluation_record(
        evidence,
        evaluation,
        configuration_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
    )
    typer.echo(f"Decision: {evaluation.decision}")
    typer.echo(f"Expected payout HKD: {evaluation.central_expected_payout_hkd:.8f}")
    typer.echo(f"Expected profit HKD: {evaluation.central_expected_profit_hkd:.8f}")
    typer.echo(f"Expected return percent: {evaluation.central_expected_return_percent:.6f}")
    typer.echo(f"Break-even distance HKD: {evaluation.break_even_distance_hkd:.2f}")
    typer.echo(f"Worst-case return ratio: {evaluation.worst_case_return_ratio:.8f}")
    typer.echo(f"Best-case return ratio: {evaluation.best_case_return_ratio:.8f}")
    if store:
        evidence_path_stored = store_immutable_record(
            project_root,
            evidence,
            draw_id=evidence.draw_id,
            frozen_at=evidence.frozen_at,
            kind=config.storage.evidence_kind,
            storage_directory=config.storage.directory,
        )
        evaluation_path = store_immutable_record(
            project_root,
            record,
            draw_id=evidence.draw_id,
            frozen_at=record.frozen_at,
            kind=config.storage.evaluation_kind,
            storage_directory=config.storage.directory,
        )
        typer.echo(f"Evidence record: {evidence_path_stored.relative_to(project_root)}")
        typer.echo(f"Evaluation record: {evaluation_path.relative_to(project_root)}")
    else:
        typer.echo("Records stored: false")
    typer.echo("Outcome comparison status: not_started")


def _number_list(value: str | None, name: str) -> tuple[int, ...] | None:
    if value is None:
        return None
    try:
        return tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as error:
        raise typer.BadParameter(f"{name} must be a comma-separated integer list") from error


@app.command("tickets")
def tickets(
    budget_hkd: Annotated[int, typer.Option("--budget", min=10)] = 100,
    entry_type: str = typer.Option("uniform", "--entry-type"),
    seed: int = typer.Option(20260915),
    selections: str | None = typer.Option(None, help="Comma-separated Multiple selections."),
    bankers: str | None = typer.Option(None, help="Comma-separated banker numbers."),
    legs: str | None = typer.Option(None, help="Comma-separated Banker leg numbers."),
    split_risk_filter: bool = typer.Option(
        False, help="Use assumption-based qualitative split-risk filtering."
    ),
) -> None:
    """Create a unique, exact-cost uniform, Multiple, or Banker ticket plan."""

    from typing import Literal, cast

    from mark_six.final_system.models import TicketPlan
    from mark_six.final_system.tickets import plan_tickets

    if entry_type not in {"uniform", "multiple", "banker"}:
        raise typer.BadParameter("entry-type must be uniform, multiple, or banker")
    plan: TicketPlan = plan_tickets(
        entry_type=cast("Literal['uniform', 'multiple', 'banker']", entry_type),
        budget_hkd=budget_hkd,
        seed=seed,
        selections=_number_list(selections, "selections"),
        bankers=_number_list(bankers, "bankers"),
        legs=_number_list(legs, "legs"),
        split_risk_filter=split_risk_filter,
    )
    typer.echo(f"Entry type: {plan.entry_type}")
    typer.echo(f"Combinations: {plan.combination_count}")
    typer.echo(f"Unique combinations: {plan.unique_combination_count}")
    typer.echo(f"Exact cost HKD: {plan.exact_cost_hkd_cents / 100:.2f}")
    typer.echo(f"Unused budget HKD: {plan.unused_budget_hkd_cents / 100:.2f}")
    for ticket in plan.combinations:
        typer.echo(" ".join(f"{number:02d}" for number in ticket))
    typer.echo(plan.draw_probability_statement)
    typer.echo(plan.packaging_statement)
    if plan.split_risk_note:
        typer.echo(plan.split_risk_note)


@app.command("verify-all")
def verify_all() -> None:
    """Verify the full frozen research chain and final Phase 9 outputs."""

    from mark_six.final_system.runner import verify_phase9_outputs

    for name, value in verify_phase9_outputs(_project_root()).items():
        typer.echo(f"{name}: {value}")


# PHASE9_EXTENSION_END
