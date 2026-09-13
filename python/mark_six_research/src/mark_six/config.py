"""Typed project-configuration loading."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict


class ProjectConfig(BaseModel):
    """Stable, human-editable settings for the research project."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    project_name: str
    project_slug: str
    status: str
    timezone: str
    currency: str
    random_seed: int


def default_config_path() -> Path:
    """Return the project configuration path for a source checkout."""

    return Path(__file__).resolve().parents[2] / "configs" / "project.yaml"


def load_project_config(path: Path | None = None) -> ProjectConfig:
    """Load and validate the project configuration."""

    config_path = path or default_config_path()
    with config_path.open(encoding="utf-8") as config_file:
        raw: Any = yaml.safe_load(config_file)

    if not isinstance(raw, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {config_path}")

    return ProjectConfig.model_validate(raw)
