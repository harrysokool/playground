# OCR_Benchmark_V20.pptx: text, chart data and notes


## Slide 1 (cover)

- Internal Audit AI project: progress update / What we have built, what we tested and where it could go
- AI-Assisted Medical Receipt Extraction

  Notes: This is a progress update on our medical receipt AI extraction project. We have built and demonstrated a working extraction workflow with Azure Document Intelligence and Azure OpenAI, and benchmarked it against two OCR and rules approaches. Today we will cover the problem, the potential value, what we built, what the benchmark showed, how the data could support future audit tests, the privacy questions still open, and the next steps. The workflow is demonstrated on development receipts; it is not yet validated for audit use.

## Slide 2 (main slide 1)

- Manual Receipt Review Limits Audit Coverage
- 2
- ESTIMATES · NOT MEASURED
- Manually reviewing medical receipts takes significant auditor time and effort, limiting how many receipts can be checked.
- ~25 / receipts in a typical audit sample / Every one / reviewed manually by an auditor / Sample size is a team estimate. Time per receipt not yet measured.
- What auditors check on each receipt   from the business auditor checklist
- Authenticity:  Letterhead, provider registration number, signature and stamp
- Data integrity:  Claimant, provider, treatment date, diagnosis and amounts vs the claims system
- Coverage:  Service date within the policy period; diagnosis covered; charges within agreed fees
- Fraud indicators:  Duplicate receipts by receipt number, treatment date, amount and provider
- The bottleneck: auditor time and effort. Reviewing each receipt manually keeps coverage to a small sample.

  Notes: A typical audit sample includes around 25 receipts. Each one is reviewed manually by an auditor. The sample size is the team's estimate. We have not measured the time per receipt; our rough team estimate is 5 to 10 minutes per receipt, which we plan to confirm with a short time study in the next phase, separating the time spent finding receipt details from investigation time. The checks come from the business auditor checklist: authenticity (letterhead with the provider's legal name, address and registration or licence number; signature and company stamp; no unauthorised alteration); data integrity (claimant name, provider name, treatment date, diagnosis code, receipt amount and claimed amount against the claims system); coverage (date of service within the policy period, diagnosis within coverage, charges within agreed fees); and fraud, waste and abuse indicators such as duplicate receipts by receipt number, treatment date, amount and provider. The bottleneck is auditor time and effort, which keeps coverage to a small sample.

## Slide 3 (main slide 2)

- The Business Value We Are Working Toward
- 3
- POTENTIAL · NOT MEASURED
- Structured receipt data could free auditor time and extend audit coverage.
- Less manual effort
- TODAY / Auditors review each receipt manually.
- WITH EXTRACTED RECEIPT DATA / Receipt details arrive as structured data, ready to check.
- Wider coverage
- TODAY / Coverage is limited to a small sample.
- WITH EXTRACTED RECEIPT DATA / The capability to screen a materially larger receipt population.
- Reusable structured data
- TODAY / Receipt details are not held as structured data.
- WITH EXTRACTED RECEIPT DATA / Extract once, reuse the same data across many audit tests.
- Focus on exceptions
- TODAY / Time goes on manually reviewing routine receipts.
- WITH EXTRACTED RECEIPT DATA / Auditor time goes to the receipts that need judgement.
- Where we are: the extraction workflow is built and demonstrated. These benefits are the expected value; none has been measured yet.

  Notes: These are the benefits we expect if receipt extraction proves reliable at scale. Less manual effort: receipt details arrive as structured data instead of being found manually on each receipt. Wider coverage: the capability to screen a materially larger receipt population than a small manual sample. Reusable structured data: extract once and reuse the same data across audit tests. Focus on exceptions: auditor time goes to the receipts that need judgement. None of these has been measured yet. What is demonstrated today is the extraction workflow itself, on 9 development receipts; time savings and wider coverage would be measured in the next phase. Specific examples of audit tests come later in the deck.

## Slide 4 (main slide 3)

