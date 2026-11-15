# OCR_Benchmark_V12.pptx: text, chart data and notes


## Slide 1

- PaddleOCR + Rules · Azure DI + Rules · Azure DI + AOAI / 9 test receipts · 6 fields
- Medical Receipt Extraction: Which Approach?

  Notes: We compared three ways of extracting information from medical receipts and recommend Azure DI + AOAI. Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 2

- Summary
- ‹#›
- We recommend Azure DI + AOAI for receipt information extraction.
- 1
- Most accurate / Highest accuracy overall and on every one of the six fields (slides 3 and 4).
- 2
- Reads the context / Picks the right name, date or amount where fixed rules pick the wrong one (slide 6).
- 3
- Easier to extend / New layouts and fields can often be handled through instructions, with fewer hand-written rules to maintain.
- Where it runs: receipts are processed on Azure; audit checks happen in another authorized system (slide 9).

  Notes: Three reasons: it was the most accurate overall and on every field; it uses the context of the receipt to pick the right name, date or amount where fixed rules pick the wrong one; and new layouts and fields can often be handled through its instructions instead of new hand-written rules (not guaranteed). Receipt extraction runs on Azure; audit checks happen in another authorized system. Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 3

- Overall Accuracy
- ‹#›
- Azure DI + AOAI extracted 49 of 51 fields correctly.
  chart 'Accuracy': PaddleOCR + Rules 26/51=51.0, Azure DI + Rules 36/51=70.6, Azure DI + AOAI 49/51=96.1
- PaddleOCR + Rules / Open-source text reading, then hand-written rules
- Azure DI + Rules / Azure text reading, then the same rules
- Azure DI + AOAI / Azure text reading, then AI extraction
- 9 test receipts. The rules and AOAI instructions were developed with these receipts; results are not yet independently validated.

  Notes: Accuracy = correct fields out of 51 (9 receipts, 6 fields; 3 receipts have no registration number). PaddleOCR + Rules: 51.0% (26/51); Azure DI + Rules: 70.6% (36/51); Azure DI + AOAI: 96.1% (49/51). Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 4

