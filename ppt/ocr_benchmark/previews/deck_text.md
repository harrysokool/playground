# OCR_Benchmark_V2.pptx: text, chart data and notes


## Slide 1

- Can Azure OpenAI replace hand-written extraction rules? / 9 receipts · 6 fields · 4 approaches
- Medical Receipt OCR Benchmark

  Notes: Objective: compare open-source OCR plus extraction rules with Azure Document Intelligence plus Azure OpenAI for extracting six fields from medical receipts: accuracy, the manual effort needed to reach it, and the ongoing maintenance effort. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 2

- What We Tested
- ‹#›
- 9 receipts with different layouts and languages. Each approach reads the text, then finds 6 fields.
- English
- Bilingual
- Chinese
  | Approach | 1. Read text | 2. Find fields |
  | PaddleOCR Light | Open-source OCR | Rules |
  | PaddleOCR Heavy | Open-source OCR | Rules |
  | Azure DI | Azure OCR | Rules |
  | Azure DI + AOAI | Azure OCR | Azure OpenAI |
- Fields: doctor, registration no., patient, receipt no., service date, total. 51 fields scored.

  Notes: Receipts: English, bilingual and Traditional Chinese layouts. Fields: doctor, registration number, patient, receipt number, service date, total. 51 fields were present on the receipts and scored. Step 1 (text recognition, OCR) turns the photo into text; step 2 (field extraction) picks the six values from that text, either with hand-written rules or with Azure OpenAI. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 3

- Results: Same Accuracy, Different Effort
- ‹#›
- Rules reached 88.2% only after manual tuning. DI + AOAI reached 88.2% with its prompt unchanged.
  | Approach | Original rules | Improved rules* | Time per receipt |
  | PaddleOCR Light | 37.3%  (19/51) | 88.2%  (45/51) | 13.9 s |
  | PaddleOCR Heavy | 29.4%  (15/51) | 64.7%  (33/51) | 53.3 s |
  | Azure DI | 41.2%  (21/51) | 86.3%  (44/51) | 3.8 s |
  | Azure DI + AOAI | 88.2%  (45/51) | No rules (prompt unchanged) | 6.2 s |
- * Tuned using these 9 receipts, so not a measure of accuracy on new receipts. Accuracy = correct fields out of 51. All approaches processed all 9 receipts.

  Notes: Accuracy = correct fields / 51 fields present on the 9 receipts. Original and improved rules read the same OCR text. Improved rules were tuned using these 9 receipts. The AOAI prompt was not changed. Time = average per receipt (PaddleOCR: CPU on Azure ML compute; Azure: API call time incl. network). Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 4

- AOAI Replaces the Manual Rule Layer
- ‹#›
- Both pipelines read the text the same way. Only the step that finds the fields changes.
- Rule-based / PaddleOCR Light + improved rules / 88.2% after tuning
- Read text (OCR) / PaddleOCR Light
- Extraction rules / written and updated by hand (69 → 225 label phrases)
- 6 fields / doctor, patient, total, …
- AI extraction / Azure DI + AOAI / 88.2%, prompt unchanged
- Read text (OCR) / Azure DI
- Azure OpenAI / one fixed prompt, not changed for these receipts
- 6 fields / doctor, patient, total, …
- replaced by
- AOAI replaces the manual rule layer. It still makes mistakes (6 of 51 fields wrong) and has not yet been tested on a large set of unseen receipts.

  Notes: Rule-based pipeline: OCR text, then hand-written extraction rules. To reach 88.2% the rules were rewritten after reviewing the errors on these 9 receipts (label phrases 69 to 225). AI pipeline: the same kind of OCR text is passed to Azure OpenAI (gpt-5-mini) with one fixed prompt, which was not changed for these receipts, and it reached 88.2%. So on this benchmark the model did the job the rules were tuned to do. It still made mistakes, and it has not been tested on a large set of unseen receipts. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 5

- Example 1: The OCR Was Right, the Rules Were Wrong
- ‹#›
- Both OCR engines read the names. The original rules took the label 病人 as the patient's name.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Patient | 蔡嘉穎 | ✗ 病人 | ✓ 蔡嘉穎 | ✓ 蔡嘉穎 |
  | Doctor | Dr. Siu Ka Wai | ✗ not found | ✓ Dr. Siu Ka Wai | ✓ Dr. Siu Ka Wai |
- Original rules: took the Chinese label 病人 ("patient") as the patient's name. / Improved rules: fixed by adding bilingual labels by hand. / AOAI: correct with the same prompt; no change needed.
- Bilingual medical centre receipt. Rules shown on PaddleOCR Light text; Azure DI with the original rules made the same patient error.

  Notes: Receipt 8 (medical centre). Both OCR engines read the patient name and the doctor's name (checked in the raw OCR). The original rules matched 'Patient' and took the Chinese half of the label, 病人, as the name. The improved rules needed bilingual labels added by hand. AOAI read the fields correctly with its unchanged prompt (6 of 6 fields on this receipt). Values: rules on PaddleOCR Light text; detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 6

