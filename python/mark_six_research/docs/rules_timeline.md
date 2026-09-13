# Mark Six Rules Timeline

**Status:** current interval and current mathematics verified; historical assignments intentionally partial
**Reviewed:** 2026-09-13

Exact probability, validation, ticket-cost, and expected-value calculations must use the rule version
effective for each draw. Unknown boundaries are never filled from the current rules.

## Evidence keys

- **R1:** HKJC, “Rules of The Hong Kong Lotteries,” current edition retrieved 2026-09-13:
  <https://www.hkjc.com/english/betting/template_betting_rule_files/pdf/Lotteries_Rule_3_Eng_20260330.pdf>
- **R2:** HKJC Mark Six Betting Guide, current page retrieved 2026-09-13:
  <https://is.hkjc.com/aosbs/help/en/mk6_guide.html>
- **R3:** HKJC, “Revised Snowball Pool arrangement for Mark Six,” published 2024-05-18:
  <https://corporate.hkjc.com/corporate/corporate-news/english/2024-05/news_2024051802131.aspx?iframe=1>
- **R4:** HKJC, “Mark Six enhancement measures,” published 2010-09-28:
  <https://www.hkjc.com/english/pressrelease/mcs01_showhtml.asp?filename=20100928_194443_E_NEWS.htm>
- **R5:** HKJC prize-allocation page:
  <https://special.hkjc.com/e-win/en-US/betting-info/marksix/allocation-of-prize-fund/>
- **R6:** HKJC entry-types page:
  <https://special.hkjc.com/e-win/en-US/betting-info/marksix/types-of-entry/>
- **R7:** HKJC lottery schedule page:
  <https://special.hkjc.com/e-win/en-US/betting-info/marksix/lottery/>
- **R8:** HKJC draw-integrity article, published 2016-02-19:
  <https://www.hkjc.com/english/corporate/racing_news_item.asp?in_file=%2Fenglish%2Fnews%2F2016-02%2Fnews_2016021901440.html>
- **R9:** HKJC 2002/03 Annual Report: 6-out-of-49 effective 2002-07-03, First Division
  HKD 38 million ceiling removed, Seventh Prize of HKD 20 introduced:
  <https://www.hkjc.com/chinese/special/2003_annual_report/ar03_rev_racing.pdf>
- **R10:** full retained GraphQL coverage. Source fields observe HKD 4 through draw 1995/041 on
  1995-05-25 and HKD 5 from draw 1995/042 on 1995-05-30. Draw 1996/046 on 1996-06-11 is the last
  draw before the first observed result containing a number above 45; draw 1996/047 on 1996-06-13
  contains 47. These observations are not treated as formal rule-effective dates.
- **R11:** HKJC current prize-qualification page:
  <https://special.hkjc.com/e-win/en-US/betting-info/marksix/prize-qualification/>
- **R12:** HKJC current Multiple/Banker chance and cost table:
  <https://special.hkjc.com/e-win/en-US/betting-info/marksix/chance-table/>
- **R13:** HKJC 2026 Mark Six fun facts, publishing First Division odds of 1 in 13,983,816:
  <https://campaigns.hkjc.com/2026-marksix/en/funfacts>
- **R14:** HKJC 2022 Summer Snowball notice, including an eight-number Multiple example:
  <https://racingnews.hkjc.com/english/2022/08/03/mark-six-summer-snowball-draw-to-be-held-next-tuesday-estimated-first-division-prize-fund-could-reach-50-million/>

R1 and R2 exact bytes are preserved locally with SHA-256 prefixes `aa87a5d89fb0` and
`4bbb55f07c55`. R3/R4 boundaries are corroborated by official GraphQL draw samples 2024/058 and
2010/130. Evidence status means adequate for the stated fields, not that every historical procedure
has been reconstructed.

## Timeline index

| Rule version | Effective date | End date | Summary | Evidence | Status |
|---|---|---|---|---|---|
| `hkjc_mark_six_2024_05_21` | 2024-05-21, draw 2024/058 | Open as reviewed 2026-09-13 | Current 1–49 game, HKD 10 unit, seven divisions, current Snowball Deduction/Pool arrangement | R1–R7 + draw 2024/058 | `verified` |
| `hkjc_mark_six_2010_11_09_partial` | 2010-11-09, draw 2010/130 | 2024-05-20 | HKD 10 unit, HKD 5 partial Multiple/Banker, doubled fixed prizes, HKD 8m First Division minimum; full old Snowball arithmetic not yet transcribed | R4 + draws 2010/130 and 2024/058 | `partially_verified` |
| `hkjc_mark_six_2002_07_03_partial` | 2002-07-03 | 2010-11-08 | 1–49, HKD 5, seven divisions; older payout formula incomplete | R9, R4, GraphQL | `partially_verified` |
| `hkjc_mark_six_1997_to_2002_07_02_partial` | 1997-01-01 | 2002-07-02 | 1–47, HKD 5, six source-reported divisions | R4, GraphQL | `partially_verified` |
| `hkjc_mark_six_1996_pool_transition_unresolved` | 1996-01-01 | 1996-12-31 | Conservative 1–47 upper bound; exact 45→47 boundary unresolved | R4, GraphQL | `partially_verified` / range unresolved |
| `hkjc_mark_six_1995_stake4_transition_unresolved` | 1995 records reporting HKD 4 | 1995 only | 1–45; assignment follows source stake without asserting policy boundary | R4, R10 | `partially_verified` / stake boundary unresolved |
| `hkjc_mark_six_1995_stake5_transition_unresolved` | 1995 records reporting HKD 5 | 1995 only | 1–45; assignment follows source stake without asserting policy boundary | R4, R10 | `partially_verified` / stake boundary unresolved |
| `hkjc_mark_six_1993_to_1994_partial` | 1993-01-01 | 1994-12-31 | 1–45, HKD 4, six source-reported divisions | R4, GraphQL | `partially_verified` |

