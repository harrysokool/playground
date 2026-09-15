# Source Register

**Status:** Phase 3 measured acquisition complete; Phase 8 economic evidence reviewed
**Reviewed:** 2026-09-14
**Policy:** official evidence first, exact raw bytes retained, no access-control bypass, sequential
narrow requests, no automatic retries, and local-only raw storage while terms remain unclear.

Verification is field- and coverage-specific. `sample_verified` does not mean the complete history
is complete or unchanged. Terms notes below are factual observations, not legal conclusions.

## Source index

| Source ID | Publisher / status | Exact URL or pattern | Data and format | Observed coverage | Retrieval | Limits and usage observations | Priority / verification |
|---|---|---|---|---|---|---|---|
| `hkjc_marksix_graphql` | Hong Kong Jockey Club (HKJC), official | `https://info.cld.hkjc.com/graphql/base/` | JSON: draw ID/year/number, dates, status, six numbers and Extra Number, turnover, source `jackpot`, stake, estimated/derived first prize, division dividends and `winningUnit`, special-draw codes/names | 602 sequential windows measured 1975-09-05 through 2026-09-13. Responses are valid but empty before draw 93/001 on 1993-01-05. Populated development coverage ends at draw 26/099 on 2026-09-12: 4,387 unique draws. | Unauthenticated HTTP POST using the exact allowlisted operation embedded in the official results application | Undocumented contract; schema may change. Full run used one-second spacing, zero retries, immutable cache, and stopped-on-error semantics. Storage/redistribution rights and general automated-use terms remain unclear. | **P0 primary draw source / `coverage_measured`** |
| `hkjc_marksix_results_ui` | HKJC, official | `https://bet.hkjc.com/en/marksix/results` | JavaScript results interface; currently presents recent/date search and is the provenance bridge to the GraphQL operation | UI defaults to ten recent draws; current bundle permits recent or date-range search. Historical depth was measured through GraphQL, not assumed from the UI. | Browser-rendered HTML/JavaScript | UI may enter maintenance mode and bundle/query names may change. `https://bet.hkjc.com/robots.txt` allows `/marksix` and `/en/marksix` while disallowing `/info/*` and `/ContentServer/*`; it does not mention the separate GraphQL host. | P0 discovery/corroboration / `structure_reviewed` |
| `hkjc_current_rules_pdf` | HKJC, official | `https://www.hkjc.com/english/betting/template_betting_rule_files/pdf/Lotteries_Rule_3_Eng_20260330.pdf` | Seven-page PDF, “Rules of The Hong Kong Lotteries”: entry definitions, draw mechanics, qualifications, allocation, fixed prizes, partial units, Snowball Pool, no-winner and rounding rules | Current rules retrieved 2026-09-13; filename identifies the 2026-03-30 edition. Earlier editions not yet located. | Manual/HTTP PDF download; exact bytes preserved | Copyright applies; retain for internal evidence and quote minimally. `www.hkjc.com/robots.txt` returned 404. No conclusion is made about broader automated retrieval. | **P0 primary rule source / `sample_verified`** |
| `hkjc_betting_guide` | HKJC, official | `https://is.hkjc.com/aosbs/help/en/mk6_guide.html` | HTML: all prize qualifications, unit and partial stakes, fixed prizes, prize-fund percentage, top-three allocation, Snowball Deduction formula, ratio adjustments, Multiple and Banker mechanics | Current guide; explicitly states Snowball Deduction effective 2024-05-21 | Direct HTML | Help-site presentation can change; exact bytes preserved. Access terms remain unclear, so only one manual sample was retained. | **P0 rule corroboration / `sample_verified`** |
| `hkjc_entry_types` | HKJC, official | `https://special.hkjc.com/e-win/en-US/betting-info/marksix/types-of-entry/` | HTML explanation of Single, Multiple, and Banker entries | Current | Manual browser/HTML | Presentation source, not a historical rules archive | P1 / `structure_reviewed` |
| `hkjc_prize_qualification` | HKJC, official | `https://special.hkjc.com/e-win/en-US/betting-info/marksix/prize-qualification/` | Current seven prize qualifications; 49-number pool; full and partial-unit entry context | Current | Manual browser/HTML | Current presentation source, not evidence for historical mechanics | **P0 current mathematics check / `structure_reviewed`** |
| `hkjc_chance_table` | HKJC, official | `https://special.hkjc.com/e-win/en-US/betting-info/marksix/chance-table/` | Current Multiple and Banker selection, combination-count, and cost tables | Current | Manual browser/HTML | Tabulated examples corroborate formulas but do not replace formal rules | P1 mathematics corroboration / `structure_reviewed` |
| `hkjc_2026_fun_facts` | HKJC, official | `https://campaigns.hkjc.com/2026-marksix/en/funfacts` | Publishes current First Division chance as 1 in 13,983,816 | 2026 campaign | Manual browser/HTML | Campaign presentation; used only as an independent check against derivation | P1 odds corroboration / `structure_reviewed` |
| `hkjc_2022_multiple_example` | HKJC, official | `https://racingnews.hkjc.com/english/2022/08/03/mark-six-summer-snowball-draw-to-be-held-next-tuesday-estimated-first-division-prize-fund-could-reach-50-million/` | States eight-number Multiple has 28 combinations and a specified draw overlap yields 1 First, 12 Third, and 15 Fifth prizes | 2022-08-03 | Manual browser/HTML | One current-era example, not a complete system-entry rule history | P1 mathematics corroboration / `sample_verified` |
| `hkjc_prize_allocation` | HKJC, official | `https://special.hkjc.com/e-win/en-US/betting-info/marksix/allocation-of-prize-fund/` | HTML summary of current allocation, HKD 8 million First Division minimum, no stated maximum, and no-winner carry-forward | Current | Manual browser/HTML | Summary should be read with the formal rules and betting guide | P1 / `structure_reviewed` |
| `hkjc_schedule` | HKJC, official | `https://special.hkjc.com/e-win/en-US/betting-info/marksix/lottery/` | Normal draw cadence and links to the latest results | Current | Manual browser/HTML | Schedule is operational and can change for racing calendars, weather, holidays, or special draws | P1 / `structure_reviewed` |
| `hkjc_2024_snowball_change` | HKJC, official | `https://corporate.hkjc.com/corporate/corporate-news/english/2024-05/news_2024051802131.aspx?iframe=1` | Announcement of revised Snowball Pool arrangement effective draw 2024/058 on 2024-05-21 | One dated change point | Manual HTML | Explains change intent and boundary; formal arithmetic comes from the rules/guide | **P0 boundary evidence / `sample_verified`** |
| `hkjc_2010_rule_change` | HKJC, official | `https://www.hkjc.com/english/pressrelease/mcs01_showhtml.asp?filename=20100928_194443_E_NEWS.htm` | Announcement effective 2010-11-09: HKD 10 unit, HKD 5 partial unit for Multiple/Banker, doubled fixed prizes, HKD 8 million First Division minimum; also lists earlier pool and price changes by year | Exact 2010 boundary; earlier changes only to calendar year | Manual HTML | Earlier year-only references cannot establish exact rule intervals | **P0 historical boundary / `sample_verified`** |
| `hkjc_draw_notices` | HKJC, official | Corporate/press-release pages under `hkjc.com` and `racingnews.hkjc.com` | Special jackpots, draw scheduling changes, postponements, sales/draw times, machine changes | Individual dated notices found for COVID-era frequency changes, 2025/2026 postponements, 2025 Lucky Tuesday, 2026 50th Anniversary Snowball, and 2026 machine replacement | Manual discovery initially | Distributed archives; not a complete index. Each event needs its own immutable record before canonical use. | P1 / `sample_verified` for listed notices only |
| `hkjc_2026_anniversary_economics` | HKJC, official | `https://www.hkjc.com/english/pressrelease/mcs01_showhtml.asp?SelType=NEWS&filename=20260829_114346_E_NEWS.htm` | Before-draw notice for 2026/096: HKD 185m carried Snowball and HKD 228m estimated First Division fund | One dated draw-specific reconciliation | Manual HTML review | Proves the two advertised amounts for this draw, not invariant GraphQL field semantics | **P0 Phase 8 field reconciliation / `sample_verified`** |
| `baker_mchale_2011` | Peer-reviewed external research | `https://doi.org/10.1111/j.1467-985X.2011.00693.x` | Statistical evidence of conscious selection and clustering in UK/Spain lottery choices | Other markets, not Mark Six | Publication abstract and bibliographic review | Cannot quantify Hong Kong selection probabilities | P1 behavioral context / `external_not_hk` |
| `hong_kong_superstition_values` | Peer-reviewed external research | `https://pmc.ncbi.nlm.nih.gov/articles/PMC7113914/` | Hong Kong licence-plate auction evidence for premiums on 8 and discounts on 4 | Hong Kong cultural behavior, not lottery ticket selection | Open publication review | Does not establish Mark Six number-choice frequencies | P2 cultural context / `not_ticket_microdata` |
| `hkjc_draw_integrity` | HKJC, official | `https://www.hkjc.com/english/corporate/racing_news_item.asp?in_file=%2Fenglish%2Fnews%2F2016-02%2Fnews_2016021901440.html` | Description of electronic draw machine, six main draws, supervision, ball checks, sign-off, and secure storage | 2016 description, not assumed timeless | Manual HTML | Operational description is not a substitute for a dated formal rule interval | P1 / `structure_reviewed` |
| `hksar_gambling_policy` | HKSAR Government, official | `https://www.hyab.gov.hk/en/policy_responsibilities/District_Community_and_Public_Relations/gambling.htm` | Public policy and authorized-outlet context for Mark Six | Current policy page | Manual HTML | Does not provide result records or prize mechanics | P1 context / `structure_reviewed` |
| `hksar_lotteries_fund` | Social Welfare Department, HKSAR Government, official | `https://www.swd.gov.hk/en/ngo/lotteriesf/` | Official Lotteries Fund purpose/context | Current | Manual HTML | Context only | P2 context / `structure_reviewed` |
| `hkjc_bet2_legacy_json` | HKJC, official but deprecated | `https://bet2.hkjc.com/marksix/getJSON.aspx/?sd=YYYYMMDD&ed=YYYYMMDD&sb=0` | Former JSON result endpoint found in archived third-party collector code | Historically used; now redirects to the current site | HTTP check only | Do not build against it unless HKJC restores/document it | P3 / `rejected_as_primary` |
| `icelam_mark_six_data_visualization` | Unverified third party | `https://github.com/icelam/mark-six-data-visualization` | Quarterly JSON copied from the legacy HKJC endpoint, apparently from 1993; its 2026 file was empty when checked | Claimed/observed repository files from 1993, not independently coverage-audited | GitHub/manual only | No repository licence was visible; transformations, omissions, corrections, and redistribution rights are unclear | P2 gap discovery / `not_accepted` |
| `renavon_marksix_dataset` | Unverified third party | `https://renavon.com/hk-mark-six-results` | Downloadable historical table claiming about 4,385 rows from 1993 onward | Claimed, not measured | Website download not performed | Provenance, licence, transformations, revision policy, and completeness unclear | P2 cross-check candidate / `not_accepted` |
| `marksixinfo` | Unverified third party | `https://marksixinfo.com/` | Result presentation useful for spot comparison | Unknown | Manual only | No authority or completeness guarantee; never override HKJC | P3 corroboration / `not_accepted` |

