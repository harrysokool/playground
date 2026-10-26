# OCR_Benchmark_V8.pptx: text, chart data and notes


## Slide 1

- Medical receipt extraction benchmark / 9 receipts · 6 fields · rules vs AI extraction
- Can OCR Rules Replace Azure OpenAI?

  Notes: Question: is OCR with hand-written extraction rules enough to replace Azure OpenAI (AOAI) for medical receipts, and what value does AOAI add? Every number comes from the saved benchmark results. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 2

- Executive Summary
- ‹#›
- OCR + rules is not enough to replace AOAI across varied receipts.
- 96.1% / Azure DI + AOAI (prompt v2) / Development result
- 51.0–70.6% / OCR + multilingual rules / 51.0% PaddleOCR Light · 70.6% Azure DI / Retrospective baseline
- Why AOAI may still be needed / Fewer rules to write and maintain for new layouts and scenarios / Can potentially extract more fields for analytics (not yet benchmarked) / Rules remain fine for simple, clearly labelled checks

  Notes: Azure DI + AOAI with prompt v2: 96.1% (49/51). OCR + general multilingual rules: 51.0% with PaddleOCR Light and 70.6% with Azure DI (26/51 and 36/51). Rules must be written and maintained for every new label, language and layout; AOAI works from plain-language instructions and could extract further fields (potential, not yet benchmarked). Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 3

- What We Compared
- ‹#›
- For each of the 9 receipts, we extract 6 key fields and compare the results across 3 approaches.
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
- Azure OpenAI instructions
- 6 fields
- 1. Read the text (OCR)
- 2. Find the fields
- English
- Bilingual
- Chinese
- 9 receipts: 7 printed test receipts (English, bilingual, Chinese layouts) and 2 from the first benchmark round. / 6 fields: doctor, registration no., patient, receipt no., service date, total.
- 51 of 54 possible fields were scored. 3 receipts do not contain a doctor registration number, so those fields were excluded.

  Notes: 9 receipts: 7 printed, fictional test receipts photographed with a phone (English, bilingual and Traditional Chinese layouts) and 2 receipts from the first benchmark round. Six fields: doctor, registration number, patient, receipt number, service date, total. 51 of 54 possible fields were scored: 3 receipts do not contain a doctor registration number, so those fields were excluded. Azure OpenAI deployment: gpt-5-mini. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 4

- Rules vs AOAI on the Same Receipts
- ‹#›
- MEASURED · DEVELOPMENT SET
- Multilingual OCR rules reached 51.0–70.6%; Azure DI + AOAI reached 96.1%.
  chart 'Accuracy': PaddleOCR Light + multilingual rules* 26/51=51.0, Azure DI + multilingual rules* 36/51=70.6, Azure DI + AOAI prompt v2† 49/51=96.1
- Multilingual rules* / General rules with common Chinese labels / No receipt-specific rules
- To close the gap, rules would need / New labels and layouts written by hand / Retesting every receipt after each change
- * Retrospective baseline   † Development result (prompt refined on these receipts)   Neither is independent validation. 9 receipts, 51 fields.

  Notes: Accuracy = correct fields / 51 on the 9 receipts. Multilingual rules = general extraction rules with common Traditional and Simplified Chinese labels and basic bilingual handling (python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md); a retrospective baseline. AOAI = prompt v2, a development result: the prompt was refined after reviewing these receipts. Remaining rule errors need new label types, labels inside lines, layout logic or OCR-tolerant matching; PaddleOCR Light also loses fields because its OCR glues words and mixes characters in bilingual labels. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 5

- The Key Difference: Maintenance
- ‹#›
- MEASURED · DEVELOPMENT SET
- Rules need us to anticipate every case in code. AOAI can often cope through plain-language instructions.
- Manual extraction rules
- A new label, language or layout appears
- A developer anticipates it and writes rule code
- Retest every receipt; a change can break a working one
- Seen in this benchmark / 69 → 225 label phrases written by hand / 1 correct field broken by a rule change
- AOAI extraction
- New wording appears
- Often handled by the existing instructions
- If not: refine the instructions in plain language, rerun
- Seen in this benchmark / One prompt revision: 4 fields fixed, 0 broken
- Where rules were enough: a yes/no check for a diagnosis comment under clear labels. Rules matched AOAI on 13/13 receipts (development result).

  Notes: Rules: to handle these 9 receipts the label vocabulary grew from 69 to 225 hand-written phrases (Chinese and bilingual labels, distractor labels, layout handling), and one change broke 1 field that was already correct. AOAI: one prompt revision fixed 4 fields and broke 0. Whether AOAI copes with layouts it has not seen is expected, not proven: it has not been tested on enough unseen receipts, still makes mistakes and needs testing and monitoring. Diagnosis-comment check (results/diagnosis): rules matched AOAI on 13/13 receipts, because the comments sat under clear labels. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

