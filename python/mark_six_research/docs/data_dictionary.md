# Canonical Data Dictionary

**Status:** Phase 3 canonical schema frozen; Phase 4 rule-model extension documented
**Schema version:** 2

The seven Phase 3 publication tables below describe implemented Parquet/DuckDB fields; later strategy
and backtest sections remain forward designs. A source value is never silently coerced or
repaired: the original response remains in `data/raw`, and discrepancies are recorded in
`validation_issues`.

## Conventions

- Primary and foreign keys are stable UTF-8 strings unless otherwise noted. Content-derived IDs may
  be used only after their canonicalization method is documented.
- All timestamps are timezone-aware and stored as UTC (`timestamp[us, UTC]`). Hong Kong civil dates
  and times are interpreted with `Asia/Hong_Kong` before conversion.
- Calendar dates use ISO 8601 `date32`; they are not timestamps at midnight.
- HKD money uses signed `int64` **cents**. For example, HKD 10 is stored as `1000`. Source text and
  currency remain available through provenance. Calculated ratios use documented `decimal` types;
  binary floating point is not authoritative for money.
- Lottery numbers use integers. Winning numbers are stored as individual rows in `draw_numbers`, not
  only as a concatenated string.
- `nullable = yes` means absence is legitimate or expected from some sources. It does not authorize
  arbitrary parser failures; the reason for material missingness must be recorded.
- Enumerations shown below are proposed controlled vocabularies and may be extended only through a
  schema decision record.
- A source field name is not a semantic definition. In particular, HKJC GraphQL `jackpot`,
  `estimatedPrize`, and `derivedFirstPrizeDiv` remain separately named observations until their
  meaning and time of availability are verified.
- Current GraphQL `drawDate` is a local civil date, not proof of an exact draw timestamp. Its
  `closeDate` is a timezone-aware sales-close timestamp. Publication time is not present in sampled
  result records and must not be inferred from either value.

## Relationships

- `draws.rule_version_id` -> `rule_versions.rule_version_id`
- `draw_numbers.draw_id`, `prize_results.draw_id`, and `jackpot_events.draw_id` -> `draws.draw_id`
- source-bearing rows reference `source_records.source_record_id`
- `ticket_predictions.strategy_run_id` and `backtest_results.strategy_run_id` ->
  `strategy_runs.strategy_run_id`
- `backtest_results.draw_id` -> `draws.draw_id`

## `draws`

