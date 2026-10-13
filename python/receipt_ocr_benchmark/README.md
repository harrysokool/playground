# Receipt OCR Benchmark

A disposable benchmark, **not production code**, comparing approaches for turning medical
receipts into structured data. It exists to answer one question: is the extra cost and
complexity of Azure Document Intelligence + Azure OpenAI justified over simpler alternatives?

Approaches compared (see project notes for the full plan):

1. Pure OCR — light PaddleOCR (PP-OCRv5 mobile)
2. Pure OCR — heavier PaddleOCR (PP-OCRv5 server)
3. Azure Document Intelligence + deterministic rules
4. Existing Azure DI + Azure OpenAI solution (not rebuilt here — compared against separately)

**Phase 1**: raw OCR only. Run a receipt image/PDF through the light or heavy PaddleOCR
configuration and get back a normalized JSON of text, confidence, coordinates, and timing.

**Phase 3** (current): deterministic rule-based extraction of 6 fields (doctor/provider name,
registration number, patient name, receipt number, service date, total amount) from the raw
OCR JSON — label matching, regex, and nearby-block lookup by coordinates. No line items yet,
no Azure DI, no LLM. If a field has no reliable simple rule, it's left `null` with a warning
rather than guessed.

## Setup

Requires Python 3.9–3.13 (pinned `paddlepaddle==3.3.1` only ships CPU wheels for those versions).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Models (fully offline)

The configs load PaddleOCR models from local directories instead of downloading them, so the
benchmark runs with no internet access (required on the Azure VM). Extract the four PP-OCRv5
model archives under `models/` (not committed to Git — see `models/README.md`):

```
models/
├── PP-OCRv5_mobile_det_infer/   # configs/paddle_light.yaml
├── PP-OCRv5_mobile_rec_infer/   # configs/paddle_light.yaml
├── PP-OCRv5_server_det_infer/   # configs/paddle_heavy.yaml
└── PP-OCRv5_server_rec_infer/   # configs/paddle_heavy.yaml
```

Commands must be run from the project root (`configs/*.yaml` reference `models/...` as a
relative path).

## Usage

```bash
# Light OCR (PP-OCRv5 mobile)
python -m receipt_bench.cli --config configs/paddle_light.yaml --input data/raw --output results/paddle_light

# Heavy OCR (PP-OCRv5 server)
python -m receipt_bench.cli --config configs/paddle_heavy.yaml --input data/raw --output results/paddle_heavy
```

`--input` may be a single image/PDF file or a directory of them. One JSON file per input document
is written to `--output`, containing the normalized raw OCR result (see `receipt_bench/raw_ocr.py`).

## Extraction (Phase 3)

Runs deterministic rules over already-generated raw OCR JSON (from `## Usage` above), not
over the receipt files directly:

```bash
python -m receipt_bench.extract_cli --input results/paddle_light --output results/paddle_light_extracted
python -m receipt_bench.extract_cli --input results/paddle_heavy --output results/paddle_heavy_extracted
```

Rules live in `receipt_bench/extraction.py` — see `FIELD_RULES` for the exact labels matched
per field. Each field tries a label match first (same block, or nearest block by OCR
coordinates if the label is alone), then falls back to a standalone pattern for unlabeled
values (e.g. "Dr Chan", "M12345") if no label matched anywhere. Each output JSON has the 6
fields, a `sources` map (which OCR block text each value came from), and a `warnings` list
for anything left `null`.

## Overfit extraction experiment (Phase 3b)

`receipt_bench/extraction_tuned.py` is a deliberately **overfit** rule set, tuned by hand to
the 6 receipts in `data/raw` (4 layouts), to measure how far OCR + deterministic rules can go
when you invest in layout-specific handling. It is not meant to generalize. Every rule is
tagged `[GENERAL]` or `[OVERFIT]` in the code and in each output's `rules` map. Unknown
layouts fall back to the Phase 3 baseline rules.

