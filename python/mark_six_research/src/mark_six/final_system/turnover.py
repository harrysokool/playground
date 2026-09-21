"""Explainable pre-draw turnover estimation without machine learning."""

from __future__ import annotations

from mark_six.final_system.models import PreDrawFacts, TurnoverConfig, TurnoverForecast


def forecast_turnover(facts: PreDrawFacts, config: TurnoverConfig) -> TurnoverForecast:
    """Forecast turnover from draw class and a dated official First Division amount."""

    baseline = (
        config.special_baseline_hkd if facts.draw_type == "special" else config.normal_baseline_hkd
    )
    fund_hkd = facts.official_first_division_fund_hkd_cents / 100
    excess_fund = max(0.0, fund_hkd - config.reference_first_division_fund_hkd)
    central = max(
        config.floor_hkd, round(baseline + excess_fund * config.fund_response_hkd_per_hkd)
    )
    lower = max(config.floor_hkd, round(central * config.lower_multiplier))
    upper = max(central, round(central * config.upper_multiplier))
    return TurnoverForecast(
        method=config.method,
        central_hkd=central,
        lower_hkd=lower,
        upper_hkd=upper,
        confidence="Medium",
        evidence_class=config.evidence_class,
        explanation=(
            "Frozen current-rule draw-class median plus a 0.25 HKD/HKD response to the amount "
            "above the HKD 8m reference. The response and range are assumptions informed by "
            "pre-holdout completed-draw associations, not causal or official forecasts."
        ),
    )
