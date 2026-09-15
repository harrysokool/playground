# Hong Kong Mark Six Research

A reproducible research project for studying Hong Kong Mark Six with historical data,
probability, statistics, simulation, and leakage-resistant backtesting.

The project does **not** claim that lottery numbers are predictable. A historical pattern is not
evidence of predictive advantage unless it survives the pre-specified out-of-sample process in
[`docs/research_protocol.md`](docs/research_protocol.md).

## Current scope

Phase 8 adds a preregistered economic analysis after the one-time independent Phase 7 historical
replication of the leakage-resistant Phase 6 walk-forward forecasting family on the frozen Phase 3
provenance-linked
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
fair-history simulations. Phase 6 evaluates a deliberately small fixed family of generic historical
models against the uniform baseline using exact whole-set probabilities, proper scores, paired
sequential inference, and 500 complete fair-process simulations. Phase 7 opened the final 676
eligible 6/49 rows exactly once through a controlled path after freezing the protocol and passing
the pre-opening quality gate. Every non-uniform model again had a negative mean primary log-score
difference, so the negative Phase 6 conclusion replicated; no model met the conjunctive success
criteria. The reserve manifest remains metadata-only, while the reserve is now consumed for
confirmatory purposes. Phase 8 models exact current prize-fund accounting, fixed and variable
expected payout, jackpot/turnover scenarios, prize sharing, Multiple and Banker equivalence,
portfolio overlap, and deterministic simulation. It does not reopen historical-number prediction.
The prospective holdout remains sealed with zero entries.

Phase 9 integrates the closed historical research into a conservative pre-draw economic system.
It accepts only timestamped official pre-draw evidence, uses a frozen explainable turnover range,
reuses the Phase 8 economic engine, and emits `SKIP`, `WATCH`, or `ECONOMICALLY_INTERESTING` only
under preregistered rules. It does not predict numbers or open the prospective holdout.

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
uv run mark-six predict models
uv run mark-six predict run
uv run mark-six predict report
uv run mark-six predict verify
uv run mark-six replicate run
uv run mark-six replicate verify
uv run mark-six replicate report
uv run mark-six replicate compare
uv run mark-six economics expected-value --turnover-hkd 100000000 --first-division-fund-hkd 50000000
uv run mark-six economics breakeven --turnover-hkd 100000000 --target-return 1
uv run mark-six economics sharing --turnover-hkd 100000000
uv run mark-six economics multiple --selections 7
uv run mark-six economics banker --bankers 2 --legs 5
uv run mark-six economics portfolio --budget-hkd 100
uv run mark-six economics run
uv run mark-six economics reports
uv run mark-six economics verify
```

Final-system commands:

```bash
uv run mark-six build-final-system
uv run mark-six current --evidence path/to/predraw_evidence.json
uv run mark-six evaluate --evidence path/to/predraw_evidence.json
uv run mark-six tickets --budget 100 --entry-type uniform --seed 20260915
uv run mark-six verify-all
```

Real evidence/evaluation records are timestamped, content-addressed, immutable, and ignored under
`data/predraw/`. Phase 9 itself creates no real prospective evaluation. See Decision 0009 and the
generated `system_guide.md` before any future use.

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

The frozen Phase 6 forecast family, split, scoring rules, inference method, seeds, and conjunctive
success criteria are in
[`docs/decisions/0006_predictive_signal_protocol.md`](docs/decisions/0006_predictive_signal_protocol.md).
`mark-six predict run` can access only the first 2,700 rows of the 3,376-draw primary 6/49
population. It creates 2,450 sequential forecasts after a 250-draw warm-up and verifies the
outcome-free 676-row Phase 7 reserve before running. Generated forecasts, diagnostics, simulation
calibration, report, and manifest remain ignored artifacts; `mark-six predict verify` recomputes
their hashes and all upstream integrity checks.

The frozen Phase 7 opening rules, unchanged candidate family, independent inference, fair-history
calibration, and conjunctive success criteria are in
[`docs/decisions/0007_historical_replication_protocol.md`](docs/decisions/0007_historical_replication_protocol.md).
`mark-six replicate run` uses all 2,700 eligible pre-reserve draws to initialize model state, then
scores all 676 reserve targets strictly sequentially in four fixed blocks of 169. The generated
report is `reports/generated/historical_replication.md`; supporting tables are under
`reports/generated/phase7/`, and `mark-six replicate verify` validates the self-hashed analysis
manifest plus all 11 recorded output hashes. Phase 6 and Phase 7 are compared independently rather
than pooled. The consumed reserve must not be used to tune another confirmatory model.

The frozen Phase 8 questions, time-state rules, evidence classes, sharing assumptions, scenario
grids, simulation seed, and materiality rule are in
[`docs/decisions/0008_economic_value_protocol.md`](docs/decisions/0008_economic_value_protocol.md).
Calculation details and bounded source-field interpretations are in
[`docs/economic_model.md`](docs/economic_model.md). `mark-six economics run` generates three reports,
14 supporting tables, and a self-hashed manifest. Generated artifacts stay ignored. The historical
table ends at draw 26/099; no Phase 8 path reads the prospective holdout.