One canonical row per draw. Winning numbers live in `draw_numbers`.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `draw_id` | Internal stable draw key | string | no | `hkjc:24/001` | Deterministic from authority and canonical draw number |
| `source_draw_id` | Publisher's unmodified draw key | string | no | `202699N` | Official GraphQL `id`; uniqueness must be coverage-audited |
| `draw_number` | Draw identifier as published | string | no | `24/001` | Official draw record; format not assumed constant |
| `draw_date` | Hong Kong calendar date of draw | date32 | no | `2024-01-02` | Official draw record |
| `draw_at` | Exact draw timestamp, when verifiable | timestamp UTC | yes | `2024-01-02T13:30:00Z` | Official schedule/result converted from Hong Kong time |
| `sales_open_date` | Source-reported local sales-open date | date32 | yes | `2026-09-10` | GraphQL `openDate`; blank in the 1995 sample |
| `sales_close_at` | Source-reported timezone-aware sales-close time | timestamp UTC | yes | `2026-09-12T13:15:00Z` | GraphQL `closeDate`; blank in the 1995 sample |
| `status` | Draw state: `scheduled`, `completed`, `postponed`, `cancelled`, `unknown` | string enum | no | `completed` | Official result or notice |
| `source_status` | Publisher's status before controlled mapping | string | no | `Result` | GraphQL `status` |
| `rule_version_id` | Rules applicable to the draw | string | no | `rules:pending-2024` | Effective-date join to verified `rule_versions` |
| `unit_stake_hkd_cents` | Source-reported unit stake | int64 | no | `1000` | GraphQL `lotteryPool.unitBet`, converted exactly to cents |
| `turnover_hkd_cents` | Total published turnover | int64 | yes | `12345678900` | Official result, converted exactly to cents |
| `reported_jackpot_hkd_cents` | Value in source field `lotteryPool.jackpot`; semantics remain source-qualified | int64 | yes | `18500000000` | GraphQL value converted exactly to cents; blank in older samples |
| `estimated_first_prize_hkd_cents` | Source-reported estimated First Division prize | int64 | yes | `5000000000` | GraphQL `estimatedPrize`; blank in completed samples reviewed |
| `reported_derived_first_prize_hkd_cents` | Source-reported derived First Division value | int64 | yes | `22800000000` | GraphQL `derivedFirstPrizeDiv`; meaning requires further confirmation |
| `snowball_code` | Official special/Snowball designation code | string | yes | `ANN` | GraphQL `snowballCode`; blank means null |
| `snowball_name_en` | Official English designation | string | yes | `Mark Six 50th Anniv. Snowball 2` | GraphQL source text |
| `is_special_draw` | Whether officially designated special | bool | yes | `true` | Derived only from a documented designation mapping |
| `source_pool_sell` | Source pool `sell` flag | bool | yes | `false` | GraphQL source value |
| `source_pool_status` | Source pool status | string | yes | `Payout` | GraphQL source value |
| `source_record_id` | Primary evidence record for canonical row | string | no | `src:sha256:…` | `source_records` foreign key |
| `source_item_sha256` | Hash of canonical JSON for the source draw object | fixed string(64) | no | `abc123…` | Deduplication/revision audit |
| `recorded_at` | Latest retrieval represented by this publication | timestamp UTC | no | `2026-09-13T10:00:00Z` | Deterministic maximum input retrieval time |

Uniqueness is required for `draw_id` and for the verified authority plus `draw_number`. A completed
draw must have exactly six `main` rows and one `extra` row under the currently anticipated mechanism;
the actual constraint will be parameterized by `rule_versions` rather than hard-coded historically.

## `draw_numbers`

One row per number and role in a draw. This table preserves individual numeric values and, when the
source supplies it, physical draw order.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `draw_id` | Draw containing the number | string | no | `hkjc:24-001` | `draws` foreign key |
| `number_role` | `main` or `extra` | string enum | no | `main` | Official result semantics |
| `draw_position` | One-based physical draw position | int16 | yes | `3` | Official source when order is explicit; never inferred from sorting |
| `number_value` | Numeric ball value | int16 | no | `27` | Official draw result parsed as an integer |
| `display_position` | Source presentation position, if distinct | int16 | yes | `2` | Source page layout |
| `source_record_id` | Evidence for this value | string | no | `src:sha256:…` | `source_records` foreign key |

The candidate key is (`draw_id`, `number_role`, `number_value`). Valid ranges and role counts come
from the linked rule version. Sorting for analysis must create derived data and must not overwrite
physical order.

The sampled GraphQL `drawnNo` arrays appear sorted. Phase 2 therefore treats them as display values
and leaves physical `draw_position` null rather than inventing machine order.

## `prize_results`

One row per draw and prize division as published.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `draw_id` | Associated draw | string | no | `hkjc:24-001` | `draws` foreign key |
| `division_code` | Stable rule-versioned division identifier | string | no | `division_1` | Official division mapped through rules |
| `division_label` | Label printed by source | string | yes | `1st Prize` | Verbatim normalized source label |
| `source_winning_unit_amount` | Unmodified GraphQL `winningUnit` value | decimal(20,4) | yes | `35.0000` | Preserved because the official UI scales this value |
| `winning_units` | Published count of winning units/shares | decimal(20,4) | yes | `2.0000` | Official result; may differ from ticket count |
| `winning_tickets` | Ticket count if explicitly distinguished | int64 | yes | `2` | Official result only; not inferred from units |
| `prize_per_winning_unit_hkd_cents` | Exact dividend per published winning unit | int64 | yes | `450000000` | Official result converted to cents |
| `total_division_payout_hkd_cents` | Total payout for division | int64 | yes | `900000000` | Official value or exact documented derivation |
| `is_fixed_prize` | Whether rule version defines a fixed amount | bool | yes | `false` | `rule_versions` / division rule evidence |
| `source_record_id` | Evidence record | string | no | `src:sha256:…` | `source_records` foreign key |

