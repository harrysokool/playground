# OCR_Benchmark_V2.pptx: text, chart data and notes


## Slide 1

- Traditional OCR with rules vs Azure AI extraction / Version 2 results · 9 receipts · 51 scored fields
- Medical Receipt OCR Benchmark

  Notes: Purpose: decide whether Azure Document Intelligence plus Azure OpenAI is worth its cost and complexity compared with OCR plus fixed rules. All figures come from the Version 2 benchmark results. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 2

- Business Problem and Objective
- ‹#›
- Every medical claim needs the same few fields from a receipt; we tested how well that can be automated.
- THE QUESTION / Is Azure Document Intelligence + Azure OpenAI worth its extra cost and complexity? / Compared with open-source OCR plus fixed extraction rules that run on our own compute.
- SIX FIELDS PER RECEIPT / Doctor name / Registration number / Patient name / Receipt number / Service date / Total amount
- JUDGED ON / Accuracy / Speed / Reliability / Cost / Maintenance effort

  Notes: We focus on six fields a claim needs. The question is not only accuracy but also cost, speed, reliability and how much ongoing effort each option needs.

## Slide 3

- Methodology
- ‹#›
- Two steps per receipt: read the text (OCR), then find the six fields. We changed one step at a time.
- STEP 1 · READ THE TEXT (OCR)
- STEP 2 · FIND THE SIX FIELDS
- 1
- PaddleOCR Light
- Open-source OCR, small model
- Rules: original, then improved
- 2
- PaddleOCR Heavy
- Open-source OCR, large model
- Rules: original, then improved
- 3
- Azure DI
- Cloud OCR (prebuilt-read)
- Rules: original, then improved
- 4
- Azure DI + AOAI
- Cloud OCR (prebuilt-read)
- Azure OpenAI gpt-5-mini (prompt unchanged)
- 9 receipts / 51 fields scored / Red = paid Azure call

  Notes: 9 receipts, 51 fields that exist on them (fields not printed on a receipt are excluded). Three OCR engines feed the same fixed rules; the fourth approach replaces the rules with Azure OpenAI. The improved rules were written after examining these receipts, so their scores are tuned results. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 4

- The Receipts: Different Layouts and Languages
- ‹#›
- Seven new printed receipts photographed by phone, plus two receipts carried over from Version 1.
- GP clinic · English
- Hospital invoice · bilingual
- Chinese medicine · Chinese
- ALL NINE RECEIPTS / English: GP, specialist, physiotherapy / Bilingual: hospital, dental, medical centre / Traditional Chinese: Chinese medicine / From Version 1: vet invoice, NZ pharmacy / Several include distractors such as referring doctors, issue dates, patient numbers, insurer payments and balances.

  Notes: Shown: three of the nine benchmark images. The full set: GP clinic, specialist, hospital invoice, Chinese medicine, dental, physiotherapy, medical centre (new, photographed); a vet invoice and a New Zealand pharmacy receipt (from Version 1). Images: python/receipt_ocr_benchmark/data/receipts_v2/printable_images.

## Slide 5

- Accuracy with the Original Rules
- ‹#›
- Azure DI + AOAI 88.2%; the three rule-based approaches 29.4–41.2%.
  chart 'Accuracy': PaddleOCR Light 19/51=0.373, PaddleOCR Heavy 15/51=0.294, Azure DI 21/51=0.41200000000000003, Azure DI + AOAI 45/51=0.882
- TWO DIFFERENT STEPS / Text recognition (OCR) / Azure DI and PaddleOCR Light read almost every value correctly on the new receipts. / Field extraction / The original rules only knew English labels and missed bilingual and Chinese layouts. This is where most errors came from.
- 9 receipts, 51 applicable fields. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

  Notes: Accuracy = correct fields / fields that exist on the receipts. The OCR engines read most of the text correctly; the original fixed rules then failed to pick the fields on new, bilingual and Chinese layouts (see FINAL_ANALYSIS.md). Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 6

