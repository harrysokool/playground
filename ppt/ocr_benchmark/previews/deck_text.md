# OCR_Benchmark_V15.pptx: text, chart data and notes


## Slide 1 (cover)

- Turning medical receipts into structured, reusable audit data / Proposed approach, evidence and next steps
- Medical Receipt Data Extraction for Internal Audit

  Notes: This deck explains the receipt-data problem, the proposed extraction solution, the value it could bring to Internal Audit, why we prefer the AI approach, and how the solution and later audit tests would be governed. The current priority is reliable extraction of important receipt information into structured data. Downstream audit tests are possible later uses of that data, not the current scope.

## Slide 2 (main slide 1)

- The Problem and Our Proposed Solution
- ‹#›
- CURRENT PROJECT SCOPE
- Build a reliable receipt-data extraction layer so auditors can use receipt information at greater scale.
- The problem
- Important information is locked inside unstructured medical receipts.
- Business auditors read sampled receipts by hand and compare them with the claims system.
- Manual extraction limits how many receipts can be reviewed.
- Proposed solution
- 1
- Read: Azure Document Intelligence (DI) reads the receipt text and layout.
- 2
- Extract: Azure OpenAI identifies the audit-relevant fields and returns them in a fixed structure.
- 3
- Export: The structured data is exported for later audit testing and analysis.
- Current focus: reliable extraction and structured export. Audit tests that use the data are a later stage.

  Notes: Problem: important information is locked inside unstructured medical receipts. Business auditors read sampled receipts by hand and compare them with the claims system, which limits how many receipts can be reviewed. Solution: Azure Document Intelligence reads the receipt; Azure OpenAI identifies the audit-relevant fields and returns them in a fixed structure; the structured data is exported for later audit testing and analysis. The current project covers reading, extraction and structured export. Audit tests that use the data are a later stage.

## Slide 3 (main slide 2)

- What Reliable Receipt Data Could Bring
- ‹#›
- FUTURE POSSIBILITY
- Structured receipt data can widen coverage, reduce manual work and support new audit tests.
- 1
- Broader coverage / Move from a limited manual sample toward population-scale screening of available, supported receipts.
- 2
- Improved efficiency / Less manual reading, field identification and transcription. More auditor time for exceptions and judgement.
- 3
- Automation of manual testing / Structured fields can later be compared automatically with claims-system and policy data.
- 4
- Additional insight / Supports duplicate screening, practitioner checks, pattern analysis and other future tests.
- Potential, not yet measured. Auditors keep responsibility for judgement and conclusions.

  Notes: Four areas of potential value. Broader coverage: move from a limited sample toward population-scale screening of the available and supported receipts. Improved efficiency: less manual reading, field identification and transcription, so auditors spend more time on exceptions and judgement. Automation of manual testing: structured receipt fields can later be compared automatically with claims-system and policy data. Additional insight: duplicate screening, practitioner checks, pattern analysis and other future tests. These are potential benefits: none has been measured yet, and the data does not provide full audit assurance. Auditors keep responsibility for judgement and conclusions.

## Slide 4 (main slide 3)

- Why the Current Process Does Not Scale
- ‹#›
- The bottleneck is access to receipt data, not auditor effort.
- ~25 / receipts in a manual sample / Illustrative example only, not a confirmed audit sample size.
- Limited sample:  Only a small number of receipts can be read and checked by hand.
- Varied formats:  Clinics, hospitals and practitioners use different languages, labels and layouts.
- Manual identification:  Practitioner, patient, treatment date, diagnosis, treatment items and amount are found by eye.
- Repetitive work:  The same reading and transcription is repeated for each receipt and procedure.
- Not reusable:  Receipt information stays unstructured, so cross-claim and population analysis is hard.
- In short: this is a data-access and scalability problem. Structured receipt data would let auditors look further than a small sample.

  Notes: Today business auditors review a limited sample of receipts; around 25 is used here only as an illustrative example, not a confirmed audit sample size. Receipt formats vary across clinics, hospitals, practitioners, languages and layouts. Auditors identify the practitioner, patient, treatment date, diagnosis, treatment items and amount by hand, which is repetitive and time-consuming. The information stays unstructured and hard to reuse, and small samples limit cross-claim and population-level analysis. This is a data-access and scalability problem, not a criticism of the auditors' work.

## Slide 5 (main slide 4)

