# OCR_Benchmark_V3.pptx: text and notes


## Slide 1

- Can Azure OpenAI replace hand-written extraction rules? / 9 receipts · 6 fields · manual rules vs AI extraction
- Medical Receipt OCR Benchmark

  Notes: Objective: compare hand-written extraction rules with AI extraction (Azure OpenAI) for six fields on medical receipts: the development effort, the maintenance, and the ability to handle different receipt layouts. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 2

- What We Tested
- ‹#›
- 9 receipts with different layouts and languages. Each approach reads the text, then finds 6 fields.
- English
- Bilingual
- Chinese
  | Approach | 1. Read text | 2. Find fields |
  | PaddleOCR Light | Open-source OCR | Rules |
  | Azure DI | Azure OCR | Rules |
  | Azure DI + AOAI | Azure OCR | Azure OpenAI |
- Fields: doctor, registration no., patient, receipt no., service date, total. 51 fields scored.

  Notes: Receipts: English, bilingual and Traditional Chinese layouts. Fields: doctor, registration number, patient, receipt number, service date, total. 51 fields were present on the receipts and scored. Step 1 (text recognition, OCR) turns the photo into text; step 2 (field extraction) picks the six values from that text, either with hand-written rules or with Azure OpenAI. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 3

- Initial Results
- ‹#›
- Before any tuning on these 9 receipts, AI extraction was far ahead of the first rule sets.
  | Approach | Accuracy | Time / receipt |
  | PaddleOCR Light + rules | 37.3%  (19/51) | 13.9 s |
  | Azure DI + rules | 41.2%  (21/51) | 3.8 s |
  | Azure DI + AOAI | 88.2%  (45/51) | 6.2 s |
- Why the rules scored low / The original rules knew English labels only: no Chinese or bilingual labels. / On Chinese and bilingual receipts the OCR read the values, but the rules could not find them. / So this compares initial implementations, not the best each approach can do.
- Accuracy = correct fields out of 51. The AOAI prompt was written before these receipts. All approaches processed all 9 receipts.

  Notes: Accuracy = correct fields / 51 fields present on the 9 Version 2 receipts, before anything was changed for them. The original extraction rules knew English labels only, with no Chinese or bilingual labels, although four of the receipts are Chinese or bilingual. On those receipts the OCR read the values but the rules could not find them (see example 1). The AOAI prompt was written before these receipts existed. So this compares initial implementations, not the maximum capability of each approach. Time = average per receipt (PaddleOCR: CPU on Azure ML compute; Azure: API call time incl. network). Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 4

- How We Improved Accuracy
- ‹#›
- Both approaches improved after reviewing these receipts. Changing rules took far more work than changing a prompt.
  | Approach | What we changed | Development score | Fixed / broke |
  | PaddleOCR Light + rules | Rewrote the rules by hand: Chinese and bilingual labels, distractor labels, layouts (69 → 225 label phrases) | 88.2%  (45/51) | +27 / −1 |
  | Azure DI + rules | The same rule changes, on Azure DI text | 86.3%  (44/51) | +24 / −1 |
  | Azure DI + AOAI, prompt v2 | Revised the prompt wording: clearer definitions of each field | 96.1%  (49/51) | +4 / −0 |
- Changing rules / Code and vocabulary for every new wording or language, then a retest of every receipt. One change broke a receipt that was already correct.
- Changing the AI prompt / Plain-language edits to one prompt, then a rerun. No field broke on these receipts.
- Development results: every change was made after reviewing these 9 receipts, so these scores are not independent validation.

  Notes: All changes were made after reviewing the errors on these 9 receipts, so the scores are development results, not independent validation. Rules: rewritten by hand (label phrases 69 to 225: Chinese and bilingual labels, distractor labels, layout handling); on PaddleOCR Light text this fixed 27 fields and broke 1, on Azure DI text it fixed 24 and broke 1. AOAI: prompt v2 with clearer field definitions fixed 4 fields and broke 0. The row layout and Python checks added at the same time changed no result (see the prompt v2 slide). A small held-out check on Version 1 receipts (4-6 receipts, mostly handwritten) is too small to say whether either approach generalises better, so it is not shown on the slides. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 5

