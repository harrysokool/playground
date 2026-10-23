# Diagnosis comment: present or missing (investigation, Oct 2026)

**Requirement:** flag receipts that have no diagnosis comment. We only need to know whether a
comment exists. What it says, and whether it is medically right, does not matter.

**Scope:** investigation only. Nothing is implemented, and no new OCR or API calls were made.
This is kept separate from the six-field benchmark and its accuracy scores.

**Sources:**
- Azure DI text: `results/v2/di_aoai_v2_rows/*.json` (`input_text`) and
  `results/v1_heldout/di_aoai_v2_rows/*.json`.
- PaddleOCR text: `results/v2/paddle_light/`, `results/v2/paddle_heavy/`, and the Version 1
  outputs at tag `ocr-benchmark-v1`.

## 1. Which receipts have a diagnosis comment

Version 2 (the nine benchmark receipts) has **one** receipt with a diagnosis comment. Version 1
adds four handwritten template receipts (V1 4 and 6 are the same images as V2 9 and 10).

| Receipt | Comment? | Evidence in the OCR text | Note |
|---|---|---|---|
| V2 1 GP | No | none | Items are consultation, medication and a sick leave certificate |
| V2 2 Cardiology | No | none | "Resting electrocardiogram (ECG)" is a service, not a diagnosis |
| V2 3 Hospital | No | none | X-ray and blood test are services. 診症編號 means "episode no." |
| V2 4 Chinese medicine | No | none | 診金, 中藥 and 針灸 are services. 診症日期 is the visit date, 覆診日期 the follow-up date |
| V2 5 Dental | No | none | "Composite filling, tooth 36" is a treatment |
| V2 6 Physiotherapy | No | none | "Treatment: manual therapy…" is a treatment label |
| V2 8 Medical centre | No | none | |
| V2 9 Vet invoice | **Yes, labelled** | `Diagnosis: \| Colitis`, `Symptoms: \| diarrhoea.`, `Encounter: Vomiting Acute ddx` | The only labelled example, and it is not a human medical receipt |
| V2 10 NZ pharmacy | No | none | Prescription items only |
| V1 1 | **Yes, under NOTES** | `NOTES:` then "patient is severely injured and he need more rest…"; item "broken ribs." | Handwritten. PaddleOCR Light reads "patient B cverely injurel" |
| V1 2 | No, **empty label** | `NOTES: \| MED CLAIM`, then nothing | "MED CLAIM" is the next column header, not a comment |
| V1 3 | **Yes, under Notes** | `Notes: \| Back pain need water.` | Handwritten. Light splits it into "1Back" and "pain. need water." |
| V1 5 | No, **empty label** | `NOTES: \| MED CLAIM \| -` | A dash, not a comment |

These labels are my reading of the receipts. **The business still has to confirm the
definition** (section 5).

## 2. What makes this hard

- **Treatment vs diagnosis:** "Treatment:", "Composite filling" and "ECG" describe what was done,
  not what is wrong. A rule must not count them.
- **Chinese near-misses:** 診斷 (diagnosis) and 診症 (consultation) differ by one character,
  and 診症 appears on three receipts (診症日期, 診症編號, 普通科診症). 覆診 means follow-up.
  Both simplified and traditional forms occur (診斷/诊断, 備註/备注).
- **Generic labels:** "Notes" holds a medical comment on V1 1 and V1 3, but on other receipts
  it could hold something like "Please pay within 30 days." The word also turns up in ordinary
  text ("Please Note. We are open…" on V2 10).
- **Empty labels:** on V1 2 and V1 5 the label is printed with nothing after it. In the row
  text, the next column header ("MED CLAIM") sits beside the label and must not be read as a
  value.
- **Comments without a label:** "broken ribs." is written as a line item on V1 1, and
  "Encounter: Vomiting Acute ddx" on V2 9. Here both receipts also have a labelled comment, so
  they don't change the result.
