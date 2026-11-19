# Receipt OCR Benchmark – Decks

**Version 16 (current)** is a short deck for senior management screening our AI innovation idea (not approving
a finished product): we identified repetitive manual audit work, demonstrated a working Azure DI + Azure OpenAI
receipt extraction workflow, compared three approaches, and explored how structured receipt data could improve
Internal Audit. Version 15 was a longer management deck built from [`deck_direction.md`](deck_direction.md).
Versions 1–14 answered a narrower question: **is Azure Document Intelligence + Azure OpenAI worth its additional
cost and complexity compared with simpler OCR solutions?** (audience: business and technical stakeholders).

| Version | Deck | Generator | Source of truth (under `python/receipt_ocr_benchmark/`) |
|---|---|---|---|
| **Version 16 (current)**, cover + 8 slides + 2 appendix | `current/OCR_Benchmark_V16.pptx` | `scripts/generate_ppt_v16.py` | As Version 11, plus `results/v2/di_aoai_v2_rows/receipt8.json` (the extracted output on main slide 2); manual-review estimates from the team; checks from the business auditor checklist |
| Version 15, cover + 10 slides + 2 appendix (archived) | `archive/v15_final/OCR_Benchmark_V15.pptx` (+ PDF preview) | `scripts/generate_ppt_v15.py` (unchanged) | As Version 11; storyline from `deck_direction.md` |
| Version 14, 9 slides (archived) | `archive/v14_final/OCR_Benchmark_V14.pptx` (+ PDF preview) | `scripts/generate_ppt_v14.py` (unchanged) | As Version 13 |
| Version 13, 9 slides (archived; as last saved in PowerPoint, commit `2e7b4eb`) | `archive/v13_final/OCR_Benchmark_V13.pptx` (+ PDF preview of the generated version) | `scripts/generate_ppt_v13.py` (unchanged; without the PowerPoint edits) | As Version 11; the audit test examples come from the auditor discussion (not in the repository) |
| Version 12, 9 slides (archived) | `archive/v12_final/OCR_Benchmark_V12.pptx` (+ PDF preview) | `scripts/generate_ppt_v12.py` (unchanged) | As Version 11 |
| Version 11, 8 slides (archived) | `archive/v11_final/OCR_Benchmark_V11.pptx` (+ PDF preview) | `scripts/generate_ppt_v11.py` (unchanged) | `results/v2/scores_multilingual/` and `scores_aoai_improved/` (summary, detail), `results/v2/extracted_multilingual_*`, the receipt photos |
| Version 10, 11 slides (archived) | `archive/v10_final/OCR_Benchmark_V10.pptx` (+ PDF preview) | `scripts/generate_ppt_v10.py` (unchanged) | As Version 9; the auditor checklist comes from the auditor discussion (not in the repository) |
| Version 9, 10 slides (archived) | `archive/v9_final/OCR_Benchmark_V9.pptx` (+ PDF preview) | `scripts/generate_ppt_v9.py` (unchanged) | As Version 6, plus `results/v2/extracted_multilingual_*` and the receipt photos |
| Version 8, 8 slides (archived) | `archive/v8_final/OCR_Benchmark_V8.pptx` (+ PDF preview) | `scripts/generate_ppt_v8.py` (unchanged) | As Version 6 |
| Version 7, 9 slides (archived) | `archive/v7_final/OCR_Benchmark_V7.pptx` (+ PDF preview) | `scripts/generate_ppt_v7.py` (unchanged) | As Version 6 |
| Version 6, 10 slides (archived) | `archive/v6_final/OCR_Benchmark_V6.pptx` (+ PDF preview) | `scripts/generate_ppt_v6.py` (unchanged) | As Version 5, plus `results/v2/scores_multilingual/` |
| Version 5, 10-slide management version (archived) | `archive/v5_final/OCR_Benchmark_V5.pptx` (+ PDF preview) | `scripts/generate_ppt_v5.py` (unchanged) | `results/v2/scores_improved/` and `scores_aoai_improved/`, `results/v1_heldout/`, `results/diagnosis/`, `results/v2/*/receiptN.json`, `receipt_bench/di_aoai.py` (prompt text) |
| Version 4, 12-slide redesign (archived) | `archive/v4_final/OCR_Benchmark_V4.pptx` (+ PDF preview) | `scripts/generate_ppt_v4.py` (unchanged) | `results/v2/scores_improved/` and `scores_aoai_improved/`, `results/v1_heldout/`, `results/diagnosis/`, `data/diagnosis/`, `results/v2/*/receiptN.json`, `receipt_bench/di_aoai.py` (prompt text) |
| Version 3, final 12-slide deck (archived) | `archive/v3_final/OCR_Benchmark_V3.pptx` (+ PDF preview) | `scripts/generate_ppt_v3.py` (unchanged) | `results/v2/scores_improved/` and `scores_aoai_improved/` (summary, detail), `results/v1_heldout/`, `results/v2/*/receiptN.json`, receipt photos in `data/receipts_v2/` |
| Version 3, 10-slide revision before the field and prompt v2 slides (archived) | `archive/v3_10slides/OCR_Benchmark_V3.pptx` (+ PDF preview) | `scripts/generate_ppt_v3.py` at commit `c06d945` | Same as Version 3 |
| Version 3, first revision (archived): no rule accuracy figures | `archive/v3_first/OCR_Benchmark_V3.pptx` (+ PDF preview) | `scripts/generate_ppt_v3.py` at commit `3678fd9` | Same as Version 3 |
| Version 2, final 10-slide deck (archived) | `archive/v2_final/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` (unchanged) | `results/v2/scores_improved/` (summary, detail), `results/v2/*/receiptN.json`, receipt photos in `data/receipts_v2/` |
| Version 2, 10-slide revision before the slide 9 rewrite (archived; as last saved in PowerPoint) | `archive/v2_10slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `dbec587` | Same as Version 2 |
| Version 2, 9-slide revision (archived) | `archive/v2_9slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `5e11b39` | Same as Version 2 |
| Version 2, 8-slide revision (archived) | `archive/v2_8slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `772e109` | Same as Version 2 |
| Version 2, first draft (archived), 12 slides | `archive/v2_12slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `6fd991c` | Same as Version 2 |
| Version 1 (frozen), 8 slides | `archive/v1/OCR_Benchmark_Comparison.pptx` (+ PDF preview) | `scripts/generate_ppt.py` | Version 1 results, available only at Git tag `ocr-benchmark-v1` |

