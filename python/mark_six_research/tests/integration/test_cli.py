from pathlib import Path

import pytest
from typer.testing import CliRunner

from mark_six.cli import app
from mark_six.prediction.analysis import PredictionRunResult
from mark_six.replication.models import ReplicationRunResult
from mark_six.statistics.analysis import AnalysisRunResult

runner = CliRunner()


def test_info_command_starts_and_reports_environment() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "Project: Hong Kong Mark Six Research" in result.stdout
    assert "Python: 3.12." in result.stdout
    assert "Status: phase_9_final_research_system" in result.stdout


def test_probability_report_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)

    result = runner.invoke(app, ["mathematics", "prize-probabilities"])

    assert result.exit_code == 0
    assert "reports/generated/prize_probabilities.md" in result.stdout
    report = tmp_path / "reports" / "generated" / "prize_probabilities.md"
    assert "**MATCH**" in report.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["mathematics", "odds"], "any_prize: probability=4654/249711"),
        (
            ["mathematics", "first-division", "--pool-size", "47"],
            "First Division probability: 1/10737573",
        ),
        (
            ["mathematics", "multiple", "--selections", "8"],
            "Combinations: 28\nCost cents: 28000",
        ),
        (
            ["mathematics", "multiple", "--selections", "8", "--partial-unit"],
            "Cost cents: 14000",
        ),
        (
            ["mathematics", "banker", "--bankers", "2", "--legs", "5"],
            "Combinations: 5\nCost cents: 5000",
        ),
        (
            [
                "mathematics",
                "simulate",
                "--trials",
                "2000",
                "--seed",
                "7",
                "--pool-size",
                "45",
                "--prize-divisions",
                "6",
            ],
            "Evidence: simulation_estimate\nTrials: 2000\nSeed: 7",
        ),
    ],
)
def test_mathematics_inspection_commands(arguments: list[str], expected: str) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 0, result.stdout
    assert expected in result.stdout


def test_all_mathematics_reports_are_generated_without_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)

    result = runner.invoke(app, ["mathematics", "reports"])

    assert result.exit_code == 0
    assert not (tmp_path / "data").exists()
    for filename in (
        "prize_probabilities.md",
        "current_game_mathematics.md",
        "expected_value_foundation.md",
    ):
        path = tmp_path / "reports" / "generated" / filename
        assert path.exists()
        assert "holdout" not in path.read_text(encoding="utf-8").lower()


def test_statistics_run_reports_scope_and_corrections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "reports" / "generated" / "randomness_analysis.md"
    manifest = tmp_path / "reports" / "generated" / "phase5_analysis_manifest.json"
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)
    monkeypatch.setattr(
        "mark_six.cli.run_randomness_analysis",
        lambda _root, seed, simulations: AnalysisRunResult(
            report_path=report,
            manifest_path=manifest,
            output_directory=report.parent / "phase5",
            included_draws=4_281,
            excluded_draws=106,
            individual_hypotheses=3_529,
            omnibus_hypotheses=42,
            raw_significant=180,
            corrected_significant=2,
            inconsistent_findings=(),
        ),
    )

    result = runner.invoke(app, ["stats", "run", "--seed", "7", "--simulations", "10"])

    assert result.exit_code == 0
    assert "Included draws: 4281" in result.stdout
    assert "Excluded draws: 106" in result.stdout
    assert "Confirmatory hypotheses: 3571" in result.stdout
    assert "Meaningful fair-null deviations: 0" in result.stdout


def test_statistics_inspection_commands_require_generated_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)

    result = runner.invoke(app, ["stats", "pairs"])

    assert result.exit_code != 0
    assert "run `mark-six stats run` first" in result.stderr


def test_prediction_models_lists_frozen_pair_free_family() -> None:
    result = runner.invoke(app, ["predict", "models"])

    assert result.exit_code == 0, result.stdout
    assert "Protocol: phase6-predictive-signal-v1" in result.stdout
    assert result.stdout.count('"name"') == 11
    assert '"name": "uniform"' in result.stdout
    assert "2-26" not in result.stdout


