"""Machine-readable rule periods supported by reviewed evidence."""

from datetime import date

from mark_six.domain.models import RuleVersion

CURRENT_RULES = RuleVersion(
    rule_version_id="hkjc_mark_six_2024_05_21",
    effective_from=date(2024, 5, 21),
    effective_to=None,
    verification_status="verified",
    number_min=1,
    number_max=49,
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=1_000,
    prize_divisions=7,
    reported_prize_division_count=7,
)

RULES_2010_PARTIAL = RuleVersion(
    rule_version_id="hkjc_mark_six_2010_11_09_partial",
    effective_from=date(2010, 11, 9),
    effective_to=date(2024, 5, 20),
    verification_status="partially_verified",
    number_min=1,
    number_max=49,
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=1_000,
    prize_divisions=7,
    reported_prize_division_count=7,
)

RULES_2002_PARTIAL = RuleVersion(
    rule_version_id="hkjc_mark_six_2002_07_03_partial",
    effective_from=date(2002, 7, 3),
    effective_to=date(2010, 11, 8),
    verification_status="partially_verified",
    number_min=1,
    number_max=49,
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=500,
    prize_divisions=7,
    reported_prize_division_count=7,
)

RULES_1997_TO_2002_PARTIAL = RuleVersion(
    rule_version_id="hkjc_mark_six_1997_to_2002_07_02_partial",
    effective_from=date(1997, 1, 1),
    effective_to=date(2002, 7, 2),
    verification_status="partially_verified",
    number_min=1,
    number_max=47,
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=500,
    prize_divisions=6,
)

# The exact 1996 pool transition is unresolved. A maximum of 47 is deliberately an upper bound,
# not a claim that every 1996 draw used 47 balls.
RULES_1996_UNRESOLVED = RuleVersion(
    rule_version_id="hkjc_mark_six_1996_pool_transition_unresolved",
    effective_from=date(1996, 1, 1),
    effective_to=date(1996, 12, 31),
    verification_status="partially_verified",
    number_min=1,
    number_max=47,
    number_range_status="conservative_upper_bound",
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=500,
    prize_divisions=6,
)

# The exact 1995 stake transition is resolved per record from the official source's unitBet field.
RULES_1995_STAKE4_UNRESOLVED = RuleVersion(
    rule_version_id="hkjc_mark_six_1995_stake4_transition_unresolved",
    effective_from=date(1995, 1, 1),
    effective_to=date(1995, 12, 31),
    verification_status="partially_verified",
    number_min=1,
    number_max=45,
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=400,
    unit_stake_status="source_observed",
    prize_divisions=6,
)

RULES_1995_STAKE5_UNRESOLVED = RuleVersion(
    rule_version_id="hkjc_mark_six_1995_stake5_transition_unresolved",
    effective_from=date(1995, 1, 1),
    effective_to=date(1995, 12, 31),
    verification_status="partially_verified",
    number_min=1,
    number_max=45,
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=500,
    unit_stake_status="source_observed",
    prize_divisions=6,
)

RULES_1993_TO_1994_PARTIAL = RuleVersion(
    rule_version_id="hkjc_mark_six_1993_to_1994_partial",
    effective_from=date(1993, 1, 1),
    effective_to=date(1994, 12, 31),
    verification_status="partially_verified",
    number_min=1,
    number_max=45,
    main_numbers_drawn=6,
    extra_numbers_drawn=1,
    unit_stake_hkd_cents=400,
    prize_divisions=6,
)

# Compatibility alias for the Phase 2 fixture.
RULES_1995_SAMPLE_PARTIAL = RULES_1995_STAKE4_UNRESOLVED

_RULES = (
    CURRENT_RULES,
    RULES_2010_PARTIAL,
    RULES_2002_PARTIAL,
    RULES_1997_TO_2002_PARTIAL,
    RULES_1996_UNRESOLVED,
    RULES_1995_STAKE4_UNRESOLVED,
    RULES_1995_STAKE5_UNRESOLVED,
    RULES_1993_TO_1994_PARTIAL,
)
RULE_VERSIONS = {rule.rule_version_id: rule for rule in _RULES}


def rule_for_draw(draw_date: date, unit_stake_hkd_cents: int) -> RuleVersion:
    """Resolve a sampled draw without guessing inside the 1995 stake transition."""

    if draw_date.year == 1995:
        if unit_stake_hkd_cents == 400:
            return RULES_1995_STAKE4_UNRESOLVED
        if unit_stake_hkd_cents == 500:
            return RULES_1995_STAKE5_UNRESOLVED
        raise LookupError(f"No 1995 rule candidate has source stake {unit_stake_hkd_cents} cents")
    return rule_for_draw_date(draw_date)


def rule_for_draw_date(draw_date: date) -> RuleVersion:
    """Return an unambiguous reviewed rule period for a draw date."""

    matches = [
        rule
        for rule in _RULES
        if rule.effective_from is not None
        and draw_date >= rule.effective_from
        and (rule.effective_to is None or draw_date <= rule.effective_to)
    ]
    if len(matches) != 1:
        raise LookupError(f"No unambiguous reviewed rule version covers {draw_date.isoformat()}")
    return matches[0]
