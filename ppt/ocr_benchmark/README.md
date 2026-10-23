# Receipt OCR Benchmark – Decks

The decks answer one question: **is Azure Document Intelligence + Azure OpenAI worth its
additional cost and complexity compared with simpler OCR solutions?**

**Audience:** business and technical stakeholders.

| Version | Deck | Generator | Source of truth (under `python/receipt_ocr_benchmark/`) |
|---|---|---|---|
| **Version 3 (current)**, 12 slides | `current/OCR_Benchmark_V3.pptx` | `scripts/generate_ppt_v3.py` | `results/v2/scores_improved/` and `scores_aoai_improved/` (summary, detail), `results/v1_heldout/`, `results/v2/*/receiptN.json`, receipt photos in `data/receipts_v2/` |
| Version 3, 10-slide revision before the field and prompt v2 slides (archived) | `archive/v3_10slides/OCR_Benchmark_V3.pptx` (+ PDF preview) | `scripts/generate_ppt_v3.py` at commit `c06d945` | Same as Version 3 |
| Version 3, first revision (archived): no rule accuracy figures | `archive/v3_first/OCR_Benchmark_V3.pptx` (+ PDF preview) | `scripts/generate_ppt_v3.py` at commit `3678fd9` | Same as Version 3 |
| Version 2, final 10-slide deck (archived) | `archive/v2_final/OCR_Benchmark_V2.pptx` (+ PDF preview) | `scripts/generate_ppt_v2.py` (unchanged) | `results/v2/scores_improved/` (summary, detail), `results/v2/*/receiptN.json`, receipt photos in `data/receipts_v2/` |
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
| `current/` | The current deck (Version 3) |
| `previews/` | PDF and PNG previews of the current deck |
| `archive/v1/` | The frozen Version 1 deck and its preview. Never written to by the generators. |
| `archive/v2_12slides/` | The first, 12-slide Version 2 deck and its PDF preview, kept for reference |
| `archive/v2_8slides/` | The 8-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_9slides/` | The 9-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_10slides/` | The 10-slide revision before the slide 9 rewrite, and its PDF preview |
| `archive/v3_10slides/` | The 10-slide Version 3 revision and its PDF preview |
| `archive/v3_first/` | The first Version 3 revision (rule accuracy not shown) and its PDF preview |
| `archive/v2_final/` | The final Version 2 deck (with PaddleOCR Heavy and the tuned rule accuracies) and its PDF preview |
| `assets_v2/` | Receipt crops and thumbnails produced by `generate_ppt_v2.py` and `generate_ppt_v3.py` (identical) |
| `scripts/` | The generators |

## Version 3: what changed from Version 2

Version 3 tells the story in two steps; the OCR code, results and ground truth are unchanged.
- **Slide 3, Initial Results:** every approach before any tuning on the nine Version 2 receipts
  (PaddleOCR Light + rules 37.3%, Azure DI + rules 41.2%, Azure DI + AOAI 88.2%). The original rules
  had no Chinese labels, so this compares initial implementations, not maximum capability.
- **Slide 4, How We Improved Accuracy:** one table of what was changed in each approach, the resulting
  development scores (88.2%, 86.3%, AOAI prompt v2 96.1%) and fields fixed / broken (rules +27/−1 and
  +24/−1, prompt +4/−0), plus the effort of changing rules vs a prompt. Labelled as development results,
  not independent validation.
- **Slide 5, Accuracy by Field:** the three tuned approaches per field, every count taken from
  `scores_aoai_improved/detail.csv` and checked against `summary.csv`; labelled as development results.
  Registration number has 6 applicable receipts, every other field 9.
- **Slide 6, What Changed in AOAI Prompt V2:** the four fields prompt v2 fixed (88.2% → 96.1%), the
  original and new replies, and the prompt v2 wording behind each (checked against `SYSTEM_PROMPT_V2`).
  The fixes are already in the model's own reply, in the plain-text, row-layout and photo runs alike; the
  Python checks changed no value. So the credit goes to the prompt wording only.
- **Later slides do not repeat these figures.** The "AOAI replaces the rule layer" diagram was dropped
  (slide 2 already shows the two steps); slides 8–10 focus on effort, maintenance and new layouts.
- **The small held-out Version 1 check** is mentioned only in the speaker notes, and is not used to say
  that either approach generalises better.
- **PaddleOCR Heavy is removed everywhere** (discontinued in October 2026).

`scripts/check_deck_v3.py` enforces: 12 slides; no Heavy; every per-field count on slide 5; original rule figures only on a slide that explains the
missing Chinese support; 86.3% and 96.1% only on a slide that calls them development results.

## Generate the Version 3 deck

This reads committed results only: no OCR, scoring or Azure calls. Run it anywhere that has
python-pptx and Pillow; the committed deck was built on a Mac. From the repository root:

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v3.py --force   # deck + receipt crops in assets_v2/
python3 ppt/ocr_benchmark/scripts/check_deck_v3.py              # verifies figures and labels; writes previews/deck_text.md
```

Without `--force`, the script won't overwrite an existing deck. It always refuses to write
into `archive/` or `template/`. `scripts/generate_ppt_v2.py` and `check_deck_v2.py` are kept
unchanged to reproduce the archived Version 2 deck (use `--output` to write it elsewhere).

`scripts/build_v3_on_azure.sh` does the same on Azure ML compute, then commits and pushes.

## Previews

These need LibreOffice and Poppler:

```bash
cd ppt/ocr_benchmark
soffice --headless --convert-to pdf --outdir previews current/OCR_Benchmark_V3.pptx
mv previews/OCR_Benchmark_V3.pdf previews/OCR_Benchmark_V3_preview.pdf
pdftoppm -png -r 80 previews/OCR_Benchmark_V3_preview.pdf previews/slide
```

LibreOffice may substitute fonts, so the preview is for review. PowerPoint renders Arial and
Microsoft JhengHei (Traditional Chinese).

## Outstanding before distribution

1. **Prices.** Compute rate, Document Intelligence page price and gpt-5-mini token prices are
   still unconfirmed; slide 8 says so.
2. **Sensitivity label.** The deck carries the template's **[AIA – PUBLIC]** label. Apply the
   correct label in PowerPoint (Home → Sensitivity) before sharing.
3. **Presenter name and date,** if required.
