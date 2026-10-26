# OCR_Benchmark_V9.pptx: text, chart data and notes


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
- Why AOAI may still be needed / Can often handle unfamiliar layouts without new rules (not guaranteed) / Can potentially extract more fields for analytics (not yet benchmarked) / Rules remain fine for simple, clearly labelled checks

  Notes: Azure DI + AOAI with prompt v2: 96.1% (49/51). OCR + general multilingual rules: 51.0% with PaddleOCR Light and 70.6% with Azure DI (26/51 and 36/51). Unfamiliar labels, languages and layouts may require additional rules and retesting; AOAI works from plain-language instructions and could extract further fields (potential, not yet benchmarked). Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

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
- What explains the gap / PaddleOCR misread labels (slide 5) / Rules missed context that AOAI used (slide 6)
- * Retrospective baseline   † Development result (prompt refined on these receipts)   Neither is independent validation. 9 receipts, 51 fields.

  Notes: Accuracy = correct fields / 51 on the 9 receipts. Multilingual rules = general extraction rules with common Traditional and Simplified Chinese labels and basic bilingual handling (python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md); a retrospective baseline. AOAI = prompt v2, a development result: the prompt was refined after reviewing these receipts. Remaining rule errors need new label types, labels inside lines, layout logic or OCR-tolerant matching; PaddleOCR Light also loses fields because its OCR glues words and mixes characters in bilingual labels. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 5

- Why Azure DI Beat PaddleOCR Light
- ‹#›
- MEASURED · RETROSPECTIVE
- Same rules on both. PaddleOCR misread the labels, so the rules could not find the values.
- 10 extra errors with PaddleOCR / All from reading the label text: words run together, wrong characters, a misread HK$ sign. None from the rules or the layout. / On this receipt PaddleOCR lost 4 fields: patient, registration no., treatment date and receipt no.
  | Field | Correct value | PaddleOCR read the label as… | Azure DI read it as… |
  | Registration no. | D03158 | ✗ Reg.No.註冊編號  words run together → not found | ✓ Reg. No. 註冊編號  → found |
  | Treatment date | 27/06/2026 | ✗ TreatmentDate治療日期  words run together → not found | ✓ Treatment Date 治療日期  → found |
  | Receipt no. | DEN-77342 | ✗ Receipt No.收據编號  编 read for 編 → not found | ✓ Receipt No. 收據編號  → found |
- Same multilingual rules (retrospective baseline) on both engines. Receipt 5 is a bilingual dental receipt.

  Notes: Both engines ran exactly the same multilingual rules (retrospective baseline). PaddleOCR Light made 10 more errors than Azure DI (51.0% vs 70.6%), and every one of them is a text recognition problem on a label, checked against the receipt photos: 5 labels with words run together, 2 run together and with a Simplified character, 2 with a wrong or missing character, and 1 'HK$' read as 'HKS'. None comes from layout or from different rules. The errors both engines share come from the rules themselves (labels they do not know, layouts they cannot follow). Receipt 5 (dental) loses four fields this way. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

- Why AOAI Beat the Rules
- ‹#›
- MEASURED · RETROSPECTIVE
- Both read the same Azure DI text. AOAI used the context; the rules followed fixed patterns.
  | Field | Correct | Rules | AOAI |
  | Practitioner Receipt 6 | CHEUNG Hoi Ying | ✗ Dr. Kwok Man Hin took the referring doctor | ✓ CHEUNG Hoi Ying |
  | Service date Receipt 6 | 16 Jul 2026 | ✗ 17 Jul 2026 took the date the receipt was issued | ✓ 16 Jul 2026 |
  | Total Receipt 6 | HK$1,200 | ✗ not found could not read the card layout | ✓ HK$1,200 |
  | Total Receipt 5 | HK$1,575 | ✗ HK$1,750 added up the items, ignored the discount | ✓ HK$1,575 |
- Rules: logic written case by case / Unfamiliar labels, layouts or scenarios may need additional rules and retesting (tuning these 9 grew the rules from 69 to 225 label phrases).
- AOAI: plain-language instructions / Can often handle varied wording without new code (not guaranteed); one prompt revision fixed 4 fields and broke none.
- AOAI was right with its original prompt (written before these receipts) and with prompt v2. Rules = Azure DI + multilingual rules (retrospective baseline).

  Notes: Azure DI + multilingual rules (retrospective baseline) vs Azure DI + AOAI on the same OCR text. On receipt 6 (physiotherapy) the rules took the referring doctor as the practitioner, the issue date as the session date, and could not read the total from the card row (Total / Amount Paid / Outstanding Balance). On receipt 5 the rules summed the items (the subtotal) and missed the 10% member discount. AOAI got all four right with its original prompt, written before these receipts existed, and again with prompt v2, so these wins do not come from prompt tuning. Of the 15 fields Azure DI + rules got wrong, AOAI's original prompt got 11 right. Unfamiliar labels, layouts or scenarios may need additional rules and retesting; the label vocabulary already grew from 69 to 225 phrases when the rules were tuned, and one change broke 1 correct field. One prompt revision fixed 4 fields and broke 0. Whether AOAI copes with layouts it has not seen is not yet tested. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 7

