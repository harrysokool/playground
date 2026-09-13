# Exact Mathematical Model

**Status:** Phase 4 implemented through the visible payout-expectation requirements
**Arithmetic:** integers, `fractions.Fraction`, and integer HKD cents
**Scope:** lottery-rule mathematics only; no prediction or historical number-pattern analysis

## Ordinary ticket outcome space

For a pool of `N` numbers, an ordinary ticket is an unordered set of six distinct numbers. There
are exactly:

`C(N,6)`

possible tickets. Fix a draw consisting of a six-number main set and one Extra Number drawn from
the remaining `N - 6` numbers. The current prize counts are then:

| Division | Ticket condition | Count |
|---:|---|---:|
| 1 | Six main | `C(6,6) = 1` |
| 2 | Five main plus Extra | `C(6,5) C(1,1) = 6` |
| 3 | Five main, not Extra | `C(6,5) C(N-7,1)` |
| 4 | Four main plus Extra | `C(6,4) C(1,1) C(N-7,1)` |
| 5 | Four main, not Extra | `C(6,4) C(N-7,2)` |
| 6 | Three main plus Extra | `C(6,3) C(1,1) C(N-7,2)` |
| 7 | Three main, not Extra | `C(6,3) C(N-7,3)` |

Each probability is its count divided by `C(N,6)`. No Prize is the exact complement of the
applicable prize divisions. The implementation asserts that the mutually exclusive probabilities,
including No Prize, sum to exactly one. Six-division historical models treat the three-main,
not-Extra outcome as No Prize.

The generated [`prize_probabilities.md`](../reports/generated/prize_probabilities.md) contains
exact fractions and decimal displays for 6/45, 6/47, and 6/49. The decimal column is presentation
only; no binary floating point participates in the calculation.

## Historical model assignment

- 1993-1995 uses the 6/45, six-division candidate model.
- The unresolved 1996 transition deliberately has both 6/45 and 6/47 candidates. The code does not
  invent a date boundary.
- 1997 through 2002-07-02 uses the 6/47, six-division candidate model.
- From 2002-07-03 the pool is 49 and the source reports seven divisions.

Historical assignments remain conditional where contemporaneous formal evidence for prize
qualification or Extra Number mechanics has not been located. A model mapping is not an upgrade to
the rule registry's evidence status.

## Multiple entries

A Multiple entry selecting `s > 6` distinct numbers expands to all `C(s,6)` ordinary combinations
in lexicographic order. Its full-unit cost is:

`C(s,6) * applicable unit stake`

Because those combinations are distinct, First Division coverage is exactly
`C(s,6) / C(N,6)`. They share selected numbers, so lower-division and joint-win events are not
independent. The implementation instead conditions on how many main numbers overlap the selected
set and whether it contains the Extra Number. Closed-form binomial counts produce a simultaneous
seven-division `PrizeVector` without expanding large entries.

For example, if an eight-number Multiple contains all six main numbers but not the Extra Number,
its 28 ordinary combinations yield simultaneously one First, 12 Third, and 15 Fifth Division
prizes. This matches HKJC's published example.

## Banker entries

With `b` bankers and `l` legs, every underlying ticket contains all `b` bankers and chooses
`6 - b` legs. The exact number of tickets is:

`C(l, 6-b)`

The deterministic expansion rejects duplicated, overlapping, or out-of-range banker/leg values.
Closed-form prize vectors condition separately on main and Extra membership among bankers, legs,
and unselected numbers. A Banker entry and any other set containing the same number of unique
ordinary combinations have the same First Division coverage. Packaging does not itself improve
expected return.

## Ticket cost and partial units

Money is integer cents. A Single contains exactly one full-unit combination. Multiple and Banker
costs are the expansion count times either the rule's full stake or its verified partial stake.
Partial Single entries and partial stakes absent from a rule version are rejected. Dividend scaling
uses an exact rational value; the code does not guess historical rounding.

## Payout expectation boundary

Probability, prize schedule, and supplied dividends are separate inputs. Under current verified
rules, Divisions 4-7 are represented as fixed full-unit prizes of HKD 9,600, HKD 640, HKD 320, and
HKD 40. Divisions 1-3 are explicitly variable. An exact expected payout can be calculated only for
dividends supplied to the function:

`sum(probability[division] * dividend[division])`

The primitive does not estimate future turnover, winning units, Snowball additions, pari-mutuel
dividends, or expected value from incomplete historical rules.

### Current prize-fund arithmetic

The current official turnover shares are represented exactly: 54% Prize Fund, 25% Lottery Duty,
15% Lotteries Fund, and 6% commission. Given explicit fixed-division winning units, the implementation
calculates the fixed liability and then applies the Snowball Deduction effective 2024-05-21:

`S = 9% * [P - F - 55% * (60% * P - F)] + 55% * (60% * P - F)`

Here `P` is the Prize Fund and `F` is the amount payable to Divisions 4-7. The standard formula is
refused when `F > 60% P`; formal Rule 3.16 exceptional Snowball funding and possibly rateable
reduction then apply. This guard prevents a negative deduction from being presented as official
arithmetic. The remaining variable pool is allocated 45%/15%/40% to Divisions 1/2/3 before
minimum-prize adjustments.

The variable settlement API accepts, as separately named values, the available variable pool,
allocation shares, winning units, carried Jackpot, Snowball addition, and special-jackpot addition.
It implements current no-winner reallocation and carry-forward rules. The First Division minimum
helper reports the amount topped up from the Snowball Pool and any unmet shortfall rather than
pretending an insufficient balance can fund the HKD 8 million minimum.

The formal minimum-prize hierarchy does not publish a unique adjustment algorithm for every state.
Sole partial-unit winners, exceptional Rule 3.16 rateable reductions, and Rule 3.17 rounding require
their full input state before a final historical dividend can be reproduced. These cases remain
explicit rather than being guessed.

## Verification-only simulation

The seeded Monte Carlo module samples six main numbers without replacement and then one distinct
Extra Number. It supports pool sizes 45, 47, and 49, validates tickets, and compares every empirical
outcome with the exact engine. A conservative convergence band uses six binomial standard errors
plus one trial's discretization. Simulation results are labeled `simulation_estimate`; exact
fractions remain the source of truth.

The simulation does not load historical draws, score numbers, or forecast an outcome. Its only role
in Phase 4 is to make an implementation error in the exact model easier to detect independently.

## Evidence categories

- `exact_combinatorial_result`: closed-form counts and rational probabilities.
- `official_rule_based_calculation`: an exact calculation from verified HKJC rules or percentages.
- `historical_source_observation`: a value directly observed in dated source evidence.
- `simulation_estimate`: a finite seeded Monte Carlo result.
- `economic_assumption`: a future turnover, pool, Jackpot, or Snowball input.
- `behavioral_assumption`: a future other-player winning-unit or ticket-selection input.

APIs and generated reports carry these labels so assumptions cannot silently appear as exact
results.

## Reproduction

```bash
uv run mark-six mathematics prize-probabilities
uv run mark-six mathematics reports
uv run mark-six mathematics odds
uv run mark-six mathematics simulate --trials 100000 --seed 20260913
uv run pytest tests/unit/test_combinatorics.py tests/unit/test_entries.py \
  tests/unit/test_payouts.py tests/unit/test_prize_fund.py \
  tests/unit/test_reporting.py tests/unit/test_simulation.py
```

The report generator reads no draw data, invokes no random process, and does not access the sealed
holdout.