Every number, and every value in the receipt examples, is read from the benchmark files; nothing
is typed in by hand.
- **Example values** are taken from `detail.csv` and cross-checked against the extraction JSON.
  The build stops on any mismatch.
- **Receipt crops** are placed using Azure DI's text positions. The build stops if an anchor
  text isn't found.
- **Crops and thumbnails** are written to `assets_v2/`.

## Folder structure

| Folder | Contents |
|---|---|
| `template/` | Official AIA PowerPoint template (`aia_ppt_template.pptx`). Do not edit. |
| `current/` | The current deck (Version 16) |
| `previews/` | PDF and PNG previews of the current deck, and `deck_text.md` (all slide text and notes) |
| `deck_direction.md` | The direction for Version 15: storyline, required positioning and design rules |
| `codex_take/` | An alternative auditor-focused deck built with PptxGenJS from the earlier direction plan; not used by Versions 15–16 |
| `archive/v15_final/` | The Version 15 deck (cover + 10 slides + 2 appendix) and its PDF preview |
| `archive/v14_final/` | The 9-slide Version 14 deck and its PDF preview |
| `archive/v1/` | The frozen Version 1 deck and its preview. Never written to by the generators. |
| `archive/v2_12slides/` | The first, 12-slide Version 2 deck and its PDF preview, kept for reference |
| `archive/v2_8slides/` | The 8-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_9slides/` | The 9-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_10slides/` | The 10-slide revision before the slide 9 rewrite, and its PDF preview |
| `archive/v13_final/` | The Version 13 deck (with the PowerPoint edits) and its PDF preview |
| `archive/v12_final/` | The 9-slide Version 12 deck and its PDF preview |
| `archive/v11_final/` | The 8-slide Version 11 deck and its PDF preview |
| `archive/v10_final/` | The 11-slide Version 10 deck and its PDF preview |
| `archive/v9_final/` | The 10-slide Version 9 deck and its PDF preview |
| `archive/v8_final/` | The 8-slide Version 8 deck and its PDF preview |
| `archive/v7_final/` | The 9-slide Version 7 deck and its PDF preview |
| `archive/v6_final/` | The 10-slide Version 6 deck and its PDF preview |
| `archive/v5_final/` | The 10-slide Version 5 deck and its PDF preview |
| `archive/v4_final/` | The 12-slide Version 4 deck and its PDF preview |
| `archive/v3_final/` | The final 12-slide Version 3 deck and its PDF preview |
| `archive/v3_10slides/` | The 10-slide Version 3 revision and its PDF preview |
| `archive/v3_first/` | The first Version 3 revision (rule accuracy not shown) and its PDF preview |
| `archive/v2_final/` | The final Version 2 deck (with PaddleOCR Heavy and the tuned rule accuracies) and its PDF preview |
| `assets_v2/` | Receipt crops and thumbnails produced by `generate_ppt_v2.py`, `generate_ppt_v3.py`, `generate_ppt_v4.py`, `generate_ppt_v5.py`, `generate_ppt_v6.py`, `generate_ppt_v7.py`, `generate_ppt_v8.py` and `generate_ppt_v9.py`; Version 15 adds `crop_v15_*.jpg` (also used by Version 16) and Version 16 adds `full_v16_receipt8.jpg` |
| `scripts/` | The generators |