- Accuracy by Field (Development Results)
- ‹#›
- After tuning, all three approaches miss the same two fields; the rules also miss patient and receipt numbers.
  | Field | Receipts | PaddleOCR Light + rules | Azure DI + rules | Azure DI + AOAI, prompt v2 |
  | Doctor | 9 | 88.9%  (8/9) | 88.9%  (8/9) | 88.9%  (8/9) |
  | Registration no. | 6* | 100.0%  (6/6) | 100.0%  (6/6) | 100.0%  (6/6) |
  | Patient | 9 | 77.8%  (7/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | Receipt no. | 9 | 77.8%  (7/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | Service date | 9 | 88.9%  (8/9) | 88.9%  (8/9) | 88.9%  (8/9) |
  | Total | 9 | 100.0%  (9/9) | 88.9%  (8/9) | 100.0%  (9/9) |
- Development results after tuning on these 9 receipts, not independent validation. * Registration number is printed on 6 of the 9 receipts; every other field on all 9.

  Notes: Development results after tuning on these 9 receipts, not independent validation. Counts from results/v2/scores_aoai_improved/detail.csv, checked against the per-field percentages in summary.csv. Registration number is printed on 6 of the 9 receipts, so it has 6 applicable receipts; every other field has 9. All three approaches miss the vet invoice's doctor (two practitioners, and the OCR misread the signature) and the pharmacy receipt's service date (print date vs item date, an open ground-truth question). The rules also miss patient and receipt number on the vet invoice and the pharmacy receipt (an OCR artefact on the label, a payment receipt number, no labels); Azure DI + rules also misses one total. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

- What Changed in AOAI Prompt V2
- ‹#›
- 88.2% → 96.1%: four fields fixed, all by clearer prompt wording. Nothing else changed a result.
  | Field fixed | Original prompt replied | Prompt v2 wording added | Prompt v2 replied |
  | Registration no. GP receipt | ✗ MBBS (HK) · Reg. No. M17642 | “the identifier only, without its label” | ✓ M17642 |
  | Doctor Dental receipt | ✗ Dr. Ho Ching Yee, BDS (HK) | “Leave out qualifications and post-nominals” | ✓ Dr. Ho Ching Yee |
  | Doctor Pharmacy receipt | ✗ Dr Jessica Sterenborg Picton Medical Centre | “clinic, hospital or practice names” | ✓ Dr Jessica Sterenborg |
  | Total Vet invoice | ✗ HKD 1361.50 | “after any discounts, rounding or other adjustments” | ✓ HKD 1361.00 |
- Prompt wording / 4 fields fixed
- Python checks / changed 0 values
- OCR row layout / plain text also 49/51
- Photo attached / also 49/51
- Development result: prompt v2 was written after reviewing these errors. Still wrong: the vet invoice doctor and the pharmacy service date.

  Notes: Original prompt 88.2% (45/51); prompt v2 96.1% (49/51), a development result because prompt v2 was written after reviewing these errors. The four fixes are in the model's own reply (before any Python check) in all three prompt v2 runs. Credit: prompt wording only. The Python checks changed 0 values; plain-text OCR input (49/51) scores the same as the row layout (49/51); attaching the photo also scores 49/51. Remaining errors: the vet invoice doctor (two practitioners; OCR misread the signature) and the pharmacy service date (open ground-truth question). Prompt text: receipt_bench/di_aoai.py (SYSTEM_PROMPT and SYSTEM_PROMPT_V2, commit 034d7d5). Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 7

- Example 1: The OCR Was Right, the Rules Were Wrong
- ‹#›
- Both OCR engines read the names. The original rules took the label 病人 as the patient's name.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Patient | 蔡嘉穎 | ✗ 病人 | ✓ 蔡嘉穎 | ✓ 蔡嘉穎 |
  | Doctor | Dr. Siu Ka Wai | ✗ not found | ✓ Dr. Siu Ka Wai | ✓ Dr. Siu Ka Wai |
- Original rules: took the Chinese label 病人 ("patient") as the patient's name. / Improved rules: fixed by adding bilingual labels by hand. / AOAI: correct with its original prompt; no change needed.
- Bilingual medical centre receipt. Rules shown on PaddleOCR Light text; Azure DI with the original rules made the same patient error. DI + AOAI = original prompt.

  Notes: Receipt 8 (medical centre). Both OCR engines read the patient name and the doctor's name (checked in the raw OCR). The original rules matched 'Patient' and took the Chinese half of the label, 病人, as the name. The improved rules needed bilingual labels added by hand. AOAI, with its original prompt, read the fields correctly (6 of 6 fields on this receipt). Values: rules on PaddleOCR Light text; detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 8

- Example 2: Every New Layout Meant Manual Rule Work
- ‹#›
- Each label wording was added by hand, and one change broke a receipt that was already correct.
- Chinese medicine receipt: original rules 0/6 fields; after Chinese labels were added by hand 6/6; DI + AOAI 6/6 (original prompt).
- 69 → 225 / label phrases in the rules, added by hand after reviewing the errors
- 369303 → 380048 / vet invoice receipt number: correct before the changes, wrong after (a regression)
- New layouts / will likely need more rule changes and a retest of every receipt
- With its original prompt, DI + AOAI needed none of these changes for these receipts. Whether that holds for new layouts still needs to be tested.

  Notes: Receipt 4 (Chinese medicine): the OCR read every value, but the original rules only knew English labels (0 of 6 fields). After adding Chinese labels by hand: 6 of 6. DI + AOAI with its original prompt: 6 of 6. The label vocabulary grew from 69 to 225 phrases (counted in extraction_general.py and extraction_improved.py). On the vet invoice (receipt 9) the original rules found receipt number 369303; after the changes they return 380048. Whether AOAI needs less maintenance on new layouts has not been tested yet. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 9

- Example 3: AOAI Still Makes Mistakes
- ‹#›
- On the vet invoice, the improved rules and AOAI each got a different field wrong.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Receipt no. | 369303 | ✓ 369303 | ✗ 380048 | ✓ 369303 |
  | Patient | Fuk Jai | ✗ not found | ✗ not found | ✓ Fuk Jai |
  | Total | 1361 | ✓ 1361.0 | ✓ 1361.0 | ✗ 1361.5 |
- Improved rules: picked the payment receipt number. / Rules: the OCR read "FPatient:", so the patient label was missed. / AOAI (original prompt): picked the sub total instead of the total.

  Notes: Receipt 9 (vet invoice). The improved rules now take the payment table's 'Receipt #' (380048) instead of the invoice number. Both OCR engines read 'FPatient:' (a stray mark merged into the label), so no rule matched the patient label; AOAI still found the name. AOAI with the original prompt chose the sub total (1361.50) instead of the total (1361.00). Prompt v2 returns the correct total, but it was written after reviewing this error. Values: detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 10

- Development Effort and Maintenance
- ‹#›
- The difference is the manual work to handle each layout, and to keep it working.
  |  | PaddleOCR Light + rules | Azure DI + AOAI |
  | Effort to improve | Rules rewritten by hand after reviewing errors on these receipts | One prompt revision after reviewing errors |
  | What a change looks like | Code and label lists (69 → 225 phrases) | Prompt wording and a few general checks |
  | Side effects seen | 1 correct field broken by the rule changes | 0 correct fields broken by the prompt revision |
  | New receipt layouts | Likely more rule updates and a regression test of every receipt | Possibly no change; not yet tested |
  | Time and running cost | 13.9 s, own compute, no API fee | 6.2 s, Azure fees per receipt (to confirm) |
- The main question is not API price but who maintains the extraction logic as layouts change. Lower maintenance for AOAI is implied by this benchmark, not yet proven.

  Notes: Effort: the rules were rewritten by hand after reviewing the errors on these receipts (label phrases 69 to 225); the AOAI prompt was revised once. Side effects on these receipts: the rule changes broke 1 correct field on PaddleOCR Light text, the prompt revision broke 0. Lower maintenance for AOAI on new layouts is the key implication of this benchmark, not a result proven in production. Running cost: DI page plus about 602 input / 263 output gpt-5-mini tokens per receipt (original prompt); prices are not yet confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 11

- Manual Rules vs. AI Extraction: Pros and Cons
- ‹#›
- "Measured" = this benchmark; the rest is expected.
- Manual extraction rules (PaddleOCR Light)
- New formats need manual rule updates, which can break working cases and add maintenance and testing.
- Pros / Full control; transparent and predictable on formats the rules know. / No API fees: open-source OCR on our own compute. / Measured: the OCR read the values; the misses were missing labels.
- Cons / Each new format or language needs rule updates by hand. / Measured: a rule change broke a receipt that was already correct. / Measured: 69 → 225 label phrases added by hand.
- AI extraction (Azure DI + AOAI)
- Less rule maintenance expected: accuracy depends mainly on the AI model, OCR output and prompt.
- Pros / Measured: highest accuracy before any tuning on these receipts. / Reads varied formats using existing model capabilities. / Measured: faster, 6.2 s vs 13.9 s per receipt.
- Cons / Measured: still makes mistakes, e.g. a sub total taken as the total. / Less direct control: results depend on model, OCR, prompt. / API fees; needs validation, monitoring and prompt upkeep.
- Neither is maintenance free. The difference is where the effort sits: rules for every layout, or one prompt plus validation.

  Notes: Measured: rules grew from 69 to 225 label phrases while being tuned on these 9 receipts; vet invoice receipt number 369303 correct before tuning, 380048 after. Azure DI + AOAI had the highest accuracy before any tuning; it still made mistakes, e.g. vet invoice total 1361.5 although the Azure DI text contains the correct 1361.00; 6.2 s vs 13.9 s per receipt. Expected, not measured: that new formats need rule updates, that AOAI needs less rule maintenance, control, API fees and the upkeep AOAI still needs (validation, monitoring, prompt). AOAI is not maintenance free. Prices are not yet confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 12

- Conclusion and Next Steps
- ‹#›
- The real trade-off: maintain extraction rules ourselves, or let AI replace that layer.
- Initial implementations: AI extraction led by a wide margin, mainly because the first rules had no Chinese support. / After reviewing these receipts both improved. Rules needed code and vocabulary changes; AI needed one prompt revision. Neither is validated on unseen receipts. / So the choice is whether to keep writing and maintaining extraction rules, or to use AI for that layer.
- 1. Freeze both / Lock the improved rules and AOAI prompt v2.
- 2. Test on unseen receipts / 30+ real, anonymised receipts. Measure accuracy and count the rule changes needed.
- 3. Then compare cost / Compute, Document Intelligence pages and gpt-5-mini tokens.
- Limitation: 9 receipts, mostly printed mock receipts; the rules and prompt v2 were tuned on them. AOAI still makes mistakes and has not been tested on a large unseen set.

  Notes: Initial implementations: Azure DI + AOAI 88.2%, rules 37.3% and 41.2%, the gap mostly from missing Chinese support in the rules. After reviewing these receipts: rules 88.2% and 86.3%, AOAI prompt v2 96.1%, all development results. The benchmark is small (9 receipts), so this is not a production decision. A small held-out check on Version 1 receipts (4-6 receipts, mostly handwritten) is too small to say whether either approach generalises better, so it is not shown on the slides. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
