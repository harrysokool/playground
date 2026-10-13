# OCR_Benchmark_V2.pptx: text, chart data and notes


## Slide 1

- Can open-source OCR with rules match Azure AI at extracting receipt fields? / 9 receipts · 6 fields · 4 approaches
- Medical Receipt OCR Benchmark

  Notes: Objective: compare open-source OCR plus extraction rules with Azure Document Intelligence plus Azure OpenAI for extracting six fields from medical receipts, on accuracy, speed, cost drivers and maintenance. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

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

  Notes: Receipts: English, bilingual and Traditional Chinese layouts. Fields: doctor, registration number, patient, receipt number, service date, total. 51 fields were present on the receipts and scored. Step 1 (text recognition, OCR) turns the photo into text; step 2 (field extraction) picks the six values from that text. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 3

- Results: Field Accuracy and Speed
- ‹#›
- Improving the rules raised PaddleOCR Light from 37.3% to 88.2%. AOAI reached 88.2% without changes.
  | Approach | Original rules | Improved rules* | Time per receipt |
  | PaddleOCR Light | 37.3%  (19/51) | 88.2%  (45/51) | 13.9 s |
  | PaddleOCR Heavy | 29.4%  (15/51) | 64.7%  (33/51) | 53.3 s |
  | Azure DI | 41.2%  (21/51) | 86.3%  (44/51) | 3.8 s |
  | Azure DI + AOAI | 88.2%  (45/51) | Not applicable (prompt unchanged) | 6.2 s |
- * Tuned using these 9 receipts, so not a measure of accuracy on new receipts. Accuracy = correct fields out of 51. All approaches processed all 9 receipts.

  Notes: Accuracy = correct fields / 51 fields present on the 9 receipts. Original and improved rules read the same OCR text. Improved rules were tuned using these 9 receipts. The AOAI prompt was not changed. Time = average per receipt (PaddleOCR: CPU on Azure ML compute; Azure: API call time incl. network). Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 4

- Why Accuracy Improved: The Rules, Not the OCR
- ‹#›
- The OCR read the text correctly. The original rules picked the wrong text.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Patient | 蔡嘉穎 | ✗ 病人 | ✓ 蔡嘉穎 | ✓ 蔡嘉穎 |
  | Doctor | Dr. Siu Ka Wai | ✗ not found | ✓ Dr. Siu Ka Wai | ✓ Dr. Siu Ka Wai |
- Original rules: took the Chinese label 病人 ("patient") as the patient's name. / Improved rules: added bilingual labels, so the label and the value are kept apart.
- Bilingual medical centre receipt. Rules shown on PaddleOCR Light text; Azure DI with the original rules made the same patient error.

  Notes: Receipt 8 (medical centre). Both OCR engines read the patient name and the doctor's name (checked in the raw OCR). The original rules matched 'Patient' and took the Chinese half of the label, 病人, as the name. The improved rules recognise bilingual labels. AOAI read the fields correctly with its unchanged prompt. Values: rules on PaddleOCR Light text; detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 5

- The Trade-off: Rules Need Manual Maintenance
- ‹#›
- High accuracy came from rewriting the rules by hand, and one fix broke another receipt.
- Chinese medicine receipt: original rules 0/6 fields, improved rules 6/6.
- 69 → 225 / label phrases in the rules, added by hand after reviewing the errors
- 369303 → 380048 / vet invoice receipt number: correct before the changes, wrong after (a regression)
- New layouts / may need more rule changes and retesting of every receipt
- AOAI used the same prompt for every receipt. Whether that means less maintenance on new layouts still needs to be tested.

  Notes: Receipt 4 (Chinese medicine): the OCR read every value, but the original rules only knew English labels (0 of 6 fields). After adding Chinese labels: 6 of 6. The label vocabulary grew from 69 to 225 phrases (counted in extraction_general.py and extraction_improved.py). On the vet invoice (receipt 9) the original rules found receipt number 369303; after the changes they return 380048. Whether AOAI needs less maintenance on new layouts has not been tested yet. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 6

- Where Errors Remain: Both Approaches Make Mistakes
- ‹#›
- On the vet invoice, the improved rules and AOAI each got a different field wrong.
  | Field | Correct | Original rules | Improved rules | DI + AOAI |
  | Receipt no. | 369303 | ✓ 369303 | ✗ 380048 | ✓ 369303 |
  | Patient | Fuk Jai | ✗ not found | ✗ not found | ✓ Fuk Jai |
  | Total | 1361 | ✓ 1361.0 | ✓ 1361.0 | ✗ 1361.5 |
- Improved rules: picked the payment receipt number. / Rules: the OCR read "FPatient:", so the patient label was missed. / AOAI: picked the sub total instead of the total.

  Notes: Receipt 9 (vet invoice). The improved rules now take the payment table's 'Receipt #' (380048) instead of the invoice number. Both OCR engines read 'FPatient:' (a stray mark merged into the label), so no rule matched the patient label; AOAI still found the name. AOAI chose the sub total (1361.50) instead of the total (1361.00). Values: detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 7

- Practical Comparison of the Two Candidates
- ‹#›
- Similar accuracy on these receipts; they differ in cost, speed and how new layouts are handled.
  |  | PaddleOCR Light + improved rules | Azure DI + AOAI |
  | Accuracy (these 9 receipts) | 88.2% (45/51), tuned | 88.2% (45/51), prompt unchanged |
  | Time per receipt | 13.9 s | 6.2 s |
  | Where it runs | Our own compute, offline | Azure cloud services |
  | Cost per receipt | CPU time only, no API fee | DI page + about 602 input / 263 output tokens (prices to confirm) |
  | New receipt layouts | Edit rules and retest | Same prompt; still to be tested |
  | Main risk | Maintenance and regressions | API cost and model variability |
- Both approaches read the receipt text well; the differences are in finding the fields.

  Notes: Accuracy and time from summary.csv. AOAI tokens are averages over the 9 receipts. Prices for compute, Document Intelligence pages and gpt-5-mini tokens are not yet confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.

## Slide 8

- Conclusion and Next Steps
- ‹#›
- Rules can reach high accuracy, but only with ongoing manual work. That is the decision to make.
- The question is not only which method is most accurate. / It is whether we want to keep updating extraction rules each time an unfamiliar receipt layout appears, or pay per request for a model that may handle new layouts without changes.
- 1. Freeze both / Lock the improved rules and the AOAI prompt.
- 2. Test on new receipts / 30+ real, anonymised receipts not seen before. Count the rule changes needed.
- 3. Confirm prices / Compute, Document Intelligence pages and gpt-5-mini tokens.
- Limitation: 9 receipts, mostly printed mock receipts; the improved rules were tuned on them. Candidates for further testing: PaddleOCR Light + improved rules, and Azure DI + AOAI.

  Notes: Main finding: PaddleOCR Light reached 88.2% and Azure DI 86.3% only after the rules were rewritten for these receipts; Azure DI + AOAI reached 88.2% with no change. The benchmark is small (9 receipts) and the improved rules were tuned on it, so this is not a production decision. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (summary.csv, detail.csv) and extraction JSON.