## Version 16: senior management screening deck (cover + 8 slides + 2 appendix)

Version 15 reorganised into 8 main slides, shorter and less repetitive, for senior management screening the AI
innovation idea. It presents our team's practical AI exploration and its potential value, not a request to
approve a production system. The working extraction workflow is shown as demonstrated; processing 500 to 1,000
receipts, broader field extraction, automated audit checks and time savings are shown as future goals only.

| Deck slide | Main slide | Title | Key message |
|---|---|---|---|
| 1 | — | AI-Assisted Medical Receipt Extraction (cover) | An Internal Audit AI innovation idea: what we built, what we tested and where it could go |
| 2 | 1 | The Problem: Manual Receipt Reviews Take Time | ~25 receipts per sample at an estimated 5–10 minutes each (team estimates, not measured); what auditors check, from the business auditor checklist; the bottleneck is auditor time |
| 3 | 2 | Our AI Solution and Business Value | Working receipt → Azure DI → Azure OpenAI → structured data workflow, with benchmark receipt 8 and its saved output; three potential benefits; 500 to 1,000 receipts is an initial future target, not yet demonstrated |
| 4 | 3 | Three Approaches Tested | 51.0% / 70.6% / 96.1%: development results from nine receipts, not production accuracy |
| 5 | 4 | Why AI Instead of OCR and Rules? | OCR reads the text; AI uses context (referring doctor, treatment date, discounted total); AI can also make mistakes |
| 6 | 5 | Advantages, Limitations and Alternatives | Simplified pros and cons; OCR + regex + doctor database as a feasible, not-benchmarked alternative |
| 7 | 6 | Future Audit Analytics | Receipt amount vs claim, treatment dates, duplicate receipts, unusual provider fees; later, on another authorized platform; not implemented |
| 8 | 7 | Privacy and Platform Design | Only approved receipt data goes to Azure; PII protection, storage, access controls and transfer still to be agreed |
| 9 | 8 | Conclusion and Next Steps | What we demonstrated, why it matters; priorities: expand extraction, validate independently, confirm privacy and platform design |
| 10 | A1 | Accuracy by Field | Per-field figures recomputed from `detail.csv` |
| 11 | A2 | How the Benchmark Was Run | Dataset, why the results are directional, future goals not yet tested |

The extracted output on main slide 2 is read from the saved result for receipt 8 and must match the ground truth
for all six fields (asserted at build time). The checklist content on main slide 1 is summarised from the business
auditor checklist (`manual_sample_test.png`). The 2–4 hours per sample on main slide 1 is 25 × 5–10 minutes,
labelled as an estimate.