- How AI Changes the Audit Process
- ‹#›
- Extract once, then reuse the structured data across many audit tests.
- Proposed extraction scope
- Future stage (not being built now)
- Medical receipts / Images or PDFs
- →
- OCR / Azure DI reads the text
- →
- AI extraction / Azure OpenAI finds the fields
- →
- Structured dataset / Exported receipt data
- →
- Audit testing / Compare with claims and policy
- →
- Auditor review / Exceptions and judgement
  | Current approach | AI-enabled approach |
  | Limited manual sample | Potential population-scale receipt processing |
  | Manual reading and transcription | Automated field extraction |
  | Receipt reviewed separately for each procedure | Structured data reused across tests |
  | Auditor effort spent on normal and exceptional cases | Greater focus on exceptions |
  | Limited cross-claim analysis | Potential additional analytics and insights |
- The current project covers extraction and structured export. Audit testing and review that use the data are a later stage.

  Notes: Future flow: medical receipts, then OCR (Azure Document Intelligence), then AI extraction (Azure OpenAI), then a structured receipt dataset that is exported. These first four steps, including the structured export, are the proposed extraction scope. Downstream audit testing and auditor review are a future stage. The table compares today's approach with what an AI-enabled approach could offer; the right-hand column describes potential, not results already achieved.

## Slide 6 (main slide 5)

- Three Approaches Tested
- ‹#›
- TESTED · DEVELOPMENT SET
- Azure DI + Azure OpenAI was the most accurate approach on our development set.
  chart 'Accuracy': PaddleOCR + rules 26 of 51 fields=51.0, Azure DI + rules 36 of 51 fields=70.6, Azure DI + Azure OpenAI 49 of 51 fields=96.1
- PaddleOCR + rules / Open-source text reading, then hand-written rules
- Azure DI + rules / Azure text reading, then the same rules
- Azure DI + Azure OpenAI / Azure text reading, then AI extraction
- How to read these results / Measured on a small development set of 9 receipts, mainly fictional mock receipts. Directional only: they do not establish production accuracy. An independent, representative validation set is still required.

  Notes: We ran three approaches on the same 9 receipts and scored six fields: practitioner, registration number, patient, receipt number, treatment date and total amount. Accuracy = correct fields out of 51 (9 receipts x 6 fields, less 3 receipts with no registration number). PaddleOCR + rules: 26/51 (51.0%); Azure DI + rules: 36/51 (70.6%); Azure DI + Azure OpenAI: 49/51 (96.1%). The dataset is a small development set of 9 receipts, mainly fictional mock receipts: seven fictional receipts printed and photographed with a phone, plus two sample receipts carried over from an earlier test round. The results are directional only and do not establish production accuracy. An independent and representative validation set is still required. Accuracy by field is in appendix A1. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 7 (main slide 6)

- What the Differences Look Like on a Receipt
- ‹#›
- TESTED · DEVELOPMENT SET
- Reading the text is not enough: extraction must understand what the text means.
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
- The AI is not perfect either: on one receipt it returned a practitioner name the OCR had misread, so extracted values still need validation.

  Notes: Three examples from the benchmark receipts. Receipt 6 (physiotherapy): both rule methods took the referring doctor, Dr. Kwok Man Hin, as the practitioner, and the date the receipt was issued (17 Jul 2026) as the treatment date; the AI returned the treating physiotherapist, CHEUNG Hoi Ying, and the session date, 16 Jul 2026. Receipt 5 (dental): both rule methods returned HK$1,750, the amount before the 10% member discount; the AI returned the HK$1,575 actually charged. In each case the OCR read the text correctly; the difference is in understanding what the text means. Further detail for questions: on the same dental receipt PaddleOCR also misread labels (words run together, a wrong Chinese character), so the rules could not find the registration number, treatment date and receipt number; Azure DI read them correctly. The AI was not perfect: on receipt 9 (a vet invoice) the OCR misread a clinician's name and the AI returned the misread name (Dr. Lok Vichol); on receipt 10 it returned the wrong date. Extracted values still need validation, especially missing, ambiguous or unsupported values. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 8 (main slide 7)

- Trade-offs and Scalability
- ‹#›
- The AI approach is preferred, but no option is perfect.
  | Approach | Advantages | Limitations |
  | PaddleOCR + rules | Low software dependency; transparent rules | Lower accuracy in the benchmark; more preprocessing; rules depend heavily on layout and wording |
  | Azure DI + rules | Stronger document reading; deterministic and explainable | Rules must be created and maintained as formats and labels change |
  | Azure DI + Azure OpenAI | Highest development-set accuracy; stronger contextual interpretation; less dependence on format-specific rules | Needs prompt and schema governance, independent validation, monitoring, PII controls and Azure cost management (prices to be confirmed) |
