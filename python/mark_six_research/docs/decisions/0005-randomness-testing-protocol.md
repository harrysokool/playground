# ADR 0005: Phase 5 Randomness-Testing Protocol

**Status:** Accepted and frozen before historical test execution
**Protocol version:** `phase5-randomness-v1`
**Frozen:** 2026-09-14 (Asia/Hong_Kong)
**Dataset:** `marksix-bc02467ec951c2d8`
**Baseline commit:** `c73697f0bc636580aa93ed27746d2da41146f640`

## Research question and scope

The confirmatory question is whether the approved historical Mark Six main-number and Extra Number
record is inconsistent with independent fair draws under the verified pool configuration applying
to each included draw. Phase 5 measures descriptive departures from that model. It does not test a
number-selection strategy, expected profit, or forecast accuracy.

A statistically unusual result is not automatically evidence that future draws are predictable.
No test may be added after seeing the main results and then presented as preregistered. Additional
ideas arising after execution are exploratory and must be reported separately.

## Null model

For every included draw with pool size `N`, six unordered main numbers are sampled uniformly
without replacement from `1..N`; one Extra Number is then sampled uniformly from the remaining
`N-6` numbers. Draws are independent. Exact expectations are used when available. Monte Carlo is
used only to calibrate multivariate, maximum, serial, gap, and distribution-shape statistics whose
joint finite-sample reference distribution is inconvenient analytically.

Alternative explanations for rejection include source or transcription defects, an incorrect
historical boundary, model misspecification, mechanical bias, operational change, dependence, or
chance remaining after correction. Rejection alone does not identify manipulation or prediction.

## Confirmatory periods and exclusions

The following non-overlapping periods are fixed:

| Analysis period | Dates | Pool | Inclusion basis |
|---|---|---:|---|
| `pool45_1993_1995` | 1993-01-01 through 1995-12-31 | 45 | pool is safely assignable; the unresolved 1995 stake change is irrelevant to draw probabilities |
| `pool47_1997_2002` | 1997-01-01 through 2002-07-02 | 47 | reviewed 6/47 interval |
| `pool49_2002_2026` | 2002-07-03 through 2026-09-13 | 49 | reviewed 6/49 interval, capped by the development cutoff |

Every 1996 draw is excluded from pool-dependent confirmatory analysis because the exact 45-to-47
boundary is unresolved. No 1995 draw is assigned to a precise stake rule; draws enter only the
pool-45 statistical period. The analysis records excluded counts and reasons. Draw schedule gaps
are not imputed. Chronologically adjacent observed draws within a stable period are compared under
the independent-draw null even when calendar spacing is irregular; no test treats elapsed days as
draws. Stability blocks are based on draw count, not calendar duration.

Sorted source arrays are unordered sets. Physical ball position and draw-order tests are out of
scope because genuine physical draw order is unavailable.

## Fixed confirmatory test family

All calculations below are performed separately in each of the three periods.

1. **Main-number frequency.** For every valid number, report count, `6n/N` expectation, frequency,
   absolute and relative deviation, binomial standardized deviation, exact two-sided binomial
   p-value, and Wilson 95% interval. Test the full vector with a Pearson dispersion statistic
   calibrated by fair-history simulation. Benjamini-Hochberg (BH) controls FDR across all 141
   period-number hypotheses. The simulated maximum absolute standardized deviation is also
   reported.
2. **Extra Number frequency.** Repeat the separate analysis with expectation `n/N`; never combine
   Extra and main occurrences. BH controls FDR across all 141 hypotheses. The full-vector Pearson
   statistic and maximum deviation are simulation-calibrated.
3. **Odd/even composition.** Count 0 through 6 odd main numbers. Compare with the exact
   hypergeometric distribution using a Pearson statistic calibrated by simulation. Report
   Cramer's `V = sqrt(X2/(6n))`.
4. **Low/high composition.** Low is fixed as `1..floor(N/2)` and high is the remaining values.
   Count 0 through 6 low numbers and use the same exact hypergeometric comparison and effect size.
5. **Winning-number sums.** Report observed and exact-null means and variances plus empirical
   quantiles. Compare the empirical sum CDF with the exact dynamic-programming sum distribution
   using a weighted Cramer-von-Mises statistic calibrated by simulation. Report standardized mean
   shift (Cohen-style `d`).
6. **Within-draw consecutive behavior.** Report the presence of any consecutive pair, total
   adjacent-pair count, and a run of at least three. Adjacent-pair-count expectations use exact run
   combinatorics; the maximum standardized departure across the three fixed summaries is
   simulation-calibrated.