- The Doctor Database Approach
- ‹#›
- PROPOSAL · NOT BENCHMARKED
- Exact matching can identify registered doctor names in OCR text, but cannot determine who treated the patient.
- The proposal
- 1
- OCR reads the receipt / Azure DI or PaddleOCR
- 2
- Match against the registry / ~40,000 doctors · ~80,000 English and Chinese name variants
- 3
- Strict exact match / No fuzzy matching, no AI
- Straightforward; no experiment needed / Low cost · Deterministic · Easy to verify
- Only works if the OCR reads the name exactly and the registry contains that practitioner.
- But a name match is not the treating doctor
  | Seen in our receipts |  |
  | Referring doctor | Receipt 6: “Referred by Dr. Kwok Man Hin”; the treatment was by a physiotherapist (also receipt 2) |
  | Several doctors or staff | Receipt 8: a doctor and a nurse. Vet invoice: a clinician and a signing vet |
  | OCR misreads the name | Signature “Dr. Lok Yi Choi” read as “Dr. Lok Vichol”: no exact match |
  | Hypothetical (not in our receipts) |  |
  | Patient is a registered doctor | The patient's own name matches the registry |
  | Clinic director in the header | A director's name printed in the letterhead |
- AOAI reads context such as “Referred by” (slide 6) but has not been tested on these cases. Names on our test receipts are fictional, so registry match rates were not measured.

  Notes: Proposal: read the receipt with OCR, then match the recognised names against the registry of about 40,000 doctors (about 80,000 English and Chinese name variants) using strict exact matching, with no fuzzy matching and no AI. This is technically straightforward, so it was not built or benchmarked. Benefits: little extra processing cost, deterministic results, and every match can be checked against the registry. Limitation: a match only says that a registered doctor's name appears somewhere on the receipt. Real examples from our receipts: receipt 6 names a referring doctor (Dr. Kwok Man Hin) while the treating practitioner is a physiotherapist, and our rules already took the referring doctor; receipt 2 shows a referring doctor (Dr. Lam Pui Shan) next to the attending doctor (Dr. Ng Chun Yip); receipt 8 lists a doctor and a nurse; the vet invoice names a clinician and a signing vet; and the signature 'Dr. Lok Yi Choi' was read as 'Dr. Lok Vichol' by Azure DI and 'Br.LokYi ehoi' by PaddleOCR, so an exact match would find nothing. Matching also depends on the registry containing the practitioner: our receipts include a dentist, a physiotherapist and a Chinese-medicine practitioner, who may be on other registers. Hypothetical cases, not in our receipts: a patient who is a registered doctor, and a clinic director named in the header. The names on our test receipts are fictional, so real registry match rates were not measured. AOAI reads context such as 'Referred by' (slide 6), but it has not been tested on these edge cases.

## Slide 8

- Advantages and Disadvantages
- ‹#›
- Rules win on cost, auditability and predictability; AOAI on accuracy, maintenance and flexibility.
  |  | OCR + rules | Azure DI + AOAI | Evidence |
  | Cost | + PaddleOCR: own compute, no API fee (Azure DI: page fee) | − Azure DI page fee + ~962 input / 243 output tokens per receipt | Prices to confirm |
  | Speed | PaddleOCR 13.9 s (CPU) · Azure DI 3.8 s | 6.4 s per receipt | Measured |
  | Accuracy | − 51.0–70.6% with multilingual rules (retrospective) | + 96.1% with prompt v2 (development result) | Measured |
  | Maintenance | − Unfamiliar labels or layouts may require additional rules and retesting | + Many changes made in plain-language instructions; still retest | Measured / expected |
  | Flexibility | − Finds only what it was written for | + New fields can be requested in the prompt (not yet benchmarked) | Expected |
  | Auditability | + Every result traceable to a rule | − Harder to explain; keep quoted evidence and logs | Expected |
  | Reliability | + Same input, same output | − Can return a confident wrong value (e.g. a sub total as the total); model updates need retesting | Measured / expected |
- Green = stronger side. Multilingual rules include common Chinese labels (retrospective baseline). Expected = not measured here.

  Notes: Measured: accuracy (multilingual rules 51.0–70.6%, retrospective baseline; AOAI prompt v2 96.1%, development result); speed per receipt (PaddleOCR Light 13.9 s on Azure ML CPU, Azure DI 3.8 s, Azure DI + AOAI prompt v2 6.4 s incl. network); AOAI prompt v2 tokens per receipt (962 input, 243 output); rule effort (69 -> 225 label phrases) and the vet invoice sub-total error. Prices are not confirmed. Flexibility, auditability and model-update effects are expectations. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 9

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

  Notes: Potential only: extracting these details has not been built or tested. Left: a real line-item section of a hospital receipt in our benchmark. Middle: an illustration of the structured data AOAI could return, typed by us from that receipt's OCR text (checked in the saved Azure DI output); it is not AOAI output. Where receipts show them, diagnoses and symptoms could be captured the same way. With rules, each new kind of detail may require additional labels and logic. Right: examples of analytics this would enable. A pilot would need ground truth, accuracy targets, a privacy review and cost checks.

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
- Evidence so far: 9 receipts; results are development or retrospective, not yet validated on unseen receipts.

  Notes: Rules are sufficient where layouts are few and stable, fields have clear labels and the question is simple (for example whether a diagnosis comment is present). AOAI adds value where providers, layouts and languages vary, where fields lack consistent labels, and potentially for richer medical data (not yet benchmarked). Next steps: freeze the rules and prompt v2; test on 30+ unseen, real, anonymised receipts and count the rule changes needed; pilot medications, treatments, symptoms and diagnoses with ground truth; confirm prices. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
