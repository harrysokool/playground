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
| `generate_receipts.py` | Builds the printable PDFs from the spec: eight separate HTML/CSS templates, printed to PDF by headless Google Chrome. It then checks every PDF against the spec and writes the previews. |
| `printable/` | `receipt1.pdf` … `receipt8.pdf`: **print these** |
| `preview/` | A PNG of each PDF and `contact_sheet.png` showing all eight designs |
| `export_images.py` | Rasterises the validated PDFs to 300 dpi PNGs, cropped to each receipt's real size, then checks them |
| `printable_images/` | `receipt1.png` … `receipt8.png` (300 dpi master images) and `contact_sheet.png` (all eight at the same physical scale) |
| `raw/` | Where the phone photos go, named `receipt1.jpg` … `receipt8.jpg` to match `receipt_id` r1…r8. |

```bash
python data/receipts_v2/build_ground_truth.py   # from python/receipt_ocr_benchmark/
python data/receipts_v2/generate_receipts.py    # needs Google Chrome, Poppler (pdftotext/pdftoppm) and Pillow
python data/receipts_v2/export_images.py        # PNGs from the PDFs (Poppler + Pillow)
```

Every printed value comes from the spec. The templates only add decoration: logos, slogans,
hospital item codes, "Page 1 of 1", a decorative barcode, and the total written in formal
Chinese numerals on receipt 4 (柒佰玖拾圓正 = 790). None of these adds a candidate answer for
the six fields. The generator uses macOS fonts (PingFang HK, LiSong Pro, Kaiti TC, Avenir
Next, Georgia, Menlo). The committed PDFs embed them, so they print the same on any machine.

## Printing and photographing

1. **Print** each PDF on plain white A4 paper, single-sided, **in colour** if possible.
   Choose **"Actual size" / 100%** and turn off "Fit to page", so each receipt keeps its real size.
2. **Cut out the small receipts.** A4 receipts (2, 3, 6, 8) need no cutting.

   | Receipt | Size | Cut along |
   |---|---|---|
   | 1, 4 | A5 | the corner trim marks |
   | 5 | A5 landscape | the two faint horizontal lines |
   | 7 | 80 mm till slip | the dashed outline |
3. **Photograph** one photo per receipt with your phone:
   - normal indoor light, no flash;
   - lay the receipt flat on a plain desk, with all edges in frame;
   - hold the phone roughly above it (a little natural tilt is fine);
   - don't crop, edit or filter.

   Use the same phone for all eight. Save as JPEG: on iPhone, set Settings → Camera → Formats →
   "Most Compatible", or export as JPEG.
4. **Save** the photos as `raw/receipt1.jpg` … `raw/receipt8.jpg`. Don't write on the receipts,
   and leave the small `SAMPLE / 測試樣本` label visible.

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


## Printing the PNG images

The PNGs are 300 dpi lossless masters, identical to the PDFs. Each is cropped to its real size,
without trim marks:

| Receipt | Size |
|---|---|
| 1, 4 | A5, 148 × 210 mm |
| 5 | A5 landscape, 210 × 148 mm |
| 2, 3, 6, 8 | A4 |
| 7 | 80 × 154 mm till slip, including its dashed cutting outline |

They print at that size only at **100% scale**. In macOS Preview: File → Print, then set
**Scale: 100%**. Many photo-printing dialogs default to "Fill" or "Fit", which enlarges the image.

The A4 images fill the whole page. Most office printers can't print the outer ~4 mm, but no text
is that close to the edge. For an exact-size cut-out, print each small receipt on A4 at 100% and
cut around it.

**If exact physical size matters, print the PDFs instead:** they carry the size themselves, and
include trim marks.

## Version 2 benchmark inputs and scoring

The benchmark runs on **all images in `printable_images/`** except `contact_sheet.png`: seven phone
photos of the printed receipts, plus two receipts carried over from Version 1. The pharmacy till
slip (receipt7) was not photographed, so it's not scored.

`benchmark_inputs/` contains relative symlinks that give each image the name its ground-truth
row expects. The originals stay untouched, and nothing is duplicated.

| Input (symlink) | Image | Receipt | Ground truth from |
|---|---|---|---|
| `receipt1.png` | `printable_images/r1.png` | GP clinic | spec r1 |
| `receipt2.png` | `printable_images/r3.png` | Specialist | spec r2 |
| `receipt3.png` | `printable_images/r4.png` | Hospital invoice | spec r3 |
| `receipt4.png` | `printable_images/r5.png` | Chinese medicine | spec r4 |
| `receipt5.png` | `printable_images/r6.png` | Dental | spec r5 |
| `receipt6.png` | `printable_images/r7.png` | Physiotherapy | spec r6 |
| `receipt8.png` | `printable_images/r2.png` | Medical centre | spec r8 |
| `receipt9.jpg` | `printable_images/r8.jpg` | Vet invoice (Version 1 receipt4) | Version 1 ground truth |
| `receipt10.png` | `printable_images/r9.png` | NZ pharmacy (Version 1 receipt6) | Version 1 ground truth |

**Orientation.** The seven photos store their pixels sideways, with EXIF orientation 6.
`prepare_inputs.py` (run on Azure ML) writes the actual benchmark inputs to `results/v2/inputs/`:
- **Photos with a rotation tag:** turned upright with an exact 90° rotation and saved as lossless
  PNG without the tag. No crop, resize or enhancement.
- **Images without a tag** (receipt9, receipt10): copied byte for byte.

All four approaches read these same files. `manifest.csv` records what was done to each image.

`benchmark_ground_truth.xlsx` has exactly these nine rows, with values copied unchanged from
`receipts_spec.json` and `data/ground_truth/ground_truth_template.xlsx`. The test
`tests/test_receipts_v2.py` checks it field by field against both sources, and checks that each
row has exactly one input image.
