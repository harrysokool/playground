from fractions import Fraction
from pathlib import Path

from mark_six.domain.rules import RULE_VERSIONS
from mark_six.mathematics.reporting import (
    MATHEMATICAL_MODELS,
    OFFICIAL_FIRST_DIVISION_ONE_IN,
    render_current_game_mathematics_report,
    render_expected_value_foundation_report,
    render_prize_probability_report,
    write_prize_probability_report,
)


def test_report_is_deterministic_and_matches_official_first_division_odds(tmp_path: Path) -> None:
    report = render_prize_probability_report()

    assert render_prize_probability_report() == report
    assert "**MATCH**" in report
    assert f"1 in {OFFICIAL_FIRST_DIVISION_ONE_IN:,}" in report
    assert "Exact probability sum including No Prize: `1/1`" in report
    assert "no draw-frequency or predictive analysis" in report

    path = write_prize_probability_report(tmp_path / "probabilities.md")
    assert path.read_text(encoding="utf-8") == report


def test_historical_model_mapping_is_complete_and_keeps_1996_ambiguous() -> None:
    mappings: dict[str, set[tuple[int, int]]] = {rule_id: set() for rule_id in RULE_VERSIONS}
    for model in MATHEMATICAL_MODELS:
        for rule_id in model.rule_version_ids:
            mappings[rule_id].add((model.pool_size, model.prize_divisions))

    assert set(mappings) == set(RULE_VERSIONS)
    assert mappings["hkjc_mark_six_1996_pool_transition_unresolved"] == {(45, 6), (47, 6)}
    assert Fraction(1, OFFICIAL_FIRST_DIVISION_ONE_IN) == Fraction(1, 13_983_816)


def test_current_game_report_contains_required_exact_results() -> None:
    report = render_current_game_mathematics_report()

    assert "C(49,6) = 13,983,816" in report
    assert "Probability of winning any prize" in report
    assert "Multiple entries" in report
    assert "Banker entries" in report
    assert "every valid combination" in report
    assert "hot number" not in report.lower()


def test_expected_value_report_separates_exact_results_and_assumptions() -> None:
    report = render_expected_value_foundation_report()

    assert "54% (`27/50`)" in report
    assert "Snowball Deduction" in report
    assert "Lottery Duty" in report
    assert "Behavioral assumption" in report
    assert "jackpot size is insufficient" in report.lower()
    assert "positive expected-value claim" in report