- Example 2: Reaching 88.2% With Rules Took Manual Work
- ‹#›
- Each new language or label wording had to be added by hand, and one change broke another receipt.
- Chinese medicine receipt: original rules 0/6 fields, improved rules 6/6, DI + AOAI 6/6 (prompt unchanged).
- 69 → 225 / label phrases in the rules, added by hand after reviewing the errors
- 369303 → 380048 / vet invoice receipt number: correct before the changes, wrong after (a regression)
- New layouts / will likely need more rule changes and a retest of every receipt
- DI + AOAI needed none of these changes for these receipts. Whether that holds for new layouts still needs to be tested.

  Notes: Receipt 4 (Chinese medicine): the OCR read every value, but the original rules only knew English labels (0 of 6 fields). After adding Chinese labels: 6 of 6. DI + AOAI: 6 of 6 with no prompt change. The label vocabulary grew from 69 to 225 phrases (counted in extraction_general.py and extraction_improved.py). On the vet invoice (receipt 9) the original rules found receipt number 369303; after the changes they return 380048. Whether AOAI needs less maintenance on new layouts has not been tested yet. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 7

- Example 3: AOAI Still Makes Mistakes
- ‹#›
- On the vet invoice, the improved rules and AOAI each got a different field wrong.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Receipt no. | 369303 | ✓ 369303 | ✗ 380048 | ✓ 369303 |
  | Patient | Fuk Jai | ✗ not found | ✗ not found | ✓ Fuk Jai |
  | Total | 1361 | ✓ 1361.0 | ✓ 1361.0 | ✗ 1361.5 |
- Improved rules: picked the payment receipt number. / Rules: the OCR read "FPatient:", so the patient label was missed. / AOAI: picked the sub total instead of the total.

  Notes: Receipt 9 (vet invoice). The improved rules now take the payment table's 'Receipt #' (380048) instead of the invoice number. Both OCR engines read 'FPatient:' (a stray mark merged into the label), so no rule matched the patient label; AOAI still found the name. AOAI chose the sub total (1361.50) instead of the total (1361.00). Across all 9 receipts AOAI got 6 of 51 fields wrong. Values: detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 8

- What It Takes to Reach 88.2%
- ‹#›
- Same accuracy. The difference is the manual work to get there, and to keep it there.
  |  | PaddleOCR Light + improved rules | Azure DI + AOAI |
  | Accuracy (9 receipts) | 88.2% (45/51) | 88.2% (45/51) |
  | Effort to get there | Rules rewritten by hand after reviewing errors on these receipts | None: prompt unchanged |
  | Extraction logic | 69 → 225 label phrases to maintain | One fixed prompt |
  | New receipt layouts | Likely more rule updates and a regression test of every receipt | Possibly no change; not yet tested |
  | Errors seen | 6 wrong fields, incl. one regression caused by tuning | 6 wrong fields, e.g. the vet invoice total |
  | Time and running cost | 13.9 s, own compute, no API fee | 6.2 s, Azure fees per receipt (to confirm) |
- The main question is not API price but who maintains the extraction logic. Lower maintenance for AOAI is implied by this benchmark, not yet proven.

  Notes: Accuracy and time from summary.csv. The improved rules were tuned on these 9 receipts; the AOAI prompt was not changed. Lower maintenance for AOAI is the key implication of this benchmark, not a result proven in production. Running cost: DI page plus about 602 input / 263 output gpt-5-mini tokens per receipt; prices are not yet confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 9

- Conclusion and Next Steps
- ‹#›
- The real trade-off: maintain extraction rules ourselves, or let AI replace that layer.
- PaddleOCR Light + improved rules and Azure DI + AOAI both reached 88.2% on this benchmark. / PaddleOCR Light needed manual rule tuning to get there. Azure DI + AOAI reached the same accuracy without changing its prompt. / So the choice is whether to keep writing and maintaining extraction rules, or to use AI for that layer.
- 1. Freeze both / Lock the improved rules and the AOAI prompt.
- 2. Test on unseen receipts / 30+ real, anonymised receipts. Measure accuracy and count the rule changes needed.
- 3. Then compare cost / Compute, Document Intelligence pages and gpt-5-mini tokens.
- Limitation: 9 receipts, mostly printed mock receipts; the improved rules were tuned on them. AOAI still makes mistakes and has not been tested on a large unseen set.

  Notes: Main finding: PaddleOCR Light reached 88.2% (and Azure DI 86.3%) only after the rules were rewritten for these receipts; Azure DI + AOAI reached 88.2% with no change to its prompt. The benchmark is small (9 receipts) and the improved rules were tuned on it, so this is not a production decision. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.
