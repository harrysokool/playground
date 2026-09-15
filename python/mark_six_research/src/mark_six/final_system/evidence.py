"""Construction and strict loading of outcome-free pre-draw evidence."""

from __future__ import annotations

from pathlib import Path

from mark_six.final_system.models import (
    CONFIDENCE_RANK,
    Confidence,
    FinalSystemConfig,
    PreDrawEvidence,
    PreDrawFacts,
)
from mark_six.final_system.turnover import forecast_turnover


def build_predraw_evidence(facts: PreDrawFacts, config: FinalSystemConfig) -> PreDrawEvidence:
    """Attach the frozen turnover forecast and conservative aggregate confidence."""

    forecast = forecast_turnover(facts, config.turnover)
    confidences: list[Confidence] = [forecast.confidence]
    confidences.extend(source.confidence for source in facts.sources)
    aggregate = min(confidences, key=lambda value: CONFIDENCE_RANK[value])
    return PreDrawEvidence(
        **facts.model_dump(),
        evidence_confidence=aggregate,
        turnover_forecast=forecast,
    )


def load_predraw_evidence(path: Path) -> PreDrawEvidence:
    """Load one strict JSON evidence record; extra or missing fields fail closed."""

    return PreDrawEvidence.model_validate_json(path.read_text(encoding="utf-8"))
