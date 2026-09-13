from typer.testing import CliRunner

from mark_six.cli import app

runner = CliRunner()


def test_info_command_starts_and_reports_environment() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "Project: Hong Kong Mark Six Research" in result.stdout
    assert "Python: 3.12." in result.stdout
    assert "Status: phase_3_dataset" in result.stdout
