# Decision 0007: One-time historical replication protocol

- Status: frozen before Phase 7 reserve outcomes are opened
- Protocol version: `phase7-historical-replication-v1`
- Phase 6 baseline commit: `c872af8a31217862e371eedd5dad8a4298e2319b`
- Dataset: `marksix-bc02467ec951c2d8`
- Dataset-manifest SHA-256: `fcfdb77b153e7fc0d48b734c55cb400235108f574547163dcb474df564a76abf`
- Phase 6 analysis-manifest SHA-256: `2ed722e70bd86a99677a933206d6c2490cd0fdbc4e707307ed147203f235a74d`
- Reserve-manifest SHA-256: `a874730ca6b8c14458745a7206f11983331b63452ce12941006a3caa24e3908b`
- Date frozen: 2026-09-14

## Research question and one-time status

Phase 7 asks whether the exact frozen Phase 6 probability models perform differently from
uniform on the 676 historical 6/49 draws deliberately withheld from Phase 6. This is a one-time
confirmatory historical replication. Once opened, these outcomes are consumed as replication
evidence and cannot be reused to design another confirmatory model.

Phase 6 found no validated predictive edge: every non-uniform candidate had negative primary
log-score improvement. Phase 7 primarily tests whether that negative conclusion independently
replicates. A positive Phase 7 result after a negative Phase 6 result would be conflicting evidence,
not automatic validation.

No ticket, betting, profit, return, prize, payout, jackpot, Banker, Multiple, machine-learning, or
prospective-holdout analysis is permitted.

## Reserve and controlled opening

The registered reserve is exactly 676 completed 6/49 draws, ordered by `(draw_date, draw_id)`, from
`hkjc:21/078` on 2021-09-07 through `hkjc:26/099` on 2026-09-12. Its immutable tracked manifest
remains metadata only. Outcomes are read from the frozen canonical `draw_numbers.parquet` only by
the Phase 7 replication loader after protocol, configuration, implementation, and synthetic tests
are complete.

The loader must require an explicit Phase 7 authorization object, verify the exact ordered reserve
IDs against the metadata manifest, reject rows after `26/099`, and reject any prospective-holdout
entry. Phase 6 loaders remain capped at the first 2,700 primary rows. The opening event is recorded
in the research log and Phase 7 analysis manifest. Deterministic reruns reproduce this one registered
analysis; they do not create new confirmatory looks or permit model changes.

## Initial information and walk-forward order

For the first reserve forecast, every model is initialized with exactly the first 2,700 eligible
6/49 draws, ending at `hkjc:21/077`. For each reserve target:

1. construct weights from completed draws strictly before the target;
2. create the forecast hash against the immediately preceding cutoff draw;
3. join and score the target outcome; and
4. update state with that completed reserve draw before forecasting the next target.

No target or later reserve outcome may influence an earlier forecast. There is no additional
warm-up and all 676 reserve draws are scored.

## Frozen candidate family and probability formulas

The configuration duplicates and the runner verifies byte-for-model equality with the Phase 6
candidate definitions. The eleven models are retained even when they performed poorly:

1. `uniform`: all weights 1.
2. `expanding_frequency`: all prior appearances plus smoothing 1.
3. `rolling_frequency_25`: previous 25 appearances plus smoothing 1.
4. `rolling_frequency_100`: previous 100 appearances plus smoothing 1.
5. `rolling_frequency_250`: previous 250 appearances plus smoothing 1.
6. `exponential_frequency_25`: decay `2^(-1/25)`, decayed count plus smoothing 1.
7. `exponential_frequency_100`: decay `2^(-1/100)`, decayed count plus smoothing 1.
8. `gap_due`: `1 + 0.5 * (1 - exp(-ln(2) * gap / 25))`.
9. `recent_appearance`: `1 + 0.5 * exp(-ln(2) * gap / 25)`.
10. `previous_draw_repeat`: weight 1.20 for numbers in the immediately previous draw, else 1.
11. `previous_draw_avoidance`: weight 0.80 for numbers in the immediately previous draw, else 1.

There is no pair model and no number-specific treatment of 2 or 26. No model may be added, removed,
combined, tuned, or reparameterized after reserve opening.

For positive weights `w`, the probability of unordered six-number set `S` remains

`P(S) = product(w_i for i in S) / e_6(w)`.

The exact elementary-symmetric-polynomial normalizer and exact marginals reuse the reviewed Phase 6
implementation. Unit weights reduce to `1 / choose(49, 6)` with marginal `6 / 49`.

## Scores and direct Phase 6 comparison

The primary metric remains whole-set natural log probability. Each non-uniform model is paired with
uniform on every reserve draw. Reports include mean log score, mean and cumulative difference in
nats, and a 95% moving-block interval.

Secondary metrics remain marginal Brier score, Brier skill relative to uniform, top-six hits, mean
top-six hits per draw, mean rank of the six observed numbers, and fixed-bin marginal calibration.
The Phase 6 calibration edges are reused unchanged:
`[0, 0.08, 0.10, 0.115, 6/49, 0.13, 0.145, 0.17, 1]`.

For every model, the independent Phase 7 summary is compared directly with Phase 6 mean primary
improvement, Brier skill, top-six hits, winner rank, and ECE. Phase 6 and Phase 7 are not pooled for
the confirmatory conclusion. The Phase 6 gap-due top-six observation and rolling-250 rank observation
are reported as secondary replication checks only.

## Inference, simulation, and multiplicity

For each of the ten non-uniform models, the one-sided hypothesis is mean paired log-score difference
greater than zero. The Phase 6 circular moving-block bootstrap design is retained: block length 25,
2,000 replicates, centered null samples, percentile 95% interval, and Holm correction across all ten
models at family alpha 0.05. The new Phase 7 bootstrap root seed is `2026091404`.

Family-wide calibration uses 500 independently simulated fair 6/49 histories of 3,376 draws with
root seed `2026091403`. Each simulated history supplies 2,700 initialization draws and a sequential
676-draw reserve period. The complete eleven-model process and selected-best non-uniform statistic
are rerun. The simulation count cannot be reduced after actual reserve results are seen.

## Stability and decision rules

The 676 reserve targets form four fixed chronological blocks of exactly 169 draws each. Boundaries
follow the ordered row indices and cannot move.

A model successfully replicates only when all conditions hold:

- mean log-score improvement is at least 0.001 nats per draw;
- the 95% moving-block interval lower bound is greater than zero;
- its one-sided Holm-adjusted p-value is below 0.05;
- it is the selected-best model and the family-wide fair-process p-value is below 0.05;
- calibration ECE is at most 0.025;
- at least three of four block means are nonnegative; and
- no block mean is below -0.005 nats per draw.

A model fails replication if its primary mean is zero or negative, or if any remaining conjunctive
condition fails. Secondary metrics cannot rescue failure. Any interesting unregistered reserve
pattern is labelled exploratory and no new model may be evaluated on this consumed reserve.

## Reproducibility and prospective holdout

The Phase 7 manifest records the baseline, dataset and table hashes, Phase 5/6 integrity, protocol
and configuration hashes, unchanged model definitions, metrics, inference and simulation settings,
reserve boundaries, opening time, code hash, output hashes, correction history, and sealed holdout
state. It is self-hashed and independently verifiable.

The prospective 312-draw holdout begins strictly after 2026-09-13 and must remain sealed with zero
entries throughout Phase 7. No Phase 7 query may cross 2026-09-12. Phase 8 does not begin here.