`scripts/check_deck_v16.py` checks: 11 slides with notes; the status tags; the estimates labelled as not measured;
the receipt 8 output matching the saved result; the chart on main slide 3 holds exactly the three overall figures
and no other main slide shows a benchmark statistic; every per-field figure in appendix A1; the three receipt
examples and the AI-mistake point; the doctor database alternative marked not benchmarked; the analytics marked
not implemented; the privacy items still to be agreed (no masking presented as implemented or approved); the
500 to 1,000 target only as a future goal; and no avoid-list wording, old or tuned figures, technical jargon, or
cost or savings figures.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v16.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v16.py
```

The Version 15 generator and check are kept unchanged to reproduce the archived Version 15 deck (use `--output`
to write it outside `archive/`).

## Version 15: management deck from `deck_direction.md` (cover + 10 slides + 2 appendix)

A new deck, not an edit of Version 14. The current scope is reliable receipt extraction and structured export;
downstream audit tests are shown only as future possibilities. Each slide carries a status tag (current
project scope, tested on the development set, future possibility, open requirement).

| Deck slide | Main slide | Title | Key message |
|---|---|---|---|
| 1 | — | Medical Receipt Data Extraction for Internal Audit (cover) | Turning medical receipts into structured, reusable audit data |
| 2 | 1 | The Problem and Our Proposed Solution | Build a reliable receipt-data extraction layer so auditors can use receipt information at greater scale |
| 3 | 2 | What Reliable Receipt Data Could Bring | Four potential value areas; not yet measured |
| 4 | 3 | Why the Current Process Does Not Scale | The bottleneck is access to receipt data, not auditor effort; ~25 receipts is an illustrative example only |
| 5 | 4 | How AI Changes the Audit Process | Extract once, reuse across tests; structured export is in scope, audit testing and review are the future stage |
| 6 | 5 | Three Approaches Tested | The only benchmark figures in the main deck (51.0% / 70.6% / 96.1%), with the development-set qualification |
| 7 | 6 | What the Differences Look Like on a Receipt | Three examples (referring doctor, issue date, discount); the AI's own miss is one line, detail in the notes |
| 8 | 7 | Trade-offs and Scalability | Pros and cons of each approach; the OCR + regex + doctor database idea as a brief, fair, not-benchmarked alternative |
| 9 | 8 | Future Audit Tests the Data Could Support | Control tests vs red-flag tests; not being built now; a red flag is not an audit finding |
| 10 | 9 | Governance, PII Protection and Platform Design | PII protection is an open design requirement (no method chosen); which activities run in Azure vs another approved platform |
| 11 | 10 | Recommendation and Next Steps | Continue with Azure DI + Azure OpenAI, subject to independent validation and governance approval; six next steps |
| 12 | A1 | Accuracy by Field | Per-field figures recomputed from `detail.csv` |
| 13 | A2 | How the Benchmark Was Run | Dataset, why the results are directional, what is not yet tested |

The benchmark is described as "a small development set of 9 receipts, mainly fictional mock receipts" (seven
fictional receipts printed and photographed, plus two receipts carried over from an earlier test round).
Method names on the slides: **PaddleOCR + rules**, **Azure DI + rules**, **Azure DI + Azure OpenAI**. No costs,
savings or audit results are stated; Azure prices are marked "to be confirmed".

`scripts/check_deck_v15.py` checks: 13 slides with notes; the status tags; the chart on main slide 5 holds
exactly the three overall figures and no other main slide shows a benchmark statistic; every per-field figure in
appendix A1, recomputed from `detail.csv`; the dataset wording and qualification; ~25 only as an illustrative
example; the scope/future split on main slide 4; the three receipt examples; the brief doctor database
alternative marked not benchmarked; PII as an open requirement; the recommendation and six next steps; and none
of the "avoid" statements from `deck_direction.md`, old or tuned figures, technical jargon or cost figures.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v15.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v15.py
```

The Version 14 generator and check are kept unchanged to reproduce the archived Version 14 deck (use
`--output` to write it outside `archive/`).

## Version 14: simpler alternative-approach slide (9 slides)

Version 13 with only slide 7 replaced, plus the three edits made to Version 13 in PowerPoint (commit `2e7b4eb`),
now built into the generator: the slide 3 footnote removed, the slide 4 subtitle shortened to "Azure DI + AOAI was
the most accurate on every field.", and slide 7 titled "Alternative Approach (with no AI)". Slides 1–6, 8 and 9
match the edited Version 13.

Slide 7 explains the manager's proposal simply and fairly:
- How it works: OCR reads the receipt; a regex search looks for the ~40,000 registered doctor names in the OCR
  text; matching names are returned, and receipts with no match or several matches are flagged for manual review.
- Advantages: simple and practical; no AI needed for doctor name matching; low additional cost; uncertain results
  go to manual review.
- Main limitation: it identifies doctor names only; patient names, treatment dates, amounts and diagnoses need
  additional rules or AI. Both rule methods were less accurate than Azure DI + AOAI on all six fields (asserted at
  build time); the doctor database matching itself was not benchmarked.
- Key takeaway, as agreed. Multiple doctor names are no longer shown as a weakness (they go to manual review).

`scripts/check_deck_v14.py` = the Version 13 checks, with the slide 7 checks replaced (steps, advantages, limitation,
"not benchmarked", the key takeaway verbatim, no multiple-practitioner limitation) and the footnote required on
slides 4 and 9.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v14.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v14.py
```

`scripts/build_v14_on_azure.sh` does the same on Azure ML compute. The Version 13 generator and check are kept
unchanged to reproduce the generated Version 13 deck (without the PowerPoint edits).

## Version 13: business value on the final slide (9 slides)

Version 12 with only the final slide replaced. Slide 9, **"Business Value: From Receipts to Audit
Analytics"**, keeps Azure DI + AOAI as the recommended approach and shows what the extracted data enables:

- Flow: medical receipt → Azure DI + AOAI extraction → structured results → (approved transfer method, to be
  agreed) → another authorized platform → data analytics. Auditors can compare what receipts show with the
  submitted claims, not only manually entered claim data.
- Five potential audit tests from the business auditor discussion: match name and treatment date to the claim;
  claimed vs receipt amounts; duplicate receipts across claims; unusual fees; unusual diagnosis and treatment
  combinations. (Unusual claim patterns across providers or agents is in the notes only: it relies mainly on
  claims data.)
- Guard rails: Azure processes only approved receipt data; claims, policy and historical data stay in another
  authorized system; the transfer method must be approved; the analytics are potential future uses, not
  implemented or benchmarked; extraction gives supporting evidence, not a final fraud or claim validity decision.

`scripts/check_deck_v13.py` = the Version 12 checks, with the final-slide checks replaced by the flow, the audit
tests and the guard-rail wording above.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v13.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v13.py
```

