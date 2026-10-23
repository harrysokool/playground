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

- Results: One Fair Accuracy Figure
- ‹#›
- AI extraction reached 88.2% with a prompt written before these receipts: the only untuned result.
  | Approach | Accuracy (9 receipts) | Time / receipt | How to read it |
  | PaddleOCR Light + rules | Not shown | 13.9 s | Rules tuned by hand on these receipts |
  | Azure DI + rules | Not shown | 3.8 s | Rules tuned by hand on these receipts |
  | Azure DI + AOAI, original prompt | 88.2%  (45/51) | 6.2 s | Prompt written before these receipts |
  | Azure DI + AOAI, prompt v2 | 96.1%*  (49/51) | 6.4 s | Development result: prompt tuned on these receipts |
- Unseen receipts (Version 1): tuning did not carry over. The improved rules scored the same as the original rules on 4 unseen receipts, and prompt v2 the same as the original prompt on 6 receipts. Too few to rank approaches.
- Rules: no accuracy shown (original rules had no Chinese labels; improved rules were tuned on these receipts). * Not independently validated.

  Notes: Accuracy = correct fields / 51 fields present on the 9 receipts. Azure DI + AOAI with the original prompt (88.2%) is the only figure measured before any tuning on these receipts. Prompt v2 (96.1%) was written after reviewing the errors on these receipts, so it is a development result. Rule accuracy is not shown: the original rules had no Chinese labels, so their scores mostly reflect missing language support, and the improved rules were tuned on these receipts. Held-out check on the Version 1 receipts: the improved rules scored the same as the original rules on the 4 unseen receipts (PaddleOCR Light 13/15, Azure DI 10/15 fields), and prompt v2 scored the same as the original prompt on 6 receipts (18/25). Time = average per receipt (PaddleOCR: CPU on Azure ML compute; Azure: API call time incl. network). Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 4

- AOAI Replaces the Manual Rule Layer
- ‹#›
- Both pipelines read the text the same way. Only the step that finds the fields changes.
- Rule-based / PaddleOCR Light + rules / tuned by hand for these layouts
- Read text (OCR) / PaddleOCR Light
- Extraction rules / written and updated by hand (69 → 225 label phrases)
- 6 fields / doctor, patient, total, …
- AI extraction / Azure DI + AOAI / 88.2%, original prompt
- Read text (OCR) / Azure DI
- Azure OpenAI / one prompt, written before these receipts
- 6 fields / doctor, patient, total, …
- replaced by
- AOAI replaces the manual rule layer. It still makes mistakes (6 of 51 fields wrong with the original prompt) and has not yet been tested on a large set of unseen receipts.

  Notes: Rule-based pipeline: OCR text, then hand-written extraction rules. To handle these receipts the rules were rewritten after reviewing their errors (label phrases 69 to 225), mostly to add Chinese and bilingual labels. AI pipeline: the same kind of OCR text is passed to Azure OpenAI (gpt-5-mini) with one prompt; with the original prompt, written before these receipts, it reached 88.2%. So on this benchmark the model did the job the rules had to be tuned to do. It still made mistakes, and it has not been tested on a large set of unseen receipts. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 5

- Example 1: The OCR Was Right, the Rules Were Wrong
- ‹#›
- Both OCR engines read the names. The original rules took the label 病人 as the patient's name.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Patient | 蔡嘉穎 | ✗ 病人 | ✓ 蔡嘉穎 | ✓ 蔡嘉穎 |
  | Doctor | Dr. Siu Ka Wai | ✗ not found | ✓ Dr. Siu Ka Wai | ✓ Dr. Siu Ka Wai |
