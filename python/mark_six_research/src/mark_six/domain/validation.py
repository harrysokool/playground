"""Rule-aware validation for parsed Mark Six draws."""

from mark_six.domain.models import ParsedDraw, RuleVersion, ValidationIssue


def validate_draw(draw: ParsedDraw, rule: RuleVersion) -> list[ValidationIssue]:
    """Return every detected problem without mutating or repairing the draw."""

    issues: list[ValidationIssue] = []

    def add(code: str, field: str, message: str) -> None:
        issues.append(ValidationIssue(code=code, field=field, message=message))

    if draw.rule_version_id != rule.rule_version_id:
        add("rule_version_mismatch", "rule_version_id", "Draw and validator rule IDs differ")
    if rule.effective_from is not None and draw.draw_date < rule.effective_from:
        add("date_before_rule", "draw_date", "Draw predates the rule interval")
    if rule.effective_to is not None and draw.draw_date > rule.effective_to:
        add("date_after_rule", "draw_date", "Draw follows the rule interval")
    if len(draw.main_numbers) != rule.main_numbers_drawn:
        add(
            "main_number_count",
            "main_numbers",
            f"Expected {rule.main_numbers_drawn} main numbers, found {len(draw.main_numbers)}",
        )
    if len(set(draw.main_numbers)) != len(draw.main_numbers):
        add("duplicate_main_number", "main_numbers", "Main numbers must be unique")
    for number in draw.main_numbers:
        if not rule.number_min <= number <= rule.number_max:
            add(
                "main_number_out_of_range",
                "main_numbers",
                f"Main number {number} is outside {rule.number_min}..{rule.number_max}",
            )
    if rule.extra_numbers_drawn != 1:
        add(
            "unsupported_extra_count",
            "extra_number",
            "This parsed source shape supports exactly one Extra Number",
        )
    if not rule.number_min <= draw.extra_number <= rule.number_max:
        add(
            "extra_number_out_of_range",
            "extra_number",
            f"Extra Number is outside {rule.number_min}..{rule.number_max}",
        )
    if draw.extra_number in draw.main_numbers:
        add("extra_number_duplicates_main", "extra_number", "Extra Number duplicates a main number")
    if draw.unit_stake_hkd_cents != rule.unit_stake_hkd_cents:
        add("unit_stake_mismatch", "unit_stake_hkd_cents", "Source stake differs from rule stake")

    money_fields = {
        "turnover_hkd_cents": draw.turnover_hkd_cents,
        "reported_jackpot_hkd_cents": draw.reported_jackpot_hkd_cents,
        "estimated_first_prize_hkd_cents": draw.estimated_first_prize_hkd_cents,
        "reported_derived_first_prize_hkd_cents": (draw.reported_derived_first_prize_hkd_cents),
    }
    for field, value in money_fields.items():
        if value is not None and value < 0:
            add("negative_money", field, "Money values cannot be negative")

    divisions: list[int] = []
    for prize in draw.prizes:
        divisions.append(prize.division)
        if not 1 <= prize.division <= rule.prize_divisions:
            add("invalid_prize_division", "prizes", f"Invalid prize division {prize.division}")
        if prize.source_winning_unit_amount < 0 or prize.winning_units < 0:
            add("negative_winning_units", "prizes", "Winning units cannot be negative")
        if prize.dividend_hkd_cents is not None and prize.dividend_hkd_cents < 0:
            add("negative_dividend", "prizes", "Prize dividends cannot be negative")
    if len(set(divisions)) != len(divisions):
        add("duplicate_prize_division", "prizes", "Prize divisions must be unique per draw")
    return issues