- Our Working Solution
- 4
- WORKING DEMONSTRATION
- We built and demonstrated a workflow that turns a receipt photo into structured data.
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
- Works end to end / Receipt photo in; six audit fields out as structured data.
- Reads the context / Picked the attending doctor, not the nurse, and the receipt total, not the plan-covered amount.
- Benchmarked / Run on 9 development receipts and compared with two OCR and rules approaches.
- Demonstrated so far: the full workflow on 9 development receipts and six fields. More fields and larger volumes are not yet tested.

  Notes: The workflow runs today on our benchmark receipts: Azure Document Intelligence reads the receipt text and layout, Azure OpenAI selects the audit-relevant fields, and the result is structured data. The example is benchmark receipt 8, a fictional bilingual medical-centre receipt that was printed and photographed. The output shown is the saved extraction result; all six fields match the ground truth. The receipt also names a nurse and an amount covered by the health plan; the AI returned the attending doctor and the receipt total. So far the workflow has been run on 9 development receipts for six fields. More fields from the auditor checklist, such as diagnosis, clinic name and itemised charges, and larger representative volumes are not yet tested.

## Slide 5 (main slide 4)

- Why We Tested Three Approaches
- 5
- BENCHMARK DESIGN
- OCR reads the words on a receipt; the hard part is deciding which value belongs in each audit field.
- The challenge:  a receipt often shows several names, dates and amounts. OCR reads them all, but does not decide which is the treating practitioner, the treatment date or the amount actually charged.
  | Approach | Step 1: read the text | Step 2: pick the fields | What the comparison shows |
  | PaddleOCR + rules | PaddleOCR (open source, in-house) | Hand-written rules | A low-cost, in-house baseline |
  | Azure DI + rules | Azure DI | The same rules | Does better text reading alone solve the problem? |
  | Azure DI + Azure OpenAI | Azure DI | Azure OpenAI, using the context | Does AI add accuracy on the same text? |
- Changing one step at a time shows whether the gain comes from better text reading or from AI. All three read the same receipt images and were scored on the same six fields.

  Notes: A medical receipt often shows several names, dates and amounts: a treating and a referring doctor, a treatment date and an issue date, a subtotal and a final charge. OCR, or text reading, reads all of them, but it does not decide which one is the treating practitioner, the treatment date or the amount actually charged. That needs a second step. We compared two ways of doing it, hand-written rules and AI, and two OCR engines. Changing one thing at a time shows where the gain comes from: PaddleOCR + rules versus Azure DI + rules shows the effect of better text reading; Azure DI + rules versus Azure DI + Azure OpenAI shows the effect of using AI with the same text. All three read the same receipt images and were scored on the same six fields.

## Slide 6 (main slide 5)

- Benchmark Results
- 6
- DEVELOPMENT RESULTS
- Azure DI + Azure OpenAI achieved the highest accuracy on our development set.
  chart 'Accuracy': PaddleOCR + rules 26 of 51 fields=51.0, Azure DI + rules 36 of 51 fields=70.6, Azure DI + Azure OpenAI 49 of 51 fields=96.1
- Why it is our preferred approach / Highest accuracy overall and on each of the six fields / Azure DI read text better: both Azure approaches beat PaddleOCR / AI used context where the rules picked the wrong value
- Development results, not production accuracy / Measured on 9 development receipts, mainly fictional mock receipts. Accuracy on new, representative receipts still needs independent validation.

  Notes: We ran three approaches on the same 9 receipts and scored six fields: practitioner, registration number, patient, receipt number, treatment date and total amount. Accuracy = correct fields out of 51 (9 receipts x 6 fields, less 3 receipts with no registration number). PaddleOCR + rules: 26/51 (51.0%); Azure DI + rules: 36/51 (70.6%); Azure DI + Azure OpenAI: 49/51 (96.1%). Both Azure approaches beat PaddleOCR + rules, so better text reading helped; adding AI on the same text helped most. The AI approach was also the most accurate on each of the six fields (appendix A1). This is why Azure DI + Azure OpenAI is our preferred approach. These are development results from nine receipts, mainly fictional mock receipts: seven printed and photographed, two carried over from an earlier test round. They are not production accuracy, and an overall figure combines fields of different importance; the next phase should report accuracy by field and on a locked holdout set. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 7 (main slide 6)