## `hkjc_mark_six_2024_05_21`

### Interval and draw mechanism

R3 states that the revised Snowball Pool arrangement took effect on 2024-05-21 with draw 2024/058.
R3 says other prize-allocation arrangements were unchanged. The current formal rules and guide were
reviewed together; the interval remains open only as of the review date.

| Field | Verified value | Evidence |
|---|---|---|
| Number pool | Integers 1 through 49 | R1, R2, R6 |
| Ordinary combination | Six different numbers | R1, R6 |
| Draw | Six main numbers are drawn, followed by one Extra Number from the remaining numbers; no replacement | R1; R8 corroborates six-number machine process |
| Normal unit stake | HKD 10 (`1000` cents) | R1, R2 |
| Partial unit | HKD 5, only for Multiple and Banker entries; prizes paid in the same fraction of a unit | R1, R2 |
| Current normal schedule | Usually three draws weekly: Tuesday, Thursday, and a non-racing Saturday or Sunday | R7; operational, not treated as immutable |

### Entry mechanics

- **Single:** one selection of six different numbers from 1–49 (R1, R6).
- **Multiple:** choose seven or more different numbers; the entry contains every six-number
  combination from that set (R1, R2, R6).
- **Banker:** choose one to five bankers plus legs; every six-number combination includes every
  banker and enough legs to total six. Banker and leg numbers must be distinct (R1, R2, R6).

R12 independently tabulates combination counts and costs for current Multiple and Banker entry
sizes. R14's published example says an eight-number Multiple contains 28 combinations and, when it
contains all six main numbers but not the Extra Number, pays one First, 12 Third, and 15 Fifth
Division prizes. The Phase 4 closed-form model reproduces these counts exactly.

### Prize qualification

| Division | Qualification | Current dividend rule | Evidence |
|---:|---|---|---|
| 1 | All six main numbers | Pari-mutuel; First Division fund minimum HKD 8m | R1, R2, R5 |
| 2 | Five main numbers plus Extra Number | Pari-mutuel | R1, R2 |
| 3 | Five main numbers, excluding Extra Number | Pari-mutuel | R1, R2 |
| 4 | Four main numbers plus Extra Number | Fixed HKD 9,600 per full unit | R1, R2 |
| 5 | Four main numbers, excluding Extra Number | Fixed HKD 640 per full unit | R1, R2 |
| 6 | Three main numbers plus Extra Number | Fixed HKD 320 per full unit | R1, R2 |
| 7 | Three main numbers, excluding Extra Number | Fixed HKD 40 per full unit | R1, R2 |

### Allocation, minimums, Snowball, and rollover

- The Prize Fund is 54% of total bets. R2 states the remaining 46% allocation as 25% Lottery Duty,
  15% Lotteries Fund, and 6% HKJC Lotteries Limited commission.
- After paying Divisions 4–7 and subtracting the Snowball Deduction, the remaining distributable
  amount is allocated 45% / 15% / 40% to Divisions 1 / 2 / 3 (R1, R2).
- R2 defines the Snowball Deduction effective 2024-05-21 as:
  `9% × [P − F − 55% × (60% × P − F)] + 55% × (60% × P − F)`, where `P` is Prize Fund and `F`
  is the total payable to Divisions 4–7.
- Top-three percentages may be adjusted so a First Division prize is at least twice a Second,
  Second at least twice Third, and Third at least twice Fourth. The formal rules also provide for
  adjustment of fixed divisions and for rounding (R1, R2).
- The First Division Prize Fund minimum is HKD 8m. R5 states no maximum. This is a fund minimum,
  not a guaranteed per-ticket dividend when there are multiple winning units.
- The Snowball Deduction is transferred to the Snowball Pool. HKJC may add Snowball Pool funds to a
  designated draw under the formal rules (R1, R3).
- If there is no First and/or Second Division winning unit, the applicable amount carries forward to
  the First Division jackpot of the next draw (R1, R5). The detailed reallocation sequence and
  rounding in R1 must be implemented before exact historical payout reconstruction.

