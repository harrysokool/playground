# ADR 0004: Exact, Rule-Versioned Lottery Mathematics

**Status:** Accepted
**Date:** 2026-09-13

## Context

Phase 4 needs auditable prize probabilities, entry costs, system-entry outcomes, and an expected
payout foundation. Historical pool and stake changes mean a single hard-coded 6/49 model would be
incorrect. Multiple and Banker tickets also share numbers, so treating their constituent tickets as
independent Bernoulli trials would give incorrect joint outcomes.

The exact 1995 stake boundary and 1996 45-to-47 pool boundary remain unsupported by exact dated
primary evidence. Mathematical implementation must not erase that uncertainty.

## Decision

- Use closed-form combinations and exact rational probabilities; never Monte Carlo where the
  combinatorial result is available.
- Represent ticket money as integer HKD cents and partial scaling as a rational value.
- Expand Multiple and Banker entries deterministically only when callers request the combinations;
  use closed-form overlap states for probability distributions and simultaneous prizes.
- Keep probability, fixed-prize schedules, and variable dividends as separate objects.
- Represent the official turnover split, fixed liability, Snowball Deduction, variable allocation,
  minimum top-up, sharing, and rollover as composable exact functions. Reject use of a standard
  formula when the formal rules require an exceptional branch whose inputs are absent.
- Require variable-payout inputs explicitly and label future prize-pool values as economic
  assumptions and future other-player winning units as behavioral assumptions.
- Permit seeded Monte Carlo only as an independently labeled convergence check against the exact
  engine; simulation never supplies an authoritative probability.
- Map the unresolved 1996 rule version to both 6/45 and 6/47 candidates in reports. Refuse to select
  a draw-level candidate without further evidence.
- Treat historical prize qualification and Extra Number assumptions as conditional until
  contemporaneous formal rules are found.
- Generate the probability report entirely from tested code and without reading development or
  holdout draw outcomes.

## Consequences

All primary results are reproducible exactly and probability partitions can be checked with strict
equality. Large 49-number Multiple entries remain feasible because ordinary combinations are
streamed rather than materialized. Expected-payout work cannot silently fill unknown top-three
dividends or historical rounding. Historical uncertainty remains visible to every downstream
consumer instead of being encoded as a false precision.

The current formal rules do not specify a unique computational adjustment procedure for every
minimum-prize state. Complete exceptional funding, rateable reduction, sole-partial-winner, and
rounding calculations therefore require the complete applicable input state; they are not inferred
from an advertised jackpot.