The candidate key is (`draw_id`, `division_code`). Calculated totals retain a derivation identifier so
they cannot be confused with published totals.

For the reviewed GraphQL application, official JavaScript displays
`winningUnit / lotteryPool.unitBet`. Phase 2 therefore preserves the source amount and stores the
quotient as normalized units: source `35` at a HKD 10 unit stake is `3.5` units. This conversion is
source-versioned and must be rechecked when the web bundle changes. If another source reports ticket
counts, populate `winning_tickets` and do not infer units.

## `jackpot_events`

One row per jackpot, rollover, guarantee, or special-jackpot event. Multiple events may relate to one
draw.

Phase 3 creates only a `special_designation` event when official Snowball code/name fields are
present; it assigns no amount or publication time. A nonzero source field named `jackpot` does not
establish whether it is an announcement, rollover, Snowball addition, or final accounting amount.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `jackpot_event_id` | Stable event key | string | no | `jackpot:2024-001:announcement` | Deterministic canonical identifier |
| `draw_id` | Draw to which event applies | string | yes | `hkjc:24-001` | Official notice mapping; nullable until draw assigned |
| `event_type` | `special_designation` in Phase 3; future reviewed event types may be added | string enum | no | `special_designation` | Official designation mapped by parser |
| `event_at` | Time event took effect | timestamp UTC | yes | `2024-01-01T04:00:00Z` | Official notice |
| `published_at` | First evidenced public availability | timestamp UTC | yes | `2024-01-01T04:05:00Z` | Contemporaneous source metadata |
| `amount_hkd_cents` | Exact event amount | int64 | yes | `120000000` | Official source converted to cents |
| `from_draw_id` | Draw supplying a rollover | string | yes | `hkjc:23-150` | Derived only from verified official sequence/evidence |
| `description` | Short factual event description | string | yes | `Special jackpot announced` | Source-normalized text |
| `source_record_id` | Evidence record | string | no | `src:sha256:…` | `source_records` foreign key |

## `rule_versions`

One row per verified interval in which all model-relevant rules are constant. Complex prize rules may
later be normalized into child tables rather than embedded as opaque text.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `rule_version_id` | Stable rule interval identifier | string | no | `rules:2024-01` | Research registry identifier |
| `effective_from` | First local date rules apply | date32 | yes | `2024-05-21` | Dated official evidence; null if unresolved |
| `effective_to` | Last local date rules apply, inclusive | date32 | yes | `2024-12-31` | Next verified change minus one day or explicit end date |
| `verification_status` | `unverified`, `partially_verified`, or `verified` | string enum | no | `verified` | Research review workflow |
| `number_range_status` | `verified` or `conservative_upper_bound` | string enum | no | `verified` | Boundary evidence status |
| `number_pool_min` | Smallest selectable number | int16 | no | `1` | Official rules for interval |
| `number_pool_max` | Largest selectable number | int16 | no | `49` | Official rules for interval |
| `main_numbers_selected` | Count of main numbers drawn | int16 | no | `6` | Official rules for interval |
| `extra_numbers_selected` | Count of Extra Numbers drawn | int16 | no | `1` | Official rules for interval |
| `unit_stake_hkd_cents` | Cost of one unit stake | int64 | no | `1000` | Official rules converted to cents |
| `unit_stake_status` | `verified` or `source_observed` | string enum | no | `verified` | Boundary evidence status |
| `partial_unit_stake_hkd_cents` | Permitted partial-unit cost for Multiple/Banker, if verified | int64 | yes | `500` | Official rules converted to cents; null means not established for the interval |
| `prize_division_count` | Number of defined prize divisions | int16 | no | `7` | Official rules for interval |
| `reported_prize_division_count` | Expected divisions in the GraphQL result when verified | int16 | yes | `7` | Source contract and rule evidence |