- Example 1: Bilingual Labels (Medical Centre)
- ‹#›
- The original rules read the Chinese half of a label as the value; the improved rules and AOAI do not.
  | Field | Correct value | Original rules (PaddleOCR Light) | Improved rules (PaddleOCR Light) | Azure DI + AOAI |
  | Patient | 蔡嘉穎 | ✗ 病人 | ✓ 蔡嘉穎 | ✓ 蔡嘉穎 |
  | Doctor | Dr. Siu Ka Wai | ✗ (not found) | ✓ Dr. Siu Ka Wai | ✓ Dr. Siu Ka Wai |
  | Reg. no. | M19903 | ✗ (not found) | ✓ M19903 | ✓ M19903 |
  | Receipt no. | MC-2609-3391 | ✗ (not found) | ✓ MC-2609-3391 | ✓ MC-2609-3391 |
  | Service date | 2026-09-03 | ✗ (not found) | ✓ 2026-09-03 | ✓ 2026-09-03 |
- Rules shown on PaddleOCR Light text; Azure DI with the original rules made the same patient error. ✓ correct · ✗ wrong or missing.

  Notes: Receipt8 (medical centre). Labels such as 'Patient 病人' put the value in a separate block. The original rules took the Chinese label '病人' as the patient's name and missed other fields; Azure DI with the original rules also returned '主診醫生' as the doctor. The improved rules strip label translations; AOAI read the text correctly with its unchanged prompt. Values from detail.csv, checked against the extraction JSON. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 7

- Example 2: Chinese-Only Receipt (Chinese Medicine)
- ‹#›
- The original rules found nothing; the improved rules and AOAI found all six fields.
  | Field | Correct value | Original rules (PaddleOCR Light) | Improved rules (PaddleOCR Light) | Azure DI + AOAI |
  | Patient | 麥詠琳 | ✗ (not found) | ✓ 麥詠琳 | ✓ 麥詠琳 |
  | Doctor | 葉卓謙 | ✗ (not found) | ✓ 葉卓謙 | ✓ 葉卓謙 |
  | Reg. no. | 006821 | ✗ (not found) | ✓ 006821 | ✓ 006821 |
  | Service date | 2026-06-09 | ✗ (not found) | ✓ 2026-06-09 | ✓ 2026年6月9日 |
  | Total amount | 790 | ✗ (not found) | ✓ 790.0 | ✓ 790.0 |
- Rules shown on PaddleOCR Light text; Azure DI and Heavy behaved the same. ✓ correct · ✗ wrong or missing.

  Notes: Receipt4 (Traditional Chinese medicine). Every value was read correctly by the OCR, but the original rules only knew English labels. The improved rules add Traditional Chinese labels (病人姓名, 主診中醫師, 註冊中醫編號, 診症日期, 合計) and Chinese dates. AOAI's date is shown as it returned it (2026年6月9日); the scorer reads it as the same date. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 8

- Accuracy Before and After Improving the Rules
- ‹#›
- Improved rules lifted PaddleOCR Light to 88.2% and Azure DI to 86.3% — on the receipts they were tuned on.
  chart 'Original rules': PaddleOCR Light=0.373, PaddleOCR Heavy=0.294, Azure DI=0.41200000000000003, Azure DI + AOAI=None
  chart 'Improved rules (tuned on these receipts)': PaddleOCR Light=0.882, PaddleOCR Heavy=0.647, Azure DI=0.863, Azure DI + AOAI=None
  chart 'AOAI (unchanged prompt)': PaddleOCR Light=None, PaddleOCR Heavy=None, Azure DI=None, Azure DI + AOAI=0.882
  | 7 new receipts | Correct |
  | PaddleOCR Light (improved) | 41/41 |
  | Azure DI (improved) | 40/41 |
  | PaddleOCR Heavy (improved) | 29/41 |
  | Azure DI + AOAI | 39/41 |
- Read with care / Equal scores here do not mean equal accuracy on unfamiliar receipts: the rules were tuned on these receipts, the AOAI prompt was not.
- 51 applicable fields per approach. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

  Notes: Original vs improved rules on the same OCR text; Azure DI + AOAI is unchanged. The improved rules were written after examining these nine receipts, so their scores are tuned results, not accuracy on unseen receipts. The AOAI prompt was not changed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 9

- Example 3: What Still Goes Wrong (Vet Invoice)
- ‹#›
- Each approach fails differently: a rule change picked the wrong number, AOAI picked the subtotal.
  | Field | Correct value | Original rules (PaddleOCR Light) | Improved rules (PaddleOCR Light) | Azure DI + AOAI |
  | Receipt no. | 369303 | ✓ 369303 | ✗ 380048 | ✓ 369303 |
  | Patient | Fuk Jai | ✗ (not found) | ✗ (not found) | ✓ Fuk Jai |
  | Doctor | Angel Tseng, Lok Yi Choi | ✗ (not found) | ✗ (not found) | ✗ Angel Tseng |
  | Total amount | 1361 | ✓ 1361.0 | ✓ 1361.0 | ✗ 1361.5 |
