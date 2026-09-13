"""Evidence labels that prevent estimates and assumptions from appearing as exact results."""

from enum import StrEnum


class EvidenceType(StrEnum):
    """Controlled evidence vocabulary for the Phase 4 mathematical layer."""

    EXACT_COMBINATORIAL_RESULT = "exact_combinatorial_result"
    OFFICIAL_RULE_CALCULATION = "official_rule_based_calculation"
    HISTORICAL_SOURCE_OBSERVATION = "historical_source_observation"
    SIMULATION_ESTIMATE = "simulation_estimate"
    ECONOMIC_ASSUMPTION = "economic_assumption"
    BEHAVIORAL_ASSUMPTION = "behavioral_assumption"
