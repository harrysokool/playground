# OCR_Benchmark_V5.pptx: text, chart data and notes


## Slide 1

- Medical receipt extraction benchmark / 9 receipts · 6 fields · rules vs AI extraction
- Can OCR Rules Replace Azure OpenAI?

  Notes: Question: is OCR with hand-written extraction rules enough to replace Azure OpenAI (AOAI) for medical receipts, and what value does AOAI add? Every number comes from the saved benchmark results. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 2

- The Answer in Brief
- ‹#›
- Rules are enough for simple, clearly labelled checks, not as a general replacement for AOAI.
- Not as a general replacement. / Rules work for simple, clearly labelled checks. / AOAI reduces the case-by-case logic we must write, and could unlock richer medical data.
- 88.2% vs 37.3–41.2%
- First versions: AOAI far ahead. The first rules had no Chinese support.
- 96.1% (development)
- Clearer prompt instructions fixed four more fields. Not yet independently validated.
- Less logic to maintain
- Rules must anticipate every label, language and layout. AOAI works from plain-language instructions.
- Small benchmark: 9 receipts. Development results are not independent validation.

  Notes: Initial implementations: rules 37.3–41.2%, AOAI 88.2% (the first rules had no Chinese labels). Prompt v2: 96.1%, a development result. Rules must anticipate each new label, language and layout in code; AOAI follows plain-language instructions, which often cover varied wording, though this is not guaranteed for unseen layouts. Extra medical fields are potential, not yet benchmarked. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

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
- Azure OpenAI instructions
- 6 fields
- 1. Read the text (OCR)
- 2. Find the fields
- English
- Bilingual
- Chinese
- 9 receipts: 7 printed test receipts (English, bilingual, Chinese layouts) and 2 from the first benchmark round. / 51 fields scored: doctor, registration no., patient, receipt no., service date, total.

  Notes: 9 receipts: 7 printed, fictional test receipts photographed with a phone (English, bilingual and Traditional Chinese layouts) and 2 receipts from the first benchmark round. Six fields: doctor, registration number, patient, receipt number, service date, total; 51 fields are printed on the receipts and scored. Azure OpenAI deployment: gpt-5-mini. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 4

- Initial Results: AOAI Was Far Ahead
- ‹#›
- MEASURED · BEFORE TUNING
- First versions of each approach, before anything was changed for these receipts.
  chart 'Accuracy': PaddleOCR Light + rules 19/51=37.3, Azure DI + rules 21/51=41.2, Azure DI + AOAI 45/51=88.2
- Why the rules scored low / The first rules knew English labels only: no Chinese or bilingual labels. / So this compares initial implementations, not the best each can do.
- The OCR read the name 蔡嘉穎. / The first rules returned the label 病人 ("patient") instead.
- Accuracy = correct fields out of 51 on 9 receipts. Receipt shown: bilingual medical centre receipt.

  Notes: Accuracy = correct fields / 51 on the 9 receipts. The AOAI prompt was written before these receipts existed. The original rules knew English labels only; on the Chinese and bilingual receipts the OCR read the values but the rules could not find them, e.g. the OCR read the patient name 蔡嘉穎 and the rules returned the label 病人 ('patient'). So this compares initial implementations, not the best possible performance of each approach. The rules were later adapted by hand to these receipts; that accuracy is not shown because it says nothing about new formats. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 5

- Improving AOAI: Clearer Instructions
- ‹#›
- MEASURED · DEVELOPMENT SET
- Prompt v2 fixed four fields: 88.2% → 96.1%. A development result, not independent validation.
  | Field fixed | Before | Instruction added | After |
  | Registration GP receipt | MBBS (HK) · Reg. No. M17642 | “the identifier only, without its label” | M17642 |
  | Doctor Dental receipt | Dr. Ho Ching Yee, BDS (HK) | “Leave out qualifications and post-nominals” | Dr. Ho Ching Yee |
  | Doctor Pharmacy receipt | Dr Jessica Sterenborg Picton Medical Centre | “clinic, hospital or practice names” | Dr Jessica Sterenborg |
  | Total Vet receipt | HKD 1361.50 | “after any discounts, rounding or other adjustments” | HKD 1361.00 |
  | AOAI by field | Original | Prompt v2 |
  | Doctor | 67% 6/9 | 89% 8/9 |
  | Registration* | 83% 5/6 | 100% 6/6 |
  | Patient | 100% 9/9 | 100% 9/9 |
  | Receipt no. | 100% 9/9 | 100% 9/9 |
  | Service date | 89% 8/9 | 89% 8/9 |
  | Total | 89% 8/9 | 100% 9/9 |
