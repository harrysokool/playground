# Decision 0008: Mark Six economic-value protocol

- Status: frozen before the main historical economic analysis
- Protocol version: `phase8-economic-value-v1`
- Phase 7 baseline commit: `aea6923df86e6e20623064abd8fe824cba3eb17a`
- Dataset: `marksix-bc02467ec951c2d8`
- Dataset-manifest SHA-256: `fcfdb77b153e7fc0d48b734c55cb400235108f574547163dcb474df564a76abf`
- Current rule interval: `hkjc_mark_six_2024_05_21`, from draw `24/058`
- Last eligible development draw: `26/099` on 2026-09-12
- Date frozen: 2026-09-14

## Scope and questions

Phase 8 studies ticket economics: current prize-fund accounting, fixed and variable expected payout,
jackpot and turnover interactions, prize sharing, Multiple and Banker packaging, and fixed-budget
portfolio risk. It asks when expected return changes and which ticket choices change expected value,
coverage, variance, or hypothetical split risk.

Historical-number prediction is closed. No hot/cold, gap, frequency, pair, triple, recent-number,
machine-learning, or other number-prediction model is created or evaluated. Every valid combination
has the same draw probability under the fair model. The prospective holdout strictly after
2026-09-13 stays sealed with zero entries and is never queried.

## Primary unit and economic quantities

The primary unit is one current full-unit ordinary combination costing exactly HKD 10. Money is
represented in cents or rational arithmetic until display rounding.

- expected payout: probability-weighted gross prizes;
- expected profit: expected payout minus HKD 10 cost;
- expected return ratio: expected payout divided by cost;
- house disadvantage: one minus expected return ratio; and
- expected value percent: expected profit divided by cost, times 100.

Expected payout is never described as profit. Multiple and Banker entries are expanded to their
ordinary combinations and costed by full-unit lines unless a separate partial-unit scenario is
explicitly named.

## Evidence classes and time states

Every material field or conclusion is classified as one of:

1. `exact_rule_math`: exact combinatorics or a formula uniquely determined by official rules;
2. `official_pre_draw`: an official amount or state demonstrably published before sales closed;
3. `source_reported_post_draw`: a value in the completed-draw source without proven publication
   time;
4. `derived_historical`: an arithmetic derivation from historical source values;
5. `external_behavioral_evidence`: published evidence not directly observing Hong Kong Mark Six
   entry choices;
6. `synthetic_assumption`: an explicit scenario input; or
7. `simulation_estimate`: a deterministic Monte Carlo estimate checked against exact mathematics.

The historical table keeps separate pre-draw, post-draw, and derived columns. A completed-draw
GraphQL field is not promoted to pre-draw information without dated official evidence. Actual
winner counts and dividends are ex-post descriptive facts only. Null source values stay null; they
are not zero-filled or imputed.

## Current prize-fund accounting

For turnover `T`, current rules allocate 25% to duty, 15% to the Lotteries Fund, 6% to commission,
and 54% to the Prize Fund. Expected fixed liabilities use the exact Division 4--7 qualification
probabilities and official fixed full-unit payouts. The published Snowball Deduction is applied to
the Prize Fund, subject to its stated cap, before the remaining variable pool starts at 45% First,
15% Second, and 40% Third Division. The current minimum First Division fund is HKD 8 million.

No-winner balances roll according to the formal rules. Special Snowball contributions and carried
amounts are separate inputs and are not inferred from an ambiguous source field. The implementation
reuses Phase 4 primitives. It stops with an explicit unsupported-state result where the official
text does not uniquely determine the minimum hierarchy, a sole partial-unit settlement, Rule 3.16
funding, or another exceptional operational adjustment.

## Variable-prize expected value

For division `d`, the base qualification probability is exact. A scenario supplies or derives an
available division fund and a distribution of other winning units. Expected contribution is the
qualification probability times the fund times the expected share factor, with full- and
partial-unit weights represented explicitly. Division allocation, rounding, minimums, Snowball,
carryover, and exceptional funding remain distinct state components before aggregation.

