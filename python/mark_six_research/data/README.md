# Data layers

- `raw/`: immutable source responses plus separately versioned provenance manifests
- `interim/`: parsed records that have not passed all canonical validation
- `processed/`: versioned, validated canonical datasets, normally stored as Parquet
- `external/`: clearly attributed third-party data kept separate from official draw data
- `reserves/`: tracked, outcome-free manifests that protect later-phase historical rows

Downloaded and derived data are ignored by Git. Each Phase 2 raw HTTP response has a metadata
sidecar, and POST sources also retain the exact request body. No source file may be edited in place:
a parser change produces a new derived artifact linked to the original content hash.

The Phase 7 historical prediction reserve manifest is intentionally different from downloaded or
processed data: it is small, versioned metadata containing only draw identifiers, dates, rule IDs,
and sealed status. Winning numbers and other outcomes are prohibited from reserve manifests.