No official CSV download was found. The former `bet2` JSON endpoint is no longer usable; the current
official web application sends an allowlisted GraphQL POST. The exact operation document and request
variables are versioned in `src/mark_six/sources/hkjc.py`.

## Primary-source recommendation

Use `hkjc_marksix_graphql` as the primary historical draw source because it is the structured source
used by the official HKJC results interface. The completed Phase 3 measurement found populated
coverage from 1993-01-05 through 2026-09-12. This says nothing about game inception: earlier empty
responses are endpoint-coverage evidence, not evidence that no earlier draws occurred.

The source hierarchy is:

1. GraphQL exact responses for draw/result fields.
2. Formal HKJC lottery rules plus dated HKJC change announcements for rule versions.
3. Contemporaneous HKJC notices for special jackpots, postponements, and publication timing.
4. HKSAR sources for regulatory/context claims.
5. Third parties only to identify possible gaps and independently spot-check; never silently repair
   or override an official field.

## GraphQL source contract observed in Phase 2

- Method: `POST`; content type: JSON; no authentication observed.
- Operation: `marksixResult`; draw type: `All`.
- Recent variable: `lastNDraw` (the official UI defaults to 10; Phase 2 code caps samples at 10).
- Historical variables: `startDate` and `endDate` in `YYYYMMDD` format. The Phase 2 helper caps a
  request to 31 elapsed days; the current UI appears to allow roughly three months, but that is not
  treated as permission or a stable API guarantee.
