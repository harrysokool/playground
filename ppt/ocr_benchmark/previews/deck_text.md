# OCR_Benchmark_V16.pptx: text, chart data and notes


## Slide 1 (cover)

- An Internal Audit AI innovation idea / What we built, what we tested and where it could go
- AI-Assisted Medical Receipt Extraction

  Notes: This is an AI innovation idea from our team. We identified repetitive manual audit work, demonstrated a working receipt extraction workflow with Azure Document Intelligence and Azure OpenAI, compared three approaches, and explored how structured receipt data could improve Internal Audit. We are sharing what we built and learned and its potential value; this is an exploration, not a finished product.

## Slide 2 (main slide 1)

- The Problem: Manual Receipt Reviews Take Time
- ‹#›
- ESTIMATES · NOT MEASURED
- Reading receipts by hand takes auditor time, which limits how many claims we can cover.
- ~25 / receipts per sample / 5–10 min / per receipt / ≈ 2–4 hours of reading per sample. Team estimates, not measured.
- What auditors check on each receipt   from the business auditor checklist
- Authenticity:  Letterhead, provider registration number, signature and stamp
- Data integrity:  Claimant, provider, treatment date, diagnosis and amounts vs the claims system
- Coverage:  Service date within the policy period; diagnosis covered; charges within agreed fees
- Fraud indicators:  Duplicate receipts by receipt number, treatment date, amount and provider
- The bottleneck: auditor time and effort. Reading each receipt by hand keeps coverage to a small sample.

  Notes: For each audit sample, business auditors review around 25 receipts by hand. Each receipt takes an estimated 5 to 10 minutes, roughly 2 to 4 hours of reading per sample (25 x 5-10 minutes). These are the team's estimates, not measured figures. The checks come from the business auditor checklist: authenticity (letterhead with the provider's legal name, address and registration or licence number; signature and company stamp; no unauthorised alteration); data integrity (claimant name, provider name, treatment date, diagnosis code, receipt amount and claimed amount against the claims system); coverage (date of service within the policy period, diagnosis within coverage, charges within agreed fees); and fraud, waste and abuse indicators such as duplicate receipts by receipt number, treatment date, amount and provider. The bottleneck is auditor time and effort, which keeps coverage to a small sample.

## Slide 3 (main slide 2)

- Our AI Solution and Business Value
- ‹#›
- WORKING DEMONSTRATION
- We built a working workflow that turns a receipt photo into structured data.
- Receipt photo
- →
- Azure DI reads the text
- →
- Azure OpenAI selects the fields
- →
- Structured data
- →
  | Extracted output |  |
  | Practitioner | Dr. Siu Ka Wai |
  | Registration no. | M19903 |
  | Patient | 蔡嘉穎 |
  | Receipt no. | MC-2609-3391 |
  | Treatment date | 3 Sep 2026 |
  | Total amount | HK$795 |
- Benchmark receipt 8 (fictional) and its saved output.
- Less manual work / Less reading and retyping of receipt details by hand.
- Wider coverage / Check far more receipts than a small manual sample.
- Reusable data / The same structured data can feed many audit tests.
- Initial future target: 500 to 1,000 receipts and more fields from the auditor checklist. Not yet demonstrated.

  Notes: The workflow runs today on our benchmark receipts: Azure Document Intelligence reads the receipt text and layout, Azure OpenAI selects the audit-relevant fields, and the result is structured data. The example is benchmark receipt 8, a fictional bilingual medical-centre receipt that was printed and photographed. The output shown is the saved extraction result; all six fields match the ground truth. The receipt also names a nurse and an amount covered by the health plan; the AI returned the attending doctor and the receipt total. Potential benefits: less manual reading and transcription, wider coverage than a small sample, and data that can be reused across audit tests. Our initial future target is 500 to 1,000 receipts and more fields from the auditor checklist, such as diagnosis, clinic name and itemised charges. That target has not been demonstrated; so far the workflow has been run on 9 development receipts for six fields.

## Slide 4 (main slide 3)