- Why Context Matters: Receipt Examples
- 7
- DEVELOPMENT RESULTS
- In each case the text was read correctly; the rules picked the wrong value and the AI used the context.
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
- AI can also make mistakes: on one receipt it returned a doctor's name the OCR had misread. Independent validation and exception handling are required before audit use.

  Notes: Three examples from the benchmark receipts. Receipt 6 (physiotherapy): both rule methods took the referring doctor, Dr. Kwok Man Hin, as the practitioner, and the date the receipt was issued (17 Jul 2026) as the treatment date; the AI returned the treating physiotherapist, CHEUNG Hoi Ying, and the session date, 16 Jul 2026. Receipt 5 (dental): both rule methods returned HK$1,750, the amount before the 10% member discount; the AI returned the HK$1,575 actually charged. In each case the text was read correctly; the difference is understanding what the text means. On the same dental receipt PaddleOCR also misread several labels, so the rules missed further fields; Azure DI read them correctly. The AI also makes mistakes: on receipt 9 (a vet invoice) the OCR misread a clinician's name and the AI returned the misread name (Dr. Lok Vichol); on receipt 10 it returned the wrong date. Independent validation and exception handling are required before audit use. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 8 (main slide 7)

- Advantages, Limitations and Alternatives
- 8
- Contextual AI handled field ambiguity best in the development benchmark; each approach has trade-offs.
  | Approach | Advantages | Limitations |
  | PaddleOCR + rules | + Runs in-house; transparent rules | − Least accurate in our test; rules break when layouts or labels change |
  | Azure DI + rules | + Better text reading; predictable, explainable results | − Rules need ongoing updates as new layouts, labels, languages and ambiguous fields appear |
  | Azure DI + Azure OpenAI | + Most accurate in our test; uses context; fewer format-specific rules | − Can still make mistakes; needs validation, monitoring and confirmed costs |
- Limited-scope alternative: OCR + doctor-name matching  (not benchmarked) / Matches registered doctor names from the doctor database and sends no-match or multiple-match receipts to manual review. Useful for practitioner screening, but not a substitute for multi-field receipt extraction.

  Notes: PaddleOCR + rules runs in-house with transparent rules, but was the least accurate in our test and its rules break when layouts or labels change. Azure DI + rules reads text better and gives predictable, explainable results, but rules need ongoing updates as new layouts, labels, languages and ambiguous field patterns appear. Azure DI + Azure OpenAI was the most accurate and uses context, with fewer format-specific rules, but it can still make mistakes and needs validation, monitoring and confirmed Azure costs (prices not yet confirmed). Limited-scope alternative: OCR + doctor-name matching. OCR reads the receipt and a regex search looks for registered doctor names (about 40,000 in the doctor database); no match or several matches go to manual review. It is useful, low-cost practitioner screening, but it does not extract the other receipt fields, so it is not a substitute for multi-field extraction, and it was not benchmarked.

## Slide 9 (main slide 8)

- Future Audit Analytics: Example Tests
- 9
- FUTURE · NOT IMPLEMENTED
- Specific audit tests the extracted receipt data could support later, on the Internal Data Platform.
- 1
- Receipt amount vs claim / Does the claimed amount match the amount on the receipt? / Uses: Receipt total, claimed amount
- 2
- Treatment dates / Does the treatment date match the claim and fall within the policy period? / Uses: Treatment date, claim and policy dates
- 3
- Duplicate receipts / Has the same receipt been used for more than one claim? / Uses: Receipt number, date, amount, provider
- 4
- Line item arithmetic / Do the individual charges and discounts add up correctly to the final receipt total? / Uses: Itemised charges, discounts and receipt total (not among the six tested fields)
- Later, on the Internal Data Platform: joined with claims data. Not implemented yet; any flag still needs auditor review.
- Some tests need fields beyond the six tested, such as itemised charges and discounts.

  Notes: Examples of tests that use extracted receipt information; the first three are drawn from the business auditor checklist. Receipt amount versus the claimed amount. Treatment date versus the claim and the policy coverage period. Duplicate receipts: the same receipt number, treatment date, amount and provider across claims. Line item arithmetic: whether the individual charges and discounts add up correctly to the final receipt total. Itemised charges and discounts were not among the six benchmark fields, so this test needs broader extraction first. These tests would run later on the Internal Data Platform, where the receipt data can be joined with claims and policy data. They are not implemented yet. Some need fields beyond the six we tested, such as itemised charges and discounts. Any flag would still need auditor review before it supports a finding.

