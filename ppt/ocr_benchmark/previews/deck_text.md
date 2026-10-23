# OCR_Benchmark_V4.pptx: text, chart data and notes


## Slide 1

- Medical receipt extraction benchmark / 9 receipts · 6 fields · 3 approaches · plus a diagnosis-comment test
- Can OCR Rules Replace Azure OpenAI?

  Notes: Question: can traditional OCR with hand-written extraction rules replace Azure OpenAI (AOAI) for medical receipts, and if not, why is AOAI needed? Every number in this deck comes from the saved benchmark results. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 2

- The Answer in Brief
- ‹#›
- Rules can replace AOAI only for simple, clearly labelled tasks.
- Not as a general replacement. / Rules can match AI on simple, labelled checks, after manual work. / AOAI is needed when receipt layouts vary and when richer medical information is wanted.
- 88.2% vs 37.3–41.2%
- Before any tuning, AOAI was far ahead. The first rules had no Chinese labels.
- 96.1% vs 86.3–88.2%
- After tuning on the same receipts (development results). Rules needed 69 → 225 label phrases; AOAI one prompt revision.
- 13/13 for all
- On a yes/no diagnosis-comment check with clear labels, rules matched AOAI.
- Development results are not independent validation; a test on 30+ unseen real receipts is still needed.

  Notes: Before tuning: rules 37.3–41.2%, AOAI 88.2%. After tuning on the same 9 receipts (development results): rules 86.3–88.2%, AOAI prompt v2 96.1%; the rules needed 69 -> 225 label phrases written by hand, AOAI one prompt revision. Diagnosis-comment check: all three methods 13/13. None of this is validated on unseen receipts. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 3

- What We Compared
- ‹#›
- Three ways to turn a receipt photo into six fields. Only the extraction step differs between rules and AI.
- PaddleOCR Light + rules
- PaddleOCR Light / open source, own compute
- Hand-written rules
- 6 fields
- Azure DI + rules
- Azure Document Intelligence / cloud OCR
- Hand-written rules
- 6 fields
- Azure DI + AOAI
- Azure Document Intelligence / cloud OCR
- Azure OpenAI prompt
- 6 fields
- 1. Read the text (OCR)
- 2. Find the fields
- English
- Bilingual
- Chinese
- 9 receipts: 7 printed test receipts (English, bilingual, Chinese layouts) and 2 from the first benchmark round. / 51 fields scored: doctor, registration no., patient, receipt no., service date, total.

  Notes: 9 receipts: 7 printed, fictional test receipts photographed with a phone (English, bilingual and Traditional Chinese layouts) and 2 receipts from the first benchmark round. Six fields: doctor, registration number, patient, receipt number, service date, total; 51 fields are printed on the receipts and scored. Azure OpenAI deployment: gpt-5-mini. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 4

- Before Tuning: AOAI Was Far Ahead
- ‹#›
- MEASURED · BEFORE TUNING
- Out of the box, AI extraction found more than twice as many fields as the first rule sets.
  chart 'Accuracy': PaddleOCR Light + rules 19/51=37.3, Azure DI + rules 21/51=41.2, Azure DI + AOAI 45/51=88.2
- Why the rules scored low / The first rules knew English labels only: no Chinese or bilingual labels. / So this compares first versions, not the best each approach can do.
- The OCR read the name 蔡嘉穎. / The first rules returned the label 病人 ("patient") instead.
- Accuracy = correct fields out of 51 on 9 receipts. Receipt shown: bilingual medical centre receipt, PaddleOCR Light text.

  Notes: Accuracy = correct fields / 51 on the 9 receipts, before anything was changed for them. The AOAI prompt was written before these receipts existed. The original rules knew English labels only; on the Chinese and bilingual receipts the OCR read the values but the rules could not find them, e.g. receipt 8: the OCR read the patient name 蔡嘉穎 but the rules returned the label 病人 ('patient'). So this compares initial implementations, not the maximum capability of each approach. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 5

- After Tuning: All Improved, at Very Different Cost
- ‹#›
- MEASURED · DEVELOPMENT SET
- Rules closed most of the gap, but only by being rewritten by hand for these receipts.
  chart 'Before tuning': PaddleOCR Light + rules=37.3, Azure DI + rules=41.2, Azure DI + AOAI=88.2
  chart 'After tuning (development)': PaddleOCR Light + rules=88.2, Azure DI + rules=86.3, Azure DI + AOAI=96.1
- Rules: rewritten by hand / 69 → 225 label phrases: Chinese, bilingual, layouts / Code changes, then a retest of every receipt / Fixed 27 fields, broke 1 that was correct
- AOAI: one prompt revision / Clearer definition of each field / Plain-language edits, then a rerun / Fixed 4 fields, broke 0
- Development results: changes made after reviewing these 9 receipts; not independent validation. Rule figures shown for PaddleOCR Light.

  Notes: Development results: every change was made after reviewing the errors on these 9 receipts, so the scores are not independent validation. Rules: label phrases 69 -> 225 (Chinese and bilingual labels, distractor labels, layout handling); fixed 27 fields and broke 1 on PaddleOCR Light text, fixed 24 and broke 1 on Azure DI text. AOAI: prompt v2 with clearer field definitions; fixed 4, broke 0. A small held-out check on Version 1 receipts (4-6 receipts, mostly handwritten) is too small to say whether either approach generalises better, so it is not shown on the slides. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