- Three Approaches Tested
- ‹#›
- DEVELOPMENT RESULTS
- Azure DI + Azure OpenAI was the most accurate of the three approaches.
  chart 'Accuracy': PaddleOCR + rules 26 of 51 fields=51.0, Azure DI + rules 36 of 51 fields=70.6, Azure DI + Azure OpenAI 49 of 51 fields=96.1
- PaddleOCR + rules / Open-source text reading, then hand-written rules
- Azure DI + rules / Azure text reading, then the same rules
- Azure DI + Azure OpenAI / Azure text reading, then AI extraction
- Development results, not production accuracy / Measured on 9 development receipts, mainly fictional mock receipts. Accuracy on new, representative receipts still needs independent validation.

  Notes: We ran three approaches on the same 9 receipts and scored six fields: practitioner, registration number, patient, receipt number, treatment date and total amount. Accuracy = correct fields out of 51 (9 receipts x 6 fields, less 3 receipts with no registration number). PaddleOCR + rules: 26/51 (51.0%); Azure DI + rules: 36/51 (70.6%); Azure DI + Azure OpenAI: 49/51 (96.1%). These are development results from nine receipts, mainly fictional mock receipts: seven printed and photographed, two carried over from an earlier test round. They are not production accuracy. Accuracy by field is in appendix A1. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 5 (main slide 4)

- Why AI Instead of OCR and Rules?
- ‹#›
- DEVELOPMENT RESULTS
- OCR reads the text; AI uses the context to pick the correct field.
- 1  Who treated the patient?
  | Correct value | CHEUNG Hoi Ying |
  | PaddleOCR + rules | ✗ Dr. Kwok Man Hin |
  | Azure DI + rules | ✗ Dr. Kwok Man Hin |
  | Azure DI + Azure OpenAI | ✓ CHEUNG Hoi Ying |
- The rules took the referring doctor. The AI found the treating physiotherapist.
- 2  Which date is the treatment?
  | Correct value | 16 Jul 2026 |
  | PaddleOCR + rules | ✗ 17 Jul 2026 |
  | Azure DI + rules | ✗ 17 Jul 2026 |
  | Azure DI + Azure OpenAI | ✓ 16 Jul 2026 |
- The rules took the date the receipt was issued, not the treatment date.
- 3  What was actually charged?
  | Correct value | HK$1,575 |
  | PaddleOCR + rules | ✗ HK$1,750 |
  | Azure DI + rules | ✗ HK$1,750 |
  | Azure DI + Azure OpenAI | ✓ HK$1,575 |
- The rules took the amount before the 10% member discount.
- AI can also make mistakes: on one receipt it returned a doctor's name the OCR had misread. Extracted values still need checking.

  Notes: Three examples from the benchmark receipts. Receipt 6 (physiotherapy): both rule methods took the referring doctor, Dr. Kwok Man Hin, as the practitioner, and the date the receipt was issued (17 Jul 2026) as the treatment date; the AI returned the treating physiotherapist, CHEUNG Hoi Ying, and the session date, 16 Jul 2026. Receipt 5 (dental): both rule methods returned HK$1,750, the amount before the 10% member discount; the AI returned the HK$1,575 actually charged. In each case the text was read correctly; the difference is understanding what the text means. On the same dental receipt PaddleOCR also misread several labels, so the rules missed further fields; Azure DI read them correctly. The AI also makes mistakes: on receipt 9 (a vet invoice) the OCR misread a clinician's name and the AI returned the misread name (Dr. Lok Vichol); on receipt 10 it returned the wrong date. Extracted values still need validation. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 6 (main slide 5)

- Advantages, Limitations and Alternatives
- ‹#›
- Each approach has trade-offs; AI handled varied receipts best in our test.
  | Approach | Advantages | Limitations |
  | PaddleOCR + rules | + Runs in-house; transparent rules | − Least accurate in our test; rules break when layouts or labels change |
  | Azure DI + rules | + Better text reading; predictable, explainable results | − Rules must be written and maintained for each new receipt format |
  | Azure DI + Azure OpenAI | + Most accurate in our test; uses context; fewer format-specific rules | − Can still make mistakes; needs validation, monitoring and confirmed costs |
