"""Check the generated Version 4 deck against the benchmark results, and dump its text for review.

    python3 ppt/ocr_benchmark/scripts/check_deck_v4.py      (after generate_ppt_v4.py)

Checks:
- 12 slides, every slide has speaker notes;
- PaddleOCR Heavy and its accuracy figures appear nowhere (slides or notes);
- every chart value is an accuracy in the score files;
- the initial and development accuracies, the diagnosis results and the AOAI time all appear;
- a slide showing an original rule figure (37.3 / 41.2) also mentions the missing Chinese support;
- a slide showing a development figure (86.3 / 96.1) also says "development" (numbers are matched
  without the % sign, since ranges are written "37.3–41.2%");
- the "beyond six fields" slide carries the POTENTIAL tag and says the fields are not yet tested.
Writes previews/deck_text.md (all slide text, chart data and notes). Exits non-zero on failure.
"""
import csv
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
BENCH = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark"
RES = BENCH / "results" / "v2"
DECK = PROJECT / "current" / "OCR_Benchmark_V4.pptx"


def summary(path):
    with open(path, newline="") as fh:
        return {r["approach"]: r for r in csv.DictReader(fh)}


SUM, SUM_V2 = summary(RES / "scores_improved" / "summary.csv"), summary(RES / "scores_aoai_improved" / "summary.csv")
DIAG = summary(BENCH / "results" / "diagnosis" / "scores" / "summary.csv")
pct = lambda r: f"{float(r['accuracy_pct']):.1f}%"  # noqa: E731
AOAI_PCT, AOAI_V2_PCT = pct(SUM["azure_di_aoai"]), pct(SUM_V2["aoai_v2_rows"])
AOAI_SECS = f"{int(SUM['azure_di_aoai']['mean_ms_per_receipt']) / 1000:.1f} s"
INITIAL = {pct(SUM[a]) for a in ("paddle_light_general", "azure_di_general")}
DEVELOPMENT = {pct(SUM[a]) for a in ("paddle_light_improved", "azure_di_improved")} | {AOAI_V2_PCT}
HEAVY = {pct(r) for a, r in SUM.items() if "heavy" in a} - INITIAL - DEVELOPMENT - {AOAI_PCT}
CHART_OK = {round(float(r["accuracy_pct"]), 1) for a, r in SUM.items() if "heavy" not in a} | \
    {round(float(SUM_V2["aoai_v2_rows"]["accuracy_pct"]), 1)}
DIAG_FIGS = {f"{r['correct']}/{r['receipts']}" for r in DIAG.values()}

prs = Presentation(DECK)
problems, out = [], [f"# {DECK.name}: text, chart data and notes\n"]
if len(prs.slides) != 12:
    problems.append(f"expected 12 slides, found {len(prs.slides)}")
slide_texts = []
for i, s in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}\n")
    paras = []
    for sh in s.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            out.append("- " + sh.text_frame.text.replace("\n", " / "))
            paras += [p.text for p in sh.text_frame.paragraphs]
        if sh.has_table:
            for row in sh.table.rows:
                cells = [c.text.replace("\n", " ") for c in row.cells]
                out.append("  | " + " | ".join(cells) + " |")
                paras += cells
        if sh.has_chart:
            plot = sh.chart.plots[0]
            cats = [c.replace("\n", " ") for c in plot.categories]
            for ser in plot.series:
                vals = list(ser.values)
                out.append(f"  chart '{ser.name}': " + ", ".join(f"{c}={v}" for c, v in zip(cats, vals)))
                problems += [f"slide {i}: chart value {v} is not an accuracy in the score files"
                             for v in vals if round(v, 1) not in CHART_OK]
    notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
    out.append(f"\n  Notes: {notes}")
    text = "\n".join(paras)
    slide_texts.append(text)
    low = text.lower()
    if not notes.strip():
        problems.append(f"slide {i}: no speaker notes")
    for where, t in (("slide", text), ("notes", notes)):
        if "heavy" in t.lower() or any(p in t for p in HEAVY):
            problems.append(f"slide {i} {where}: mentions PaddleOCR Heavy or its results")
    if any(p[:-1] in text for p in INITIAL) and "chinese" not in low:
        problems.append(f"slide {i}: original rule accuracy without the missing Chinese support")
    if any(p[:-1] in text for p in DEVELOPMENT - {AOAI_PCT}) and "development" not in low:
        problems.append(f"slide {i}: development result without a development label")
    if "beyond six fields" in low and not ("potential" in low and "not yet tested" in low):
        problems.append(f"slide {i}: future capabilities not marked as potential / not yet tested")

joined = "\n".join(slide_texts)
for needed in sorted({p[:-1] for p in INITIAL | DEVELOPMENT} | DIAG_FIGS | {AOAI_PCT, AOAI_SECS}):
    if needed not in joined:  # accuracies as numbers: ranges are written "37.3–41.2%"
        problems.append(f"{needed} not found in slide text")
if not any("beyond six fields" in t.lower() for t in slide_texts):
    problems.append("no 'beyond six fields' slide")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides; no Heavy; charts match the score files; initial, development "
      "and diagnosis results present and labelled; potential slide marked; text in previews/deck_text.md")
