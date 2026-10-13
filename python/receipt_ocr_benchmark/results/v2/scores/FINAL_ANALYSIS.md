# Receipt OCR Benchmark, Version 2: Final Analysis

**Sources:**
- `results/v2/scores/report.md`, `summary.csv` and `detail.csv`;
- the per-receipt JSON files under `results/v2/` (raw OCR, extracted fields, DI + AOAI outputs);
- `results/v2/inputs/manifest.csv`;
- `data/receipts_v2/benchmark_ground_truth.xlsx`;
- Version 1 results from the Git tag `ocr-benchmark-v1`.

Nothing was re-run for this analysis.

## 1. Executive summary

- **Azure DI + Azure OpenAI is clearly the most accurate approach on Version 2:** 88.2%
  (45 of 51 fields). The three rule-based approaches score 29–41%.
- **The gap is caused by the extraction step, not by text recognition.** On the seven new printed
  receipts, all three OCR engines read almost every correct value. The exception is PaddleOCR
  Heavy, which failed to detect text on two photos. The fixed general rules, written while
  looking at the Version 1 receipts, failed on:
  - the new layouts;
  - bilingual labels (e.g. "Attending Doctor 主診醫生");
  - the Chinese-only receipt.

  The language model handled all of these.
- **Speed:**

  | Approach | Average per receipt |
  |---|---|
  | Azure DI | 3.8 s |
  | DI + AOAI | 6.2 s |
  | PaddleOCR Light | 13.9 s |
  | PaddleOCR Heavy | 53.3 s |
- **Reliability:** all four approaches processed all 9 receipts, with no failed requests and
  no invented values.
- **PaddleOCR Heavy is the weakest option:** it is the least accurate (29.4%), and about 4× slower
  than Light.
- **Version 1 and Version 2 are not comparable,** because they use different receipts. Version 1's
  three-way tie at 72% came from receipts the rules were built on. Version 2 suggests that tie
  does not hold on unfamiliar layouts.
- **Nine receipts are still too few to pick a production solution,** but the direction is
  consistent and large.

## 2. Verification

| Check | Result |
|---|---|
| Receipts scored | 9: receipt1–6 and receipt8 (new printed photos), receipt9 and receipt10 (from Version 1). receipt7 (pharmacy slip) was not photographed and is not in the dataset. |
| Result files | Each approach has exactly one result file per receipt (9 each); no missing, extra or duplicate files. |
| Inputs | `manifest.csv`: the 7 photos were rotated upright (EXIF orientation 6, 3024×4032), and receipt9/receipt10 copied unchanged. All approaches read the same files. |
| Applicable fields | 51 = 9 × 6, minus 3 cells marked N/A (registration number on receipt3, receipt9 and receipt10). |
| Accuracy arithmetic | Recounted by hand from `detail.csv`: 19, 15, 21 and 45 correct, matching `summary.csv`. |
| Failed requests | 0 for every approach. All 9 DI + AOAI replies finished normally (`finish_reason: stop`). |
| Invented values | 0 for every approach. |
| Timings | Taken from the per-receipt files. The per-receipt averages match `summary.csv`. |

**No errors were found in the scoring.**

## 3. Comparison

| | PaddleOCR Light | PaddleOCR Heavy | Azure DI | Azure DI + AOAI |
|---|---|---|---|---|
| **Accuracy** | 37.3% (19/51) | 29.4% (15/51) | 41.2% (21/51) | **88.2% (45/51)** |
| Wrong or missing fields | 32 | 36 | 30 | 6 |
| Invented values | 0 | 0 | 0 | 0 |
| Receipts processed | 9/9 | 9/9 | 9/9 | 9/9 |
| Average time per receipt | 13.9 s | 53.3 s | 3.8 s | 6.2 s |
| AOAI tokens (total for 9 receipts) | — | — | — | 5,421 input / 2,368 output (1,728 reasoning) |
| AOAI tokens per receipt | — | — | — | 602 input / 263 output |

### Accuracy by field (correct / applicable)

| Field | Light | Heavy | Azure DI | DI + AOAI |
|---|---|---|---|---|
| Doctor name | 3/9 | 2/9 | 3/9 | **6/9** |
| Registration number | 1/6 | 1/6 | 1/6 | **5/6** |
| Patient name | 3/9 | 2/9 | 3/9 | **9/9** |
| Receipt number | 4/9 | 3/9 | 4/9 | **9/9** |
| Service date | 3/9 | 2/9 | 4/9 | **8/9** |
| Total amount | 5/9 | 5/9 | 6/9 | **8/9** |

### Correct fields by receipt