## Slide 10 (main slide 9)

- Proposed Architecture and Data Flow
- 11
- PROPOSED · NOT IMPLEMENTED
- A proposed design, not yet implemented: only masked OCR text would reach Azure OpenAI.
- The benchmark sent unmasked OCR text to Azure OpenAI, so accuracy on masked text is not yet tested. Masking, transfers and controls still need approval.

  Notes: This slide shows a proposed architecture for future use; it is not implemented or approved. It is different from the benchmark workflow, where Azure Document Intelligence read the receipt images and the unmasked OCR text went straight to Azure OpenAI. The proposed flow has three areas: the Internal Data Platform, an authorized internal environment; SharePoint, a controlled file exchange; and Azure for OCR and AI processing. (1) Approved receipt images are uploaded to SharePoint. (2) Azure Document Intelligence reads the original images, which requires PII approval, and (3) returns the OCR text, which is unmasked and may contain personal information. (4) The Internal Data Platform retrieves the text and masks personal information; customer, claims and policy records stay internal. (5) The masked text is uploaded and (6) Azure OpenAI extracts the fields from masked text only. (7) The results return to SharePoint and (8) the Internal Data Platform retrieves them and links them to the original receipts for audit tests against claims and records. The benchmark used unmasked OCR text, so accuracy on masked text still needs testing. The masking method, data transfers and security controls still require review and approval; the open decisions are on the next slide.

## Slide 11 (main slide 10)

- Privacy and Governance
- 10
- TO BE AGREED
- Masking and data handling must be agreed and approved before real receipts are processed.
- Masking must keep required fields
- Patient and practitioner names are required fields. Masking must protect personal data without losing them, or they must be linked back on the Internal Data Platform.
- Azure DI receives original images
- The full receipt image, which can show diagnosis and contact details, goes to Azure DI. This needs approved data handling controls.
- SharePoint may hold unmasked text
- OCR text returned by Azure DI may sit unmasked in SharePoint before masking. This needs approved data handling controls.
- Benchmark note: the benchmark used unmasked OCR text. Accuracy on masked text must be re-tested.
- Still to be agreed and approved
- PII masking method / Not yet chosen or approved
- Storage and retention / Where data is kept, including SharePoint, and for how long
- Access controls / Who can see receipts, OCR text and results
- Transfer and linkage / How results move and link back to audit records

  Notes: These are the privacy and governance decisions still open for the proposed architecture. Nothing here is implemented or approved, and no masking or redaction method has been chosen. First, masking must keep what the extraction needs: patient and practitioner names are required fields, and the practitioner name is where the AI used context in our examples. The design must protect personal data without losing those fields, or they must be linked back on the Internal Data Platform after extraction. Second, Azure Document Intelligence receives the original receipt images, which can show diagnosis, the patient's name and contact details; this needs approved data handling controls. Third, the OCR text returned to SharePoint is unmasked until masking, so SharePoint may temporarily hold personal information; this also needs approved controls. The benchmark used unmasked OCR text, so extraction accuracy on masked text must be re-tested. Still to be agreed and approved: the PII masking method; where data is stored, including SharePoint, and for how long; who can access receipts, OCR text and results; and how results are transferred and linked back to audit records on the Internal Data Platform, where claims, policy and historical records stay.

## Slide 12 (main slide 11)

