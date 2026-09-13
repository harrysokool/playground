# Decision 0001: Phase 1 foundation

- **Status:** accepted
- **Date:** 2026-09-13

## Context

The repository contains unrelated experimental Python and C++ projects. Mark Six research requires a
reproducible environment and a protocol that prevents leakage, selective reporting, and retrofitted
hypotheses before historical-pattern analysis begins.

## Decision

- Isolate the work in `python/mark_six_research` with a `src` package layout.
- Require Python 3.12 and manage the environment and lockfile with `uv`.
- Use immutable raw artifacts, typed Parquet canonical data, and reproducible DuckDB query layers.
- Store HKD money as integer cents or documented exact decimals.
- Establish the protocol, data dictionary, source register, and rule-timeline evidence framework
  before collecting the full history or implementing strategies.
- Keep downloaded data, local databases, and generated reports out of Git during the foundation
  phase.
- Do not add scikit-learn until a pre-specified modelling experiment requires it.

## Consequences

The initial installation is larger than the runnable CLI strictly requires because it locks the
agreed core scientific and data-validation stack early. Conversely, model-selection packages and
workflow infrastructure remain deferred. Empty stage directories exist locally but are not padded
with placeholder files solely to make Git track them.