- The gain came from the prompt wording; code checks, OCR layout and attaching the photo changed no result. * Registration is printed on 6 of 9 receipts.

  Notes: Original prompt 88.2% (45/51); prompt v2 96.1% (49/51). Prompt v2 was written after reviewing these errors, so this is a development result. The four fixes are already in the model's own reply, before any Python check, and appear the same with plain or row-grouped OCR text and with the photo attached; the Python checks changed no value. So the gain came from the prompt wording alone. Still wrong: the vet invoice doctor (two practitioners; OCR misread the signature) and the pharmacy service date (open ground-truth question). Registration number is printed on 6 of the 9 receipts. Prompt text: receipt_bench/di_aoai.py, commit 034d7d5. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

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

## Slide 7

- Advantages and Disadvantages
- ‹#›
- Rules win on cost, auditability and predictability; AOAI on accuracy, maintenance and flexibility.
  |  | OCR + rules | Azure DI + AOAI | Evidence |
  | Cost | + PaddleOCR: own compute, no API fee (Azure DI: page fee) | − Azure DI page fee + ~602 input / 263 output tokens per receipt | Prices to confirm |
  | Speed | PaddleOCR 13.9 s (CPU) · Azure DI 3.8 s | 6.2 s per receipt | Measured |
  | Accuracy | − First versions 37.3–41.2% (no Chinese support) | + 88.2% first; 96.1% with prompt v2 (development) | Measured |
  | Maintenance | − New labels, languages and layouts need code and a full retest | + Many changes made in plain-language instructions; still retest | Measured / expected |
  | Flexibility | − Finds only what it was written for | + New fields can be requested in the prompt (not yet benchmarked) | Expected |
  | Auditability | + Every result traceable to a rule | − Harder to explain; keep quoted evidence and logs | Expected |
  | Reliability | + Same input, same output | − Can return a confident wrong value (e.g. a sub total as the total); model updates need retesting | Measured / expected |
- Green = stronger side. First versions = before tuning; the first rules had no Chinese labels. Expected = not measured here.

  Notes: Measured: initial accuracy (rules 37.3–41.2%, AOAI 88.2%; prompt v2 96.1%, development result); speed per receipt (PaddleOCR Light 13.9 s on Azure ML CPU, Azure DI 3.8 s, Azure DI + AOAI 6.2 s incl. network); AOAI tokens per receipt with the original prompt (602 input, 263 output); rule effort (69 -> 225 label phrases) and the vet invoice sub-total error. Prices are not confirmed. Flexibility, auditability and model-update effects are expectations. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 8

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

## Slide 9

- Limits of This Evidence
- ‹#›
- The direction is clear, but the numbers are not yet proof.
- 1 / Small dataset / 9 receipts, 51 fields. 7 are printed test receipts.
- 2 / First rules lacked Chinese / The initial gap (37.3–41.2% vs 88.2%) overstates what rules can do.
- 3 / Tuned on the same receipts / Prompt v2's 96.1% is a development result. Tuned rule scores are not shown.
- 4 / Little independent validation / Only 4 unseen handwritten receipts. On all 4, Azure DI misread the year 2026 as 2020.
- 5 / Costs not confirmed / Token counts are measured; Document Intelligence and gpt-5-mini prices are not.

  Notes: 9 receipts and 51 fields; 7 are printed, fictional test receipts. The original rules had no Chinese labels, so the initial gap overstates what rules can do. Prompt v2 (and the rules) were tuned on the same receipts; the tuned rule accuracy is not shown for that reason, and 96.1% is a development result. Unseen test: only 4 handwritten Version 1 receipts were not used for tuning; on all 4, Azure DI read the handwritten year 2026 as 2020 (results/v1_heldout), an OCR error no extraction step can fix. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 10

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
