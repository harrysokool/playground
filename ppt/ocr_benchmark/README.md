# Receipt OCR Benchmark – Decks

The decks answer one question: **is Azure Document Intelligence + Azure OpenAI worth its
additional cost and complexity compared with simpler OCR solutions?**

**Audience:** business and technical stakeholders.

| Version | Deck | Generator | Source of truth (under `python/receipt_ocr_benchmark/`) |
|---|---|---|---|
| **Version 2 (current)**, 10 slides | `current/OCR_Benchmark_V2.pptx` | `scripts/generate_ppt_v2.py` | `results/v2/scores_improved/` (summary, detail), `results/v2/*/receiptN.json`, receipt photos in `data/receipts_v2/` |
| Version 2, 10-slide revision before the slide 9 rewrite (archived; as last saved in PowerPoint) | `archive/v2_10slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `dbec587` | Same as Version 2 |
| Version 2, 9-slide revision (archived) | `archive/v2_9slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `5e11b39` | Same as Version 2 |
| Version 2, 8-slide revision (archived) | `archive/v2_8slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `772e109` | Same as Version 2 |
| Version 2, first draft (archived), 12 slides | `archive/v2_12slides/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` at commit `6fd991c` | Same as Version 2 |
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
| `archive/v2_12slides/` | The first, 12-slide Version 2 deck and its PDF preview, kept for reference |
| `archive/v2_8slides/` | The 8-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_9slides/` | The 9-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_10slides/` | The 10-slide revision before the slide 9 rewrite, and its PDF preview |
| `assets_v2/` | Receipt crops and thumbnails produced by `generate_ppt_v2.py` |
| `scripts/` | The generators |

## Generate the Version 2 deck

This reads committed results only: no OCR, scoring or Azure calls. Run it anywhere that has
python-pptx and Pillow; the committed deck was built on a Mac. From the repository root:

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v2.py --force   # deck + receipt crops in assets_v2/
python3 ppt/ocr_benchmark/scripts/check_deck_v2.py              # verifies figures; writes previews/deck_text.md
```

Without `--force`, the script won't overwrite an existing deck. It always refuses to write
into `archive/` or `template/`.

`scripts/build_v2_on_azure.sh` does the same on Azure ML compute, then commits and pushes.

## Previews

These need LibreOffice and Poppler:

```bash
cd ppt/ocr_benchmark
soffice --headless --convert-to pdf --outdir previews current/OCR_Benchmark_V2.pptx
mv previews/OCR_Benchmark_V2.pdf previews/OCR_Benchmark_V2_preview.pdf
pdftoppm -png -r 80 previews/OCR_Benchmark_V2_preview.pdf previews/slide
```

LibreOffice may substitute fonts, so the preview is for review. PowerPoint renders Arial and
Microsoft JhengHei (Traditional Chinese).

## Outstanding before distribution

1. **Prices.** Compute rate, Document Intelligence page price and gpt-5-mini token prices are
   still unconfirmed; slides 8 and 9 say so.
2. **Sensitivity label.** The deck carries the template's **[AIA – PUBLIC]** label. Apply the
   correct label in PowerPoint (Home → Sensitivity) before sharing.
3. **Presenter name and date,** if required.
