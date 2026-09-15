"""Human-readable Phase 8 economic reports."""

from __future__ import annotations

from pathlib import Path
from typing import cast


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_economic_reports(
    project_root: Path,
    *,
    fixed_rows: list[dict[str, object]],
    jackpot_rows: list[dict[str, object]],
    sharing_rows: list[dict[str, object]],
    breakeven_rows: list[dict[str, object]],
    turnover_rows: list[dict[str, object]],
    normal_special: list[dict[str, object]],
    system_rows: list[dict[str, object]],
    portfolio_rows: list[dict[str, object]],
    simulation_rows: list[dict[str, object]],
) -> tuple[Path, ...]:
    """Write the three required reports from registered output rows."""

    fixed_total = sum(float(cast(float, row["expected_payout_hkd"])) for row in fixed_rows)
    positive = [row for row in jackpot_rows if float(cast(float, row["return_ratio"])) > 1.0]
    best = max(jackpot_rows, key=lambda row: float(cast(float, row["return_ratio"])))
    positive_by_mode = {
        mode: sum(
            float(cast(float, row["return_ratio"])) > 1.0
            for row in jackpot_rows
            if row["sharing_mode"] == mode
        )
        for mode in ("no_sharing", "uniform", "higher_sharing")
    }
    uniform_150 = [
        row
        for row in jackpot_rows
        if row["sharing_mode"] == "uniform" and row["first_division_fund_hkd"] == 150_000_000
    ]
    uniform_150_text = ", ".join(
        f"{int(cast(int, row['turnover_hkd'])) // 1_000_000}m turnover: "
        f"{float(cast(float, row['return_ratio'])):.4f}"
        for row in uniform_150
    )
    hundred = [row for row in breakeven_rows if row["target_return_ratio"] == 1.0]
    minimum_threshold = min(
        float(cast(float, row["required_first_division_fund_hkd"])) for row in hundred
    )
    maximum_threshold = max(
        float(cast(float, row["required_first_division_fund_hkd"])) for row in hundred
    )
    jackpot = f"""# Phase 8 jackpot economics

## Result

One current full-unit ticket costs HKD 10. Exact fixed Divisions 4--7 contribute HKD
{fixed_total:.12f} of expected gross payout. The remaining value is conditional on explicit
Division 1--3 funds and sharing. Expected payout, not profit, is shown; profit subtracts HKD 10.

Across the frozen grid, {len(positive)} of {len(jackpot_rows)} conditional scenarios exceed a 100%
return. The highest is {float(cast(float, best["return_ratio"])):.6f} at turnover HKD
{int(cast(int, best["turnover_hkd"])):,}, First Division fund HKD
{int(cast(int, best["first_division_fund_hkd"])):,}, under `{best["sharing_mode"]}`. This is a
scenario result, not a claim that an advertised jackpot is the available First Division fund.

Positive cases by model are: no sharing {positive_by_mode["no_sharing"]}, uniform
{positive_by_mode["uniform"]}, and synthetic higher sharing
{positive_by_mode["higher_sharing"]}. The no-sharing case gives one unit an entire variable
division fund and is deliberately unrealistic. At a stated HKD 150m First Division fund,
uniform-selection return ratios are {uniform_150_text}.

The 100% thresholds across all models span HKD {minimum_threshold:,.0f}
to HKD {maximum_threshold:,.0f}
over the registered turnover and sharing assumptions. Zero occurs only because no-sharing assigns
complete Division 2 and 3 funds to a sole qualifying unit. Uniform thresholds are HKD 110.19m,
128.94m, and 173.04m at HKD 50m, 100m, and 200m turnover. There is no universal break-even jackpot.

## Current accounting

Turnover is allocated exactly: 54% Prize Fund, 25% duty, 15% Lotteries Fund, and 6% HKJC
commission. Expected fixed liabilities and the published Snowball Deduction are removed before the
remaining pool starts at 45%/15%/40% for Divisions 1/2/3. The HKD 8m First Division minimum,
carryover, and special contributions are explicit state components. Exceptional Rule 3.16,
minimum-hierarchy, or sole-partial-unit cases stop rather than being guessed.

## Historical evidence

The current-rule historical association analysis is descriptive and uses completed-draw fields
only. It does not claim publication timing or causality. Turnover rows: {len(turnover_rows)};
normal/special
groups: {len(normal_special)}. Actual winner counts and dividends are ex-post facts and never become
prospective inputs.

Official sources: [current allocation and notice](https://special.hkjc.com/e-win/en-US/betting-info/marksix/important-notice/),
[formal rules](https://www.hkjc.com/english/betting/template_betting_rule_files/pdf/Lotteries_Rule_3_Eng_20260330.pdf),
and the [2026/096 announcement](https://www.hkjc.com/english/pressrelease/mcs01_showhtml.asp?SelType=NEWS&filename=20260829_114346_E_NEWS.htm).
"""
    representative = sharing_rows[len(sharing_rows) // 2]
    sole_text = ", ".join(
        f"{float(cast(float, row['sole_winner_probability'])):.4f}" for row in sharing_rows
    )
    multiple_text = ", ".join(
        f"{float(cast(float, row['share_with_multiple_probability'])):.4f}" for row in sharing_rows
    )
    sharing = f"""# Phase 8 prize sharing

## Uniform benchmark

Every combination has draw probability 1/13,983,816. Conditional on our ticket winning First
Division, `X`, the other winning units under independent uniform line selection, is binomial. The
expected share is `E[1/(1+X)]`; exact sole, one-other, and multiple-other probabilities are
reported.

At turnover HKD {int(cast(int, representative["turnover_hkd"])):,}, the model has
{float(cast(float, representative["expected_other_first_winners"])):.6f} expected other First
Division units, sole-winner probability
{float(cast(float, representative["sole_winner_probability"])):.6f}, one-other probability
{float(cast(float, representative["share_with_one_probability"])):.6f}, and multiple-other
probability {float(cast(float, representative["share_with_multiple_probability"])):.6f}. The
Poisson expected-share approximation differs by
{float(cast(float, representative["absolute_approximation_error"])):.3g}.

Across HKD 50m, 100m, and 200m turnover, sole-winner probabilities are {sole_text};
multiple-other-winner probabilities are {multiple_text}.

## Human choice and limits

No Hong Kong Mark Six ticket-selection microdata was found. External lottery research documents
conscious clustering, birthdays, lucky numbers, and visual/representative patterns in other markets.
General Hong Kong evidence supports cultural salience of 8 and aversion to 4, but not Mark Six sales
frequencies. A 2026 Hong Kong preprint is an unreviewed research lead and is not used to estimate a
split advantage or reopen prediction.

Unpopular-looking combinations may reduce payout sharing conditional on winning if human choices
are nonuniform. They do not improve draw probability. The three-times popularity case is synthetic
sensitivity, not an estimated Hong Kong behavior model.

Evidence: [Baker and McHale (2011)](https://doi.org/10.1111/j.1467-985X.2011.00693.x),
[gambler's-fallacy choice evidence](https://www.sciencedirect.com/science/article/pii/S0167268114002716),
and [Hong Kong superstition evidence](https://pmc.ncbi.nlm.nih.gov/articles/PMC7113914/).
"""
    system_summary = ", ".join(
        f"{row['entry_type']}={str(row['expectation_equal']).lower()}" for row in system_rows
    )
    budget_100 = [row for row in portfolio_rows if row["budget_hkd"] == 100]
    budget_100_risk = "; ".join(
        f"{row['construction']}: any-prize "
        f"{float(cast(float, row['simulated_probability_any_prize_hkd100_budget'])):.4f}, "
        f"variance HKD^2 "
        f"{float(cast(float, row['simulated_payout_variance_hkd_squared_hkd100_budget'])):,.0f}"
        for row in budget_100
    )
    simulation_ok = all(bool(row["within_three_standard_errors"]) for row in simulation_rows)
    construction = f"""# Phase 8 ticket construction

## Packaging result

Multiple and Banker entries are exactly their expanded ordinary combinations at the equivalent
stake. Their expected payout equals buying those same lines separately ({system_summary}). System
entries can produce simultaneous prizes, and shared numbers create covariance, so payout variance
and chance of any prize need not match an independence shortcut.

## Fixed budgets

The registered HKD 100, 500, and 1,000 examples contain {len(portfolio_rows)} named constructions.
Expected payout is linear in owned units. Unique lines increase First Division coverage relative to
duplicates; lower overlap changes risk and number-pool coverage, not per-line expectation. An
intentional duplicate preserves expected payout per dollar but concentrates outcomes. No portfolio
is universally best without naming the objective.

For the HKD 100 portfolio, the registered 500,000-draw joint simulations give {budget_100_risk}.
Variable qualifications use one-cent markers so `any-prize` includes all seven divisions, while
the reported variance is effectively fixed-prize variance and does not pretend to estimate the
rare variable-prize tail. These are risk estimates under the fair draw, not expected-value
advantages.

Split-risk features are qualitative scenario inputs only. Birthday range, sequences, repeated last
digits, parity, and salient numbers do not change draw probability. Simulation was deterministic
and agreed with registered exact expectations within three Monte Carlo standard errors:
{str(simulation_ok).lower()}.
"""
    return (
        _write(project_root / "reports/generated/jackpot_economics.md", jackpot),
        _write(project_root / "reports/generated/prize_sharing.md", sharing),
        _write(project_root / "reports/generated/ticket_construction.md", construction),
    )
