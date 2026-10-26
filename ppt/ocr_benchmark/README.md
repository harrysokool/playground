# Receipt OCR Benchmark – Decks

The decks answer one question: **is Azure Document Intelligence + Azure OpenAI worth its
additional cost and complexity compared with simpler OCR solutions?**

**Audience:** business and technical stakeholders.

| Version | Deck | Generator | Source of truth (under `python/receipt_ocr_benchmark/`) |
|---|---|---|---|
| **Version 8 (current)**, 8 slides | `current/OCR_Benchmark_V8.pptx` | `scripts/generate_ppt_v8.py` | As Version 6 |
| Version 7, 9 slides (archived) | `archive/v7_final/OCR_Benchmark_V7.pptx` (+ PDF preview) | `scripts/generate_ppt_v7.py` (unchanged) | As Version 6 |
| Version 6, 10 slides (archived) | `archive/v6_final/OCR_Benchmark_V6.pptx` (+ PDF preview) | `scripts/generate_ppt_v6.py` (unchanged) | As Version 5, plus `results/v2/scores_multilingual/` |
| Version 5, 10-slide management version (archived) | `archive/v5_final/OCR_Benchmark_V5.pptx` (+ PDF preview) | `scripts/generate_ppt_v5.py` (unchanged) | `results/v2/scores_improved/` and `scores_aoai_improved/`, `results/v1_heldout/`, `results/diagnosis/`, `results/v2/*/receiptN.json`, `receipt_bench/di_aoai.py` (prompt text) |
| Version 4, 12-slide redesign (archived) | `archive/v4_final/OCR_Benchmark_V4.pptx` (+ PDF preview) | `scripts/generate_ppt_v4.py` (unchanged) | `results/v2/scores_improved/` and `scores_aoai_improved/`, `results/v1_heldout/`, `results/diagnosis/`, `data/diagnosis/`, `results/v2/*/receiptN.json`, `receipt_bench/di_aoai.py` (prompt text) |
| Version 3, final 12-slide deck (archived) | `archive/v3_final/OCR_Benchmark_V3.pptx` (+ PDF preview) | `scripts/generate_ppt_v3.py` (unchanged) | `results/v2/scores_improved/` and `scores_aoai_improved/` (summary, detail), `results/v1_heldout/`, `results/v2/*/receiptN.json`, receipt photos in `data/receipts_v2/` |
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
| `current/` | The current deck (Version 8) |
| `previews/` | PDF and PNG previews of the current deck |
| `archive/v1/` | The frozen Version 1 deck and its preview. Never written to by the generators. |
| `archive/v2_12slides/` | The first, 12-slide Version 2 deck and its PDF preview, kept for reference |
| `archive/v2_8slides/` | The 8-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_9slides/` | The 9-slide revision of Version 2 and its PDF preview, kept for reference |
| `archive/v2_10slides/` | The 10-slide revision before the slide 9 rewrite, and its PDF preview |
| `archive/v7_final/` | The 9-slide Version 7 deck and its PDF preview |
| `archive/v6_final/` | The 10-slide Version 6 deck and its PDF preview |
| `archive/v5_final/` | The 10-slide Version 5 deck and its PDF preview |
| `archive/v4_final/` | The 12-slide Version 4 deck and its PDF preview |
| `archive/v3_final/` | The final 12-slide Version 3 deck and its PDF preview |
| `archive/v3_10slides/` | The 10-slide Version 3 revision and its PDF preview |
| `archive/v3_first/` | The first Version 3 revision (rule accuracy not shown) and its PDF preview |
| `archive/v2_final/` | The final Version 2 deck (with PaddleOCR Heavy and the tuned rule accuracies) and its PDF preview |
| `assets_v2/` | Receipt crops and thumbnails produced by `generate_ppt_v2.py`, `generate_ppt_v3.py`, `generate_ppt_v4.py`, `generate_ppt_v5.py`, `generate_ppt_v6.py`, `generate_ppt_v7.py` and `generate_ppt_v8.py` (identical) |
| `scripts/` | The generators |

## Version 8: concise 8-slide deck

1. Title
2. **Executive summary:** Azure DI + AOAI prompt v2 96.1% (development result) vs OCR + multilingual rules
   51.0–70.6% (51.0% PaddleOCR Light, 70.6% Azure DI; retrospective baseline), and why AOAI may still be
   needed. Small labels only, no caveat bar.
3. What we compared (9 receipts, 6 fields, 3 approaches; 51 of 54 fields scored)
4. **Rules vs AOAI on the same receipts:** multilingual rules 51.0% / 70.6% vs AOAI prompt v2 96.1%. No
   English-only rules and no original prompt.
5. **The key difference: maintenance**, without the "Not guaranteed" box. That caveat is in the notes;
   diagnosis stays a one-line example.
6. **Advantages and disadvantages.** AOAI speed and tokens now come from the prompt v2 run (6.4 s; about
   962 input / 243 output tokens per receipt).
7. **Beyond six fields, redesigned:** a real hospital receipt's line items → an illustration of the
   structured data AOAI could return (typed from the receipt's OCR text, not AOAI output) → example
   analytics. Marked potential, not yet tested.
8. **Recommendation and next steps,** with a one-line "evidence so far" note.

The limitations slide was removed. Its points are in the speaker notes of slides 2, 4, 6 and 8, and in the
note on slide 8. `scripts/check_deck_v8.py` = the Version 7 checks for 8 slides, plus: no slide shows 88.2%
or the English-only figures, and charts show only the multilingual rules and prompt v2.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v8.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v8.py
```