```bash
python -m receipt_bench.extract_cli --rules tuned --input results/paddle_light --output results/extracted_tuned_light
python -m receipt_bench.extract_cli --rules tuned --input results/paddle_heavy --output results/extracted_tuned_heavy
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach tuned_light=results/extracted_tuned_light --approach tuned_heavy=results/extracted_tuned_heavy
```

## General rules baseline (Phase 3c)

`receipt_bench/extraction_general.py` is the honest non-AI baseline: reusable deterministic
rules only (label vocabularies, same-line / below / above-right lookup, generic date and
amount parsing, totals semantics, arithmetic checks), with **no** layout detection, per-layout
handlers, receipt coordinates or ground-truth-driven fixes. It fails closed. Each output also
records `timings.ocr_predict_ms` (from the raw OCR JSON) and `timings.extract_ms`.

```bash
python -m receipt_bench.extract_cli --rules general --input results/paddle_light --output results/extracted_general_light
python -m receipt_bench.extract_cli --rules general --input results/paddle_heavy --output results/extracted_general_heavy
```

## Scoring all approaches (Phase 1 of the final comparison)

`receipt_bench/score.py` scores any number of named approaches against the same ground truth
and the same six fields: `doctor_name`, `registration_number`, `patient_name`,
`receipt_number`, `service_date`, `total_amount`.

```bash
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach paddle_light=results/extracted_general_light \
    --approach paddle_heavy=results/extracted_general_heavy \
    --approach azure_di=results/<azure_di_run_dir> \
    --approach azure_di_aoai=results/<azure_di_aoai_run_dir> \
    --output-dir results/scores
```

Each receipt × field is marked:

- **Correct**: the field is on the receipt and the approach returned the same value.
- **Wrong**: the field is on the receipt and the approach returned a different value or
  nothing. A missing result file, a failed run (e.g. a timeout) or a result with no extracted
  fields counts as nothing, so failures can only lower accuracy.
- **N/A**: the field is not on the receipt (ground truth `na`). These are excluded from
  accuracy. A value returned anyway is counted separately as **invented**.

`Accuracy = Correct / applicable fields × 100`, overall and for each field.

Normalization is kept simple:
- Names ignore case, punctuation, spacing and titles (Dr / 醫生 / 医生).
- Dates are compared as calendar dates with no day/month swapping. The ground truth must be
  ISO text, and a non-ISO predicted date is read day-first.
- Amounts are equal within 0.005.
- Receipt and registration numbers are an exact match.

`--output-dir` writes:
- `report.md`: overall table, per-field accuracy and a per-receipt detail table.
- `summary.csv`: one row per approach (correct, applicable, accuracy %, invented, receipts
  with no result, mean processing ms, per-field accuracy %). Use this for the deck.
- `detail.csv`: one row per approach × receipt × field.

**Adding an approach:** write one JSON per receipt (`receipt1.json`, …) into a directory and
pass it as `--approach NAME=DIR`. The scorer reads two formats today (see `read_result`):
- the six fields at the top level, as `extract_cli` writes them, with optional
  `timings.ocr_predict_ms` / `timings.extract_ms`;
- the Azure DI + AOAI runner format, with fields under `benchmark_fields`, plus `status`,
  `timings_seconds.total` and `aoai_output`.

Use the six standard field names and `null` for anything not found. Write dates as ISO
`YYYY-MM-DD` if possible. Other names for a field are mapped in `FIELD_ALIASES` (currently
`visit_date` → `service_date`); an alias only fills a standard field that is empty.

Ground-truth corrections and open questions are in `data/ground_truth/GROUND_TRUTH_REVIEW.md`.

## Data

Real receipt samples go in `data/raw/` and are **not committed to Git** (see `data/README.md`).

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

`test_paddle_engine.py` runs both configs for real against a tiny synthetic fixture receipt
(`tests/fixtures/receipt.png` — no real patient data). Requires `models/` to be populated (see above).