- PaddleOCR Heavy also found almost no text on two photos (3 and 0 text blocks): an OCR failure no rule can fix. ✓ correct · ✗ wrong or missing.

  Notes: Receipt9 (vet invoice carried over from Version 1). The improved rules now reach the 'Receipt #' column in the payments table (380048) instead of the invoice number; the ground truth uses the invoice number (an open policy question). The OCR glued a stray 'F' to 'FClinician' and 'FPatient', so no rule recognises those labels. AOAI chose the sub total 1361.50 instead of the total 1361.00, and both clinicians are expected by the ground truth. Separately, PaddleOCR Heavy detected only 3 and 0 text blocks on receipts 2 and 5, so no rule could help there. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 10

- Speed, Reliability and Cost
- ‹#›
- Azure DI is fastest (3.8 s); every approach processed all 9 receipts.
  chart 'Seconds': PaddleOCR Light=13.9, PaddleOCR Heavy=53.3, Azure DI=3.8, Azure DI + AOAI=6.2
- RELIABILITY / 9 / 9 / receipts processed by every approach, no failed requests
- COST DRIVERS (MEASURED) / Rules: 4–10 ms of CPU per receipt / PaddleOCR: CPU time on our compute; no per-call fee / AOAI: about 602 input + 263 output tokens per receipt / Prices still to be confirmed
- Times measure different things (CPU vs API call incl. network); receipts were processed one at a time.

  Notes: Average seconds per receipt. PaddleOCR = CPU on Azure ML compute; Azure = API call time including network. Rule extraction adds 4–10 ms (original rules 10.2 ms, improved 4.1 ms on average). AOAI tokens are averages over the 9 receipts. Prices (compute, Document Intelligence pages, gpt-5-mini tokens) are not yet confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 11

- Key Findings and Trade-offs
- ‹#›
- Most errors came from field extraction, not OCR; better rules close the gap on known layouts.
- 1
- OCR was mostly right / On the new receipts, Azure DI and PaddleOCR Light read almost every value.
- 2
- Original rules were weak / English-only labels: 37.3–41.2% for Light and DI.
- 3
- Rules can be improved / Tuned rules: Light 88.2%, DI 86.3%; label vocabulary grew about 3×.
- 4
- AOAI handled new layouts as-is / 88.2% with a prompt never tuned to these receipts.
- 5
- Heavy adds nothing / Lowest accuracy and slowest (53.3 s); OCR failed on two photos.
  |  | PaddleOCR Light + improved rules | Azure DI + AOAI |
  | Runs where | Our compute, offline | Azure cloud services |
  | Per-request fee | None (compute only) | DI pages + AOAI tokens |
  | New layouts | Needs new rules | Handled by the prompt |
  | Main risk | Rule maintenance | Cost, model variability |

  Notes: Findings from FINAL_ANALYSIS.md and RULES_COMPARISON.md in python/receipt_ocr_benchmark/results/v2. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.

## Slide 12

- Recommendation and Next Steps
- ‹#›
- Keep two candidates and decide on a larger set of receipts that neither has seen.
- CANDIDATE 1 / PaddleOCR Light + improved rules  88.2% (tuned) · 13.9 s / Offline, no per-request charges; needs rules maintained for each new layout.
- CANDIDATE 2 / Azure DI + AOAI  88.2% · 6.2 s / Flexible on varied layouts with an unchanged prompt; API costs and run-to-run variability.
- Limitation:  9 receipts, mostly mock and printed; the improved rules were tuned on them.
- NEXT STEP 1 / Freeze both / Lock the improved rules and the AOAI prompt before any new test
- NEXT STEP 2 / Test on unseen receipts / 30+ real, anonymised receipts; count rule fixes needed per new layout
- NEXT STEP 3 / Confirm prices / Compute rate, Document Intelligence pages, gpt-5-mini tokens

  Notes: Nine receipts (51 fields) are not enough for a production decision, and the improved rules were tuned on them. A fair comparison freezes both candidates first, then tests on unseen, representative receipts and also counts the effort to keep rules working on new layouts. Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON.
