# Findings: PaddleOCR Light / Heavy vs Azure DI (prebuilt-read)

All three approaches use the same six receipts, ground truth, general extraction rules and
`score.py`. Scores are in `report.md`, `summary.csv` and `detail.csv` in this folder.

| | Paddle Light | Paddle Heavy | Azure DI |
|---|---|---|---|
| Accuracy (correct / applicable) | 72.0% (18/25) | 72.0% (18/25) | 60.0% (15/25) |
| Mean time per receipt | 8.7 s | 35.8 s | 2.6 s |
| Receipts processed | 6/6 | 6/6 | 6/6 |
| Invented values | 0 | 0 | 0 |

How the runs were done:
- Paddle times are CPU inference on the Azure ML compute (paddlepaddle 3.2.2).
- DI time is the wall-clock time of the API call (upload, analysis, polling), plus about 10 ms
  of rule extraction.
- DI used a fresh prebuilt-read run (API 2024-11-30) with no errors. All 6 responses are in
  `../azure_di/di_response/`.

## Extraction problems

**Azure DI misreads the handwritten year.** On receipts 1, 2, 3 and 5, DI reads "2026" as
"2020" (e.g. `07/02/2020`). The rules pick the right field each time, but the value is wrong.
This alone costs DI 4 of its 10 errors and is the whole accuracy gap to Paddle (service_date
1/6 vs 5/6). Paddle reads these years correctly.

**DI reads printed and handwritten names better.** Doctor name is 4/6 for DI vs 3/6 for Paddle.
DI gets receipt 1's handwritten "Dr. Lau Sai Kit, Lawrence" exactly right, while Paddle misreads
it in both models. On receipt 4, DI misreads the signature "Dr. Lok Yi Choi" as
"Dr. Lok Vichol".

**Failures shared by all three approaches** (limits of the general rules or open ground-truth
questions, not OCR):
- r3 doctor_name: the name is written in a box labelled "Clinic Name", which the rules don't
  treat as a doctor label.
- r4 doctor_name: the ground truth combines two people ("Angel Tseng, Lok Yi Choi"); see
  `data/ground_truth/GROUND_TRUTH_REVIEW.md`. r4 patient_name ("Fuk Jai", a pet) is not found.
- r6 patient_name, receipt_number and service_date: the receipt doesn't label them, and the
  receipt number is the barcode number.

**Low-confidence DI lines.** 10 DI lines across 4 receipts had a mean word confidence below 0.5
and were dropped by the general rules (same threshold as Paddle). They were all noise apart from
one duplicate "1540.00" on receipt 1, so no field was affected.

**Light vs Heavy.** Both find the same values except doctor-name spelling on receipts 1 and 2.
Heavy is about 4× slower for identical accuracy.