Prize qualification, allocation, minimums, rollovers, Banker, and Multiple rules may require
normalized child tables in a later canonical schema. Phase 4 represents the verified current
mathematics in tested code and exact formula documentation rather than embedding opaque prose in
the Phase 3 dataset. Adding `partial_unit_stake_hkd_cents` to a future build schema does not mutate
or republish the frozen `marksix-bc02467ec951c2d8` baseline.

## `source_records`

One row per retrieved source artifact. This is the provenance spine of the project.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `source_record_id` | Immutable source-artifact key | string | no | `hkjc:timestamp:abc…` | Source ID, UTC retrieval timestamp, and content-hash prefix |
| `source_name` | Registered source identifier | string | no | `hkjc_mark_six_results` | `source_register.md` / source configuration |
| `organization` | Publishing organization | string | no | `The Hong Kong Jockey Club` | Source register |
| `url` | Exact retrieval URL | string | no | `https://bet.hkjc.com/...` | HTTP request |
| `http_method` | Request method | string enum | yes | `POST` | HTTP request; null for non-HTTP artifacts |
| `request_parameters` | Canonically serialized public query variables | JSON/string | yes | `{"lastNDraw":5}` | Request builder; never store secrets |
| `request_body_sha256` | SHA-256 of exact request body | fixed string(64) | yes | `abc123…` | Acquisition calculation |
| `request_body_path` | Project-relative exact request-body path | string | yes | `data/raw/...request.json` | Present for sampled POST requests |
| `retrieval_method` | `http`, `browser`, `manual_download`, or `api` | string enum | no | `http` | Acquisition process |
| `retrieved_at` | Retrieval completion time | timestamp UTC | no | `2026-09-13T10:00:00Z` | Acquisition clock |
| `published_at` | Source publication time if evidenced | timestamp UTC | yes | `2024-01-02T14:00:00Z` | Source metadata/header/content |
| `http_status` | HTTP response status | int16 | yes | `200` | HTTP response |
| `media_type` | Response content type | string | yes | `text/html` | Header plus content validation |
| `content_sha256` | Lowercase SHA-256 of exact bytes | fixed string(64) | no | `abc123…` | Acquisition calculation |
| `byte_length` | Exact artifact size | int64 | no | `48291` | Raw byte count |
| `raw_path` | Project-relative immutable raw path | string | no | `data/raw/hkjc/2024/...html` | Acquisition policy |
| `parser_version` | Parser/code version used, if parsed | string | yes | `hkjc-results-v1` | Pipeline metadata |
| `terms_review_status` | `pending`, `approved`, `restricted`, or `rejected` | string enum | no | `pending` | Source-governance review |
| `hash_verified` | Whether raw bytes matched recorded size and SHA-256 at publication | bool | no | `true` | Provenance verifier |

URL alone is not provenance: the exact bytes and content hash are required.

The sidecar also records a unique `snapshot_id` and metadata `schema_version`. `source_records`
includes a `hash_verified` boolean computed at publication. Response
headers beyond media type are not yet retained; add them through schema evolution if cache validators
or source publication metadata prove necessary.

## `validation_issues`

One row per detected quality issue, including issues later resolved.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `validation_issue_id` | Stable issue key | string | no | `issue:000012` | Validation system |
| `detected_at` | Detection timestamp | timestamp UTC | no | `2026-09-13T10:05:00Z` | Validation clock |
| `dataset_name` | Affected canonical dataset | string | no | `draw_numbers` | Validator context |
| `record_key` | Serialized stable key of affected record | string | yes | `hkjc:24-001/main/27` | Validator; null for dataset-level issues |
| `field_name` | Affected field | string | yes | `number_value` | Validator; null for cross-record issue |
| `check_code` | Versioned machine-readable rule | string | no | `NUMBER_OUT_OF_RANGE` | Validation specification |
| `classification` | `confirmed_data_problem`, `expected_historical_behavior`, `requires_rule_research`, or `requires_source_research` | string enum | no | `requires_rule_research` | Audit classification policy |
| `severity` | `info`, `warning`, `error`, or `fatal` | string enum | no | `error` | Validation specification |
| `observed_value` | Safe textual representation of source value | string | yes | `52` | Validator; not used as canonical replacement |
| `message` | Human-readable explanation | string | no | `Number exceeds rule-version maximum` | Validator |
| `source_record_id` | Evidence artifact involved | string | yes | `src:sha256:…` | `source_records` foreign key |
| `status` | `open`, `resolved`, `accepted`, or `false_positive` | string enum | no | `open` | Review workflow |

