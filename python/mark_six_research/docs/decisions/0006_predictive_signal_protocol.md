# Decision 0006: Preregistered predictive-signal protocol

- Status: frozen before historical forecast evaluation
- Protocol version: `phase6-predictive-signal-v1`
- Frozen dataset: `marksix-bc02467ec951c2d8`
- Frozen dataset-manifest SHA-256: `fcfdb77b153e7fc0d48b734c55cb400235108f574547163dcb474df564a76abf`
- Phase 5 baseline commit: `e8382a4ff8cab319725316f597f1005dfa343d6a`
- Date frozen: 2026-09-14

## Question and scope

Phase 6 asks one narrow question: did information available before each historical draw
improve out-of-sample probability forecasts for the unordered set of six main numbers?
It does not forecast the Extra Number and does not analyse tickets, returns, prizes,
jackpots, payout strategy, Banker or Multiple entries. It does not train a machine-learning
model or inspect any future prospective-holdout outcome.

Phase 5 found no compelling systemwide evidence against fair random drawing. Its isolated
corrected pair result for 2–26 is recorded research history, not a Phase 6 feature or rule.
No candidate model may contain a number-specific or pair-specific parameter.

## Frozen populations and ordering

The primary population is the 3,376 completed 6/49 draws from 2002-07-03 through
2026-09-12, ordered by `(draw_date, draw_id)`. Only the first 2,700 rows are accessible to
Phase 6 outcome loading. The last 676 rows form a protected Phase 7 historical prediction
reserve. Its tracked manifest contains draw ID, date, rule version, and reserve status only;
it contains no drawn numbers.

The first 250 accessible primary draws are warm-up observations. Forecasts are scored on
the following 2,450 draws. A forecast at index `t` may use only main-number outcomes at
indices strictly less than `t`; it is made before the target outcome updates any state.

Secondary replication is performed only after the primary process, using the same frozen
formulas and parameters. The 6/45 period (1993-01-01 through 1995-12-31) and 6/47 period
(1997-01-01 through 2002-07-02) each use their first 100 draws as warm-up and score all
remaining draws. Calendar year 1996 remains excluded because its pool transition is
unresolved.

## Probability model

For a pool of `N` numbers and positive weights `w_1, ..., w_N`, every unordered six-number
set `S` receives probability

`P(S) = product(w_i for i in S) / e_6(w_1, ..., w_N)`,

where `e_6` is the sixth elementary symmetric polynomial. The implementation computes the
normalizer by dynamic programming and number marginals by polynomial division; neither
quantity is estimated by Monte Carlo and the approximately 14 million 6/49 sets are not
enumerated. Multiplying every weight by a common positive constant must leave all set
probabilities and marginals unchanged. Unit weights must reproduce the uniform probability
`1 / choose(N, 6)` and marginal `6 / N`.

## Frozen candidate family

Every count has additive smoothing `alpha = 1.0`. Gaps are measured immediately before
the target draw. All functions are generic in number identity.

1. `uniform`: every weight is 1.
2. `expanding_frequency`: cumulative prior appearances plus 1.
3. `rolling_frequency_25`: appearances in the previous 25 draws plus 1.
4. `rolling_frequency_100`: appearances in the previous 100 draws plus 1.
5. `rolling_frequency_250`: appearances in the previous 250 draws plus 1.
6. `exponential_frequency_25`: exponentially decayed prior appearances plus 1, with
   per-draw decay `2^(-1/25)`.
7. `exponential_frequency_100`: the same formula with decay `2^(-1/100)`.
8. `gap_due`: weight `1 + 0.5 * (1 - exp(-ln(2) * gap / 25))`.
9. `recent_appearance`: weight `1 + 0.5 * exp(-ln(2) * gap / 25)`.
10. `previous_draw_repeat`: weight 1.20 for a number in the immediately preceding draw,
    otherwise 1.
11. `previous_draw_avoidance`: weight 0.80 for a number in the immediately preceding draw,
    otherwise 1.

No pair model is included. Candidate definitions, the family size, smoothing, windows,
half-lives, multipliers, and tie-breaking are frozen before historical scoring.

## Scores and diagnostics

The primary score is the natural logarithm of the assigned probability of the entire
observed unordered set. Each non-uniform model is compared draw by draw with the uniform
model; positive log-score difference means improvement. The primary effect is mean nats
per scored draw.

Secondary diagnostics are marginal Brier score over every draw-number pair, Brier skill
relative to uniform, hits among the six highest marginal probabilities, mean rank of the
six observed numbers, and marginal calibration. Equal probabilities are ranked by number
ascending. Calibration uses the fixed probability edges
`[0, 0.08, 0.10, 0.115, 6/49, 0.13, 0.145, 0.17, 1]`; empty bins are reported as empty,
and expected calibration error is observation-count weighted. Stability uses four
contiguous, nearly equal scored-draw blocks.

Each scored row records the model version, target draw ID and date, immediately preceding
cutoff draw ID, forecast SHA-256, whole-set log score, uniform log score, difference,
Brier score, top-six hits, and mean observed rank. The forecast hash binds the model,
target, cutoff, pool size, and the exact hexadecimal representation of every weight.

## Inference and family-wide calibration

For each of the ten non-uniform candidates, the one-sided hypothesis is that its mean
paired log-score difference is greater than zero. A circular moving-block bootstrap uses
block length 25, 2,000 replicates, and root seed 2026091402. Bootstrap null samples are
centered by subtracting the observed mean. One-sided raw p-values are adjusted across all
ten candidates with Holm's procedure at family alpha 0.05. Percentile 95% intervals are
also reported from uncentered moving-block samples.

To calibrate model selection and the complete adaptive forecast process, 500 independent
fair 6/49 histories of 2,700 draws are generated with root seed 2026091401. Every frozen
candidate is rerun with the same 250-draw warm-up and 2,450 scored draws. The family-wide
p-value compares the best observed candidate mean with the simulated distribution of the
maximum candidate mean. Simulation batching is computational only and cannot alter the
random stream or statistic.

## Predeclared interpretation

A primary predictive signal is declared only if one model simultaneously satisfies all of
the following:

- positive mean log-score difference of at least 0.001 nats per draw;
- one-sided Holm-adjusted bootstrap p-value below 0.05;
- family-wide fair-process p-value below 0.05;
- calibration ECE no greater than 0.025;
- nonnegative mean log-score difference in at least three of four stability blocks, with
  no block below -0.005 nats per draw.

Anything less is not primary evidence of useful predictive signal. Secondary metrics and
historical-period replication are diagnostic and cannot rescue a failed primary result.
No result is translated into a betting or profit claim.

## Required validation and provenance

Before historical scoring, tests must establish the exact weighted-subset normalizer and
marginals against brute-force small pools, uniform equivalence, scaling invariance, and
forecast-hash determinism. Synthetic fair histories must show no systematic advantage;
synthetic histories with a deliberately planted pre-draw dependency must be detected.
Leakage tests must prove that changing a target or later outcome cannot change that target's
forecast, and reserve guards must reject access to any of the 676 protected IDs.

Generated tables, report, simulation output, and the Phase 6 analysis manifest are ignored
artifacts. The manifest binds the protocol, configuration, source revision, dataset and
canonical table hashes, reserve manifest, sealed prospective holdout, seeds, output hashes,
and any deviations. Verification must recompute every recorded hash. No Phase 7 outcome is
opened in Phase 6.
