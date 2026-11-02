# OCR_Benchmark_V10.pptx: text, chart data and notes


## Slide 1

- Benchmark results and pilot direction / OCR rules vs Azure OpenAI · 9 receipts · 6 fields
- Medical Receipt Extraction

  Notes: Question: is OCR with hand-written extraction rules enough to replace Azure OpenAI (AOAI) for medical receipts, and what value does AOAI add? Every number comes from the saved benchmark results. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 2

- Executive Summary
- ‹#›
- Recommendation: Azure DI + AOAI prompt v2 for the next receipt extraction pilot, not production.
- 96.1% / Azure DI + AOAI (prompt v2) / Development result
- 51.0–70.6% / OCR + multilingual rules / 51.0% PaddleOCR Light · 70.6% Azure DI / Retrospective baseline
- What we recommend / Azure DI + AOAI prompt v2 for the next extraction pilot / Python validation: format checks today, missing-field checks planned / Only approved receipt data on Azure; audit checks stay in another authorized system / A pilot, not a production approval

  Notes: Azure DI + AOAI with prompt v2: 96.1% (49/51), a development result (prompt refined on these receipts). OCR + general multilingual rules: 51.0% with PaddleOCR Light and 70.6% with Azure DI (26/51 and 36/51), a retrospective baseline. Neither is independently validated. AOAI handles contextual extraction more flexibly and could extract further fields without manual rules for every layout (not guaranteed); ordinary Python validation stays for formats and missing fields. Scope: Azure processes approved receipt data only; claims records, policy data and the audit checks stay in another authorized system. This is a direction for further testing, not a production approval. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 3

- Scope and Data Boundary
- ‹#›
- PLANNED WORKFLOW · NOT BUILT
- Azure only reads receipts and extracts data. Audit checks happen in another authorized system.
- Approved Azure environment: receipt data only
- Medical receipt / approved receipt only
- Azure DI / reads the text
- Azure OpenAI / extracts the fields
- Python checks / existing: formats, review flags
- Structured results / e.g. names, date, amounts
- Today: Azure DI + Azure OpenAI on 6 fields, with existing Python checks (date and amount formats, label clean-up, review flags). / Planned: required-field checks and checks for the new fields.
- Approved transfer / to be designed
- Another authorized system / Holds claims records, policy data and claim history / Runs the audit checks: claim comparison, policy checks, duplicates
- Never uploaded to Azure: claims records, policyholder databases, policy documents or other sensitive business information.
- Planned workflow. The transfer method must be approved before implementation; the integration and the audit checks are not being built yet.

  Notes: Planned workflow, not yet built: a medical receipt enters the approved Azure environment; Azure Document Intelligence reads it; Azure OpenAI extracts structured information; Python checks validate the result (existing: date and amount normalisation, registration and doctor-name clean-up, review flags for values not found in the OCR text or a total equal to the subtotal, in receipt_bench/aoai_validation.py; planned: required-field checks and checks for new fields); the results are transferred, by an approved method that is not yet designed, to another authorized system, which holds the claims and policy data and performs the audit checks (claim comparison, policy checks, duplicate detection). Only approved receipt data is processed in Azure. Claims records, policyholder databases, policy documents and other sensitive business information are not uploaded to Azure. Neither the transfer nor the audit checks are being implemented yet.

## Slide 4

- Benchmark: Three Approaches, Same 9 Receipts
- ‹#›
- MEASURED · DEVELOPMENT SET
- Multilingual OCR rules reached 51.0–70.6%; Azure DI + AOAI reached 96.1%.
- PaddleOCR Light + rules / Open-source OCR  →  Hand-written rules
- Azure DI + rules / Azure OCR  →  Hand-written rules
- Azure DI + AOAI / Azure OCR  →  Azure OpenAI
- 9 receipts · English, bilingual, Chinese layouts / 6 fields: doctor, registration no., patient, receipt no., date, total
  chart 'Accuracy': PaddleOCR Light + multilingual rules* 26/51=51.0, Azure DI + multilingual rules* 36/51=70.6, Azure DI + AOAI prompt v2† 49/51=96.1
- * Retrospective baseline   † Development result   Neither is independent validation. 51 of 54 fields scored (3 receipts have no registration number).

  Notes: 9 receipts: 7 printed, fictional test receipts photographed with a phone (English, bilingual and Traditional Chinese layouts) and 2 from the first benchmark round. Six fields: doctor, registration number, patient, receipt number, service date, total. 51 of 54 possible fields were scored: 3 receipts have no doctor registration number. Accuracy = correct fields / 51. Multilingual rules = general extraction rules with common Chinese labels and basic bilingual handling, a retrospective baseline (python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md). AOAI = prompt v2, a development result. Why the scores differ: slides 5 and 6. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

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
  | Reliability | + Same input, same output | − Can return a confident wrong value (e.g. a sub total); needs Python validation and retesting | Measured / expected |
- Green = stronger side. Multilingual rules include common Chinese labels (retrospective baseline). Expected = not measured here.

  Notes: Measured: accuracy (multilingual rules 51.0–70.6%, retrospective baseline; AOAI prompt v2 96.1%, development result); speed per receipt (PaddleOCR Light 13.9 s on Azure ML CPU, Azure DI 3.8 s, Azure DI + AOAI prompt v2 6.4 s incl. network); AOAI prompt v2 tokens per receipt (962 input, 243 output); rule effort (69 -> 225 label phrases) and the vet invoice sub-total error. Prices are not confirmed. Flexibility, auditability and model-update effects are expectations. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 9

