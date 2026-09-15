"""Deterministic final research, operating-guide, and limitation reports."""

from __future__ import annotations

from pathlib import Path

from mark_six.final_system.models import FinalSystemConfig


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_final_reports(project_root: Path, config: FinalSystemConfig) -> tuple[Path, ...]:
    """Write the three final reports without accessing draw outcomes."""

    summary = """# Final Mark Six research summary

## Evidence-backed conclusions

The historical dataset was collected from retained official evidence, rule-aware validated, and
published as the immutable canonical dataset `marksix-bc02467ec951c2d8`. The randomness test family
found no compelling system-wide anomaly after correction and fair-process calibration. The frozen
historical number-prediction family failed in Phase 6, and its negative conclusion replicated on
the independent 676-draw historical reserve in Phase 7. Historical number prediction is closed.

Under the fair 6/49 model, every valid six-number combination has exactly the same draw probability.
Hot, cold, due, recent, patterned, or unusual-looking numbers do not gain draw probability. Multiple
and Banker entries merely package their expanded ordinary combinations; equivalent full-unit lines
have the same cost and expected payout and packaging creates no additional expected value.

Ticket economics can nevertheless vary materially when official First Division funds, turnover,
and payout sharing vary. Positive expected value is conditional on a complete named set of official
inputs, turnover estimates, sharing assumptions, and current-rule calculations. It is not a general
jackpot rule. Higher turnover can increase lower-division funds while also increasing expected prize
sharing, materially changing a large First Division fund's value.

Actual Hong Kong Mark Six number-choice behavior, including Quick Pick share, remains unknown
because the project has no player-selection microdata. Uniform selection is a benchmark; lower and
higher sharing cases are behavioral sensitivities, not measured facts. The final system therefore
makes conservative decisions and fails closed when required evidence or exceptional funding state
is missing or uncertain.

## Final use boundary

Phase 9 builds the pre-draw system but performs no real prospective evaluation. The prospective
312-draw holdout remains sealed with zero entries and no outcome access. Any later comparison with
outcomes requires a separate, approved protocol and must use a decision record frozen before the
draw.
"""
    guide = f"""# Final Mark Six system guide

## Architecture

The system has five layers: strict official pre-draw evidence, an explainable turnover estimate,
the frozen Phase 8 economic engine, conservative decision rules, and timestamped immutable evidence
and evaluation records. No layer uses historical-number patterns or post-draw data.

## Commands

- `mark-six current --evidence PATH` validates and displays a complete pre-draw evidence record.
- `mark-six evaluate --evidence PATH` calculates the economic envelope and stores immutable records.
- `mark-six tickets --budget 100 --entry-type uniform --seed 20260915` creates unique random lines.
- `mark-six tickets --budget 500 --entry-type multiple --selections 1,2,3,4,5,6,7`
  expands a Multiple.
- `mark-six tickets --budget 500 --entry-type banker --bankers 1,2 --legs 3,4,5,6,7`
  expands a Banker.
- `mark-six verify-all` verifies the canonical data, Phases 5--9, outputs, and sealed holdout.

`current` and `evaluate` never fetch the completed-draw GraphQL history. Evidence must identify an
official draw-specific announcement or rule source, its publication and retrieval times, and a
freeze time before the draw. The official First Division amount must be named according to the
source; ambiguous `jackpot` or `derivedFirstPrizeDiv` fields are not accepted as invariant meanings.

## Turnover and decisions

Turnover method: `{config.turnover.method}`. The normal and special draw baselines are frozen
pre-holdout medians of HKD {config.turnover.normal_baseline_hkd:,} and HKD
{config.turnover.special_baseline_hkd:,}. A {config.turnover.fund_response_hkd_per_hkd:g} HKD/HKD
response above the HKD {config.turnover.reference_first_division_fund_hkd:,} reference is an
explicit assumption informed by Phase 8's descriptive association, not a causal model. The
interval is {config.turnover.lower_multiplier:.0%} to {config.turnover.upper_multiplier:.0%} of the
central case.

The nine-scenario envelope combines lower, central, and upper turnover with lower-sharing, uniform,
and higher-sharing cases. `ECONOMICALLY_INTERESTING` requires the worst case to return at least
{config.decision_rules.economically_interesting_minimum_worst_case_return_ratio:.0%} with at least
Medium evidence. `WATCH` requires the best case to reach
{config.decision_rules.watch_minimum_best_case_return_ratio:.0%}. Low confidence yields `SKIP`;
missing or exceptional-state evidence blocks evaluation entirely.

## Ticket plans and records

Budgets HKD 100, 500, and 1,000 are frozen defaults. Uniform plans sample without replacement inside
each line and reject duplicate combinations across the plan. Multiple and Banker plans show every
expanded combination, exact cost, combination count, and unused budget. The optional split-risk
filter is assumption-based and never described as changing draw probability.

Stored paths are `data/predraw/DRAW_ID/evidence/` and `data/predraw/DRAW_ID/evaluation/`. Filenames
contain a UTC timestamp and content-hash prefix; exclusive creation prevents overwrite. Evaluation
records bind the evidence hash, configuration hash, decision, metrics, sensitivities, and all nine
scenarios. Outcome fields are structurally absent and comparison status remains `not_started`.
"""
    limitations = """# Final system limitations

1. The turnover forecast is deliberately simple. Its draw-class baselines are historical medians,
   while the response to an official First Division amount and its uncertainty multipliers are
   explicit assumptions. Completed-draw association does not prove causality.
2. The GraphQL fields `jackpot` and `derivedFirstPrizeDiv` were reconciled only for a specific draw.
   Their meanings and pre-/post-draw availability are not assumed invariant.
3. Actual Hong Kong combination popularity and Quick Pick share are unknown. Lower- and
   higher-sharing cases are sensitivity assumptions, not estimates of player behavior.
4. Exceptional funding, incomplete Snowball state, rateable reductions, and other unresolved rule
   branches make the system fail closed. It does not impute missing economic inputs.
5. An advertised or estimated First Division amount must not be confused with an economically
   available fund unless the dated official source supports that use for the specific draw.
6. Positive expected value is conditional and assumption-dependent. No HKD 150 million or other
   advertised amount is an actionable universal rule; turnover and sharing can reverse the result.
7. Optional split-risk features may affect sharing only if unobserved player choices are nonuniform.
   They never change draw probability and lack Hong Kong microdata validation.
8. Multiple and Banker packaging changes covariance and prize bundling, not expected value per
   equivalent full-unit combination.
9. The 676-draw historical reserve has already served its Phase 7 replication purpose. The separate
   prospective holdout remains sealed and is not used to tune or validate Phase 9.
10. Phase 9 creates a prospective record format but does not start real-draw evaluation or outcome
    comparison. That work requires a separately frozen and approved future protocol.
"""
    paths = tuple(project_root / relative for relative in config.outputs.reports)
    return (
        _write(paths[0], summary),
        _write(paths[1], guide),
        _write(paths[2], limitations),
    )
