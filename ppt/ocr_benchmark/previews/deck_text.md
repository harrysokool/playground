# OCR_Benchmark_V7.pptx: text, chart data and notes


## Slide 1

- Medical receipt extraction benchmark / 9 receipts · 6 fields · rules vs AI extraction
- Can OCR Rules Replace Azure OpenAI?

  Notes: Question: is OCR with hand-written extraction rules enough to replace Azure OpenAI (AOAI) for medical receipts, and what value does AOAI add? Every number comes from the saved benchmark results. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 2

- Executive Summary
- ‹#›
- OCR + rules is not enough to replace AOAI across varied receipts.
- 96.1% / Azure DI + AOAI (prompt v2) / Development result
- 51.0–70.6% / OCR + general multilingual rules / 51.0% = PaddleOCR Light + rules · 70.6% = Azure DI + rules
- Why AOAI may still be needed / Fewer rules to write and maintain for new layouts and scenarios / Can potentially extract more fields for analytics (not yet benchmarked) / Rules remain fine for simple, clearly labelled checks
- Caveat: 9 receipts. 96.1% is a development result (prompt refined on these receipts); 51.0–70.6% is a retrospective baseline. Neither is independent validation.

  Notes: Azure DI + AOAI with prompt v2: 96.1% (49/51), a development result: the prompt was refined after reviewing these 9 receipts. OCR + general multilingual rules: 51.0% with PaddleOCR Light and 70.6% with Azure DI (26/51 and 36/51), a retrospective baseline: the rules add common Chinese labels and were fixed before scoring, but written after these receipts were examined. Neither result is independent validation. Rules must be written and maintained for every new label, language and layout; AOAI works from plain-language instructions and could extract further fields (potential, not yet benchmarked). Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

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

- A Fairer Comparison: Rules vs AOAI
- ‹#›
- MEASURED · RETROSPECTIVE
- With multilingual rules, OCR + rules reached 51.0–70.6%. AOAI reached 88.2% before any prompt tuning.
  chart 'Accuracy': PaddleOCR Light + multilingual rules* 26/51=51.0, Azure DI + multilingual rules* 36/51=70.6, Azure DI + AOAI original prompt 45/51=88.2
- Multilingual rules* / General rules plus common Chinese labels and basic bilingual handling / No receipt-specific tuning
- To close the gap, rules would need / New label types and layouts written by hand / OCR-tolerant matching and retesting of every receipt
- * Retrospective: Chinese labels added after these receipts were examined (rules fixed before scoring); not an independent test. Accuracy = correct fields out of 51 on 9 receipts.

  Notes: Accuracy = correct fields / 51 on the 9 receipts. Multilingual rules = the original general rules plus common Traditional and Simplified Chinese translations of their labels and basic bilingual handling, nothing else (python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md). Retrospective: Chinese labels added after these receipts were examined (rules fixed before scoring); not an independent test. AOAI uses the original prompt, written before these receipts existed. The remaining rule errors need new label types, labels inside lines, layout logic or OCR-tolerant matching; PaddleOCR Light also loses fields because its OCR glues words and mixes characters in bilingual labels. The prompt v2 development result (96.1%) is on the executive summary. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

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
- Not guaranteed: AOAI has not been tested on enough unseen layouts. It still makes mistakes and needs testing and monitoring.
- Where rules were enough: a yes/no check for a diagnosis comment under clear labels. Rules matched AOAI on 13/13 receipts (development result).

  Notes: Rules: to handle these 9 receipts the label vocabulary grew from 69 to 225 hand-written phrases (Chinese and bilingual labels, distractor labels, layout handling), and one change broke 1 field that was already correct. AOAI: one prompt revision fixed 4 fields and broke 0. Whether AOAI copes with layouts it has not seen is expected, not proven: it has not been tested on enough unseen receipts. Diagnosis-comment check (results/diagnosis): rules matched AOAI on 13/13 receipts, because the comments sat under clear labels. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

- Advantages and Disadvantages
- ‹#›
- Rules win on cost, auditability and predictability; AOAI on accuracy, maintenance and flexibility.
  |  | OCR + rules | Azure DI + AOAI | Evidence |
  | Cost | + PaddleOCR: own compute, no API fee (Azure DI: page fee) | − Azure DI page fee + ~602 input / 263 output tokens per receipt | Prices to confirm |
  | Speed | PaddleOCR 13.9 s (CPU) · Azure DI 3.8 s | 6.2 s per receipt | Measured |
  | Accuracy | − 51.0–70.6% with multilingual rules (retrospective) | + 88.2% first; 96.1% with prompt v2 (development) | Measured |
  | Maintenance | − New labels, languages and layouts need code and a full retest | + Many changes made in plain-language instructions; still retest | Measured / expected |
  | Flexibility | − Finds only what it was written for | + New fields can be requested in the prompt (not yet benchmarked) | Expected |
  | Auditability | + Every result traceable to a rule | − Harder to explain; keep quoted evidence and logs | Expected |
  | Reliability | + Same input, same output | − Can return a confident wrong value (e.g. a sub total as the total); model updates need retesting | Measured / expected |