def test_prediction_run_reports_registered_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "reports" / "generated" / "predictive_signal_analysis.md"
    manifest = tmp_path / "reports" / "generated" / "phase6_analysis_manifest.json"
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)
    monkeypatch.setattr(
        "mark_six.cli.run_predictive_analysis",
        lambda _root: PredictionRunResult(
            report_path=report,
            manifest_path=manifest,
            output_directory=report.parent / "phase6",
            primary_scored_draws=2450,
            candidate_models=11,
            simulation_histories=500,
            selected_best_model="gap_due",
            primary_signal=False,
        ),
    )

    result = runner.invoke(app, ["predict", "run"])

    assert result.exit_code == 0, result.stdout
    assert "Primary scored draws: 2450" in result.stdout
    assert "Candidate models: 11" in result.stdout
    assert "Fair histories: 500" in result.stdout
    assert "Primary predictive signal: false" in result.stdout


def test_replication_run_reports_registered_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "reports" / "generated" / "historical_replication.md"
    manifest = tmp_path / "reports" / "generated" / "phase7_analysis_manifest.json"
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)
    monkeypatch.setattr(
        "mark_six.replication.runner.run_historical_replication",
        lambda _root: ReplicationRunResult(
            report_path=report,
            manifest_path=manifest,
            output_directory=report.parent / "phase7",
            reserve_draws=676,
            candidate_models=11,
            simulation_histories=500,
            selected_best_model="gap_due",
            successful_models=(),
            phase6_conclusion_replicated=True,
        ),
    )

    result = runner.invoke(app, ["replicate", "run"])

    assert result.exit_code == 0, result.stdout
    assert "Reserve draws: 676" in result.stdout
    assert "Candidate models: 11" in result.stdout
    assert "Fair histories: 500" in result.stdout
    assert "Phase 6 conclusion replicated: true" in result.stdout


def test_replication_inspection_commands_require_generated_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)

    for command in ("report", "compare"):
        result = runner.invoke(app, ["replicate", command])
        assert result.exit_code != 0
        assert "Phase 7" in result.stderr
        assert "absent" in result.stderr


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["economics", "expected-value"], "Expected payout HKD:"),
        (["economics", "breakeven"], "Conditional required First Division fund HKD:"),
        (["economics", "sharing"], "Sole winner probability:"),
        (["economics", "multiple", "--selections", "7"], "Expanded expectation equal: true"),
        (
            ["economics", "banker", "--bankers", "2", "--legs", "5"],
            "Expanded expectation equal: true",
        ),
        (["economics", "portfolio", "--budget-hkd", "100"], "duplicate: lines=10 unique=1"),
    ],
)
def test_economics_inspection_commands(arguments: list[str], expected: str) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 0, result.stdout
    assert expected in result.stdout


def test_economics_reports_require_generated_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("mark_six.cli._project_root", lambda: tmp_path)

    result = runner.invoke(app, ["economics", "reports"])

    assert result.exit_code != 0
    assert "Phase 8 outputs are absent" in result.stderr


def test_phase9_current_and_evaluate_synthetic_fixture() -> None:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "tests/fixtures/final_system/synthetic_predraw_watch.json"
    )
    current = runner.invoke(app, ["current", "--evidence", str(fixture)])
    assert current.exit_code == 0, current.output
    assert "Evidence confidence: Medium" in current.stdout
    assert "Outcome data accessed: false" in current.stdout

    evaluation = runner.invoke(app, ["evaluate", "--evidence", str(fixture), "--no-store"])
    assert evaluation.exit_code == 0, evaluation.output
    assert "Decision: WATCH" in evaluation.stdout
    assert "Records stored: false" in evaluation.stdout
    assert "Outcome comparison status: not_started" in evaluation.stdout


def test_phase9_ticket_cli_is_unique_and_exact_cost() -> None:
    result = runner.invoke(
        app,
        ["tickets", "--budget", "100", "--entry-type", "uniform", "--seed", "20260915"],
    )
    assert result.exit_code == 0, result.output
    assert "Combinations: 10" in result.stdout
    assert "Unique combinations: 10" in result.stdout
    assert "Exact cost HKD: 100.00" in result.stdout
    assert "same draw probability" in result.stdout