The `no_sharing` scenario gives our winning unit the whole stated division fund. It is a theoretical
upper-level comparison, not a realistic player expectation. The uniform benchmark assumes other
full-unit-equivalent entries independently choose among all 13,983,816 combinations. For a specific
First Division combination, other winners are exactly binomial; a Poisson approximation is reported
only as a validation. A `higher_sharing` sensitivity multiplies the specific-combination selection
probability by three, capped at one, and is synthetic rather than an estimate of Hong Kong behavior.

No universal break-even jackpot is reported. Thresholds are conditional on turnover, funds in all
three variable divisions, and sharing. First Division fund scenarios are HKD 8m, 10m, 20m, 30m,
50m, 80m, 100m, and 150m. Return targets are 50%, 75%, 90%, and 100%. Turnover scenarios are HKD
50m, 100m, and 200m. The word `jackpot` is retained as source-qualified wherever its official
economic meaning remains unresolved.

## Historical analysis

Exact current-rule accounting is restricted to completed draws from 2024-05-21 through 2026-09-12.
Earlier draws may appear only as rule-aware descriptive context when their required rule fields are
verified; they are excluded from current-formula estimates. Eligible source columns include draw ID,
date, turnover, unit stake, special-draw designation, source-reported jackpot-related values, and
post-draw Division 1--3 winning units and dividends. Fixed liabilities are derived only when stake,
turnover, rule interval, and exact current payouts support the calculation.

Turnover associations with source-reported jackpot fields, Snowball/special designations, and
normal/special status are descriptive. Correlation and simple regressions do not establish causality.
Ex-ante modeled return is kept separate from ex-post payout structure. The main methodology and
scenario grid cannot change after viewing historical results.

## Source-field interpretation

The GraphQL fields `jackpot`, `derivedFirstPrizeDiv`, `estimatedPrize`, and Snowball-related fields
are reconciled against dated official notices and formal rules. For each field, the report records
observed behavior, official support, confidence, and whether it is safe for ex-ante modeling.
Ambiguous values retain source-qualified names. One matching notice may support a draw-specific
interpretation but does not establish invariant semantics across every era or draw status.

## Ticket-choice behavior and split risk

The project has no Hong Kong Mark Six ticket-selection microdata. The uniform benchmark is exact
under its assumptions. External lottery studies, general Hong Kong number-superstition evidence,
and unreviewed research leads are labelled separately. Birthday-range counts, consecutive or
arithmetic patterns, repeated last digits, parity patterns, and culturally salient numbers are
split-risk features only. They never alter draw probability. No precise Hong Kong payout advantage
is claimed from weak evidence; synthetic popularity multipliers are shown as sensitivity ranges.

## Entry packaging, portfolios, and simulation

Multiple and Banker entries are compared with the identical expanded set of ordinary combinations.
Equivalent full-unit lines have identical cost and expected payout. Packaging can change neither
line probabilities nor expectation, although overlapping lines create covariance and simultaneous
prizes.

Budgets of HKD 100, 500, and 1,000 are evaluated under named objectives: expected payout, chance of
any prize, First Division coverage, variance, overlap, number-pool coverage, and hypothetical split
risk. Duplicate combinations are reported; intentional duplicates preserve expectation per dollar
but reduce unique coverage and alter risk. Diversification is not called an expected-value edge.

Simulation uses seed `2026091501` and 500,000 fair 6/49 draws. Exact formulas remain authoritative;
simulation validates reproducibility, portfolio payout mechanics, and agreement within registered
Monte Carlo uncertainty. Important outputs vary turnover, First Division fund, sharing strength,
Snowball contribution, and portfolio overlap.

## Materiality and reporting

A return-ratio movement of at least one percentage point is economically material for scenario
comparison. Positive expected value requires expected return strictly above 100% under the complete
named assumptions; equality is break-even. Small simulated deviations are not material unless they
exceed three registered Monte Carlo standard errors. Assumption-fragile conclusions must show their
sensitivity and may not be generalized beyond the scenario.

Generated reports and the self-verifying Phase 8 manifest are ignored artifacts. The manifest binds
this protocol and configuration, the Phase 7 Git baseline, dataset identity, current rule, source
fields, assumptions, seed, count, scenario definitions, code hash, output hashes, timestamp, and
sealed-holdout state. Phase 9 is not authorized by this decision.