- Feasible alternative: OCR + regex + doctor database  (not benchmarked) / Matches registered doctor names and flags no-match or multiple-match receipts for manual review. It does not extract the other receipt fields, such as patient, dates and amounts.

  Notes: PaddleOCR + rules runs in-house with transparent rules, but was the least accurate in our test and its rules break when layouts or labels change. Azure DI + rules reads text better and gives predictable, explainable results, but the rules must be written and maintained for each new receipt format. Azure DI + Azure OpenAI was the most accurate and uses context, with fewer format-specific rules, but it can still make mistakes and needs validation, monitoring and confirmed Azure costs (prices not yet confirmed). Alternative: OCR + regex + the doctor database. OCR reads the receipt and a regex search looks for registered doctor names (about 40,000 in the database); no match or several matches go to manual review. It is a feasible, low-cost way to match registered doctor names and flag exceptions, but it does not extract the other receipt fields, and it was not benchmarked.

## Slide 7 (main slide 6)

- Future Audit Analytics
- ‹#›
- FUTURE · NOT IMPLEMENTED
- Extracted receipt data could support practical audit tests later.
- 1
- Receipt amount vs claim / Does the claimed amount match the amount on the receipt? / Uses: Receipt total, claimed amount
- 2
- Treatment dates / Does the treatment date match the claim and fall within the policy period? / Uses: Treatment date, claim and policy dates
- 3
- Duplicate receipts / Has the same receipt been used for more than one claim? / Uses: Receipt number, date, amount, provider
- 4
- Unusual provider fees / Are charges far from the usual range for the treatment? / Uses: Itemised charges, provider
- Later, on another authorized platform: joined with claims data. Not implemented yet; any flag still needs auditor review.
- Some tests need fields beyond the six tested, such as clinic name and itemised charges.

  Notes: Examples that use extracted receipt information, drawn from the business auditor checklist. Receipt amount versus the claimed amount. Treatment date versus the claim and the policy coverage period. Duplicate receipts: the same receipt number, treatment date, amount and provider across claims. Unusual provider fees: charges far from the usual range for a treatment. These tests would run later on another authorized internal platform, where the receipt data can be joined with claims and policy data. They are not implemented yet. Some need fields beyond the six we tested, such as clinic name and itemised charges. Any flag would still need auditor review before it supports a finding.

## Slide 8 (main slide 7)

- Privacy and Platform Design
- ‹#›
- TO BE AGREED
- Only approved receipt data goes to Azure; claims, policy and historical records stay internal.
- Azure: approved receipt data only
- Receipt  →  Azure DI  →  Azure OpenAI  →  Structured data / Reads receipts and extracts the fields
- →
- Another authorized internal platform
- Claims, policy and historical records / Future audit analytics would run here
- Still to be agreed
- PII protection / Method not yet chosen or approved
- Storage / Where data is kept, and for how long
- Access controls / Who can see receipts and results
- Approved transfer / How results move between platforms

  Notes: Azure would process only approved receipt data: reading the receipt and extracting the fields. Claims records, policy information and historical data stay on another authorized internal platform, where any future audit analytics would run. Still to be agreed: how personal information is protected (no masking or redaction method has been chosen or approved), where data is stored and for how long, who can access it, and the approved method for transferring structured results between the two platforms.

## Slide 9 (main slide 8)