## `strategy_runs`

One immutable row per strategy execution. The table is defined now so unsuccessful strategies cannot
be silently discarded later; Phase 1 creates no strategy rows.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `strategy_run_id` | Immutable execution identifier | string | no | `run:01J…` | Experiment runner |
| `experiment_id` | Pre-registered experiment identifier | string | no | `exp:hot-number-v1` | Experiment registry |
| `strategy_name` | Stable strategy family | string | no | `uniform_random` | Frozen configuration |
| `strategy_version` | Version of full strategy specification | string | no | `1.0.0` | Code/config registry |
| `run_status` | `planned`, `running`, `completed`, `failed`, `invalidated` | string enum | no | `completed` | Runner |
| `failure_reason` | Reason a run failed or was invalidated | string | yes | `Input cutoff violation` | Runner or reviewer; required for failed/invalidated |
| `started_at` | Execution start | timestamp UTC | no | `2027-01-10T10:00:00Z` | Runner clock |
| `completed_at` | Execution completion | timestamp UTC | yes | `2027-01-10T10:03:00Z` | Runner clock |
| `training_start_date` | First eligible training draw date | date32 | yes | `2000-01-01` | Frozen experiment configuration |
| `training_end_date` | Last training date for non-walk-forward setup | date32 | yes | `2018-12-31` | Frozen experiment configuration |
| `evaluation_start_date` | First evaluated draw date | date32 | no | `2019-01-01` | Frozen experiment configuration |
| `evaluation_end_date` | Last evaluated draw date | date32 | no | `2023-12-31` | Frozen experiment configuration |
| `code_revision` | Git commit or immutable source revision | string | no | `abc1234` | Version control |
| `config_sha256` | Hash of canonical frozen run configuration | fixed string(64) | no | `def456…` | Experiment runner |
| `data_manifest_sha256` | Hash identifying all eligible input artifacts | fixed string(64) | no | `987abc…` | Data manifest |
| `random_seed` | Root reproducibility seed, if stochastic | uint64 | yes | `20260913` | Frozen configuration |
| `notes` | Non-result-dependent execution notes | string | yes | `First registered execution` | Research log |

## `ticket_predictions`

One row per ordinary six-number combination emitted for a target draw. Multiple and Banker entries
must be deterministically expanded into their ordinary combinations while retaining entry metadata.
Numbers are held in six individual sorted integer fields, not a single text combination.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `ticket_prediction_id` | Immutable predicted-combination key | string | no | `prediction:01J…` | Prediction writer |
| `strategy_run_id` | Producing execution | string | no | `run:01J…` | `strategy_runs` foreign key |
| `draw_id` | Target draw | string | no | `hkjc:24-001` | Pre-draw schedule mapping |
| `generated_at` | Prediction persistence time | timestamp UTC | no | `2024-01-02T08:00:00Z` | Prediction writer clock |
| `as_of_at` | Latest permitted source availability time | timestamp UTC | no | `2024-01-02T07:59:59Z` | Frozen experiment cutoff |
| `entry_id` | Parent purchased/simulated entry identifier | string | no | `entry:0001` | Ticket construction |
| `entry_type` | `single`, `multiple`, or `banker` | string enum | no | `single` | Strategy output normalized from verified rules |
| `combination_index` | One-based index within expanded entry | int32 | no | `1` | Deterministic expansion |
| `number_1` | Lowest selected number | int16 | no | `3` | Strategy output sorted strictly ascending |
| `number_2` | Second selected number | int16 | no | `11` | Strategy output sorted strictly ascending |
| `number_3` | Third selected number | int16 | no | `19` | Strategy output sorted strictly ascending |
| `number_4` | Fourth selected number | int16 | no | `27` | Strategy output sorted strictly ascending |
| `number_5` | Fifth selected number | int16 | no | `35` | Strategy output sorted strictly ascending |
| `number_6` | Sixth selected number | int16 | no | `44` | Strategy output sorted strictly ascending |
| `unit_stake_hkd_cents` | Stake assigned to this combination | int64 | no | `1000` | Strategy budget under applicable rule version |
| `selection_score` | Optional strategy score; higher meaning must be specified | float64 | yes | `0.0142` | Frozen strategy output, never treated as money |
| `prediction_sha256` | Hash of canonical prediction payload | fixed string(64) | no | `123abc…` | Prediction writer |