- Green = stronger side. Multilingual rules include common Chinese labels (retrospective baseline). Expected = not measured here.

  Notes: Measured: accuracy (multilingual rules 51.0–70.6%, retrospective baseline; AOAI 88.2%; prompt v2 96.1%, development result); speed per receipt (PaddleOCR Light 13.9 s on Azure ML CPU, Azure DI 3.8 s, Azure DI + AOAI 6.2 s incl. network); AOAI tokens per receipt with the original prompt (602 input, 263 output); rule effort (69 -> 225 label phrases) and the vet invoice sub-total error. Prices are not confirmed. Flexibility, auditability and model-update effects are expectations. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 7

- Beyond Six Fields: What AOAI Could Unlock
- ‹#›
- POTENTIAL · NOT YET TESTED
- Our receipts already carry medical details. AOAI could turn them into data for analytics.
  | Type | Text already in our OCR | Receipt |
  | Medication | Omeprazole 20mg Capsules | Pharmacy |
  | Medication | Metronidazole 50mg Tablet | Vet invoice |
  | Test | Chest X-ray | Hospital |
  | Treatment | 針灸 (acupuncture) | Chinese medicine |
  | Treatment | Scaling and polishing | Dental |
  | Symptom | diarrhoea | Vet invoice |
  | Diagnosis | Colitis | Vet invoice |
- Which could enable / Claims analytics by diagnosis, treatment and medication / Cost benchmarks per treatment and provider / Medication and treatment patterns over time / Consistency checks: does the treatment fit the diagnosis and amount? / Faster triage and fewer manual look-ups for reviewers
- Potential, not yet benchmarked. Text shown is OCR input, not AOAI output. A pilot needs ground truth and a privacy review.

  Notes: Potential only: extraction of these fields has not been built or benchmarked. The table shows text that Azure DI already read from our benchmark receipts (checked in the saved OCR output); it illustrates the target output, not AOAI results. Rules would need new labels and logic for every such detail. Possible uses depend on a pilot with ground truth, accuracy targets, a privacy review and cost checks.

## Slide 8

- Limits of This Evidence
- ‹#›
- The direction is clear, but the numbers are not yet proof.
- 1 / Small dataset / 9 receipts, 51 fields. 7 are printed test receipts.
- 2 / Retrospective rules baseline / Multilingual rules (51.0–70.6%) were written after these receipts were examined.
- 3 / Tuned on the same receipts / Prompt v2's 96.1% is a development result. Tuned rule scores are not shown.
- 4 / Little independent validation / Only 4 unseen handwritten receipts. On all 4, Azure DI misread the year 2026 as 2020.
- 5 / Costs not confirmed / Token counts are measured; Document Intelligence and gpt-5-mini prices are not.

  Notes: 9 receipts and 51 fields; 7 are printed, fictional test receipts. The original rules had no Chinese labels, so the initial gap overstates what rules can do; with common Chinese labels added (retrospective baseline, rules fixed before scoring but written after these receipts were examined) they reached 51.0–70.6%. Prompt v2 (and the rules) were tuned on the same receipts; the tuned rule accuracy is not shown for that reason, and 96.1% is a development result. Unseen test: only 4 handwritten Version 1 receipts were not used for tuning; on all 4, Azure DI read the handwritten year 2026 as 2020 (results/v1_heldout), an OCR error no extraction step can fix. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 9

- Recommendation
- ‹#›
- Use rules for simple, labelled checks. Use AOAI where receipts vary or richer data is needed.
- Simple OCR rules are sufficient when… / Layouts are few, known and stable / Fields have clear printed labels / The question is simple, e.g. is a diagnosis comment present? / No API fee and fully traceable output are required
- AOAI adds real value when… / Providers, layouts and languages vary (Chinese, bilingual) / Fields lack consistent labels: names with titles, totals vs subtotals / We want less scenario-specific code to maintain / Richer medical data is wanted (potential, not yet benchmarked)
- 1. Freeze / the rules and AOAI prompt v2
- 2. Validate / 30+ unseen, real, anonymised receipts; count rule changes
- 3. Pilot extra fields / medications, treatments, symptoms, diagnoses with ground truth
- 4. Confirm cost / Document Intelligence pages and gpt-5-mini tokens

  Notes: Rules are sufficient where layouts are few and stable, fields have clear labels and the question is simple (for example whether a diagnosis comment is present). AOAI adds value where providers, layouts and languages vary, where fields lack consistent labels, and potentially for richer medical data (not yet benchmarked). Next steps: freeze the rules and prompt v2; test on 30+ unseen, real, anonymised receipts and count the rule changes needed; pilot medications, treatments, symptoms and diagnoses with ground truth; confirm prices. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
