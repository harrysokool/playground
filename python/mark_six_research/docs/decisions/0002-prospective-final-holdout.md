# Decision 0002: Prospective final untouched holdout

- **Status:** accepted
- **Date:** 2026-09-13
- **Protocol:** 1.1

## Context

The full official historical coverage and every historical rule boundary are not yet verified.
Phase 2 necessarily inspected a few official outcomes through draw 2026/099 (2026-09-12) to validate
the source, schema, and parser. Choosing an apparently historical “untouched” segment later would
risk accidental exposure, flexible boundary choice, and leakage through fixtures or summaries.

A fixed calendar duration would contain a variable number of observations because schedules and
postponements change. A percentage split would also move when older coverage is extended. Neither is
stable enough for a final confirmatory gate.

## Decision

- Reserve the first **312 eligible completed draws strictly after 2026-09-13** as the final holdout.
- Determine the endpoint by eligible-draw count, not by a forecast date or later dataset percentage.
- Include only official, rule-valid results whose relevant draw mechanism is within a verified rule
  version; document cancellations, voids, missing records, special draws, and rule transitions.
- Permit integrity-only collection and hashing while withholding numbers, prizes, and aggregate
  outcome summaries from strategy development and ordinary analysis paths.
- Unseal once, only after the final strategy and analysis specification are frozen.
- Pause and make a new prospective decision, without opening outcomes, if a material rule change
  invalidates the registered estimand.

## Consequences

At the current normal schedule, completion should take about two years, although draw count controls.
Historical data remains available for development and walk-forward evaluation without consuming the
final test. The holdout can estimate common draw-level metrics, but it cannot make realized jackpot
wins a well-powered primary endpoint. Phase 3 must implement the sealed manifest and access guard
before any strategy code exists.