- Result fields: `id`, `year`, `no`, `openDate`, `closeDate`, `drawDate`, `status`, Snowball fields,
  `lotteryPool`, `lotteryPrizes`, `drawnNo`, and `xDrawnNo`.
- The official bundle displays draw number as the last two year digits, `/`, and zero-padded
  three-digit `no` (for example source year `2026`, number `99` becomes `26/099`).
- The official JavaScript divides source `winningUnit` by `lotteryPool.unitBet` for display. The
  parser therefore preserves both the source amount and the normalized unit count. Example: source
  `35` with HKD 10 unit stake becomes `3.5` winning units.
- Blank strings occur in legitimate older records and are normalized only to explicit nulls.
- `jackpot` and `derivedFirstPrizeDiv` are kept as source-reported concepts; neither is silently
  reinterpreted as a pre-draw advertised jackpot.

## Access review and conservative collector policy

Observed facts:

- `bet.hkjc.com/robots.txt` permits the Mark Six page paths noted above; it does not authorize the
  separate GraphQL host. The GraphQL host's robots request returned HTTP 403. The general HKJC
  robots path returned 404.
- No CAPTCHA, login, token, or rate-limit bypass was attempted. The sampled GraphQL operation was
  publicly callable and allowlisted to the official site's exact query.
- No clear licence or terms granting automated bulk retrieval, local redistribution, or republication
  of the dataset was located during this review.

