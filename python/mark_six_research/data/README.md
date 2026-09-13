# Data layers

- `raw/`: immutable source responses plus separately versioned provenance manifests
- `interim/`: parsed records that have not passed all canonical validation
- `processed/`: versioned, validated canonical datasets, normally stored as Parquet
- `external/`: clearly attributed third-party data kept separate from official draw data

Downloaded and derived data are ignored by Git. Each Phase 2 raw HTTP response has a metadata
sidecar, and POST sources also retain the exact request body. No source file may be edited in place:
a parser change produces a new derived artifact linked to the original content hash.