`scripts/build_v8_on_azure.sh` does the same on Azure ML compute. The Version 7 generator and check are
kept unchanged to reproduce the archived Version 7 deck.

## Version 7: simplified management deck (9 slides)

1. Title
2. **Executive summary:** Azure DI + AOAI prompt v2 96.1% (development result) vs OCR + general
   multilingual rules 51.0–70.6% (51.0% = PaddleOCR Light, 70.6% = Azure DI; retrospective), why AOAI may
   still be needed, and a short caveat. The 88.2% figure is not on this slide.
3. **What we compared:** for each of the 9 receipts, 6 key fields across 3 approaches. A small note says
   51 of 54 fields are scored, because 3 receipts have no doctor registration number.
4. **A fairer comparison:** multilingual rules 51.0% / 70.6% vs AOAI with its original prompt 88.2%, and
   what rules would still need. No English-only bars.
5. The key difference: maintenance
6. Advantages and disadvantages
7. Beyond six fields (potential, not yet benchmarked)
8. Limits of this evidence
9. Recommendation and next steps

The Version 6 "Improving AOAI" slide was removed. English-only and tuned rule figures are not shown.
`scripts/check_deck_v7.py` = the Version 6 checks for 9 slides, plus: no 88.2% or English-only rule figure
on the executive summary.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v7.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v7.py
```

The Version 6 generator and check are kept
unchanged to reproduce the archived Version 6 deck.

## Version 6: Version 5 plus the multilingual rules baseline

The same 10 slides as Version 5. Slide 4, "Initial Results and a Fairer Rules Baseline", now shows the
retrospective multilingual rules baseline (`python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md`)
next to the first, English-only rules. The baseline is the original rules plus common Chinese labels,
fixed before scoring:

| | English-only rules | With Chinese labels (retrospective) | AOAI, original prompt |
|---|---|---|---|
| PaddleOCR Light | 37.3% | 51.0% | |
| Azure DI | 41.2% | 70.6% | 88.2% |

Every slide that shows these figures labels them as retrospective: the labels were added after these
receipts were examined, so they are not an independent test. The answer, pros and cons, and limitations
slides cite the baseline too.

`scripts/check_deck_v6.py` = the Version 5 checks, plus: chart values may also be the baseline figures,
and a slide showing them must say "retrospective".

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v6.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v6.py
```