- Conclusion and Next Steps
- ‹#›
- A working AI extraction workflow, with clear next steps to test its value.
- What we demonstrated / A working receipt-to-structured-data workflow / Three approaches compared; AI was the most accurate / AI handled context that fixed rules missed
- Why it matters / Less manual reading of receipts / Wider coverage than a small sample / Reusable data for future audit analytics
- Next priorities: what needs validation
- 1
- Expand receipt extraction / More fields from the auditor checklist, working toward 500 to 1,000 receipts.
- 2
- Validate independently / Test accuracy and practical time benefits on new, representative receipts.
- 3
- Confirm privacy and platform design / Agree PII protection, storage, access and the approved transfer.

  Notes: What we demonstrated: a working receipt extraction workflow with Azure Document Intelligence and Azure OpenAI, and a comparison of three approaches on 9 development receipts, where the AI approach was the most accurate and handled context the rules missed. Why it matters: structured receipt data could reduce manual reading, widen coverage beyond a small sample, and be reused for audit analytics. What needs validation next: (1) Expand receipt extraction: More fields from the auditor checklist, working toward 500 to 1,000 receipts. (2) Validate independently: Test accuracy and practical time benefits on new, representative receipts. (3) Confirm privacy and platform design: Agree PII protection, storage, access and the approved transfer. Processing 500 to 1,000 receipts, broader field extraction, automated audit checks and time savings are future goals, not yet demonstrated.

## Slide 10 (appendix A1)

- Appendix A1: Accuracy by Field
- ‹#›
- APPENDIX
- Azure DI + Azure OpenAI was the most accurate on every one of the six fields.
  | Field | PaddleOCR + rules | Azure DI + rules | Azure DI + Azure OpenAI |
  | Practitioner | 44.4%  (4/9) | 55.6%  (5/9) | 88.9%  (8/9) |
  | Registration no. | 16.7%  (1/6) | 50.0%  (3/6) | 100.0%  (6/6) |
  | Patient | 66.7%  (6/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | Receipt no. | 55.6%  (5/9) | 88.9%  (8/9) | 100.0%  (9/9) |
  | Treatment date | 44.4%  (4/9) | 66.7%  (6/9) | 88.9%  (8/9) |
  | Total amount | 66.7%  (6/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | All fields | 51.0%  (26/51) | 70.6%  (36/51) | 96.1%  (49/51) |
- Development results from 9 receipts, mainly fictional mock receipts; not production accuracy. Green = best for that field. The registration number is printed on 6 of the 9 receipts.

  Notes: Correct fields per field, from the saved results: Practitioner: PaddleOCR + rules 4/9, Azure DI + rules 5/9, Azure DI + Azure OpenAI 8/9; Registration no.: PaddleOCR + rules 1/6, Azure DI + rules 3/6, Azure DI + Azure OpenAI 6/6; Patient: PaddleOCR + rules 6/9, Azure DI + rules 7/9, Azure DI + Azure OpenAI 9/9; Receipt no.: PaddleOCR + rules 5/9, Azure DI + rules 8/9, Azure DI + Azure OpenAI 9/9; Treatment date: PaddleOCR + rules 4/9, Azure DI + rules 6/9, Azure DI + Azure OpenAI 8/9; Total amount: PaddleOCR + rules 6/9, Azure DI + rules 7/9, Azure DI + Azure OpenAI 9/9. The registration number is printed on 6 of the 9 receipts. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 11 (appendix A2)

- Appendix A2: How the Benchmark Was Run
- ‹#›
- APPENDIX
- A small, controlled comparison to choose an extraction approach, not a production test.
- What was tested / 9 development receipts, mainly fictional mock receipts: seven printed and photographed, two carried over from an earlier test round / Six fields: practitioner, registration number, patient, receipt number, treatment date, total amount / 51 scored fields (3 receipts have no registration number) / The same receipt images for all three approaches
- Why the results are directional / The rules were written after these receipts were examined (fixed before scoring) / The AI instructions were refined after reviewing errors on these receipts / Too few unseen receipts exist to validate any approach
- Future goals, not yet tested / More fields from the auditor checklist, such as diagnosis, clinic name and itemised charges / Processing 500 to 1,000 receipts / Automated audit checks and time savings / The OCR + regex + doctor database alternative

  Notes: Dataset: seven fictional receipts printed and photographed with a phone (general practitioner, specialist, hospital, Chinese medicine, dental, physiotherapy and medical centre), plus two sample receipts carried over from an earlier test round (a vet invoice and a pharmacy receipt). A pharmacy till slip was not photographed and is not scored. All three approaches read the same image files. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.
