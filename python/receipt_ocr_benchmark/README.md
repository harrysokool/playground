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

## Data

Real receipt samples go in `data/raw/` and are **not committed to Git** (see `data/README.md`).

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

`test_paddle_engine.py` runs both configs for real against a tiny synthetic fixture receipt
(`tests/fixtures/receipt.png` — no real patient data). Requires `models/` to be populated (see above).