The Version 12 generator and check are kept unchanged to reproduce the archived Version 12 deck.

## Version 12: Version 11 plus the doctor database proposal (9 slides)

Version 11 with one new slide after the two receipt examples:

7. **Manager's proposal: the doctor database (not benchmarked).** How it works (OCR reads the receipt, look up
   the registry of ~40,000 doctors / up to ~80,000 English and Chinese name variants, strict exact match without
   AOAI); advantages (simple, low additional cost, consistent, easy to verify); limitations with real cases
   (receipt 6 referring doctor Dr. Kwok Man Hin vs physiotherapist CHEUNG Hoi Ying; receipt 9 clinician and
   signing vet; "Dr. Lok Yi Choi" read as "Dr. Lok Vichol") and one labelled hypothetical (the patient is a
   doctor); and the fair point that exact matching may be sufficient if we only need to know whether a
   registered doctor appears. Every real example is asserted against the saved OCR text and ground truth.

The other slides are unchanged, except that the doctor database card is removed from the final slide (now
slide 9) and slide references are renumbered. `scripts/check_deck_v12.py` = the Version 11 checks for 9
slides, plus the content of slide 7 and no doctor database repeat on slide 9.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v12.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v12.py
```

The Version 11 generator and check are kept unchanged to reproduce the archived Version 11 deck.

## Version 11: which extraction approach, and why (8 slides)

A simplified management version of Version 10, focused on why we recommend Azure DI + AOAI. Three method
names only: **PaddleOCR + Rules**, **Azure DI + Rules**, **Azure DI + AOAI**. Prompt versions, Python checks
and other implementation detail are removed from the slides (some remain in the speaker notes for questions).
The figures are the same saved results as Version 10: the multilingual rules baseline for the two rule
methods, the refined-instruction AOAI run for Azure DI + AOAI.

1. Title: Medical Receipt Extraction: Which Approach?
2. **Summary.** The recommendation and three reasons; no accuracy figures.
3. **Overall accuracy.** Chart: 51.0% / 70.6% / 96.1% (26, 36, 49 of 51 fields).
4. **Accuracy by field.** Per-field table recomputed from `detail.csv`; best per field highlighted.
5. Example 1: Azure DI + Rules vs PaddleOCR + Rules (receipt 5, label misreads)
6. Example 2: Azure DI + AOAI vs Azure DI + Rules (receipt 6 practitioner, service date, total; receipt 5 total)
7. Advantages and disadvantages: accuracy, new layouts, maintenance, cost, transparency
8. **Recommendation.** Azure DI + AOAI; next step a pilot testing more receipt fields on approved receipts;
   where it runs (only receipt data goes to Azure, audit checks in another authorized system), what the
   auditors need, and the doctor database in one line.

Slides 3, 4 and 8 keep the limitation footnote: 9 test receipts, rules and AOAI instructions developed with
them, not yet independently validated.

`scripts/check_deck_v11.py` checks: 8 slides with notes; the three method names and no technical terms on
the slides; no figures on slide 2; the chart holds exactly the three overall figures; every per-field figure
(recomputed from `detail.csv`) is on slide 4; the footnote on slides 3, 4 and 8; the Azure boundary on slides
2 and 8; no Heavy, original-AOAI, English-only or tuned rule figures.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v11.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v11.py
```

The Version 10 generator and check are kept unchanged to reproduce the archived Version 10 deck.

## Version 10: benchmark results and pilot direction (11 slides)

Updated after the discussion with the business auditors. The project scope is unchanged: Azure only
processes approved medical receipt data and extracts structured information. Claims records, policy data
and the audit checks stay in another authorized system. The transfer between the two is not yet designed.

1. Title: Medical Receipt Extraction, benchmark results and pilot direction
2. **Executive summary.** Recommends Azure DI + AOAI prompt v2 for the next extraction pilot, not production.
   Shows 96.1% (development result) vs 51.0–70.6% (retrospective baseline).
3. **Scope and data boundary (new).** Receipt → Azure DI → AOAI → Python checks → structured results →
   approved transfer (to be designed) → another authorized system → audit checks. Separates the existing
   Python checks (formats, clean-up, review flags) from the planned ones (required fields, new fields), and
   lists what is never uploaded to Azure.
