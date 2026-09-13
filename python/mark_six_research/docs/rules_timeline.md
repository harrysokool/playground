# Mark Six Rules Timeline

**Status:** current interval verified; seven historical assignments intentionally partial  
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
- **R10:** full retained GraphQL coverage. Source fields observe HKD 4 through draw 1995/041 and
  HKD 5 from draw 1995/042, but this observation is not treated as a formal rule-effective date.

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

## Remaining rule research

- Locate archived formal rules and exact draw boundaries for every pool, stake, division, fixed-prize,
  allocation, and Snowball change.
- Verify whether Extra Number mechanics and the number of prize divisions were constant in each era.
- Transcribe the complete pre-2024 Snowball and reallocation formulas before economic analysis.
- Establish exact sales cutoff/publication behavior by era and special/postponed-draw ticket handling.
- Distinguish advertised jackpot, carried fund, Snowball addition, derived First Division fund, and
  final dividend using contemporaneous evidence.
- Build a complete official schedule-event table for frequency changes and postponements.
