from pathlib import Path

import pytest
from pydantic import ValidationError

from mark_six.config import load_project_config


def test_default_configuration_loads() -> None:
    config = load_project_config()

    assert config.project_slug == "mark-six-research"
    assert config.currency == "HKD"
    assert config.timezone == "Asia/Hong_Kong"


def test_configuration_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        """
schema_version: "1"
project_name: "Hong Kong Mark Six Research"
project_slug: "mark-six-research"
status: "foundation"
timezone: "Asia/Hong_Kong"
currency: "HKD"
random_seed: 1
unexpected: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_project_config(config_path)
