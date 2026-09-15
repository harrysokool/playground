# Phase 8 economic model

Phase 8 models one full-unit ordinary Mark Six line at HKD 10 under
`hkjc_mark_six_2024_05_21`. It studies money and sharing, not winning-number prediction. The
prospective holdout is never an input.

## Exact current accounting

For turnover `T`:

- Prize Fund = `0.54 T`;
- lottery duty = `0.25 T`;
- Lotteries Fund = `0.15 T`;
- HKJC commission = `0.06 T`;
- expected fixed liability = expected full-unit entries times exact Division 4--7 EV;
- Snowball Deduction uses the official current formula implemented and tested in
  `mathematics/prize_fund.py`; and
- remaining variable pool = Prize Fund minus fixed liability minus Snowball Deduction.

The remaining variable pool begins at 45% First, 15% Second, and 40% Third Division. The current
First Division minimum is HKD 8m. Carryover, available Snowball balance, and a special Snowball are
separate state inputs. This expected pre-draw accounting uses expected fixed liability because the
actual lower-division winners are unknown before the draw.

The rules do not uniquely resolve every minimum-hierarchy adjustment, Rule 3.16 exceptional funding
state, or sole partial-unit settlement from the inputs available here. Those cases remain explicit
boundaries; no inferred algorithm fills them in. Downward dividend rounding and partial-unit scaling
remain available through the exact Phase 4 primitives when the required state is supplied.

Primary sources are the [current HKJC notice and formula](https://special.hkjc.com/e-win/en-US/betting-info/marksix/important-notice/),
the [formal Lotteries Rules](https://www.hkjc.com/english/betting/template_betting_rule_files/pdf/Lotteries_Rule_3_Eng_20260330.pdf),
and the [2024 change announcement](https://www.hkjc.com/english/pressrelease/mcs01_showhtml.asp?filename=20240518_212151_E_NEWS.htm).

## Exact fixed expected payout

With `C = choose(49, 6) = 13,983,816`, each Division contribution is its exact qualification count
over `C` times the official full-unit payout:

| Division | Count | Payout | Exact expected HKD | Decimal HKD |
|---:|---:|---:|---:|---:|
| 4 | 630 | 9,600 | `36000/83237` | 0.432499969965 |
| 5 | 12,915 | 640 | `49200/83237` | 0.591083292286 |
| 6 | 17,220 | 320 | `32800/83237` | 0.394055528191 |
| 7 | 229,600 | 40 | `164000/249711` | 0.656759213651 |
| Total | | | `74000/35673` | **2.074398004093** |

These are gross payouts, not profit.

## Variable funds and sharing

For Division `d`, qualification probability is `q_d`, stated fund is `F_d`, and `X_d` is the number
of other winning units. The modeled contribution is:

`q_d F_d E[1 / (1 + X_d)]`.

The no-sharing scenario sets the share factor to one. Under independent uniform entry choice among
the `C` combinations, `X_d ~ Binomial(n, q_d)` for `n` other full-unit-equivalent entries and:

- expected other winners = `n q_d`;
- sole probability = `(1-q_d)^n`;
- exactly one other = `n q_d (1-q_d)^(n-1)`;
- multiple others = one minus those two probabilities; and
- expected share = `[1-(1-q_d)^(n+1)] / [(n+1)q_d]`.

The Poisson approximation with `lambda=n q_d` uses `exp(-lambda)` and
`(1-exp(-lambda))/lambda`; it is validation, not the authoritative calculation. The higher-sharing
scenario multiplies the specific First Division combination-selection probability by three. It is
synthetic and changes only sharing, never the fair draw probability.

## Return and thresholds

Total expected payout is fixed EV plus the three variable contributions. Expected profit subtracts
HKD 10. Return ratio divides expected payout by HKD 10; house disadvantage is one minus that ratio;
EV percent is expected profit divided by cost times 100.

Break-even solves the First Division fund conditional on turnover-derived Division 2/3 funds and a
named sharing model. In the frozen grid, uniform-selection 100% thresholds are about HKD 110.19m,
128.94m, and 173.04m at HKD 50m, 100m, and 200m turnover. A HKD 150m stated First Division fund
therefore exceeds 100% only in the first two uniform scenarios. These figures do not reinterpret an
advertised jackpot as an available fund.

## Historical time states and source fields

The 316-row current-rule table runs from draw 24/058 through 26/099. All GraphQL economics fields
come from completed-draw records and are post-draw/source-reported unless a separate dated notice
proves earlier public availability. Actual units and dividends are ex-post descriptive.

For draw 26/096, source `jackpot` equals the HKD 185m carried Snowball and
`derivedFirstPrizeDiv` equals the official HKD 228m estimated First Division fund in the dated
[50th Anniversary notice](https://www.hkjc.com/english/pressrelease/mcs01_showhtml.asp?SelType=NEWS&filename=20260829_114346_E_NEWS.htm).
This supports those draw-specific meanings only. Normal-draw behavior does not prove invariant
GraphQL semantics. `estimatedPrize` is null throughout the completed canonical samples.

Turnover correlations with source `jackpot` and `derivedFirstPrizeDiv` are 0.960 and 0.973 in this
interval. Special draws average HKD 210.02m turnover versus HKD 54.49m for normal draws. These are
strong completed-record associations, not causal estimates and not a leakage-safe pre-draw model.

## Entry packaging and portfolios

Multiple and Banker entries expand into ordinary combinations. Summing the exact joint outcome
distribution proves that expected payout equals the line-by-line expectation. The joint distribution
also supplies probability of any prize and payout variance without assuming owned lines are
independent; simultaneous prizes and covariance remain visible.

For a portfolio, expectation is linear in ticket units. Duplicate units reduce unique First Division
coverage and concentrate risk but do not change expected payout per dollar. Overlap changes the
joint lower-prize distribution, variance, and number-pool coverage. It is not an EV edge.

## Behavioral evidence boundary

No Hong Kong Mark Six line-selection microdata was located. External research shows that lottery
players in other markets cluster on birthdays, lucky numbers, visual patterns, and representative
sets. Hong Kong plate-auction evidence supports the cultural salience of 8 and aversion to 4, not
Mark Six selection frequencies. Ticket features are therefore qualitative split-risk flags and
synthetic sensitivities only. They do not alter draw probability or establish a precise payout edge.

Relevant evidence includes [Baker and McHale (2011)](https://doi.org/10.1111/j.1467-985X.2011.00693.x),
[empirical gambler's-fallacy choices](https://www.sciencedirect.com/science/article/pii/S0167268114002716),
and [Hong Kong superstition evidence](https://pmc.ncbi.nlm.nih.gov/articles/PMC7113914/).