- What the Auditors Check
- ‹#›
- We asked the business auditors what they check when sampling claims, and what information they need.
- 1
- Receipt authenticity / Letterhead, provider details, signature, stamp, signs of alteration
- 2
- Data accuracy and identity / Names, treatment date, diagnosis, amounts; the right patient
- 3
- Coverage and eligibility / Policy coverage, waiting periods, deadlines, preapproval
- 4
- Necessity and fees / Medically necessary treatment, agreed medical fees
- 5
- Assessment and fraud indicators / Calculations and limits, approval authority, duplicates
- Why it matters: these checks tell us which receipt information is worth extracting.
- Summarised from our discussion with the business auditors. Not every check uses receipt data.

  Notes: From our discussion with the business auditors; not part of the benchmark data. When sampling receipts and claims they check: receipt authenticity (letterhead, provider details, signatures, stamps, possible alterations); data integrity (claimant and provider names, treatment date, diagnosis code, receipt and claimed amounts) and patient identity; policy coverage, treatment eligibility, waiting periods and submission deadlines; medical necessity and agreed fees; assessor calculations, deductibles, benefit limits and approval authority; duplicate receipts and other fraud, waste and abuse indicators; preapproval amounts versus actual charges. Much of this needs data from other authorized systems, not just the receipt (next slide).

## Slide 10

- From Audit Needs to Receipt Fields
- ‹#›
- On Azure we extract what the receipt shows. Another authorized system adds the rest and runs the checks.
  | On the receipt (extracted on Azure) | Supports | Status |
  | Patient name | Accuracy | Benchmarked |
  | Doctor / practitioner name | Accuracy | Benchmarked |
  | Registration number | Authenticity, Accuracy | Benchmarked |
  | Receipt number | Fraud | Benchmarked |
  | Treatment date | Coverage | Benchmarked |
  | Receipt total | Necessity & fees, Fraud | Benchmarked |
  | Clinic name and address | Authenticity | Not yet tested |
  | Individual charges | Necessity & fees, Fraud | Not yet tested |
  | Diagnosis, symptoms (if stated) | Necessity & fees | Not yet tested |
  | Treatments, tests, medicines | Necessity & fees | Not yet tested |
  | Signature / stamp present | Authenticity | Not yet tested |
- approved transfer
- Another authorized system adds / Claimant, policy and coverage / Claimed and preapproval amounts / Claim history, fee schedules, decisions / …and runs the audit checks
- Information, not a verdict / Extraction does not decide whether a receipt is genuine, a treatment necessary, or a claim covered.
- Later: analytics (potential) / Cost by treatment, provider comparison, trends, unusual claims
- Green = the 6 benchmark fields (96.1%, development result). Other fields are not yet tested and appear only if printed or visible on the receipt.

  Notes: Receipt extraction supplies information for the audit checks; it does not decide whether a receipt is genuine, whether treatment was medically necessary, or whether the policy covers the claim. Receipt fields that could support the auditors' checks. The first 6 are the benchmark fields (Azure DI + AOAI prompt v2: 96.1%, a development result, not independently validated). The others have not been extracted or tested yet; each appears only if it is printed or visible on the receipt, and a signature or stamp can only be reported as present, not as genuine. Information that must come from another authorized system: the claimant and policy, claimed amount, coverage and waiting periods, claim history and duplicates across claims, preapproval amounts, agreed fee schedules and assessor decisions. Whether a receipt is genuine and whether treatment was medically necessary remain auditor judgements. Only approved receipt data is processed on Azure; results go to the authorized system by an approved method that is not yet designed. Later, the extracted details (treatments, tests, medicines, charges) could also feed analytics in the authorized system, such as cost by treatment, provider comparisons, trends and unusual claims: potential, not yet tested.

## Slide 11

- Recommendation and Next Steps
- ‹#›
- Pilot Azure DI + AOAI prompt v2 for receipt extraction, then grow the extracted fields step by step.
- Next extraction pilot: Azure DI + AOAI prompt v2, with Python validation / A direction for further testing, not a production approval. Only approved receipt data on Azure.
- 1. Define the schema / Which receipt fields, formats and “if printed” rules, from the auditors' checklist
- 2. Extend the prompt / Add fields a few at a time; keep the 6 benchmark fields stable
- 3. Test new fields / On approved receipt examples, including receipts not used for development
- 4. Prepare the hand-off / Agree the approved transfer method; confirm costs
- Rules still fit simple, clearly labelled checks, e.g. whether a diagnosis comment is present.
- Evidence so far: 9 receipts; development and retrospective results, not independently validated. No new fields or audit checks are implemented yet.

  Notes: Recommendation: Azure DI + AOAI prompt v2, with Python validation, for the next receipt extraction pilot. This is a direction for further testing, not a production approval. Simple, clearly labelled checks (for example whether a diagnosis comment is present) can still use rules. Next steps: define a structured extraction schema from the auditors' checklist; extend the existing prompt gradually, keeping the six benchmark fields stable; test each new field on approved receipt examples, including receipts not used for development; agree the approved transfer method before any integration; confirm Document Intelligence and gpt-5-mini costs. No new fields or audit checks are being implemented yet. Limits of this evidence: 9 receipts and 51 fields, 7 of them printed, fictional test receipts. 96.1% (prompt v2) is a development result: the prompt was refined after reviewing these receipts. 51.0–70.6% (multilingual rules) is a retrospective baseline: common Chinese labels were added after these receipts were examined, though fixed before scoring. Neither is independent validation: only 4 unseen handwritten receipts exist, and on all 4 Azure DI misread the year 2026 as 2020. Prices are not confirmed. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