- Advantages and Disadvantages
- ‹#›
- Rules win on cost, auditability and predictability; AOAI on accuracy, maintenance and flexibility.
  |  | OCR + rules | Azure DI + AOAI | Evidence |
  | Cost | + PaddleOCR: own compute, no API fee (Azure DI: page fee) | − Azure DI page fee + ~962 input / 243 output tokens per receipt | Prices to confirm |
  | Speed | PaddleOCR 13.9 s (CPU) · Azure DI 3.8 s | 6.4 s per receipt | Measured |
  | Accuracy | − 51.0–70.6% with multilingual rules (retrospective) | + 96.1% with prompt v2 (development result) | Measured |
  | Maintenance | − New labels, languages and layouts need code and a full retest | + Many changes made in plain-language instructions; still retest | Measured / expected |
  | Flexibility | − Finds only what it was written for | + New fields can be requested in the prompt (not yet benchmarked) | Expected |
  | Auditability | + Every result traceable to a rule | − Harder to explain; keep quoted evidence and logs | Expected |
  | Reliability | + Same input, same output | − Can return a confident wrong value (e.g. a sub total as the total); model updates need retesting | Measured / expected |
- Green = stronger side. Multilingual rules include common Chinese labels (retrospective baseline). Expected = not measured here.

  Notes: Measured: accuracy (multilingual rules 51.0–70.6%, retrospective baseline; AOAI prompt v2 96.1%, development result); speed per receipt (PaddleOCR Light 13.9 s on Azure ML CPU, Azure DI 3.8 s, Azure DI + AOAI prompt v2 6.4 s incl. network); AOAI prompt v2 tokens per receipt (962 input, 243 output); rule effort (69 -> 225 label phrases) and the vet invoice sub-total error. Prices are not confirmed. Flexibility, auditability and model-update effects are expectations. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 7

- Beyond Six Fields: From Receipts to Insights
- ‹#›
- POTENTIAL · NOT YET TESTED
- Today we extract 6 fields. AOAI could also capture what was treated, tested and prescribed.
- 1. What the receipt shows
- 2. What AOAI could extract
- 3. What we could analyse
  | Item | Type | HK$ |
  | Specialist consultation | Consultation | 950.00 |
  | Chest X-ray | Test | 620.00 |
  | Blood test (CBC) | Test | 380.00 |
  | Drugs | Medication | 245.50 |
- Illustration typed from the receipt text, not AOAI output
- Cost by treatment / Spend on consultations, tests and medicines
- Provider comparison / Typical charges per test across providers
- Trends over time / Which treatments and medicines are rising
- Unusual claims / Combinations or amounts that stand out
- Potential, not yet tested. Only the 6 current fields have been benchmarked. Diagnoses, symptoms, treatments and medications would need a pilot.

  Notes: Potential only: extracting these details has not been built or tested. Left: a real line-item section of a hospital receipt in our benchmark. Middle: an illustration of the structured data AOAI could return, typed by us from that receipt's OCR text (checked in the saved Azure DI output); it is not AOAI output. Where receipts show them, diagnoses and symptoms could be captured the same way. Rules would need new labels and logic for each such detail. Right: examples of analytics this would enable. A pilot would need ground truth, accuracy targets, a privacy review and cost checks.

## Slide 8

- Recommendation
- ‹#›
- Use rules for simple, labelled checks. Use AOAI where receipts vary or richer data is needed.
- Simple OCR rules are sufficient when… / Layouts are few, known and stable / Fields have clear printed labels / The question is simple, e.g. is a diagnosis comment present? / No API fee and fully traceable output are required
- AOAI adds real value when… / Providers, layouts and languages vary (Chinese, bilingual) / Fields lack consistent labels: names with titles, totals vs subtotals / We want less scenario-specific code to maintain / Richer medical data is wanted (potential, not yet benchmarked)
- 1. Freeze / the rules and AOAI prompt v2
- 2. Validate / 30+ unseen, real, anonymised receipts; count rule changes
- 3. Pilot extra fields / medications, treatments, symptoms, diagnoses with ground truth
- 4. Confirm cost / Document Intelligence pages and gpt-5-mini tokens
- Evidence so far: 9 receipts; results are development or retrospective, not yet validated on unseen receipts.

  Notes: Rules are sufficient where layouts are few and stable, fields have clear labels and the question is simple (for example whether a diagnosis comment is present). AOAI adds value where providers, layouts and languages vary, where fields lack consistent labels, and potentially for richer medical data (not yet benchmarked). Next steps: freeze the rules and prompt v2; test on 30+ unseen, real, anonymised receipts and count the rule changes needed; pilot medications, treatments, symptoms and diagnoses with ground truth; confirm prices. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
