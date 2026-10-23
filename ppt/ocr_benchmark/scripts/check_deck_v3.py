"""Check the generated Version 3 deck against the benchmark results, and dump its text for review.

    python3 ppt/ocr_benchmark/scripts/check_deck_v3.py      (after generate_ppt_v3.py)

Checks:
- 10 slides, every slide has speaker notes;
- PaddleOCR Heavy appears nowhere (slides or notes);
- no extraction-rule accuracy percentage appears (slides or notes); because the original AOAI result
  has the same value as one rule result (88.2%), a slide paragraph with that figure must not mention rules;
- the original AOAI accuracy and time appear, and the prompt v2 accuracy appears only on slides that
  call it tuned / a development result.
Writes previews/deck_text.md (all slide text and notes). Exits non-zero on failure.
"""
import csv
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
RES = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark" / "results" / "v2"
DECK = PROJECT / "current" / "OCR_Benchmark_V3.pptx"


def summary(path):
    with open(path, newline="") as fh:
        return {r["approach"]: r for r in csv.DictReader(fh)}


SUM, SUM_V2 = summary(RES / "scores_improved" / "summary.csv"), summary(RES / "scores_aoai_improved" / "summary.csv")
pct = lambda r: f"{float(r['accuracy_pct']):.1f}%"  # noqa: E731
AOAI_PCT, AOAI_V2_PCT = pct(SUM["azure_di_aoai"]), pct(SUM_V2["aoai_v2_rows"])
AOAI_SECS = f"{int(SUM['azure_di_aoai']['mean_ms_per_receipt']) / 1000:.1f} s"
RULE_PCTS = {pct(r) for a, r in SUM.items() if a != "azure_di_aoai"}  # rules, incl. historical Heavy rows

prs = Presentation(DECK)
problems, out = [], [f"# {DECK.name}: text and notes\n"]
if len(prs.slides) != 10:
    problems.append(f"expected 10 slides, found {len(prs.slides)}")
all_slide_text = []
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
    notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
    out.append(f"\n  Notes: {notes}")
    slide_text = "\n".join(paras)
    all_slide_text.append(slide_text)
    if not notes.strip():
        problems.append(f"slide {i}: no speaker notes")
    for where, t in (("slide", slide_text), ("notes", notes)):
        if "heavy" in t.lower():
            problems.append(f"slide {i} {where}: mentions PaddleOCR Heavy")
        for p in RULE_PCTS - {AOAI_PCT}:
            if p in t:
                problems.append(f"slide {i} {where}: shows rule accuracy {p}")
    for p in paras:
        if AOAI_PCT in p and "rule" in p.lower():
            problems.append(f"slide {i}: {AOAI_PCT} next to rules in {p!r}")
    if AOAI_V2_PCT in slide_text and not any(w in slide_text.lower() for w in ("tuned", "development")):
        problems.append(f"slide {i}: {AOAI_V2_PCT} without a tuned / development label")

joined = "\n".join(all_slide_text)
for needed in (AOAI_PCT, AOAI_V2_PCT, AOAI_SECS):
    if needed not in joined:
        problems.append(f"{needed} not found in slide text")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides; no Heavy, no rule accuracy; AOAI {AOAI_PCT} and labelled "
      f"{AOAI_V2_PCT} present; text in previews/deck_text.md")
