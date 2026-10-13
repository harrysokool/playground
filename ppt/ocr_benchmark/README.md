# Receipt OCR Benchmark – Comparison Deck

An 8-slide deck answering one question: **is Azure Document Intelligence + Azure OpenAI worth its
additional cost and complexity compared with simpler OCR solutions?**

- **Audience:** business and technical stakeholders.
- **Source of truth:** the benchmark in `python/receipt_ocr_benchmark/`, in particular
  `results/scores_all/FINAL_COMPARISON.md`, `summary.csv`, `detail.csv` and `results/di_aoai/*.json`.
  The generator reads every number from those files, so nothing is typed in by hand.

## Folder structure

| Folder | Contents |
|---|---|
| `template/` | Official AIA PowerPoint template (`aia_ppt_template.pptx`, same as `../contingent_worker`). Do not edit. |
| `current/` | Latest deck: `OCR_Benchmark_Comparison.pptx` |
| `previews/` | PDF preview of the current deck |
| `archive/` | Earlier versions, one subfolder per version (empty so far) |
| `scripts/generate_ppt.py` | Generates the current deck from the template and the benchmark results |

## Regenerate the deck

Requires Python 3.9+ and `python-pptx`. Run from this folder:

```bash
python3 scripts/generate_ppt.py --force
```

Without `--force`, the script won't overwrite an existing deck. It refuses to write into
`archive/` or `template/`. To check reproduction without touching the current file, write it
somewhere else:

```bash
python3 scripts/generate_ppt.py --output /tmp/check.pptx
```

**For a new version:** move the current deck into `archive/v1/` (then `v2/` and so on) first,
then regenerate.

## Generate the PDF preview

```bash
soffice --headless --convert-to pdf --outdir previews current/OCR_Benchmark_Comparison.pptx
mv previews/OCR_Benchmark_Comparison.pdf previews/OCR_Benchmark_Comparison_preview.pdf
```

LibreOffice substitutes some fonts, so the preview is for review only.

## Outstanding before distribution

1. **Prices for slide 7.** Usage per 1,000 receipts is measured, but the prices are marked
   *Pending*. We need:
   - the Azure ML VM hourly rate;
   - the Document Intelligence Read price per 1,000 pages;
   - the gpt-5-mini price per 1M input and output tokens.
2. **Sensitivity label.** The deck carries the template's **[AIA – PUBLIC]** label. Apply the
   correct label in PowerPoint (Home → Sensitivity) before sharing.
3. **Presenter name and date,** if required (the title slide says October 2026).
