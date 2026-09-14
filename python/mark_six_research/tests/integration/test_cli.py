from pathlib import Path

import pytest
from typer.testing import CliRunner

from mark_six.cli import app
from mark_six.statistics.analysis import AnalysisRunResult

runner = CliRunner()


def test_info_command_starts_and_reports_environment() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "Project: Hong Kong Mark Six Research" in result.stdout
    assert "Python: 3.12." in result.stdout
    assert "Status: phase_5_randomness_testing" in result.stdout


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