- Project Timeline and Target Rollout
- 12
- PLANNED DATES ARE TARGETS
- Built and benchmarked since June 2026; target rollout for audit use in early April 2027.
- COMPLETED
- PLANNED  ·  PROPOSED TARGETS, NOT CONFIRMED
- Mid June 2026
- ✓
- Project kickoff
- Mid July 2026
- ✓
- MVP completed and presented to the Internal Audit team
- Aug – Oct 2026
- ✓
- Application improved, extraction approaches benchmarked and more audit use cases explored
- Nov 2026
- ✓
- Business auditors consulted on their manual audit tests and requirements
- Dec 2026
- Test real masked medical receipts and evaluate extraction accuracy
- Jan – Feb 2027
- Improve accuracy from test results and complete application development
- Mar 2027
- Final validation, user acceptance testing and required approvals
- Early Apr 2027
- ★
- TARGET ROLLOUT / For actual audit use
- Planned dates are proposed targets, not confirmed commitments. They depend on test results and the required approvals, including the privacy controls.

  Notes: Where the project stands and where it is going. Completed: we kicked off in mid June 2026; by mid July 2026 we had completed the MVP and presented it to the Internal Audit team; from August to October 2026 we improved the application, benchmarked the extraction approaches and explored additional audit use cases; and in November 2026 we consulted business auditors to understand their manual audit tests and business requirements. Planned: in December 2026, test real masked medical receipts and evaluate extraction accuracy; in January and February 2027, improve accuracy based on the test results and complete application development; in March 2027, complete final validation, user acceptance testing and the required approvals; and in early April 2027, the target rollout for actual audit use. The planned dates are proposed targets, not confirmed commitments. They depend on the test results and on the required approvals, including the privacy and data handling controls on the previous slide.

## Slide 13 (appendix A1)

- Appendix A1: Accuracy by Field
- 13
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

  Notes: Correct fields per field, from the saved results: Practitioner: PaddleOCR + rules 4/9, Azure DI + rules 5/9, Azure DI + Azure OpenAI 8/9; Registration no.: PaddleOCR + rules 1/6, Azure DI + rules 3/6, Azure DI + Azure OpenAI 6/6; Patient: PaddleOCR + rules 6/9, Azure DI + rules 7/9, Azure DI + Azure OpenAI 9/9; Receipt no.: PaddleOCR + rules 5/9, Azure DI + rules 8/9, Azure DI + Azure OpenAI 9/9; Treatment date: PaddleOCR + rules 4/9, Azure DI + rules 6/9, Azure DI + Azure OpenAI 8/9; Total amount: PaddleOCR + rules 6/9, Azure DI + rules 7/9, Azure DI + Azure OpenAI 9/9. The registration number is printed on 6 of the 9 receipts. The overall figure combines fields of different importance, so field-level results matter. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 14 (appendix A2)

- Appendix A2: How the Benchmark Was Run
- 14
- APPENDIX
- A small, controlled comparison to choose an extraction approach, not a production test.
- What was tested / 9 development receipts, mainly fictional mock receipts: seven printed and photographed, two carried over from an earlier test round / Six fields: practitioner, registration number, patient, receipt number, treatment date, total amount / 51 scored fields (3 receipts have no registration number) / The same receipt images for all three approaches
- Why the results are directional / The rules were written after these receipts were examined (fixed before scoring) / The AI instructions were refined after reviewing errors on these receipts / Too few unseen receipts exist to validate any approach
- Future goals, not yet tested / More fields from the auditor checklist, such as diagnosis, clinic name and itemised charges / Larger, representative receipt volumes on a locked holdout set / Field-level error rates, not only overall accuracy / Automated audit checks and time savings / The OCR + doctor-name matching alternative

  Notes: Dataset: seven fictional receipts printed and photographed with a phone (general practitioner, specialist, hospital, Chinese medicine, dental, physiotherapy and medical centre), plus two sample receipts carried over from an earlier test round (a vet invoice and a pharmacy receipt). A pharmacy till slip was not photographed and is not scored. All three approaches read the same image files. In the next phase, report more than overall accuracy: accuracy by field and for critical fields, missing-value and incorrect-value rates, false extractions when a field is absent, document processing failures, and results on a locked holdout set. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.