| Receipt | Fields | Light | Heavy | Azure DI | DI + AOAI |
|---|---|---|---|---|---|
| receipt1 GP clinic | 6 | 5 | 5 | 5 | 5 |
| receipt2 Specialist | 6 | 4 | 0 | 5 | 6 |
| receipt3 Hospital invoice (bilingual) | 5 | 1 | 1 | 1 | 5 |
| receipt4 Chinese medicine (Chinese only) | 6 | 0 | 0 | 0 | 6 |
| receipt5 Dental (bilingual) | 6 | 0 | 0 | 0 | 5 |
| receipt6 Physiotherapy | 6 | 3 | 3 | 3 | 6 |
| receipt8 Medical centre (bilingual) | 6 | 1 | 1 | 2 | 6 |
| receipt9 Vet invoice (from Version 1) | 5 | 3 | 3 | 3 | 3 |
| receipt10 NZ pharmacy (from Version 1) | 5 | 2 | 2 | 2 | 3 |
| **Total** | **51** | **19** | **15** | **21** | **45** |

## 4. Speed and reliability

| | Average per receipt | Range | Notes |
|---|---|---|---|
| PaddleOCR Light | 13.9 s | 7.0–19.0 s | CPU on Azure ML; the rules add about 10 ms |
| PaddleOCR Heavy | 53.3 s | 19.5–67.8 s | CPU; about 3.8× Light |
| Azure DI | 3.8 s | 2.5–5.7 s | API call, including network time |
| Azure DI + AOAI | 6.2 s | 4.5–9.7 s | 3.3 s DI + 2.8 s AOAI on average; reasoning effort `low` |

**Reliability:**
- Every approach returned a result for every receipt.
- **The one serious problem was in text detection, and it was silent:** PaddleOCR Heavy found only
  3 text blocks on receipt2 (all from the footer) and none at all on receipt5. It reported no
  error, so these show up only as 12 wrong fields.

## 5. Error analysis

**How each error is classified:**
- **Recognition (OCR):** the text engine did not read the correct value.
- **Extraction:** the correct text was read, but the wrong value or nothing was selected.

**Evidence:** for the seven new receipts, I searched each engine's raw OCR for every ground-truth
value.
- **Azure DI and PaddleOCR Light** read every value correctly. The only exception is Light
  reading "18 May 2026" as "18May 2026", which did not cause the error.
- **PaddleOCR Heavy** read every value correctly except on receipt2 and receipt5, where it
  detected almost nothing.

### 5.1 Rule-based approaches (Light, Heavy, Azure DI with the same general rules)

| Cause | Type | Receipts | Fields lost (Azure DI) | What happened |
|---|---|---|---|---|
| Chinese-only receipt | Extraction | receipt4 | 6 | Every value was read (e.g. 葉卓謙, 006821, 2026年6月9日), but the rules only know English labels, so nothing matched. |
| Bilingual labels | Extraction | receipt3, receipt5, receipt8 | 14 | (1) The Chinese half of a label became the value: doctor = "主診醫生", patient = "病人". (2) A label like "Invoice No. 發票編號" or "Treatment Date 治療日期" failed the rules' check, so the receipt number, date and registration number were missed. (3) For the receipt5 total, "Total 總額" failed the check, so the rules fell back to adding up the line items and returned the 1,750.00 subtotal instead of the 1,575.00 total after discount. |
| Registration number in the middle of a line | Extraction | receipt1, receipt2 | 2 | "MBBS (HK) · Reg. No. M17642": the rules only match a label at the start of a text block. |
| Distractor chosen | Extraction | receipt6 | 2 | Doctor = the referring "Dr. Kwok Man Hin" (a "Dr" name pattern) instead of the physiotherapist. Date = "Date Issued 17 Jul 2026" instead of the session date, 16 Jul. |
| Card layout for totals | Extraction | receipt6 | 1 | "Total" sits above "HK$1,200.00" in a row of cards; the rules found no confident match. |
| Carried-over Version 1 receipts | Mixed | receipt9, receipt10 | 5 | The same failures as in Version 1. On receipt9, "Dr. Lok Vichol" is DI misreading a signature (recognition), and the ground truth combines two clinicians. Patient name, unlabelled receipt number and date are missed on receipt10. |
| **Total** | | | **30** | |

**PaddleOCR Light** loses a similar set of fields (32 in total). It also misses the receipt2
total and the receipt8 date, both read correctly, so these are extraction misses.

**PaddleOCR Heavy** loses the same fields as Light, except on receipt2 and receipt5, where it
loses all 12 fields because of its detection failure (Light lost 8 of those 12). That is
**recognition**, and it is the only large OCR failure in Version 2. It accounts for Heavy's 4
extra errors (36 vs 32).

### 5.2 Azure DI + Azure OpenAI: all six errors

