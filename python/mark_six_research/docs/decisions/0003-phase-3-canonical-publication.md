# Decision 0003: Phase 3 canonical publication

- **Status:** accepted
- **Date:** 2026-09-13

## Context

The official structured endpoint was measured through the development cutoff. It contains exact
duplicates from overlapping evidence snapshots, legitimate historical nulls, incompletely verified
rule economics, and no populated responses before 1993-01-05. Canonical publication must preserve
these distinctions without turning absence or observation into invented history.

## Decision

- Deduplicate by official source draw ID and retain the newest immutable observation; record any
  distinct item hash as a source revision rather than silently overwriting it.
- Publish seven typed Parquet tables plus DuckDB views, all derived from raw snapshots and the
  versioned rule registry.
- Derive dataset identity from input snapshot IDs/hashes and versioned transformation inputs.
- Block publication on canonical relationship failures and preserve classified research issues.
- Treat the 1996 maximum as a conservative upper bound and the 1995 split as source-observed until
  exact official boundaries are found.
- Reject development access after 2026-09-13 and keep the prospective holdout manifest outcome-free.

## Consequences

The dataset is suitable for data-quality and later preregistered research, but incomplete historical
economics cannot be presented as verified. Populated endpoint coverage begins in 1993; the game did
not necessarily begin then. Generated datasets, reports, DuckDB files, and raw official artifacts
remain local and Git-ignored under the current source-governance policy.