- Original rules: took the Chinese label 病人 ("patient") as the patient's name. / Improved rules: fixed by adding bilingual labels by hand. / AOAI: correct with its original prompt; no change needed.
- Bilingual medical centre receipt. Rules shown on PaddleOCR Light text; Azure DI with the original rules made the same patient error. DI + AOAI = original prompt.

  Notes: Receipt 8 (medical centre). Both OCR engines read the patient name and the doctor's name (checked in the raw OCR). The original rules matched 'Patient' and took the Chinese half of the label, 病人, as the name. The improved rules needed bilingual labels added by hand. AOAI, with its original prompt, read the fields correctly (6 of 6 fields on this receipt). Values: rules on PaddleOCR Light text; detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

- Example 2: Every New Layout Meant Manual Rule Work
- ‹#›
- Each label wording was added by hand, one change broke a receipt, and the tuning did not carry over.
- Chinese medicine receipt: original rules 0/6 fields; after Chinese labels were added by hand 6/6; DI + AOAI 6/6 (original prompt).
- 69 → 225 / label phrases in the rules, added by hand after reviewing the errors
- 369303 → 380048 / vet invoice receipt number: correct before the changes, wrong after (a regression)
- No gain / on 4 unseen receipts: the tuned rules scored the same as the original rules
- With its original prompt, DI + AOAI needed none of these changes for these receipts. Whether that holds for new layouts still needs to be tested.

  Notes: Receipt 4 (Chinese medicine): the OCR read every value, but the original rules only knew English labels (0 of 6 fields). After adding Chinese labels by hand: 6 of 6. DI + AOAI with its original prompt: 6 of 6. The label vocabulary grew from 69 to 225 phrases (counted in extraction_general.py and extraction_improved.py). On the vet invoice (receipt 9) the original rules found receipt number 369303; after the changes they return 380048. On the 4 Version 1 receipts not used for tuning, the improved rules scored the same as the original rules (PaddleOCR Light 13/15, Azure DI 10/15 fields). Whether AOAI needs less maintenance on new layouts has not been tested yet. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 7

- Example 3: AOAI Still Makes Mistakes
- ‹#›
- On the vet invoice, the improved rules and AOAI each got a different field wrong.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Receipt no. | 369303 | ✓ 369303 | ✗ 380048 | ✓ 369303 |
  | Patient | Fuk Jai | ✗ not found | ✗ not found | ✓ Fuk Jai |
  | Total | 1361 | ✓ 1361.0 | ✓ 1361.0 | ✗ 1361.5 |
- Improved rules: picked the payment receipt number. / Rules: the OCR read "FPatient:", so the patient label was missed. / AOAI (original prompt): picked the sub total. Prompt v2 fixes it, but was tuned on this receipt.

  Notes: Receipt 9 (vet invoice). The improved rules now take the payment table's 'Receipt #' (380048) instead of the invoice number. Both OCR engines read 'FPatient:' (a stray mark merged into the label), so no rule matched the patient label; AOAI still found the name. AOAI with the original prompt chose the sub total (1361.50) instead of the total (1361.00). Prompt v2 returns the correct total, but it was written after reviewing this error. Across all 9 receipts AOAI got 6 of 51 fields wrong with the original prompt and 2 with prompt v2 (development result). Values: detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 8

- Development Effort and Maintenance
- ‹#›
- The difference is the manual work to handle each layout, and to keep it working.
  |  | PaddleOCR Light + rules | Azure DI + AOAI |
  | Accuracy (9 receipts) | Not a fair measure: rules tuned on these receipts | 88.2% original prompt; 96.1% prompt v2 (development) |
  | Effort to get there | Rules rewritten by hand after reviewing errors on these receipts | None for the original prompt; one revision for prompt v2 |
  | Extraction logic | 69 → 225 label phrases to maintain | One prompt and a few general checks |
  | Unseen receipts | Tuning gave no gain (4 receipts) | Prompt v2 gave no gain (6 receipts) |
  | Errors seen | A rule change broke a receipt that was already correct | 6 of 51 fields wrong (original prompt), e.g. a total |
  | Time and running cost | 13.9 s, own compute, no API fee | 6.2 s, Azure fees per receipt (to confirm) |
