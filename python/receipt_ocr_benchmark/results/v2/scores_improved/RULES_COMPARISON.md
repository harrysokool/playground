# Original rules vs improved rules vs Azure DI + AOAI (Version 2)

**Sources:**
- `summary.csv`, `detail.csv` and `report.md` in this folder;
- the extraction files in `results/v2/extracted_general_*` and `results/v2/extracted_improved_*`;
- the raw OCR in `results/v2/`.

The OCR was not re-run: both rule sets read the same OCR output.

> **The improved-rule results are TUNED on these nine Version 2 receipts.**
> - The rules were written while looking at these receipts, so their scores here show what
>   tuning can reach. They are not an estimate for unfamiliar receipts.
> - Azure DI + AOAI uses a generic prompt written before Version 2 existed.
> - **Update (Oct 2026):** the Version 1 check has now been run (`results/v1_heldout/scores_rules/`).
>   On the four unseen Version 1 receipts the improved rules gained no field; see section 5.

## 1. Results

| Approach | Original rules | Improved rules (tuned) | Change |
|---|---|---|---|
| PaddleOCR Light | 37.3% (19/51) | **88.2% (45/51)** | +26 fields |
| PaddleOCR Heavy | 29.4% (15/51) | 64.7% (33/51) | +18 fields |
| Azure DI | 41.2% (21/51) | **86.3% (44/51)** | +23 fields |
| Azure DI + AOAI | 88.2% (45/51), unchanged | | |

- **Invented values:** 0 for every approach.
- **Receipts processed:** 9/9 for every approach.
- **Time per receipt is unchanged by the rules:** Light 13.9 s, Heavy 53.3 s, DI 3.8 s,
  DI + AOAI 6.2 s.
- **Extraction itself** takes about 10 ms per receipt (Phase 9 measurement).

### By group of receipts

| | Light (improved) | Heavy (improved) | DI (improved) | DI + AOAI |
|---|---|---|---|---|
| 7 new printed receipts (41 fields) | 41/41 (100%) | 29/41 (70.7%) | 40/41 (97.6%) | 39/41 (95.1%) |
| 2 carried-over Version 1 receipts (10 fields) | 4/10 | 4/10 | 4/10 | 6/10 |

### By field (correct / applicable)

| Field | Light orig → impr | Heavy orig → impr | DI orig → impr | DI + AOAI |
|---|---|---|---|---|
| Doctor name | 3 → 8 /9 | 2 → 6 /9 | 3 → 8 /9 | 6/9 |
| Registration no. | 1 → 6 /6 | 1 → 4 /6 | 1 → 6 /6 | 5/6 |
| Patient name | 3 → 7 /9 | 2 → 5 /9 | 3 → 7 /9 | 9/9 |
| Receipt number | 4 → 7 /9 | 3 → 5 /9 | 4 → 7 /9 | 9/9 |
| Service date | 3 → 8 /9 | 2 → 6 /9 | 4 → 8 /9 | 8/9 |
| Total amount | 5 → 9 /9 | 5 → 7 /9 | 6 → 8 /9 | 8/9 |

## 2. Where the improvement came from

Per-receipt correct counts, original → improved (Light / Heavy / DI):

| Receipt | Light | Heavy | DI | Main rule that fixed it |
|---|---|---|---|---|
| receipt1 GP | 5 → 6 | 5 → 6 | 5 → 6 | Registration number inside a line |
| receipt2 Specialist | 4 → 6 | 0 → 0 | 5 → 6 | Mid-line registration number; "HKS" read as "HK$" (Light) |
| receipt3 Hospital | 1 → 5 | 1 → 5 | 1 → 5 | Bilingual labels; distractor IDs and dates |
| receipt4 Chinese medicine | 0 → 6 | 0 → 6 | 0 → 6 | Chinese labels; Chinese date |
| receipt5 Dental | 0 → 6 | 0 → 0 | 0 → 5 | Bilingual and glued labels; qualification removed from the name |
| receipt6 Physiotherapy | 3 → 6 | 3 → 6 | 3 → 6 | Role header + Name row; distractors (referred by, date issued); card-row total |
| receipt8 Medical centre | 1 → 6 | 1 → 6 | 2 → 6 | Bilingual labels; label-is-not-a-value |
| receipt9 Vet (Version 1) | 3 → 2 | 3 → 2 | 3 → 2 | — (regression, see 3.2) |
| receipt10 NZ pharmacy (Version 1) | 2 → 2 | 2 → 2 | 2 → 2 | — |

**The largest gains came from three rules:**
- **Bilingual and Chinese labels:** receipts 3, 4, 5 and 8, about 20 fields per engine.
- **Distractor labels:** receipts 3, 6 and 8.
- **Mid-line registration numbers:** receipts 1 and 2.

## 3. Remaining errors, and new wrong selections

### 3.1 What causes the remaining errors

