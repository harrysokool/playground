# Diagnosis comment: present, missing or needs_review

**Requirement:** flag receipts that have no diagnosis comment.

**Definition:** a diagnosis comment is written information about the patient's condition,
symptoms or diagnosis. What it says, and whether it is medically right, is not checked.

**Kept separate** from the six-field benchmark: own ground truth, own scorer
(`receipt_bench/diagnosis_cli.py`), own results (`results/diagnosis/`). `score.py` ignores it.

## Data

- `data/diagnosis/ground_truth.csv`: `present` or `missing` for the 13 distinct receipts, with
  evidence and notes.
  - Version 2: receipts 1–6, 8, 9, 10.
  - Version 1: receipts 1, 2, 3, 5. V1 4 and 6 are the same images as V2 9 and 10.
  - Only 3 have a comment:
    - V2 9: "Diagnosis: Colitis", "Symptoms: diarrhoea" (a vet invoice);
    - V1 1: a handwritten note about an injury;
    - V1 3: "Notes: Back pain need water."
  - V1 2 and V1 5 have an empty NOTES label.
- `data/diagnosis/mock_cases.json`: 21 synthetic OCR layouts. They cover English and Chinese
  labels (traditional and simplified, bilingual), a value beside, below or mid-line, empty and
  placeholder fields, medical notes, administrative remarks, an unclear remark, treatment-only and
  診症日期 near-misses, "Please Note." text, and an unreadable page.

## Method 1: rules (`receipt_bench/diagnosis.py`)

The same code runs on PaddleOCR Light and Azure DI. It reads the saved raw OCR, so nothing is
called.

1. **Unreadable page:** fewer than 10 OCR text blocks → `needs_review`, never `missing`.
2. **Find a label.**
   - **Strong labels:** Diagnosis, Dx, Impression, Symptoms, Condition, Chief complaint,
     Clinical notes; 診斷/诊断, 症狀/症状, 病情, 病況, 病症, 主訴 …
   - **Weak labels:** Notes, Remarks, Comments; 備註/备注, 附註, 醫生意見.
   - **Position:** a label must start a block and be followed by `:`, the end of the block, or
     (Chinese) a space. A strong label with `:` may also appear mid-line.
   - **Not labels:** Treatment, 診症 and 覆診 are not in the vocabulary.
3. **Read the value:**
   - first the rest of the block;
   - else the nearby blocks on the same row, up to 6 line heights away (a distant column is not a
     value);
   - else the line below, unless it is another label or a charge line (text with an amount).
4. **Judge the value:**

   | Value | Status |
   |---|---|
   | Blank or a placeholder (-, N/A, nil, 無) | `missing` |
   | Fewer than 2 letters | `needs_review` |
   | Strong label with any text | `present` |
   | Weak label with general words about symptoms or illness (pain, fever, injur*, *itis, 痛, 咳, 炎 …) | `present` |
   | Weak label with administrative words only (payment, receipt, insurance, appointment, 收據 …) | `missing` |
   | Weak label with anything else | `needs_review` |

5. **Combine:** any label `present` → `present`; else any `needs_review` → `needs_review`;
   else `missing`.

## Method 2: AOAI (prompt v2 + `--diagnosis`)

`di_aoai.DIAGNOSIS_NOTE` is appended to prompt v2. The reply gains two keys:
- `diagnosis_comment`: present / missing / needs_review;
- `diagnosis_evidence`: the comment quoted from the text.

A `present` answer is downgraded to `needs_review` if:
- it quotes no evidence; or
- the quote's words are not all in the OCR text.

With the photo attached, a quote that isn't in the OCR text is flagged instead of downgraded.

Without the flag, the prompt and schema are exactly as before, so the six-field results are
reproducible.

## Results

### Rules (offline, saved OCR, no API calls)

`results/diagnosis/scores/` (report.md, summary.csv, detail.csv):

| | PaddleOCR Light + rules | Azure DI + rules |
|---|---|---|
| Correct (13 receipts) | 13/13 | 13/13 |
| Needs review / false missing / false present | 0 / 0 / 0 | 0 / 0 / 0 |

Other checks:
- **Mock cases:** all 21 give the expected status. The unclear remark gives `needs_review` by
  design.
- **Unreadable pages:** PaddleOCR Heavy's two blank pages give `needs_review`.

### AOAI

Not run yet: it needs Azure. Run this on Azure ML; it makes 13 AOAI calls and no DI calls, and
commits the results:

```bash
git pull --ff-only && bash python/receipt_ocr_benchmark/scripts/aoai_diagnosis_on_azure.sh
```

## Commands (rules, offline)

```bash
python -m receipt_bench.diagnosis_cli detect --input results/v2/paddle_light --output results/diagnosis/v2/rules_paddle_light
python -m receipt_bench.diagnosis_cli detect --input results/v2/azure_di --output results/diagnosis/v2/rules_azure_di
# Version 1 receipts 1, 2, 3, 5: OCR from tag ocr-benchmark-v1 (paddle_light/, azure_di/), same command
python -m receipt_bench.diagnosis_cli score --ground-truth data/diagnosis/ground_truth.csv \
    --approach rules_paddle_light=v2:results/diagnosis/v2/rules_paddle_light \
    --approach rules_paddle_light=v1:results/diagnosis/v1/rules_paddle_light \
    --approach rules_azure_di=v2:results/diagnosis/v2/rules_azure_di \
    --approach rules_azure_di=v1:results/diagnosis/v1/rules_azure_di --output-dir results/diagnosis/scores
```

## Limitations

- **The 13/13 is a development score, not an accuracy estimate.**
  - The rules and mock cases were written after reading these 13 receipts.
  - Only 3 receipts have a comment: one is a vet invoice and two are handwritten templates.
  - No real printed human-medical receipt has a diagnosis, and there is no real Chinese example.
- **Unlabelled comments are not looked for by the rules.** Examples: a condition written as a line
  item ("broken ribs."), or free handwriting with no label. The rules will say `missing`. This is
  the main case where AOAI may add value.
- **Weak labels depend on short word lists.** A medical note that uses none of the listed symptom
  words gives `needs_review`, never a wrong `present`. A remark that mixes administrative and
  medical words counts as medical.
- **Layout assumptions:**
  - values sit to the right (within 6 line heights) or on the next line;
  - the "unreadable" threshold is a fixed 10 OCR text blocks;
  - multi-page receipts: only page 1 is read, as with the six fields.
- **Next:** build a labelled test set of real, anonymised receipts with a present/missing column,
  and run the AOAI script before choosing between the two methods.
