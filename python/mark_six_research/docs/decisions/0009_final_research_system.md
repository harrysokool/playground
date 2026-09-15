# Decision 0009: Final pre-draw research system

- Status: frozen before any real prospective draw evaluation
- Protocol version: `phase9-final-system-v1`
- Phase 8 baseline: `85dbaa01c4dfff728aa73a03ad39f8197ce40975`
- Dataset: `marksix-bc02467ec951c2d8`
- Dataset-manifest SHA-256: `fcfdb77b153e7fc0d48b734c55cb400235108f574547163dcb474df564a76abf`
- Frozen: 2026-09-15

## Scope and closed questions

Phase 9 integrates the validated data, exact mathematics, negative randomness/prediction results,
independent replication, and conditional Phase 8 economics into a final operational research
system. It does not create or tune a number-prediction model. Historical number prediction is
closed. The prospective holdout after 2026-09-13 remains sealed with zero entries, and Phase 9 does
not inspect, query, or compare any future outcome.

Every valid six-number combination has equal draw probability. Ticket construction may control
duplicates, coverage, cost, covariance, and assumption-based split sensitivity, but it may not
claim that one valid combination is more likely to be drawn.

## Pre-draw evidence

Every evaluation requires a strict, outcome-free record containing draw ID/date, sales-close and freeze times,
current full-unit ticket price, draw type, a dated official First Division amount and description,
known carryover, special Snowball contribution, exceptional-funding status, source URLs,
publication/retrieval times, evidence confidence, and the turnover estimate with range.

Accepted source classes are dated official HKJC draw announcements and current official rules or
betting guidance. Material draw-specific values must be published and retrieved no later than the
record freeze time. Completed-draw GraphQL `jackpot`, `derivedFirstPrizeDiv`, and similar fields are
not treated as invariant pre-draw definitions. Missing sources, missing material amounts, outcome
data, or uncertain/present exceptional funding fail closed.

Confidence is `High`, `Medium`, or `Low`. The aggregate cannot exceed its weakest material source or
estimate. `High` means direct, dated official evidence with unambiguous draw-specific meaning;
`Medium` means official facts combined with the frozen estimated turnover or a bounded semantic
qualification; `Low` means weak, indirect, ambiguous, or incomplete support. Low confidence cannot
produce `WATCH` or `ECONOMICALLY_INTERESTING`.

## Turnover forecast

The explainable method is `frozen_draw_class_median_plus_fund_response_v1`. It starts from the
pre-holdout current-rule median turnover: HKD 47,327,267 for normal draws or HKD 165,747,171 for
special draws. It adds HKD 0.25 for each HKD of official First Division amount above the HKD 8m
reference, subject to a HKD 20m floor. The interval is 70% to 135% of the central estimate.

The medians are frozen historical observations. The deliberately modest 0.25 response and range
multipliers are scenario assumptions informed by Phase 8's descriptive completed-draw association;
they are not a fitted causal estimate, machine learning, or an official forecast. No post-cutoff
data are used.

## Economic scenarios and decisions

The existing exact Phase 8 engine calculates one HKD 10 full-unit ticket's expected payout,
expected profit/loss, return percentage, central break-even distance, and turnover/sharing
sensitivity. Three turnover cases (lower, central, upper) cross three First Division sharing cases:

1. `lower_sharing`: synthetic 0.5-times specific-combination popularity;
2. `uniform`: exact binomial sharing under uniform independent combination choice; and
3. `higher_sharing`: synthetic 3-times specific-combination popularity.

The lower/higher cases are behavioral assumptions because actual Hong Kong selection microdata and
Quick Pick share are unavailable. Division 2 and 3 funds come from current rule-based accounting at
the stated turnover case. The dated official First Division amount is an explicit scenario input;
the system does not silently promote an advertised `jackpot` label into an economically available
fund.

Decision thresholds are frozen now:

- `ECONOMICALLY_INTERESTING`: evidence is at least Medium and the **worst** of all nine scenarios
  has return ratio at least 1.02.
- `WATCH`: evidence is at least Medium, the interesting rule fails, and the **best** scenario has
  return ratio at least 0.95.
- `SKIP`: all other evaluable records, including Low confidence.
- Fail closed without a category if required evidence is missing or exceptional funding is present
  or uncertain.

These categories are research classifications, not betting advice. Positive expected value remains
conditional and assumption-dependent. No HKD 150m or other universal jackpot action rule exists.

## Ticket plans

Default budgets are HKD 100, 500, and 1,000. Uniform random plans use a recorded seed and reject
duplicate combinations. Multiple and Banker inputs expand to their exact ordinary combinations,
show combination count, exact cost, and unused budget, and fail if they exceed the budget. Optional
split-risk filtering is labeled assumption-based and never changes draw probability.

## Immutability and future comparison

Evidence and evaluation records use strict schemas, canonical JSON, timestamps, content hashes in
filenames, and exclusive file creation. Evaluation records bind evidence/configuration hashes,
decision, central metrics, and all nine scenarios. They contain no outcome fields and have
`outcome_comparison_status: not_started`.

Phase 9 generates the final reports and a self-hashed manifest binding this decision, configuration,
baseline, dataset, previous manifests, code, outputs, source definitions, turnover method, sharing
assumptions, decision rules, and sealed holdout. Actual prospective evaluation or later outcome
comparison requires a separate approved protocol; neither begins in Phase 9.