### Phase 4 prize-fund implementation boundary

Phase 4 implements exact current calculations for the 54% Prize Fund share, fixed Division 4-7
liability, the published Snowball Deduction, the initial 45%/15%/40% Division 1-3 allocation, the
HKD 8 million First Division fund minimum top-up, ordinary prize sharing, and the no-winner
reallocation/carry-forward rules in R1. Lottery Duty, Lotteries Fund contribution, commission,
Prize Fund, Snowball Deduction, Snowball additions, carried Jackpot, and special-jackpot additions
remain separately named values.

R1 does not provide a unique adjustment algorithm for every minimum-prize conflict. Rule 3.16 also
requires the available Snowball balance, all winning-unit information, and rateable rounding state
when fixed prizes exceed 60% of the Prize Fund or total funds are insufficient. Rule 3.10 has special
branches for a sole partial-unit winner, and Rule 3.17 rounds prizes down to the Unit Stake Amount.
The standard calculator stops at these exceptional boundaries unless their complete state is
provided; it does not guess a final dividend.

The GraphQL field named `jackpot` is not equated automatically with either the Snowball Pool, the
advertised estimate, or the final First Division fund. These remain separate source concepts.

## Earlier change points and unresolved intervals

R4 provides the following official chronology. Except for 2010, it gives only calendar years, so
these are research leads rather than exact machine-readable boundaries:

| Change | Officially reported point | What is known | What remains unresolved |
|---|---|---|---|
| Pool 36 → 40 | 1983 | Maximum became 40 | Exact draw/date and all simultaneous rule changes |
| Pool 40 → 42 | 1987 | Maximum became 42 | Exact draw/date |
| Pool 42 → 45 | 1990 | Maximum became 45 | Exact draw/date |
| Unit HKD 2 → 4 | 1991 | Unit stake became HKD 4 | Exact draw/date |
| Unit HKD 4 → 5 | 1995 | Unit stake became HKD 5 | Exact draw/date; official draw 1995/001 still reports HKD 4 |
| Pool 45 → 47 | 1996 | Maximum became 47 | Exact draw/date |
| Pool 47 → 49 | 2002-07-03 | 6-out-of-49, First Division HKD 38m ceiling removed, Seventh Prize HKD 20 introduced | Complete contemporaneous payout allocation text |
| Unit HKD 5 → 10; partial HKD 5 introduced; fixed prizes doubled; First Division minimum HKD 8m | 2010-11-09 | Exact effective date and sampled boundary draw 2010/130 | Complete allocation/Snowball text for the whole 2010–2024 interval |
| Snowball Pool arrangement revised | 2024-05-21, draw 2024/058 | Exact boundary and current formula | Archived pre-change formula and accounting comparison |

Official notices also show temporary draw-frequency changes during COVID-era disruptions and
individual weather/operational postponements. These belong in a schedule-event history, not as a
silent change to number-selection rules. A 2026 change from the fourth- to fifth-generation draw
machine is an operational event; no evidence reviewed here says it changed the mathematical draw
mechanism.

The machine-readable registry validates every draw against a safe period. Its 1996 maximum of 47 is
explicitly a conservative upper bound, so legitimate records are not rejected using an invented
45→47 date. The audit retains 207 `requires_rule_research` rows: 101 draws in the 1995 source-stake
split and 106 draws in the unresolved 1996 pool-transition year. Other partially verified periods
are linked but do not create a false claim that all payout economics are known.

### Phase 4 boundary research result

Targeted searches of HKJC annual-report archives, HKJC press/anniversary material, and official
HKSAR/LegCo material found no contemporaneous source establishing an exact 1995 stake-change draw or
an exact 1996 pool-change draw. R4 remains the strongest formal chronology and identifies only the
calendar years. R10 narrows what the current official results source observes, but source
observation does not establish the policy-effective boundary: a transition could have occurred on
an intervening non-draw date, and absence of 46/47 in one result does not prove a 45-ball pool.

Accordingly, no rule-registry boundary was changed. The 1995 registry continues to resolve records
by their source-reported stake, and the 1996 registry continues to use 47 only as a conservative
validation upper bound. Phase 4 probability reporting presents both 6/45 and 6/47 candidates for
1996. Historical six-division prize qualification and Extra Number mechanics also remain
conditional because no contemporaneous formal rule text was found.

## Remaining rule research

- Locate archived formal rules and exact draw boundaries for every pool, stake, division, fixed-prize,
  allocation, and Snowball change.
- Verify whether Extra Number mechanics and the number of prize divisions were constant in each era.
- Transcribe the complete pre-2024 Snowball and reallocation formulas before economic analysis.
- Establish exact sales cutoff/publication behavior by era and special/postponed-draw ticket handling.
- Distinguish advertised jackpot, carried fund, Snowball addition, derived First Division fund, and
  final dividend using contemporaneous evidence.
- Build a complete official schedule-event table for frequency changes and postponements.