- Where Errors Remain: Accuracy by Field
- ‹#›
- MEASURED · DEVELOPMENT SET
- All three miss the same two fields; the rules also miss patients and receipt numbers.
  | Field | Receipts | PaddleOCR Light + rules | Azure DI + rules | Azure DI + AOAI, prompt v2 |
  | Doctor | 9 | 88.9%  (8/9) | 88.9%  (8/9) | 88.9%  (8/9) |
  | Registration no. | 6* | 100.0%  (6/6) | 100.0%  (6/6) | 100.0%  (6/6) |
  | Patient | 9 | 77.8%  (7/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | Receipt no. | 9 | 77.8%  (7/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | Service date | 9 | 88.9%  (8/9) | 88.9%  (8/9) | 88.9%  (8/9) |
  | Total | 9 | 100.0%  (9/9) | 88.9%  (8/9) | 100.0%  (9/9) |
- Development results after tuning. * Registration number is printed on 6 of the 9 receipts; every other field on all 9.

  Notes: Development results after tuning on these 9 receipts. Counts from scores_aoai_improved/detail.csv, checked against summary.csv. Registration number is printed on 6 of the 9 receipts; every other field on all of them. All three miss the vet invoice's doctor (two practitioners; the OCR misread the signature) and the pharmacy receipt's service date (print date vs item date, an open ground-truth question). The rules also miss patient and receipt number on the vet invoice and the pharmacy receipt (a stray mark on the label, a payment receipt number, no labels); Azure DI + rules also misses one total. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 7

- What Prompt V2 Changed
- ‹#›
- MEASURED · DEVELOPMENT SET
- Four fields fixed, all by clearer wording. Code checks, layout and photos added nothing.
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

  Notes: Original prompt 88.2% (45/51); prompt v2 96.1% (49/51), a development result because prompt v2 was written after reviewing these errors. The four fixes are in the model's own reply, before any Python check, in all three prompt v2 runs. The Python checks changed 0 values; plain-text OCR input (49/51) scores the same as the row layout (49/51) and as attaching the photo (49/51). Still wrong: the vet invoice doctor (two practitioners; OCR misread the signature) and the pharmacy service date (open ground-truth question). Prompt text: receipt_bench/di_aoai.py, commit 034d7d5. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 8

- Rules vs. AOAI: Side by Side
- ‹#›
- AOAI wins on accuracy and effort; rules win on cost and control. New layouts are untested.
  |  | OCR + rules | Azure DI + AOAI | Evidence |
  | Accuracy* | 37.3–41.2% first; 86.3–88.2% after tuning | 88.2% first; 96.1% after prompt v2 | Measured |
  | Speed per receipt | 13.9 s PaddleOCR (CPU) · 3.8 s Azure DI | 6.2 s | Measured |
  | Running cost | PaddleOCR: own compute, no API fee · Azure DI: page fee | Azure DI page fee + ~602 input / 263 output tokens | Prices to confirm |
  | Development effort | Rules rewritten by hand (69 → 225 label phrases) | One prompt revision | Measured |
  | Side effects of changes | 1 correct field broken by the rule changes | 0 broken by the prompt revision | Measured |
  | New receipt layouts | New labels and rules for each layout or language | Expected to adapt without code changes | Expected |
  | Control and audit | Deterministic; every decision traceable | Depends on model and prompt; needs monitoring | Expected |
- * First = before tuning (the first rules had no Chinese labels); after tuning = development results. Green = stronger side. Expected = not measured.

  Notes: Accuracy: before tuning rules 37.3–41.2%, AOAI 88.2%; after tuning (development results) rules 86.3–88.2%, AOAI 96.1%. Speed = average per receipt: PaddleOCR Light 13.9 s on Azure ML CPU compute, Azure DI 3.8 s, Azure DI + AOAI 6.2 s (API time incl. network). Tokens = average per receipt with the original prompt (602 input, 263 output); Document Intelligence and gpt-5-mini prices are not yet confirmed. Effort and side effects measured on the development set. New layouts and control are expectations, not measurements. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 9

- When Rules Are Enough: Diagnosis Check
- ‹#›
- MEASURED · DEVELOPMENT SET
- For a simple yes/no question with clear labels, rules matched AOAI on every receipt.
- The question / Does the receipt contain a written comment about the patient's condition, symptoms or diagnosis?
- 13 receipts / 3 with a comment / 2 with an empty label / English and Chinese labels
- 13/13 / PaddleOCR Light + rules
- 13/13 / Azure DI + rules
- 13/13 / Azure DI + AOAI
- What it tells us / Rules are enough when the answer sits under a clear label (Diagnosis:, Notes:, 診斷) and the question is yes/no. / AOAI also spotted a condition written as a line item ("broken ribs."): unlabelled detail rules cannot see. / Adding the check to AOAI cost about 26% more input tokens and changed none of the six fields. / But the test was easy for both: only 3 receipts had a comment, all under a label.
- Development result: rules and prompt written after reading these receipts. Only 3 receipts had a comment.

  Notes: Question: does the receipt contain a written comment about the patient's condition, symptoms or diagnosis? Ground truth for 13 receipts: 3 with a comment, 2 with an empty label. Results (results/diagnosis/scores): rules_paddle_light 13/13, rules_azure_di 13/13, aoai_v2 13/13. Development result: the rules and the prompt addition were written after reading these receipts. AOAI quoted 'broken ribs.' (a condition written as a line item) on one receipt; the rules reached the same answer from a 'Notes' comment. Adding the check raised AOAI input tokens by about 26% and changed none of the six fields. Details: python/receipt_ocr_benchmark/docs/DIAGNOSIS_COMMENT.md.

## Slide 10

- Beyond Six Fields: What AOAI Could Add
- ‹#›
- POTENTIAL · NOT YET TESTED
- Our receipts already carry medical details that rules ignore. AOAI could turn them into data.
- Already in our receipts' OCR text / Diagnoses and symptoms / Colitis · diarrhoea / vet invoice / Treatments and tests / Chest X-ray · Blood test (CBC) · 針灸 (acupuncture) · Scaling and polishing / hospital, Chinese medicine, dental / Medications / Omeprazole 20mg Capsules · Metronidazole 50mg Tablet / pharmacy, vet invoice
- AOAI could return / Diagnosis / Symptoms / Treatment or procedure / Medication and dose / Cost per item
- Which could enable / Claims analytics by diagnosis and treatment / Cost benchmarks per treatment and provider / Medication patterns / Consistency checks: treatment vs diagnosis vs amount / Faster triage for reviewers
- Not yet tested. We have not built or measured extraction of these fields. A pilot needs ground truth, accuracy targets, a privacy review and cost checks.

  Notes: Potential only: we have not built or measured extraction of these fields. The examples are text that Azure DI already read from our benchmark receipts (checked in the saved OCR output): Diagnoses and symptoms: Colitis, diarrhoea; Treatments and tests: Chest X-ray, Blood test (CBC), 針灸, Scaling and polishing; Medications: Omeprazole 20mg Capsules, Metronidazole 50mg Tablet. 針灸 = acupuncture. Possible uses depend on a pilot with ground truth, accuracy targets, privacy review and cost checks.

## Slide 11

- Limits of What We Know
- ‹#›
- The evidence points one way, but it is not yet proof.
- 1 / Small sample / 9 receipts, 51 fields. 7 are printed test receipts.
- 2 / Rules started without Chinese / The first gap (37.3–41.2% vs 88.2%) overstates what rules can do.
- 3 / Tuned on the same receipts / Later scores (rules 86.3–88.2%, AOAI 96.1%) are development results.
- 4 / Little unseen testing / Only 4 unseen handwritten receipts: too few to compare. On all 4, Azure DI misread the year 2026 as 2020.
- 5 / Costs not confirmed / Token counts are measured; Document Intelligence and gpt-5-mini prices are not.

  Notes: 9 receipts and 51 fields; 7 are printed, fictional test receipts. The original rules had no Chinese labels, so the initial gap overstates what rules can do. Rules and prompt v2 were tuned on the same receipts, so their later scores are development results. Unseen test: 4 handwritten Version 1 receipts not used for tuning (6 receipts in all); on all 4, Azure DI read the handwritten year 2026 as 2020 (checked in results/v1_heldout), an OCR error that no extraction step can fix. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 12

- Recommendation
- ‹#›
- Not a general replacement: rules for simple, labelled tasks; AOAI where receipts vary or richer data is needed.
- Simple OCR rules are sufficient when… / Layouts are few, known and stable / Fields have clear printed labels / The question is simple, e.g. is a diagnosis comment present? / No API fee or fully deterministic output is required
- AOAI adds real value when… / Many providers, layouts and languages (Chinese, bilingual) / Fields lack consistent labels: names with titles, totals vs subtotals / New fields should be added by changing a prompt, not code / Richer medical data is wanted (potential, not yet tested)
- 1. Freeze / the improved rules and AOAI prompt v2
- 2. Test unseen / 30+ real, anonymised receipts; count rule changes
- 3. Pilot extra fields / diagnoses, treatments, medications with ground truth
- 4. Confirm cost / Document Intelligence pages and gpt-5-mini tokens

  Notes: Rules are sufficient where the task is simple and labelled and the layouts are known and stable (shown on the diagnosis-comment check and, after tuning, on the six fields of these receipts). AOAI adds value where layouts and languages vary, where fields have no consistent labels, and for richer medical information (potential, not yet tested). Next steps: freeze the improved rules and prompt v2; test on 30+ unseen, real, anonymised receipts and count the rule changes needed; pilot the extra medical fields with ground truth; confirm prices. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