- **Unreadable OCR:** PaddleOCR Heavy returned 0 text blocks on V2 5 and 3 on V2 2. With no text,
  "no comment found" is **not** the same as "comment missing". Handwriting reads badly
  ("injurel"), but for presence it only matters that some text is there.

## 3. Rules vs AOAI

**Simple OCR-text rules are enough for every case in our data.** All three comments sit under a
label (Diagnosis or Notes). Applied by hand to the OCR text, the rules in section 4 classify all
13 receipts correctly with both Azure DI and PaddleOCR Light. Nothing was run in code.

AOAI would add real value in three situations:
1. comments with no label (for example "URTI" handwritten next to the items);
2. deciding whether a "Notes"/"Remarks"/"備註" comment is medical;
3. heavily garbled handwriting.

None of the nine benchmark receipts needs it. If Azure DI + AOAI is chosen for the six fields
anyway, a `diagnosis_comment_present` flag plus a quoted evidence string could be added to the
same call at little extra cost. It would still be scored separately.

## 4. Recommended approach: label rules with three outcomes

Use the same OCR text and the same label and nearby-block lookup as the existing rules.

1. **Unreadable → `needs_review`.** Use this when the OCR returned almost no text (for example
   fewer than about 10 blocks), so the page is never reported as "missing".
2. **Look for a label:**
   - **Strong labels:** Diagnosis, Diagnoses, Dx, DDx, Impression, Clinical findings, Condition,
     Symptoms, Chief/Presenting complaint; 診斷 / 诊断, 臨床診斷, 病症, 病情, 病況, 症狀 / 症状,
     主訴 / 主诉.
   - **Weak labels:** Notes, Remarks, Comments; 備註 / 备注, 附註, 醫生意見.
   - **Never labels:** Treatment, Treatment Date, 治療, 診症, 診金, 覆診.
   - **Position:** a label must start a line or block and be followed by `:` or a column break,
     or stand alone. Otherwise "Please Note. We are open from 8.00am…" (V2 10) would count as
     a Notes label.
3. **Read the value:** take the rest of the same line, otherwise the nearest block to the right
   or below. Stop at another known label (TOTAL, PAID, MED CLAIM, Signature, table headers).
4. **Empty:** the value is blank or only `-`, `—`, `_`, `.`, `N/A`, `nil`, `none`, `無` or `无`.
5. **Outcome:**

| What the rules find | Outcome | Examples |
|---|---|---|
| Strong label with a value | `present` | V2 9 "Diagnosis: Colitis"; "診斷:上呼吸道感染" |
| Weak label with medical-looking text | `present` (shown as weak) | V1 3 "Notes: Back pain need water." |
| Weak label with other text | `needs_review` | "Remarks: Please settle within 30 days" |
| Label printed but empty | `missing` | V1 2 "NOTES:" (blank); V1 5 "NOTES: -"; "Diagnosis: N/A" |
| No label anywhere | `missing` | V2 1–8, V2 10 |
| OCR text unusable | `needs_review` | Heavy on V2 5 (0 blocks) |

Each result keeps the evidence text it found, the same way the six fields keep `sources`.

## 5. Gaps before building anything

- **Too few examples to judge accuracy.** There are 3 positives out of 13 receipts:
  - one is a vet invoice;
  - two are handwritten templates;
  - there are no printed human-medical receipts with a diagnosis, and no Chinese examples.
- **Make a small labelled set.** Add mock receipts covering each case:
  - a printed English diagnosis;
  - a printed Chinese diagnosis (診斷);
  - an empty diagnosis box;
  - a "Remarks" field with non-medical text;
  - a handwritten comment with no label.

  Then add real anonymised receipts, with a present/missing column kept apart from the
  six-field ground truth.
- **Business definition still open:**
  - Do symptoms count?
  - Does a medical comment under "Notes" count?
  - Does a diagnosis written as a line item count?