| Approach | Errors | Cause |
|---|---|---|
| Heavy | 12 of 18 | **OCR**: no usable text detected on receipt2 (3 blocks) and receipt5 (0 blocks). No rule can fix this. |
| DI | 1 of 7 | **Extraction** on a new receipt. receipt5 total = 1,750 instead of 1,575: the amount is about 720 px right of "Total 總額", beyond the "look right" distance limit (about 10 line heights, kept from the original rules). The rules fell back to the column sum, i.e. the subtotal. |
| All three | 6 | **The two carried-over receipts:** |
| | | • receipt9 doctor: DI misread the signature ("Dr. Lok Vichol", **OCR**); the ground truth also requires two names. Light and Heavy return nothing. |
| | | • receipt9 patient: the OCR glued a stray "F" to the label ("FPatient:"), so it isn't recognised (**OCR artefact**). |
| | | • receipt9 receipt number: **wrong selection**, see 3.2. |
| | | • receipt10 patient and receipt number: no labels on the receipt (**extraction**, would need layout knowledge). |
| | | • receipt10 date: the most-common-date rule picks the item date 1 Mar 2017; the ground truth uses the print date, 24 Mar (**open ground-truth question**). |

**Light's receipt5 total is correct, but for a fragile reason.** The same distance limit hides
the total label's value, so the rules used "paid in full" (the "Paid by EPS" amount). With a
partial payment, this would have been wrong.

### 3.2 Wrong selections introduced by the improved rules

- **receipt9 receipt number (regression, all three engines): 369303 → 380048.** The payments
  table has a "Receipt #" column header with 380048 below it. Under the new "a label is never a
  value" rule, the lookup now reaches that value, and "Receipt #" ranks before "Invoice No" in
  the vocabulary. The original rules stopped at the neighbouring "Payment received" header and
  found the invoice number instead. This is exactly the invoice-vs-receipt-number question
  flagged in `data/ground_truth/GROUND_TRUTH_REVIEW.md`.
- **receipt10 date:** the original returned nothing; the improved rules return a wrong date. The
  score is unchanged (wrong either way), but it is a confident wrong value instead of an honest
  gap.
- **No invented values,** and no other field that was correct before became wrong.

## 4. Complexity

| | Original general rules | Improved rules |
|---|---|---|
| Lines of code | 376 | 384 (plus 70 reused from the original) |
| Label phrases (unique) | 69 | 225 (English + Traditional Chinese, 17 label kinds incl. 5 distractor kinds) |
| Extra mechanisms | — | Block classification by longest label, translation stripping, simplified→traditional label mapping, header + Name rows, card-row totals, total fallback order |

The logic is still readable. The cost is the vocabulary: every new provider wording, language
variant or OCR quirk needs another entry, and the choice of which label wins must be kept
consistent. The receipt9 regression is an example of a rule that helped six receipts but
changed the answer on a seventh.

## 5. Will the improved rules work on unfamiliar layouts?

**Unknown, and the evidence so far is cautious:**
- **They were tuned on these receipts.** Light scoring 41/41 on the seven new receipts shows
  how far tuning can go on known layouts, not how the rules will do on new ones.
- **On the only receipts not designed around the new rules** (receipt9 and receipt10), they
  did not improve and lost one field. DI + AOAI scored 6/10 there; the rules 4/10.
- **A layout problem was hidden only by luck:** a slightly wider layout already defeats the
  distance limit (receipt5 on DI).
- **The Version 1 check (run later, Oct 2026) shows no gain on unseen receipts.** Only Version 1
  receipts 1, 2, 3 and 5 were unseen during development (handwritten, 15 applicable fields).
  Source: `results/v1_heldout/scores_rules/` (summary.csv, detail.csv, report.md).

  | | Original rules | Improved rules |
  |---|---|---|
  | Light, 4 unseen receipts | 13/15 | 13/15 |
  | DI, 4 unseen receipts | 10/15 | 10/15 |
  | Light, all 6 Version 1 receipts | 18/25 (72.0%) | 17/25 (68.0%) |
  | DI, all 6 Version 1 receipts | 15/25 (60.0%) | 14/25 (56.0%) |

  The +26 / +23 fields gained on Version 2 did not transfer. The one-field loss on all six is
  the receipt-number regression on the vet invoice (3.2). DI's service-date errors here are
  OCR: it reads the handwritten year 2026 as 2020 (Light reads it correctly). The sample is
  small, but it supports treating the Version 2 improved-rule scores as overfitted.

By contrast, the AOAI result (88.2%; 95.1% on the new receipts) came from a prompt that was not
tuned to these receipts.

## 6. Conclusion and recommendation

- **On the receipts they were tuned on, improved rules can match AOAI:**
  - **PaddleOCR Light, 88.2%:** equal to AOAI, offline, with no per-call cost.
  - **Azure DI, 86.3%.**

  So most of the original gap was **extraction logic, not OCR**.
- **This is not evidence that rules match AOAI on new receipts:**
  - AOAI's score comes from a prompt that was never tuned to these receipts.
  - The rules' score comes from tuning on them.
- **PaddleOCR Heavy remains the weakest option**, because of its OCR detection failures.

**Recommendation:** keep two candidates, PaddleOCR Light + improved rules and Azure DI + AOAI,
and decide on an **unseen** test:
1. Freeze both, including the improved rules (commit `64d18de`) and the AOAI prompt.
2. Run them on a fresh set of receipts neither has seen: ideally 30 or more real, anonymised
   receipts (the Version 1 check above has since been run).
3. Report the accuracy, plus the effort needed to fix each new layout. That ongoing
   maintenance is the real cost of the rule-based option.
4. **Optional:** PaddleOCR Light + AOAI (untested). Light's OCR text was accurate, so this
   could keep the LLM's robustness without the DI cost.

**Before the next run:**
- decide the invoice-vs-receipt-number policy (receipt9);
- resolve the receipt10 date question;
- consider widening the "look right" distance limit. That would be a new rule change, so it
  must be made **before** the unseen test, not after.