The six numbers must be unique and valid under the target rule version. A future normalized child
table may replace the six columns if ticket selection counts vary historically.

## `backtest_results`

One row per strategy run and evaluated draw, before aggregation across time.

| Field | Meaning | Type | Nullable | Example | Source or derivation |
|---|---|---:|:---:|---|---|
| `backtest_result_id` | Immutable result key | string | no | `result:01J…` | Scoring pipeline |
| `strategy_run_id` | Evaluated execution | string | no | `run:01J…` | `strategy_runs` foreign key |
| `draw_id` | Scored draw | string | no | `hkjc:24-001` | `draws` foreign key |
| `scored_at` | Time outcome was joined and scored | timestamp UTC | no | `2024-01-02T15:00:00Z` | Scoring pipeline clock |
| `ticket_count` | Ordinary combinations evaluated | int64 | no | `10` | Count of `ticket_predictions` rows |
| `total_stake_hkd_cents` | Exact total stake | int64 | no | `10000` | Sum of prediction stakes |
| `total_payout_hkd_cents` | Exact realized payout when supported | int64 | yes | `5000` | Prize results plus verified rules |
| `net_return_hkd_cents` | Payout minus stake | int64 | yes | `-5000` | Exact derivation |
| `max_main_matches` | Maximum main-number matches over emitted combinations | int16 | no | `3` | Exact comparison with `draw_numbers` |
| `mean_main_matches` | Mean main matches per combination | float64 | no | `0.74` | Exact counts divided by ticket count |
| `extra_match_ticket_count` | Combinations containing the Extra Number | int64 | no | `1` | Exact comparison with `draw_numbers` |
| `winning_combination_count` | Combinations qualifying for any prize | int64 | yes | `1` | Verified prize qualification rules |
| `highest_division_code` | Best division achieved | string | yes | `division_7` | Verified rules; null if no prize |
| `baseline_group_id` | Matched random-baseline comparison group | string | yes | `baseline:01J…` | Experiment runner |
| `eligibility_status` | `included` or `excluded` | string enum | no | `included` | Pre-registered eligibility rules |
| `exclusion_reason` | Reason draw is excluded | string | yes | `Missing verified prize result` | Required when excluded |
| `result_sha256` | Hash of canonical result payload | fixed string(64) | no | `456def…` | Scoring pipeline |

Cross-draw summaries, confidence intervals, adjusted p-values, and Monte Carlo comparisons are
derived report tables rather than fields overwritten onto these draw-level results.

## Schema evolution rules

1. A field's meaning never changes in place; incompatible changes increment the schema version.
2. Raw source columns are not added casually to canonical tables. They first receive a documented
   semantic definition and provenance rule.
3. Enumerations are validated centrally and extended through a decision record.
4. All currency conversions and repairs are deterministic and auditable.
5. Canonical publication is blocked by unresolved `fatal` issues and, by default, `error` issues.
6. Examples in this document illustrate representation only; they are not asserted historical facts.

## Dataset manifest

Each publication directory is identified by a hash of schema/parser/validation/rule-timeline
versions, the development cutoff, the rule-document hash, and every input snapshot ID/content hash.
Its manifest records the input count, raw snapshot manifest SHA-256, canonical Parquet SHA-256 values,
row counts, creation time, DuckDB path, and Git commit (null when unavailable). Dataset identity is
therefore content/configuration-derived, not timestamp-derived.
