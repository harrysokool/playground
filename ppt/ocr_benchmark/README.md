# Receipt OCR Benchmark – Decks

The decks answer one question: **is Azure Document Intelligence + Azure OpenAI worth its
additional cost and complexity compared with simpler OCR solutions?**

**Audience:** business and technical stakeholders.

| Version | Deck | Generator | Source of truth (under `python/receipt_ocr_benchmark/`) |
|---|---|---|---|
| **Version 2 (current)**, 12 slides | `current/OCR_Benchmark_V2.pptx` | `scripts/generate_ppt_v2.py` | `results/v2/scores_improved/` (summary, detail), `results/v2/*/receiptN.json`, receipt photos in `data/receipts_v2/` |
| Version 1 (frozen), 8 slides | `archive/v1/OCR_Benchmark_Comparison.pptx` (+ PDF preview) | `scripts/generate_ppt.py` | Version 1 results, available only at Git tag `ocr-benchmark-v1` |

Every number, and every value in the receipt examples, is read from the benchmark files; nothing
is typed in by hand.
- **Example values** are taken from `detail.csv` and cross-checked against the extraction JSON.
  The build stops on any mismatch.
- **Receipt crops** are placed using Azure DI's text positions. The build stops if an anchor
  text isn't found.
- **Crops and thumbnails** are written to `assets_v2/`.

## Folder structure

| Folder | Contents |
|---|---|
| `template/` | Official AIA PowerPoint template (`aia_ppt_template.pptx`). Do not edit. |
| `current/` | The current deck (Version 2) |
| `previews/` | PDF and PNG previews of the current deck |
| `archive/v1/` | The frozen Version 1 deck and its preview. Never written to by the generators. |
| `assets_v2/` | Receipt crops and thumbnails produced by `generate_ppt_v2.py` |
| `scripts/` | The generators |

## Generate the Version 2 deck (Azure ML compute)

Run from the repository root. This needs python-pptx and Pillow; Pillow is already in the
benchmark environment.

```bash
source ~/venvs/paddle322/bin/activate && git pull && pip install python-pptx==1.0.2
python3 ppt/ocr_benchmark/scripts/generate_ppt_v2.py --force
```

Without `--force`, the script won't overwrite an existing deck. It always refuses to write
into `archive/` or `template/`.

## Previews (Azure ML compute)

These need LibreOffice, Poppler, and a CJK font so Chinese text renders in the preview:

```bash
sudo apt-get update && sudo apt-get install -y libreoffice-impress poppler-utils fonts-noto-cjk
cd ppt/ocr_benchmark
soffice --headless --convert-to pdf --outdir previews current/OCR_Benchmark_V2.pptx
mv previews/OCR_Benchmark_V2.pdf previews/OCR_Benchmark_V2_preview.pdf
pdftoppm -png -r 60 previews/OCR_Benchmark_V2_preview.pdf previews/slide
```

LibreOffice substitutes fonts (Arial → Liberation Sans, Microsoft JhengHei → Noto CJK), so the
preview is for review only. PowerPoint renders the real fonts. Commit `current/`, `previews/` and
`assets_v2/` afterwards.

## Outstanding before distribution

1. **Prices.** Compute rate, Document Intelligence page price and gpt-5-mini token prices are
   still unconfirmed; slide 10 says so.
2. **Sensitivity label.** The deck carries the template's **[AIA – PUBLIC]** label. Apply the
   correct label in PowerPoint (Home → Sensitivity) before sharing.
3. **Presenter name and date,** if required.