- The main question is not API price but who maintains the extraction logic as layouts change. Lower maintenance for AOAI is implied by this benchmark, not yet proven.

  Notes: Accuracy: Azure DI + AOAI 88.2% with the original prompt; 96.1% with prompt v2, a development result because the prompt was revised on these receipts. No accuracy is shown for the rules: the original rules had no Chinese labels, and the improved rules were tuned on these 9 receipts. Unseen receipts: the improved rules scored the same as the original rules on 4 Version 1 receipts, and prompt v2 the same as the original prompt on 6 (18/25). Lower maintenance for AOAI is the key implication of this benchmark, not a result proven in production. Running cost: DI page plus about 602 input / 263 output gpt-5-mini tokens per receipt (original prompt); prices are not yet confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 9

- Manual Rules vs. AI Extraction: Pros and Cons
- ‹#›
- "Measured" = this benchmark; the rest is expected.
- Manual extraction rules (PaddleOCR Light)
- New formats need manual rule updates, which can break working cases and add maintenance and testing.
- Pros / Full control; transparent and predictable on formats the rules know. / No API fees: open-source OCR on our own compute. / Measured: the OCR read the values; the misses were missing labels.
- Cons / Each new format or language needs rule updates by hand. / Measured: a rule change broke a receipt that was already correct. / Measured: 69 → 225 label phrases; no gain on unseen receipts.
- AI extraction (Azure DI + AOAI)
- Less rule maintenance expected: accuracy depends mainly on the AI model, OCR output and prompt.
- Pros / Measured: 88.2% with a prompt written before these receipts. / Reads varied formats using existing model capabilities. / Measured: faster, 6.2 s vs 13.9 s per receipt.
- Cons / Measured: still wrong on 6 of 51 fields, e.g. a total. / Less direct control: results depend on model, OCR, prompt. / API fees; needs validation, monitoring and prompt upkeep.
- Neither is maintenance free. The difference is where the effort sits: rules for every layout, or one prompt plus validation.

  Notes: Measured: rules grew from 69 to 225 label phrases while being tuned on these 9 receipts; vet invoice receipt number 369303 correct before tuning, 380048 after; on 4 unseen receipts the tuned rules scored the same as the original rules. Azure DI + AOAI 88.2% with the original prompt; 6 of 51 fields wrong, e.g. vet invoice total 1361.5 although the Azure DI text contains the correct 1361.00; 6.2 s vs 13.9 s per receipt. Expected, not measured: that new formats need rule updates, that AOAI needs less rule maintenance, control, API fees and the upkeep AOAI still needs (validation, monitoring, prompt). AOAI is not maintenance free. Prices are not yet confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 10

- Conclusion and Next Steps
- ‹#›
- The real trade-off: maintain extraction rules ourselves, or let AI replace that layer.
- Azure DI + AOAI reached 88.2% with a prompt written before these receipts. A tuned prompt reached 96.1% on the same receipts: a development result, not validated. / The rules worked only after hand-tuning for these layouts, and the tuning did not help on unseen receipts. / So the choice is whether to keep writing and maintaining extraction rules, or to use AI for that layer.
- 1. Freeze both / Lock the improved rules and AOAI prompt v2.
- 2. Test on unseen receipts / 30+ real, anonymised receipts. Measure accuracy and count the rule changes needed.
- 3. Then compare cost / Compute, Document Intelligence pages and gpt-5-mini tokens.
- Limitation: 9 receipts, mostly printed mock receipts; the rules and prompt v2 were tuned on them. AOAI still makes mistakes and has not been tested on a large unseen set.

  Notes: Main finding: Azure DI + AOAI reached 88.2% with a prompt written before these receipts; a prompt revised on them reached 96.1% on the same receipts (development result, not validated). The rules handled these receipts only after being rewritten for them, and that tuning gave no gain on 4 unseen receipts. The benchmark is small (9 receipts), so this is not a production decision. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