| Receipt | Field | Correct | Extracted | Type | Explanation |
|---|---|---|---|---|---|
| receipt1 | Registration number | M17642 | "MBBS (HK) · Reg. No. M17642" | Extraction (format) | The model copied the whole printed line, including the label. The value is there, but the exact-match scorer counts it wrong. |
| receipt5 | Doctor name | Dr. Ho Ching Yee | "Dr. Ho Ching Yee, BDS (HK)" | Extraction (format) | The model kept the qualification printed after the name. |
| receipt9 | Total amount | 1361 | 1361.5 | Extraction (wrong value) | The receipt shows "Sub Total HKD 1361.50" and "Total Amount HKD 1361.00". The model picked the subtotal. In the Version 1 run, the same receipt got 1361.0 (correct), which points to run-to-run variation. |
| receipt9 | Doctor name | Angel Tseng, Lok Yi Choi | Angel Tseng | Ground-truth policy | The ground truth requires both clinicians. The model returned the printed "Clinician". This is the same open question as in Version 1. |
| receipt10 | Doctor name | Dr Jessica Sterenborg | Dr Jessica Sterenborg Picton Medical Centre | Recognition layout + extraction | DI returned the doctor and clinic as one line, and the model copied it. The rules' "Dr <Name>" pattern got this right for all three other approaches. |
| receipt10 | Service date | 2017-03-24 | 2017-03-01 | Ground-truth ambiguity | The receipt shows a print date (24 Mar 17) and item dates (1Mar17). The ground truth uses the print date; the model chose the item date. This is still unresolved since Version 1. |

**None of the six is a text-recognition error by DI** on the new printed receipts.
- **Two are formatting:** the value is present, but with extra text.
- **Two come from ground-truth policy questions** on the carried-over receipts.
- **One is a genuine wrong choice** (subtotal vs total).
- **One comes from DI merging two lines.**

**Sensitivity check (illustration only, not a result):** under a looser rule that accepts a
value with extra surrounding text, the two formatting cases would count and DI + AOAI would
score 47/51 (92.2%).

### 5.3 By field

| Field | Main cause of rule-based errors | DI + AOAI |
|---|---|---|
| Doctor name | Bilingual labels taken as values; the referring doctor chosen; no Chinese labels | 6/9. Errors: qualification kept, merged line, two-clinician ground truth |
| Registration number | Inline label, Chinese or bilingual labels | 5/6. Error: label copied with the value |
| Patient name | Bilingual labels ("病人"); no Chinese labels | 9/9 |
| Service date | Bilingual or Chinese labels; the issue date chosen on receipt6. Azure DI found 4/9, partly through its "most common date" fallback | 8/9. The Chinese date on receipt4 is now scored correctly |
| Receipt number | Bilingual labels; unlabelled barcode (receipt10) | 9/9 |
| Total amount | Bilingual "Total 總額" fell back to the subtotal; card layout | 8/9. Error: subtotal chosen on receipt9 |

**Handwritten years:** Version 1's main DI problem was misreading the handwritten "2026" as
"2020". It does not appear on the printed receipts: DI read every printed date correctly.

## 6. Version 1 vs Version 2

**Important:** the two versions use different receipts:
- **Version 1:** 6 receipts, 4 of them handwritten; the general rules were developed on them.
- **Version 2:** 9 receipts. 7 are new, printed and photographed; 2 are carried over.

The scores show how each approach behaves on each set. They are not a controlled before/after
experiment.

| | Version 1 (6 receipts, 25 fields) | Version 2 (9 receipts, 51 fields) | Version 2, new receipts only (7 receipts, 41 fields) |
|---|---|---|---|
| PaddleOCR Light | 72.0% (18/25), 8.7 s | 37.3% (19/51), 13.9 s | 34.1% (14/41) |
| PaddleOCR Heavy | 72.0% (18/25), 35.8 s | 29.4% (15/51), 53.3 s | 24.4% (10/41) |
| Azure DI | 60.0% (15/25), 2.6 s | 41.2% (21/51), 3.8 s | 39.0% (16/41) |
| Azure DI + AOAI | 72.0% (18/25), 5.4 s | 88.2% (45/51), 6.2 s | 95.1% (39/41) |

1. **Did accuracy improve or decrease?** It fell sharply for the three rule-based approaches and
   rose for DI + AOAI. The rules' Version 1 accuracy did not carry over to unfamiliar layouts.
2. **Did printed receipts make Azure DI more accurate?** **Its OCR, yes:** DI read every printed
   value on the new receipts, including all dates (no "2020" misreads). **Its field extraction,
   no:** with the general rules it scored only 39.0% on the new receipts, because the rules, not
   DI, were the bottleneck.
