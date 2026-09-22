# Receipt OCR Benchmark

A disposable benchmark, **not production code**, comparing approaches for turning medical
receipts into structured data. It exists to answer one question: is the extra cost and
complexity of Azure Document Intelligence + Azure OpenAI justified over simpler alternatives?

Approaches compared (see project notes for the full plan):

1. Pure OCR — light PaddleOCR (PP-OCRv5 mobile)
2. Pure OCR — heavier PaddleOCR (PP-OCRv5 server)
3. Azure Document Intelligence + deterministic rules
4. Existing Azure DI + Azure OpenAI solution (not rebuilt here — compared against separately)

**Phase 1** (current): raw OCR only. Run a receipt image/PDF through the light or heavy
PaddleOCR configuration and get back a normalized JSON of text, confidence, coordinates, and
timing. No structured field extraction yet — that's Phase 3, after inspecting real samples.

## Setup

Requires Python 3.9–3.13 (pinned `paddlepaddle==3.3.1` only ships CPU wheels for those versions).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

First run downloads the PaddleOCR models (internet required once; cached under `~/.paddlex` after).

## Usage

```bash
python -m receipt_bench.cli --config configs/paddle_light.yaml --input data/raw --output results/paddle_light
python -m receipt_bench.cli --config configs/paddle_heavy.yaml --input data/raw --output results/paddle_heavy
```

`--input` may be a single image/PDF file or a directory of them. One JSON file per input document
is written to `--output`, containing the normalized raw OCR result (see `receipt_bench/raw_ocr.py`).

## Data

Real receipt samples go in `data/raw/` and are **not committed to Git** (see `data/README.md`).

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

`test_paddle_engine.py` runs both configs for real against a tiny synthetic fixture receipt
(`tests/fixtures/receipt.png` — no real patient data) and downloads PaddleOCR models on first run.