Until clarified, a collector must identify itself, use narrow sequential requests, have no automatic
retry by default, back off on errors, cache immutable responses, avoid re-fetching known hashes, and
stop on contract/access changes. Raw official artifacts should remain local and Git-ignored. These
controls are conservative engineering choices, not a legal opinion.

## Preserved evidence and acquisition audit

Snapshot paths use:

`data/raw/<source_id>/<retrieval-year>/<retrieval-month>/<UTC timestamp>_<12 hash chars>.<ext>`

Each response has a `.metadata.json` sidecar; POST requests also have an exact `.request.json` file.
The sidecar contains URL, request variables, UTC retrieval time, status, media type, byte length,
SHA-256, raw path, and parser version. `mark-six source inspect-snapshot` checks the file against the
sidecar before parsing.

Representative result snapshots:

| Snapshot hash prefix | Query / result | Why retained |
|---|---|---|
| `3d6dd4cb0fd0` | last 5 draws: 2026/095–099 | Recent normal draws, rollover-like reported jackpot variation, and special draw 2026/096 |
| `af366d8c8a03` | 2010-11-09 | Exact 2010 rule-change boundary; special 35th Anniversary Snowball |
| `3da07952479e` | 2024-05-21 | Exact 2024 Snowball arrangement boundary, draw 2024/058 |
| `a53c4addf045` | 1995-01-03 | Older 45-number/HKD 4 source shape with missing optional fields |
| `cd1ecdaa9ecb` (two snapshots) | ISO-formatted historical probes | Valid HTTP/GraphQL empty responses that exposed the undocumented `YYYYMMDD` requirement; retained as failed evidence |

Also preserved: current rules PDF `aa87a5d89fb0…` and current betting guide HTML
`4bbb55f07c55…`. Small curated test fixtures copy representative fields; they are not substitutes for
the immutable raw files.

The 608 preserved GraphQL responses comprise the 602-window Phase 3 acquisition and six Phase 2
probes/samples. Every response has one metadata and one exact request sidecar. Before the controlled
revision requery, the audit found 608 responses, zero missing sidecars, zero hash or HTTP failures,
zero malformed JSON documents, zero unexpected GraphQL structures, 212 empty responses, and 396
nonempty responses. There are no duplicate request identities. There are 211 redundant content
observations, largely identical valid empty results; content duplication is not request or draw
duplication. Across all snapshots there are 4,395 draw observations, 4,387 unique draws, eight exact
overlapping observations, and zero conflicting draw representations.

## Remaining source questions

- Can HKJC usage/storage/redistribution expectations be clarified?
- What do `jackpot` and `derivedFirstPrizeDiv` mean in every historical era?
- When did all fields first become populated, and are blank historical prize divisions recoverable
  from official archives?
- Are archived rule PDFs or annual reports available for every rule boundary?
- Can publication timestamps be recovered independently of current-page retrieval time?
- Does the endpoint revise old responses? A small controlled check can detect changes only in the
  selected sample; zero detected revisions is not proof that revision never occurs.