- Scalability: rules-only approaches can require repeated maintenance for new receipt formats. Contextual AI may adapt better to format variation, but it still needs controlled prompts, schemas, testing and monitoring.
- Alternative raised: OCR + regex + doctor database  (not benchmarked) / A simple, low-cost way to identify registered doctor names and flag no-match or multiple-match receipts for manual review. It does not extract the other receipt fields, such as patient, dates and amounts.

  Notes: PaddleOCR + rules: low software dependency and transparent rules, but lower accuracy in the benchmark, more preprocessing, and rules that depend heavily on layout and wording. Azure DI + rules: stronger document reading, deterministic and explainable, but rules must be created and maintained as formats and labels change. Azure DI + Azure OpenAI: highest development-set accuracy, stronger contextual interpretation and less dependence on format-specific rules, but it requires prompt and schema governance, independent validation, monitoring, PII controls and Azure cost management; Azure prices are not yet confirmed. Scalability: rules-only approaches can require repeated maintenance for new receipt formats; contextual AI may adapt better to format variation, but it still needs controlled prompts, schemas, testing and monitoring. Alternative raised by management: OCR + regex + the doctor database. OCR reads the receipt and a regex search looks for registered doctor names (about 40,000 in the database); no match or several matches go to manual review. It is a simple, low-cost way to identify registered names and flag exceptions. It does not extract the other receipt fields (patient, dates, amounts, diagnosis), and it was not benchmarked.

## Slide 9 (main slide 8)

- Future Audit Tests the Data Could Support
- ‹#›
- FUTURE POSSIBILITY
- Reliable extraction is the foundation for later tests. These tests are not being built now.
- Possible tests of control (deterministic)
- Required receipt information is present / Receipt amount matches the claimed amount / Treatment date matches the claims-system date / Service date falls within the policy period / Claim amount follows the approval-authority matrix
- Possible red-flag tests
- Possible duplicate receipt / Practitioner cannot be matched or is ambiguous / Diagnosis and treatment appear inconsistent / Unusual claim, clinic, practitioner or receipt patterns
- Boundary: these tests need separate business rules, internal data, validation and auditor review. An AI-generated red flag is not an audit finding. / Diagnosis and treatment items are not yet extracted or tested.

  Notes: Two kinds of possible future use. Tests of control or deterministic tests: required receipt information is present; the receipt amount matches the claimed amount; the treatment date matches the claims-system date; the service date falls within the policy period; the claim amount follows the approval-authority matrix. Red-flag tests: possible duplicate receipt; the practitioner cannot be matched or is ambiguous; diagnosis and treatment appear inconsistent; unusual claim, clinic, practitioner or receipt patterns. These downstream tests require separate business rules, internal data, validation and auditor review. An AI-generated red flag is not an audit finding. Diagnosis and treatment items were not part of the six-field benchmark, so they are not yet extracted or tested.

## Slide 10 (main slide 9)

- Governance, PII Protection and Platform Design
- ‹#›
- OPEN REQUIREMENT
- Run each activity on the platform best suited to its data, risk and control requirements.
- Azure application (proposed extraction scope)
- Receipt / Approved receipts
- →
- Azure DI / Reads the text
- →
- Azure OpenAI / Extracts the fields
- →
- Structured output / Validated, exported
- PII controls apply across these steps: design to be agreed
- →
- Approved internal platform (future stage)
- Join with internal data → audit tests → auditor review / Claims, policy, approval-authority and historical data stay here. / Transfer from Azure: approved method to be agreed.
- PII protection: decisions still to make / Which receipt fields contain personal or sensitive medical information / Which components need which fields (extraction may need names) / The masking or redaction method (not yet chosen) / How results stay linked to the correct audit record / Approved Azure services, access controls, retention and logging
- Why some tests run on another platform / They need internal data that does not belong in the extraction application: / Claims-system records / Policy coverage and benefit information / Approval-authority tables / Historical claims; customer, provider, clinic or agent data

  Notes: PII protection is a required design step, not a completed solution, and no masking method has been chosen. Decisions still to make: which receipt fields contain personal or sensitive medical information; which components need which fields (extraction may itself need names such as the patient and practitioner); the masking or redaction approach; how approved results stay linked to the correct audit record; and approved Azure services, access controls, retention and logging. Platform separation: reading, contextual extraction, PII controls, basic validation and structured export can run within the Azure application. Some downstream tests may need to run on another approved internal platform because they need internal data: claims-system records, policy coverage and benefit information, approval-authority tables, historical claims, and customer, provider, clinic or agent data. The transfer method between the two must be agreed and approved.