4. Benchmark: three approaches, same 9 receipts (the V9 approach and results slides merged)
5. Why Azure DI beat PaddleOCR Light (receipt 5)
6. Why AOAI beat the rules (receipts 6 and 5)
7. The doctor database approach (proposal, not benchmarked)
8. Advantages and disadvantages
9. **What the auditors check (new).** Five categories, summarised from the auditor discussion.
10. **From audit needs to receipt fields (new).** The 6 benchmarked fields vs 5 fields not yet tested, the
    data another authorized system adds, "information, not a verdict" (extraction does not decide
    authenticity, medical necessity or coverage), and analytics as a later potential. Replaces V9's
    "Beyond six fields" slide.
11. **Recommendation and next steps.** Define the extraction schema, extend the prompt gradually, test new
    fields on approved receipts, then agree the transfer and confirm costs. No new fields or audit checks
    are implemented yet.

`scripts/check_deck_v10.py` = the Version 9 checks for 11 slides, plus:
- the Azure boundary wording on the executive summary, scope and recommendation slides;
- the scope slide's "never uploaded", "to be designed" and existing/planned wording;
- "not a production approval";
- no claim that extraction decides authenticity, medical necessity or coverage;
- the receipt-fields slide separates benchmarked from untested fields and marks analytics as potential.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v10.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v10.py
```

The Version 10 generator and check are kept unchanged to reproduce the archived Version 10 deck (in
`archive/v10_final/`). The Version 9 generator and check are kept unchanged to reproduce the archived Version 9 deck.

## Version 9: real-receipt examples and the doctor database (10 slides)

1. Title
2. Executive summary (96.1% development result vs 51.0–70.6% retrospective baseline)
3. What we compared
4. Rules vs AOAI on the same receipts (51.0% / 70.6% / 96.1%; what explains the gap)
5. **Why Azure DI beat PaddleOCR Light** (receipt 5). The same rules ran on both engines. All 10 extra
   PaddleOCR errors are text recognition errors on labels: words run together, wrong characters, "HKS"
   for "HK$". None comes from the rules or the layout.
6. **Why AOAI beat the rules** (receipt 6: practitioner, service date, total; receipt 5: total after the
   discount). Both read the same Azure DI text. AOAI was right with its original prompt and with prompt
   v2. Also carries the maintenance message: unfamiliar layouts may require additional rules and retesting.
7. **The doctor database approach** (proposal, not benchmarked): strict exact matching against about
   40,000 doctors and about 80,000 name variants. It only works if the OCR reads the name and the registry
   contains it, and a name match is not the treating doctor. Real cases from our receipts (referring
   doctor, several staff, an OCR misread) are kept apart from hypothetical ones (the patient is a doctor,
   a director in the letterhead).
8. Advantages and disadvantages
9. Beyond six fields (potential, not yet tested)
10. Recommendation

The separate maintenance slide was removed; its message is on slide 6. The new crops are in `assets_v2/`
(`crop_receipt5_labels.jpg`, `crop_receipt6.jpg`). Every example value is asserted from the saved
OCR, extraction and score files when the deck is built.

`scripts/check_deck_v9.py` = the Version 8 checks for 10 slides, plus:
- no absolute claim that every new layout or label needs new rules (slides or notes);
- AOAI layout claims are qualified;
- the doctor slide is marked not benchmarked, keeps hypothetical cases separate, and states its
  dependencies.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v9.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v9.py
```

The Version 8 generator and check are kept
unchanged to reproduce the archived Version 8 deck.

## Version 8: concise 8-slide deck

1. Title
2. **Executive summary:** Azure DI + AOAI prompt v2 96.1% (development result) vs OCR + multilingual rules
   51.0–70.6% (51.0% PaddleOCR Light, 70.6% Azure DI; retrospective baseline), and why AOAI may still be
   needed. Small labels only, no caveat bar.
3. What we compared (9 receipts, 6 fields, 3 approaches; 51 of 54 fields scored)
4. **Rules vs AOAI on the same receipts:** multilingual rules 51.0% / 70.6% vs AOAI prompt v2 96.1%. No
   English-only rules and no original prompt.
5. **The key difference: maintenance**, without the "Not guaranteed" box. That caveat is in the notes;
   diagnosis stays a one-line example.
6. **Advantages and disadvantages.** AOAI speed and tokens now come from the prompt v2 run (6.4 s; about
   962 input / 243 output tokens per receipt).
