# Hong Kong Mark Six Research

A reproducible research project for studying Hong Kong Mark Six with historical data,
probability, statistics, simulation, and leakage-resistant backtesting.

The project does **not** claim that lottery numbers are predictable. A historical pattern is not
evidence of predictive advantage unless it survives the pre-specified out-of-sample process in
[`docs/research_protocol.md`](docs/research_protocol.md).

## Current scope

Phase 5 adds preregistered, rule-aware randomness testing to the frozen Phase 3 provenance-linked
development dataset from the measured populated coverage of
the official structured endpoint: draw 93/001 (1993-01-05) through draw 26/099 (2026-09-12). It
includes immutable raw evidence, rule-aware parsing, classified validation, versioned Parquet,
DuckDB views, reproducible reports, and a sealed prospective-holdout guard. It does not claim that
Mark Six began in 1993; preserved empty queries show only that this endpoint's populated coverage
begins there. The Phase 4 mathematical layer covers ordinary, Multiple, Banker, full-unit, and permitted
partial-unit entries using integers and rational fractions. It keeps the unresolved 1996 pool
boundary explicit and separates prize probabilities from variable payouts. Phase 5 separately tests
main and Extra Number frequencies, exact composition and overlap laws, sums, consecutive behavior,
gaps, pairs, preregistered triple maxima, serial dependence, and fixed-block stability against matched
fair-history simulations. No number-selection strategies, prediction, or backtesting are part of
Phase 5.

## Requirements

- `uv`
- Python 3.12 (managed automatically by `uv` when available)

## Setup

```bash
uv sync --all-groups
uv run mark-six info
```

Inspect a retained current-rule response (raw snapshots are local and Git-ignored):

```bash
uv run mark-six source inspect-snapshot \
  data/raw/hkjc_marksix_graphql/2026/09/<snapshot>.metadata.json
```

Reproduce and inspect the development dataset:

```bash
uv run mark-six audit-acquisition
uv run mark-six verify-snapshots
uv run mark-six coverage
uv run mark-six validate
uv run mark-six build-dataset
uv run mark-six validate-dataset
uv run mark-six dataset-info
uv run mark-six mathematics prize-probabilities
uv run mark-six mathematics odds
uv run mark-six mathematics multiple --selections 8
uv run mark-six mathematics banker --bankers 2 --legs 5
uv run mark-six mathematics first-division --pool-size 47
uv run mark-six mathematics simulate --trials 100000 --seed 20260913
uv run mark-six mathematics reports
uv run mark-six stats run
uv run mark-six stats frequencies
uv run mark-six stats composition
uv run mark-six stats overlap
uv run mark-six stats gaps
uv run mark-six stats pairs
uv run mark-six stats report
```

`ingest` is resumable and reuses exact, hash-valid, structurally valid cached windows. Development
commands reject any range ending after 2026-09-13. A deliberate controlled source-revision check is
available as `mark-six source revision-check`; it is not part of ordinary builds.

## Quality checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
```

## Project map

- `configs/`: versioned project and experiment settings
- `data/`: raw, interim, canonical processed, and external data layers
- `docs/`: protocol, schemas, source evidence, rule history, and decision records
- `notebooks/exploratory/`: non-authoritative exploratory notebooks
- `reports/`: generated tables, figures, and research reports
- `src/mark_six/`: tested application and research code
- `tests/`: unit, integration, statistical, and fixture-based tests
- `scripts/`: thin operational entry points when a CLI command is unsuitable

Downloaded data and generated artifacts are ignored by Git by default. Provenance manifests and
small curated fixtures may be committed deliberately after their licensing and review policy is
defined.

See [`docs/mathematical_model.md`](docs/mathematical_model.md) for the exact derivations and system
entry model. The reproducible generated output is
[`reports/generated/prize_probabilities.md`](reports/generated/prize_probabilities.md),
[`reports/generated/current_game_mathematics.md`](reports/generated/current_game_mathematics.md),
and [`reports/generated/expected_value_foundation.md`](reports/generated/expected_value_foundation.md).

The frozen Phase 5 test family is in
[`docs/decisions/0005-randomness-testing-protocol.md`](docs/decisions/0005-randomness-testing-protocol.md).
`mark-six stats run` verifies the dataset and holdout before generating
[`reports/generated/randomness_analysis.md`](reports/generated/randomness_analysis.md), supporting
CSV tables, and a hash-linked Phase 5 analysis manifest. Statistical results are descriptive and
confirmatory under the protocol; they do not imply that future draws are predictable.