7. **Consecutive-draw overlap.** Compare main-set overlap counts 0 through 6 with the exact
   hypergeometric distribution for adjacent draws wholly inside one period. Use a
   simulation-calibrated Pearson statistic and report Cramer's V. No cross-pool transition is used.
8. **Appearance gaps.** For each number, report mean completed inter-arrival time (draws including
   the terminating appearance), the null mean `N/6`, and the longest observed absence run. The
   global statistic is the largest absolute relative mean-gap deviation across numbers and is
   simulation-calibrated. Leading and trailing censored gaps are used only for longest-absence
   reporting, not completed-gap means. A long gap does not make a number due: independent draws
   retain appearance probability `6/N` after every history.
9. **Pairs.** For every unordered pair, report co-appearance count, expectation
   `n*C(6,2)/C(N,2)`, binomial z score, exact two-sided p-value, relative deviation, and BH result.
   BH controls FDR across all 3,247 period-pair hypotheses. The largest absolute z score in each
   period receives a simulation-calibrated family-wise p-value.
10. **Triples.** This protocol preregisters only one maximum statistic per period: the largest
    absolute binomial z score among all `C(N,3)` triples, with a fair-history simulation p-value.
    Top observed triples and expectations are descriptive; no thousands of uncorrected triple
    p-values are presented. Power limitations are stated.
11. **Serial dependence.** The fixed statistic is the maximum absolute value among per-number lag-1
    appearance-indicator correlations, draw-sum lag-1 correlation, and odd-count lag-1
    correlation. Degenerate correlations are zero. Calibration uses independent fair histories.
12. **Temporal stability.** Each period is split chronologically into three contiguous blocks whose
    sizes differ by at most one. A number-by-block Pearson homogeneity statistic is calibrated by
    simulation. No rolling window or alternative breakpoint is searched.

This creates 3,529 individual hypotheses (141 main, 141 Extra, and 3,247 pair hypotheses) and 42
period-level omnibus hypotheses (12 fixed families plus separate main and Extra maximum-deviation
statistics, times three periods), for 3,571 confirmatory hypotheses in total. The exact final count
must be emitted by the analysis rather than assumed.

Implementation-only clarification before historical execution: the main and Extra maximum absolute
standardized deviations required above are counted as distinct simulation-calibrated omnibus
hypotheses, rather than merely descriptive columns. This correction was made during synthetic-test
validation before the historical outcome tables were queried.

## Significance, correction, and effect sizes

All tests are two-sided where a direction exists. Raw significance uses `p < 0.05`. BH at `q=0.05`
is applied once per prespecified individual family across periods. The 42 simulation-calibrated
omnibus p-values are corrected together with Holm family-wise control at `alpha=0.05`. Monte Carlo
p-values use `(1 + exceedances)/(1 + simulations)`, so zero is impossible.

Every notable result includes observed versus expected values, relative or absolute deviation,
standardized effect, interval where applicable, and simulated percentile. Practical-effect flags
are fixed before execution: individual frequencies require both `|z| >= 3` and at least 10%
relative deviation; pairs/triples require `|z| >= 3` and at least 50% relative deviation;
categorical tests require Cramer's V at least 0.10; sum means require `|d| >= 0.10`; serial
correlations require `|r| >= 0.05`. A meaningful fair-null deviation requires corrected
significance and its applicable practical threshold. Isolated uncorrected extremes, small effects,
or a single Monte Carlo tail event are not enough to claim practical bias or predictability.

## Simulation calibration

The fixed root seed is `20260914`; `1,000` independent fair histories are generated for each period.
Child seeds are deterministically derived from the root seed and period order. Each history exactly
matches the observed period's draw count and pool size. It preserves period segmentation but not
calendar gaps because the null is indexed by completed draws. The same simulated history supplies
all 14 omnibus statistics, retaining their dependence. Simulation code is validated on synthetic
fair and strongly biased histories before the historical run.

## Confirmatory versus exploratory reporting

The tests above are confirmatory. The main report contains a separate exploratory section. Any
unregistered follow-up, alternate window, alternate low/high split, subset, lag, or statistic is
excluded from confirmatory correction and cannot support predictability until independently
specified and tested on new data. Phase 5 will not access or populate the prospective holdout.

## Reproducibility and stopping rule

The generated analysis manifest records dataset ID and manifest SHA-256, baseline commit, analysis
code version, protocol version and hash, configuration hash, seeds, simulation count, correction
methods, timestamp, output hashes, included/excluded counts, and holdout state. Statistical tables
and Markdown are generated by code and never manually edited.

If execution reveals a methodological implementation defect, the defect and protocol impact must
be documented before rerunning. An unfavorable result is not a defect and no test may be replaced.
