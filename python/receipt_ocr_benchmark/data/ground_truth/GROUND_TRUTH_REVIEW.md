# Ground truth review (Phase 1)

Each value in `ground_truth_template.xlsx` was checked against the receipt images in `data/raw/`.

## Corrections made (supported by the receipt)

| receipt | field | before | after | evidence |
|---|---|---|---|---|
| r3 | doctor_name | Lee Tin Tin, Becku | Lee Tin Tin, Becky | handwriting clearly reads "Becky" |
| r2 | patient_name | na | Carol Tse | "Patient: Carol Tse" and "Name: Carol Tse" are both written on the receipt |
| all | service_date | Excel date serials (e.g. 46205) / "feb 09/2023" | ISO text, e.g. `2026-02-07` | see date note below |

Dates are now stored as text cells, so Excel can no longer convert them. `score.py` refuses any
`service_date` that is not ISO `YYYY-MM-DD` text.

## Needs manual review

1. **Day/month order for r1, r2, r3, r5.** The receipts are handwritten `07/02/2026`,
   `11/7/2026`, `07/01/2026` and `09/01/2026`. These are stored **day-first** (Hong Kong
   convention, also what the extractors assume): 2026-02-07, 2026-07-11, 2026-01-07 and
   2026-01-09. When the numbers were first typed in, Excel read them month-first, so the
   person who wrote the receipts should confirm. The photo timestamps (2026-07-08) don't settle
   it: either reading puts one of the dates after the photo was taken. If the dates are
   actually month-first, change those four cells. Nothing else needs to change.
2. **r4 receipt_number.** The ground truth uses `Invoice No: 369303`, but the receipt also shows
   `Receipt # 380048` under payments. Decide which one counts as the receipt number.
3. **r4 doctor_name.** Two people appear: "Clinician: Angel Tseng" (printed) and the
   stamp/signature "Dr. Lok Yi Choi". The ground truth stores both as one string, so an approach
   only scores if it returns both. Decide whether to keep one name or both. Also note this is a
   vet invoice (the patient, Fuk Jai, is a cat), so decide whether r4 belongs in a
   medical-receipt benchmark at all.
4. **r6 receipt_number and service_date.** `9990000505906` is the unlabelled barcode number.
   The ground-truth date is the print/dispense date (24 Mar 2017), but the line items are dated
   1 Mar 2017. Confirm both.
5. **r1 doctor_name.** The receipt also gives a Chinese name (劉世傑), but the ground truth only
   has the English name. An answer that includes both names ("Dr. Lau Sai Kit, Lawrence; 劉世傑")
   is scored Wrong. Decide whether either name should be accepted.
6. **r3 doctor_name / total_amount (minor).** The name is written in the "Clinic Name" box.
   "Total Amount Due" is a dash, so the ground truth uses the subtotal (10.00).

Left as-is and verified: r1 patient_name = na (scribbled out on the receipt), registration_number
= na on all six receipts (none shows one), and all other totals, names and receipt numbers.