7. **Beyond six fields, redesigned:** a real hospital receipt's line items → an illustration of the
   structured data AOAI could return (typed from the receipt's OCR text, not AOAI output) → example
   analytics. Marked potential, not yet tested.
8. **Recommendation and next steps,** with a one-line "evidence so far" note.

The limitations slide was removed. Its points are in the speaker notes of slides 2, 4, 6 and 8, and in the
note on slide 8. `scripts/check_deck_v8.py` = the Version 7 checks for 8 slides, plus: no slide shows 88.2%
or the English-only figures, and charts show only the multilingual rules and prompt v2.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v8.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v8.py
```

The Version 7 generator and check are
kept unchanged to reproduce the archived Version 7 deck.

## Version 7: simplified management deck (9 slides)

1. Title
2. **Executive summary:** Azure DI + AOAI prompt v2 96.1% (development result) vs OCR + general
   multilingual rules 51.0–70.6% (51.0% = PaddleOCR Light, 70.6% = Azure DI; retrospective), why AOAI may
   still be needed, and a short caveat. The 88.2% figure is not on this slide.
3. **What we compared:** for each of the 9 receipts, 6 key fields across 3 approaches. A small note says
   51 of 54 fields are scored, because 3 receipts have no doctor registration number.
4. **A fairer comparison:** multilingual rules 51.0% / 70.6% vs AOAI with its original prompt 88.2%, and
   what rules would still need. No English-only bars.
5. The key difference: maintenance
6. Advantages and disadvantages
7. Beyond six fields (potential, not yet benchmarked)
8. Limits of this evidence
9. Recommendation and next steps

The Version 6 "Improving AOAI" slide was removed. English-only and tuned rule figures are not shown.
`scripts/check_deck_v7.py` = the Version 6 checks for 9 slides, plus: no 88.2% or English-only rule figure
on the executive summary.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v7.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v7.py
```

The Version 6 generator and check are kept
unchanged to reproduce the archived Version 6 deck.

## Version 6: Version 5 plus the multilingual rules baseline

The same 10 slides as Version 5. Slide 4, "Initial Results and a Fairer Rules Baseline", now shows the
retrospective multilingual rules baseline (`python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md`)
next to the first, English-only rules. The baseline is the original rules plus common Chinese labels,
fixed before scoring:

| | English-only rules | With Chinese labels (retrospective) | AOAI, original prompt |
|---|---|---|---|
| PaddleOCR Light | 37.3% | 51.0% | |
| Azure DI | 41.2% | 70.6% | 88.2% |

Every slide that shows these figures labels them as retrospective: the labels were added after these
receipts were examined, so they are not an independent test. The answer, pros and cons, and limitations
slides cite the baseline too.

`scripts/check_deck_v6.py` = the Version 5 checks, plus: chart values may also be the baseline figures,
and a slide showing them must say "retrospective".

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v6.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v6.py
```

The Version 5 generator and check are
kept unchanged to reproduce the archived Version 5 deck.

## Version 5: the management version (10 slides)

A shorter version of Version 4 for management. The question: is OCR with hand-written extraction rules
enough to replace Azure OpenAI, and what value does AOAI add?

1. Title · 2. The answer in brief · 3. What we compared · 4. Initial results (37.3% / 41.2% / 88.2%; the
first rules had no Chinese labels) · 5. Improving AOAI: clearer instructions (96.1%, development result;
the four fixes and AOAI accuracy per field) · 6. The key difference: maintenance (rules anticipate every
case in code; AOAI works from plain-language instructions, not guaranteed for unseen layouts; the
diagnosis check as a short example where rules were enough) · 7. Advantages and disadvantages (cost,
speed, accuracy, maintenance, flexibility, auditability, reliability) · 8. Beyond six fields (potential,
not yet benchmarked) · 9. Limits of this evidence · 10. Recommendation and next steps.

**Changes from Version 4:** the tuned rule accuracies (88.2% and 86.3%, and the rules' per-field figures
after tuning) are removed everywhere, because the rules were adapted by hand to these receipts. The
per-field slide now compares AOAI's original prompt with prompt v2 only. Diagnosis detection is a
one-line example rather than a slide.

`scripts/check_deck_v5.py` enforces: 10 slides; no Heavy; no tuned rule figure in slides, tables, charts
or notes (it fails on the Version 4 deck); charts show only the initial results; 96.1% only with a
development label; original rule figures only with the missing Chinese support; the "beyond six
fields" slide marked as potential.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v5.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v5.py
```

The Version 4
generator and check are kept unchanged to reproduce the archived Version 4 deck.

## Version 4: a redesign around one question

**Can OCR with extraction rules replace Azure OpenAI for medical receipts, and if not, why is AOAI
needed?** The answer comes first, then the evidence. Every slide carries an evidence tag: measured
before tuning, measured on the development set, or potential (not yet tested).

1. Title · 2. The answer in brief · 3. What we compared · 4. Before tuning (chart; why the rules scored
low) · 5. After tuning (chart; effort of each change) · 6. Accuracy by field · 7. What prompt v2 changed ·
8. Rules vs AOAI scorecard (accuracy, speed, cost, effort, side effects, new layouts, control) ·
9. Diagnosis-comment check (when rules are enough) · 10. Beyond six fields (potential only) ·
11. Limits of what we know · 12. Recommendation and next steps.

`scripts/check_deck_v4.py` enforces: 12 slides; no Heavy; chart values match the score files; original
rule figures only with the missing Chinese support explained; development figures only with a
development label; the "beyond six fields" slide marked as potential and not yet tested.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v4.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v4.py
```

The Version 3
generator and check (`generate_ppt_v3.py`, `check_deck_v3.py`) are kept unchanged to reproduce the
archived Version 3 deck (use `--output` to write it elsewhere).

## Version 3: what changed from Version 2

Version 3 tells the story in two steps; the OCR code, results and ground truth are unchanged.
- **Slide 3, Initial Results:** every approach before any tuning on the nine Version 2 receipts
  (PaddleOCR Light + rules 37.3%, Azure DI + rules 41.2%, Azure DI + AOAI 88.2%). The original rules
  had no Chinese labels, so this compares initial implementations, not maximum capability.
- **Slide 4, How We Improved Accuracy:** one table of what was changed in each approach, the resulting
  development scores (88.2%, 86.3%, AOAI prompt v2 96.1%) and fields fixed / broken (rules +27/−1 and
  +24/−1, prompt +4/−0), plus the effort of changing rules vs a prompt. Labelled as development results,
  not independent validation.
- **Slide 5, Accuracy by Field:** the three tuned approaches per field, every count taken from
  `scores_aoai_improved/detail.csv` and checked against `summary.csv`; labelled as development results.
  Registration number has 6 applicable receipts, every other field 9.
- **Slide 6, What Changed in AOAI Prompt V2:** the four fields prompt v2 fixed (88.2% → 96.1%), the
  original and new replies, and the prompt v2 wording behind each (checked against `SYSTEM_PROMPT_V2`).
  The fixes are already in the model's own reply, in the plain-text, row-layout and photo runs alike; the
  Python checks changed no value. So the credit goes to the prompt wording only.
- **Later slides do not repeat these figures.** The "AOAI replaces the rule layer" diagram was dropped
  (slide 2 already shows the two steps); slides 8–10 focus on effort, maintenance and new layouts.
- **The small held-out Version 1 check** is mentioned only in the speaker notes, and is not used to say
  that either approach generalises better.
- **PaddleOCR Heavy is removed everywhere** (discontinued in October 2026).

`scripts/check_deck_v3.py` enforces: 12 slides; no Heavy; every per-field count on slide 5; original rule figures only on a slide that explains the
missing Chinese support; 86.3% and 96.1% only on a slide that calls them development results.

## Generate the Version 3 deck

This reads committed results only: no OCR, scoring or Azure calls. Run it anywhere that has
python-pptx and Pillow; the committed deck was built on a Mac. From the repository root:

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v3.py --force   # deck + receipt crops in assets_v2/
python3 ppt/ocr_benchmark/scripts/check_deck_v3.py              # verifies figures and labels; writes previews/deck_text.md
```

Without `--force`, the script won't overwrite an existing deck. It always refuses to write
into `archive/` or `template/`. `scripts/generate_ppt_v2.py` and `check_deck_v2.py` are kept
unchanged to reproduce the archived Version 2 deck (use `--output` to write it elsewhere).


## Previews

These need LibreOffice and Poppler:

```bash
cd ppt/ocr_benchmark
soffice --headless --convert-to pdf --outdir previews current/OCR_Benchmark_V16.pptx
mv previews/OCR_Benchmark_V16.pdf previews/OCR_Benchmark_V16_preview.pdf
pdftoppm -png -r 80 previews/OCR_Benchmark_V16_preview.pdf previews/slide
```

LibreOffice may substitute fonts, so the preview is for review. PowerPoint renders Arial and
Microsoft JhengHei (Traditional Chinese).

## Outstanding before distribution

1. **Prices.** Compute rate, Document Intelligence page price and gpt-5-mini token prices are
   still unconfirmed; Version 16 main slide 5 says costs still need confirming.
2. **Sensitivity label.** The deck carries the template's **[AIA – PUBLIC]** label. Apply the
   correct label in PowerPoint (Home → Sensitivity) before sharing.
3. **Presenter name and date,** if required.