- Accuracy by Field
- ‹#›
- Azure DI + AOAI was the most accurate on every field, with the biggest gains on doctor and registration no.
  | Field | PaddleOCR + Rules | Azure DI + Rules | Azure DI + AOAI |
  | Doctor | 44.4%  (4/9) | 55.6%  (5/9) | 88.9%  (8/9) |
  | Registration no. | 16.7%  (1/6) | 50.0%  (3/6) | 100.0%  (6/6) |
  | Patient | 66.7%  (6/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | Receipt no. | 55.6%  (5/9) | 88.9%  (8/9) | 100.0%  (9/9) |
  | Service date | 44.4%  (4/9) | 66.7%  (6/9) | 88.9%  (8/9) |
  | Total | 66.7%  (6/9) | 77.8%  (7/9) | 100.0%  (9/9) |
  | All fields | 51.0%  (26/51) | 70.6%  (36/51) | 96.1%  (49/51) |
- 9 test receipts. The rules and AOAI instructions were developed with these receipts; results are not yet independently validated. Green = best for that field. Registration number is printed on 6 of the 9 receipts.

  Notes: Correct fields per field, from the saved results: Doctor: PaddleOCR + Rules 4/9, Azure DI + Rules 5/9, Azure DI + AOAI 8/9; Reg. no.: PaddleOCR + Rules 1/6, Azure DI + Rules 3/6, Azure DI + AOAI 6/6; Patient: PaddleOCR + Rules 6/9, Azure DI + Rules 7/9, Azure DI + AOAI 9/9; Receipt no.: PaddleOCR + Rules 5/9, Azure DI + Rules 8/9, Azure DI + AOAI 9/9; Service date: PaddleOCR + Rules 4/9, Azure DI + Rules 6/9, Azure DI + AOAI 8/9; Total: PaddleOCR + Rules 6/9, Azure DI + Rules 7/9, Azure DI + AOAI 9/9. Registration number is printed on 6 of the 9 receipts. Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 5

- Example 1: Why Azure DI + Rules Beat PaddleOCR + Rules
- ‹#›
- Same rules on both. PaddleOCR misread the labels, so the rules could not find the values.
- 10 more errors with PaddleOCR / All from misreading label text. The rules were the same. / On this receipt: 4 fields lost
  | Field | Correct value | PaddleOCR + Rules read the label as… | Azure DI + Rules read it as… |
  | Registration no. | D03158 | ✗ Reg.No.註冊編號  words run together → not found | ✓ Reg. No. 註冊編號  → found |
  | Treatment date | 27/06/2026 | ✗ TreatmentDate治療日期  words run together → not found | ✓ Treatment Date 治療日期  → found |
  | Receipt no. | DEN-77342 | ✗ Receipt No.收據编號  wrong character (simplified 编) → not found | ✓ Receipt No. 收據編號  → found |
- Receipt 5, a bilingual dental receipt. Same rules on both methods; only the text reading differs.

  Notes: Both methods use exactly the same rules; only the text reading differs. PaddleOCR + Rules made 10 more errors than Azure DI + Rules, every one from misreading a label (words run together, a wrong character, a misread HK$ sign), checked against the receipt photos. On this dental receipt it lost four fields. Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 6

- Example 2: Why Azure DI + AOAI Beat Azure DI + Rules
- ‹#›
- Both read the same Azure DI text. AOAI understood the context; the rules followed fixed patterns.
  | Field | Correct | Azure DI + Rules | Azure DI + AOAI |
  | Practitioner Receipt 6 | CHEUNG Hoi Ying | ✗ Dr. Kwok Man Hin took the referring doctor | ✓ CHEUNG Hoi Ying |
  | Service date Receipt 6 | 16 Jul 2026 | ✗ 17 Jul 2026 took the date the receipt was issued | ✓ 16 Jul 2026 |
  | Total Receipt 6 | HK$1,200 | ✗ not found could not read the card layout | ✓ HK$1,200 |
  | Total Receipt 5 | HK$1,575 | ✗ HK$1,750 added up the items, ignored the discount | ✓ HK$1,575 |
- Why it matters: rules need a new hand-written rule for each case like this; AOAI used the context it was given.
- AOAI got these right even before its instructions were refined.

  Notes: Same Azure DI text for both. On receipt 6 (physiotherapy) the rules took the referring doctor as the practitioner, the issue date as the session date, and could not read the total from the card row. On receipt 5 the rules added up the items and missed the 10% discount. AOAI got all four right, and already did so before its instructions were refined. Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 7

- Manager's Proposal: The Doctor Database
- ‹#›
- Exact matching can find registered doctor names, but cannot reliably tell who treated the patient.
- How it works
- 1
- OCR reads the receipt / Text from the receipt image
- 2
- Look up the doctor registry / ~40,000 registered doctors · up to ~80,000 English and Chinese name variants
- 3
- Strict exact match / Names must match exactly · no AOAI
- Advantages
- ✓ Simple to implement
- ✓ Low additional cost
- ✓ Consistent matching
- ✓ Easy to verify
- Limitations: a name match is not the treating practitioner
- Receipt 6
- Referring doctor / “Referred by Dr. Kwok Man Hin”, but the treatment was by physiotherapist CHEUNG Hoi Ying.
- Receipt 9
- Several practitioners / A clinician (Angel Tseng) and a signing vet (Dr. Lok Yi Choi). Which one treated?
- Receipt 9
- OCR error / “Dr. Lok Yi Choi” was read as “Dr. Lok Vichol”, so exact matching finds nothing.
- Hypothetical
- Doctor is the patient / The patient's own name could match the registry, although they did not treat anyone.
- To be fair: if we only need to know whether a registered doctor appears, exact matching may be sufficient.
- Proposal only: not benchmarked, and no implementation is needed now. Receipt names are fictional, so registry match rates were not measured.

  Notes: Proposal: OCR reads the receipt, then the recognised text is matched against the registry of about 40,000 registered doctors (potentially about 80,000 English and Chinese name variants) using strict exact matching, without AOAI. Advantages: simple to implement, low additional cost, consistent results, and every match is easy to verify against the registry. Limitations, from our receipts: receipt 6 names a referring doctor (Dr. Kwok Man Hin) while the treatment was by physiotherapist CHEUNG Hoi Ying, and the rules already took the referring doctor; receipt 9 (a vet invoice) lists a clinician (Angel Tseng) and a signing vet (Dr. Lok Yi Choi); and Azure DI read 'Dr. Lok Yi Choi' as 'Dr. Lok Vichol', so an exact match finds nothing. Hypothetical, not in our receipts: a patient who is a registered doctor would match the registry. To be fair: if the requirement is only to know whether a registered doctor's name appears, exact matching may be sufficient. Matching also depends on the registry containing the practitioner (dentists, physiotherapists and vets may be on other registers). Not benchmarked; no implementation is planned for this deck. The names on our test receipts are fictional, so registry match rates were not measured.

## Slide 8

- Advantages and Disadvantages
- ‹#›
- Azure DI + AOAI wins on accuracy and flexibility; rules win on cost and transparency.
  |  | PaddleOCR + Rules / Azure DI + Rules | Azure DI + AOAI |
  | Accuracy | − Lower on every field (slides 3 and 4) | + Highest overall and on every field |
  | New receipt layouts | − May need new hand-written rules | + Often handled through instructions |
  | Maintenance | − Rules written and retested by hand | + Fewer rules to maintain; still tested |
  | Cost | + PaddleOCR: no per-receipt fee | − Azure fees per receipt (to confirm) |
  | Transparency | + Every result traced to a rule | − Harder to explain; can be confidently wrong |
- Green = stronger side. Azure prices are not yet confirmed.

  Notes: Accuracy as on slide 3. New layouts: rules may need new hand-written rules and retesting; AOAI can often handle varied wording through its instructions, not guaranteed. Cost: PaddleOCR runs on our own compute with no per-receipt fee; Azure services charge per receipt (prices to be confirmed). Transparency: every rule result can be traced to a rule; AOAI is harder to explain and can return a confident wrong value, so results still need checking. Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.

## Slide 9

- Recommendation
- ‹#›
- Most accurate in our test; next, a pilot on approved receipts.
- Use Azure DI + AOAI for receipt information extraction / Next step: a pilot that adds more receipt fields and tests them on approved receipts.
- Where it runs / Only receipt data goes to Azure. Audit checks happen in another authorized system; claims and policy data stay there.
- What auditors need / Receipt details such as names, dates, amounts and treatments. Extraction supplies information; it does not decide whether a claim is valid.
- 9 test receipts. The rules and AOAI instructions were developed with these receipts; results are not yet independently validated.

  Notes: Recommendation: Azure DI + AOAI for receipt information extraction, starting with a pilot. Business context: receipts are processed on Azure; audit checks happen in another authorized system, and claims or policy data are not uploaded to Azure; the transfer between them still needs approval. The business auditors need receipt details such as names, dates, amounts and treatments to support their checks; extraction supplies information, it does not decide whether a receipt is genuine or a claim valid. Next step: test more receipt fields on approved receipts. Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to validate. Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv), results/v1_heldout, and extraction JSON.
