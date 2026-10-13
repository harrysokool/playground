"""Check the generated Version 2 deck against the benchmark results, and dump its text for review.

    python3 ppt/ocr_benchmark/scripts/check_deck_v2.py      (run on Azure ML after generate_ppt_v2.py)

Checks: 9 slides; any chart value equals summary.csv; every accuracy figure (all seven approaches,
as "37.3%") and every time figure appear in the slide text; every slide has speaker notes. Writes previews/deck_text.md (all slide text, chart
data and notes) so the content can be reviewed without opening PowerPoint. Exits non-zero on failure.
"""
import csv
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
BENCH = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark"
DECK = PROJECT / "current" / "OCR_Benchmark_V2.pptx"

with open(BENCH / "results" / "v2" / "scores_improved" / "summary.csv", newline="") as fh:
    SUM = {r["approach"]: r for r in csv.DictReader(fh)}
expected_acc = {round(float(r["accuracy_pct"]) / 100, 4) for r in SUM.values()}
expected_secs = {round(int(r["mean_ms_per_receipt"]) / 1000, 1) for r in SUM.values()}

prs = Presentation(DECK)
problems, out = [], [f"# {DECK.name}: text, chart data and notes\n"]
if len(prs.slides) != 9:
    problems.append(f"expected 9 slides, found {len(prs.slides)}")
all_text = []
for i, s in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}\n")
    for sh in s.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            out.append("- " + sh.text_frame.text.replace("\n", " / "))
            all_text.append(sh.text_frame.text)
        if sh.has_table:
            for row in sh.table.rows:
                cells = [c.text.replace("\n", " ") for c in row.cells]
                out.append("  | " + " | ".join(cells) + " |")
                all_text.extend(cells)
        if sh.has_chart:
            plot = sh.chart.plots[0]
            cats = [c.replace("\n", " ") for c in plot.categories]
            for ser in plot.series:
                vals = list(ser.values)
                out.append(f"  chart '{ser.name}': " + ", ".join(f"{c}={v}" for c, v in zip(cats, vals)))
                for v in vals:
                    if v is None:
                        continue
                    if v <= 1 and round(v, 4) not in expected_acc:
                        problems.append(f"slide {i}: chart value {v} is not an accuracy in summary.csv")
                    if v > 1 and round(v, 1) not in expected_secs:
                        problems.append(f"slide {i}: chart value {v} is not a time in summary.csv")
    notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
    if not notes.strip():
        problems.append(f"slide {i}: no speaker notes")
    out.append(f"\n  Notes: {notes}")

joined = "\n".join(all_text)
for a in ("paddle_light_general", "paddle_heavy_general", "azure_di_general", "paddle_light_improved",
          "paddle_heavy_improved", "azure_di_improved", "azure_di_aoai"):
    pct = f"{float(SUM[a]['accuracy_pct']):.1f}%"
    if pct not in joined:
        problems.append(f"{a} accuracy {pct} not found in slide text")
for a in ("paddle_light_improved", "paddle_heavy_improved", "azure_di_improved", "azure_di_aoai"):
    t = f"{int(SUM[a]['mean_ms_per_receipt']) / 1000:.1f} s"
    if t not in joined:
        problems.append(f"{a} time {t} not found in slide text")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides; all accuracy and time figures match summary.csv; "
      "text in previews/deck_text.md")