The Version 5 generator and check are
kept unchanged to reproduce the archived Version 5 deck.

## Version 5: the management version (10 slides)

A shorter version of Version 4 for management. The question: is OCR with hand-written extraction rules
enough to replace Azure OpenAI, and what value does AOAI add?

1. Title · 2. The answer in brief · 3. What we compared · 4. Initial results (37.3% / 41.2% / 88.2%; the
first rules had no Chinese labels) · 5. Improving AOAI: clearer instructions (96.1%, development result;
the four fixes and AOAI accuracy per field) · 6. The key difference: maintenance (rules anticipate every
case in code; AOAI works from plain-language instructions, not guaranteed for unseen layouts; the
diagnosis check as a short example where rules were enough) · 7. Advantages and disadvantages (cost,
speed, accuracy, maintenance, flexibility, auditability, reliability) · 8. Beyond six fields (potential,
not yet benchmarked) · 9. Limits of this evidence · 10. Recommendation and next steps.

**Changes from Version 4:** the tuned rule accuracies (88.2% and 86.3%, and the rules' per-field figures
after tuning) are removed everywhere, because the rules were adapted by hand to these receipts. The
per-field slide now compares AOAI's original prompt with prompt v2 only. Diagnosis detection is a
one-line example rather than a slide.

`scripts/check_deck_v5.py` enforces: 10 slides; no Heavy; no tuned rule figure in slides, tables, charts
or notes (it fails on the Version 4 deck); charts show only the initial results; 96.1% only with a
development label; original rule figures only with the missing Chinese support; the "beyond six
fields" slide marked as potential.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v5.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v5.py
```

The Version 4
generator and check are kept unchanged to reproduce the archived Version 4 deck.

## Version 4: a redesign around one question

**Can OCR with extraction rules replace Azure OpenAI for medical receipts, and if not, why is AOAI
needed?** The answer comes first, then the evidence. Every slide carries an evidence tag: measured
before tuning, measured on the development set, or potential (not yet tested).

1. Title · 2. The answer in brief · 3. What we compared · 4. Before tuning (chart; why the rules scored
low) · 5. After tuning (chart; effort of each change) · 6. Accuracy by field · 7. What prompt v2 changed ·
8. Rules vs AOAI scorecard (accuracy, speed, cost, effort, side effects, new layouts, control) ·
9. Diagnosis-comment check (when rules are enough) · 10. Beyond six fields (potential only) ·
11. Limits of what we know · 12. Recommendation and next steps.

`scripts/check_deck_v4.py` enforces: 12 slides; no Heavy; chart values match the score files; original
rule figures only with the missing Chinese support explained; development figures only with a
development label; the "beyond six fields" slide marked as potential and not yet tested.

```bash
python3 ppt/ocr_benchmark/scripts/generate_ppt_v4.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v4.py
```

The Version 3
generator and check (`generate_ppt_v3.py`, `check_deck_v3.py`) are kept unchanged to reproduce the
archived Version 3 deck (use `--output` to write it elsewhere).

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


## Previews

These need LibreOffice and Poppler:

```bash
cd ppt/ocr_benchmark
soffice --headless --convert-to pdf --outdir previews current/OCR_Benchmark_V8.pptx
mv previews/OCR_Benchmark_V8.pdf previews/OCR_Benchmark_V8_preview.pdf
pdftoppm -png -r 80 previews/OCR_Benchmark_V8_preview.pdf previews/slide
```

LibreOffice may substitute fonts, so the preview is for review. PowerPoint renders Arial and
Microsoft JhengHei (Traditional Chinese).

## Outstanding before distribution

1. **Prices.** Compute rate, Document Intelligence page price and gpt-5-mini token prices are
   still unconfirmed; slide 6 says so.
2. **Sensitivity label.** The deck carries the template's **[AIA – PUBLIC]** label. Apply the
   correct label in PowerPoint (Home → Sensitivity) before sharing.
3. **Presenter name and date,** if required.