3. **Did AOAI do better on unfamiliar layouts?** Yes. 95.1% on the seven new receipts, including
   6/6 on the Chinese-only receipt and 5–6 of 6 on each bilingual receipt.
4. **Did PaddleOCR Light still match Heavy?** Light was better this time (37.3% vs 29.4%) and
   about 3.8× faster. Heavy's detection failed silently on two photos.
5. **Which new receipt types caused the most problems?** For the rule-based approaches:
   - the Chinese medicine receipt (0/6 for all three);
   - the dental receipt (0/6);
   - the bilingual hospital invoice (1/5) and medical centre receipt (1–2/6).

   The GP and specialist receipts, which use plain English labels, worked well (4–5 of 6).

**Carried-over receipts:** receipt9 and receipt10 scored exactly as in Version 1 for the three
rule-based approaches (same images, deterministic rules). DI + AOAI differed by one field
(receipt9's total), which suggests run-to-run variation in the language model.

**Speed:** times are higher than in Version 1 for all approaches. The cause was not measured;
likely contributors are that every new input is a full 12 MP photo, and possibly different
compute load. Compare speeds within a version, not across versions.

## 7. Main findings

1. **DI + AOAI is the most accurate approach** by a wide margin: 88.2% vs at most 41.2%. That's
   +47 percentage points over Azure DI alone, which reads the same OCR text.
2. **The language model's value is in field extraction, not OCR.** DI's text was essentially
   correct; the fixed rules could not reliably pick fields from new, bilingual or Chinese
   layouts.
3. **The general rules do not generalise.** Version 1's 72% tie came from receipts the rules were
   developed on.
4. **PaddleOCR Light's OCR text was also essentially correct** on the new receipts. Its low score
   comes from the rules, not the OCR engine.
5. **PaddleOCR Heavy should be dropped:** least accurate, slowest, and it failed silently on two
   photos.
6. **Azure DI alone is fastest (3.8 s), but its accuracy is limited by the rules.** Adding AOAI
   costs about 2.8 s and about 865 tokens per receipt.
7. **DI + AOAI's remaining errors are mostly formatting and ground-truth policy,** not reading
   errors. One (receipt9's total) shows the model can vary between runs.

## 8. Limitations

- **Small sample:** 9 receipts and 51 fields, so one field is worth about 2 percentage points.
  The DI + AOAI lead is large enough to be meaningful; smaller differences are not.
- **Mock receipts:** 7 receipts designed for this test, printed in black and white, photographed
  in one session with one phone. Real claims will vary more (creases, stamps, handwriting,
  multi-page PDFs).
- **Open ground-truth questions:** the two carried-over receipts bring two clinicians on
  receipt9 and print vs item date on receipt10. These cost DI + AOAI 2 fields.
- **Strict scoring:** a value with extra text (label or qualification) counts as wrong. This
  cost DI + AOAI 2 fields.
- **One run per approach:** the receipt9 total suggests DI + AOAI results vary between runs; this
  was not measured.
- **Heavy's detection failure** on receipt2 and receipt5 was not investigated (cause unknown).
- **Not tested:** no pharmacy till slip (not photographed), and no registration number on 3 of
  the 9 receipts.
- **Costs still unpriced:** token usage is measured (602 input / 263 output per receipt), but
  VM, DI page and gpt-5-mini prices are still needed to put costs in money.

## 9. Recommendation and next steps

**On this evidence, Azure DI + Azure OpenAI is the strongest candidate.** It is the only
approach that handled unfamiliar, bilingual and Chinese receipts, at about 6 seconds per
receipt. Its extra cost is roughly 2.8 seconds and 865 tokens per receipt. Whether that is
worth it depends on the pricing, which is still to be provided, but the accuracy gain is large.

**PaddleOCR Light with the general rules is not a reasonable alternative as it stands:** the rules
do not generalise. However, Light's OCR text was accurate, so it may still be useful as the OCR
step for a language model (see step 2). Drop PaddleOCR Heavy.

**This is not a production decision:** nine mock receipts are not enough.

**Next steps:**
1. Provide the three prices to complete the cost comparison.
2. **Test PaddleOCR Light + Azure OpenAI** (untested): same prompt, Paddle's OCR text instead of
   DI's. If accuracy holds, it removes the DI cost and keeps the OCR step offline.
3. Run DI + AOAI 3 times on the same receipts to measure run-to-run variation.
4. Decide the scoring policy for values with extra text (labels, qualifications), and resolve
   the receipt9/receipt10 ground-truth questions.
5. Re-test on a larger set of real, anonymised receipts (e.g. 30–50), including PDFs, handwritten
   and multi-page receipts, with the code, rules and prompt frozen beforehand.