## Slide 11 (main slide 10)

- Recommendation and Next Steps
- ‹#›
- Continue with Azure DI + Azure OpenAI as the preferred extraction approach.
- Recommendation: continue with Azure DI + Azure OpenAI as the preferred extraction approach, subject to independent validation and governance approval. / First establish reliable, traceable receipt extraction. Then use the approved structured output to develop additional audit tests on the appropriate internal platforms.
- Next steps
- 1
- Finalise the required receipt fields and structured-output schema.
- 2
- Confirm the PII protection and data-flow design.
- 3
- Build an independent, representative validation dataset.
- 4
- Measure accuracy by field, including missing and ambiguous values.
- 5
- Define acceptance criteria for critical fields.
- 6
- Confirm which downstream tests run in Azure and which on other approved internal platforms.

  Notes: Recommendation: continue with Azure Document Intelligence plus Azure OpenAI as the preferred extraction approach, subject to independent validation and governance approval. First establish reliable, traceable receipt extraction. Then use the approved structured output to develop additional audit tests on the appropriate internal platforms. Next steps: (1) Finalise the required receipt fields and structured-output schema. (2) Confirm the PII protection and data-flow design. (3) Build an independent, representative validation dataset. (4) Measure accuracy by field, including missing and ambiguous values. (5) Define acceptance criteria for critical fields. (6) Confirm which downstream tests run in Azure and which on other approved internal platforms. Decision requested: agreement to continue on this basis and to proceed with these next steps.

## Slide 12 (appendix A1)

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
- Measured on a small development set of 9 receipts, mainly fictional mock receipts; directional only. Green = best for that field. The registration number is printed on 6 of the 9 receipts.

  Notes: Correct fields per field, from the saved results: Practitioner: PaddleOCR + rules 4/9, Azure DI + rules 5/9, Azure DI + Azure OpenAI 8/9; Registration no.: PaddleOCR + rules 1/6, Azure DI + rules 3/6, Azure DI + Azure OpenAI 6/6; Patient: PaddleOCR + rules 6/9, Azure DI + rules 7/9, Azure DI + Azure OpenAI 9/9; Receipt no.: PaddleOCR + rules 5/9, Azure DI + rules 8/9, Azure DI + Azure OpenAI 9/9; Treatment date: PaddleOCR + rules 4/9, Azure DI + rules 6/9, Azure DI + Azure OpenAI 8/9; Total amount: PaddleOCR + rules 6/9, Azure DI + rules 7/9, Azure DI + Azure OpenAI 9/9. The registration number is printed on 6 of the 9 receipts. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.

## Slide 13 (appendix A2)

- Appendix A2: How the Benchmark Was Run
- ‹#›
- APPENDIX
- A small, controlled comparison to choose an extraction approach, not a production test.
- What was tested / A small development set of 9 receipts, mainly fictional mock receipts: seven printed and photographed, two carried over from an earlier test round / Six fields: practitioner, registration number, patient, receipt number, treatment date, total amount / 51 scored fields (3 receipts have no registration number) / The same receipt images for all three approaches
- Why the results are directional / The rules were written after these receipts were examined (fixed before scoring) / The AI instructions were refined after reviewing errors on these receipts / Too few unseen receipts exist to validate any approach
- Not yet tested / Diagnosis, treatment items and other receipt fields / Real production receipts, handwriting and poor-quality images at volume / The OCR + regex + doctor database alternative / PII protection, cost and processing time at scale

  Notes: Dataset: seven fictional receipts printed and photographed with a phone (general practitioner, specialist, hospital, Chinese medicine, dental, physiotherapy and medical centre), plus two sample receipts carried over from an earlier test round (a vet invoice and a pharmacy receipt). A pharmacy till slip was not photographed and is not scored. All three approaches read the same image files. Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese labels, written after these receipts were examined and fixed before scoring. The AI instructions were refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved (summary.csv, detail.csv) and the saved extraction results.
