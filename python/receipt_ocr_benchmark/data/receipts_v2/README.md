# receipts_v2: eight printed mock receipts (benchmark Version 2 input)

A separate dataset from the original six receipts in `data/raw` (Version 1, frozen). It contains
eight **fully printed, fictional** Hong Kong medical receipts, each a different receipt type and
layout. Each receipt is printed on paper and photographed with a phone. **The photos are the
benchmark input,** not the source PDFs.

| File | Purpose |
|---|---|
| `receipts_spec.json` | **Source of truth.** Each receipt's ground truth plus everything else it will show: provider, layout, people, dates, reference numbers, line items, discounts and payments. |
| `build_ground_truth.py` | Validates the spec, then writes the two files below. Run it after any edit to the JSON. |
| `ground_truth.xlsx` | The six fields in the same "Ground Truth" sheet layout as `data/ground_truth/`, so `score.py` reads it unchanged. |
| `GROUND_TRUTH.md` | A readable table for review. |
| `raw/` | Where the phone photos go, named `receipt1.jpg` … `receipt8.jpg` to match `receipt_id` r1…r8. |

```bash
python data/receipts_v2/build_ground_truth.py   # from python/receipt_ocr_benchmark/
```

## How each field is defined

Each rule is applied the same way on every receipt. The receipts are designed so that applying
the rule gives exactly one answer.

- **doctor_name:** the practitioner who provided the billed service (attending doctor, dentist,
  Chinese medicine practitioner or physiotherapist), exactly as printed. Referring doctors and
  nurses also appear, under different labels, as distractors. A pharmacy purchase has none,
  so it's N/A.
- **registration_number:** that practitioner's registration number as printed, or N/A if none
  is printed.
- **patient_name:** the patient as printed, or N/A (the pharmacy till receipt has no name).
- **service_date:** the date the service or purchase took place. Issue, invoice, print and
  payment dates, and next-appointment or recall dates, are distractors. Stored as ISO text.
- **receipt_number:** the document's own number, i.e. the number next to its title label
  ("Receipt No.", "Invoice No.", 收據編號, 發票編號). Patient, file, episode, policy, member
  and till numbers are distractors with different labels. No document shows both a "Receipt
  No." and an "Invoice No.", because either would be a reasonable answer.
- **total_amount:** the total charged after discounts and before any payment split (insurer,
  plan, patient). It is never the amount paid, the co-payment, an outstanding balance or a
  stored-value balance. Stored as a number.

**Printing rules,** so the existing scorer judges names fairly:
- Each person's name appears in **one script only** (English or Chinese). The scorer can't
  accept alternative answers.
- The only titles printed next to names are "Dr" / 醫生, because those are the only titles the
  scorer ignores. Other roles go in the label (e.g. 主診中醫師：葉卓謙).

## Before printing and scoring

1. **Fictional identity check.** All names, clinics, addresses, phone numbers and registration
   numbers are made up but realistic. Before printing, search the public registers (Medical,
   Dental, Chinese Medicine, Physiotherapists) and the business names to make sure none
   matches a real person or clinic.
2. **Known scoring gap, to fix before scoring Version 2.** Receipt 4 prints its date as
   `2026年6月9日`. Neither `score.py` nor the shared date parser reads that format, so a correct
   answer copied as written (as Azure DI + AOAI does) would be scored Wrong. Teaching the
   **scorer** to read 年月日 dates fixes this without touching the frozen extraction rules.
   That is a scoring change, so it's left for the scoring phase. All other printed formats
   (`14/03/2026`, `22 April 2026`, `18 May 2026`, `21/08/2026 14:37`, `3 Sep 2026`) are read
   correctly today.
