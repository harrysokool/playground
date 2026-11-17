"""Check the generated Version 14 deck against the benchmark results, and dump its text for review.

    python3 ppt/ocr_benchmark/scripts/check_deck_v14.py      (after generate_ppt_v14.py)

Checks:
- 9 slides, every slide has speaker notes;
- the three method names (PaddleOCR + Rules, Azure DI + Rules, Azure DI + AOAI) appear, and no other
  method labels or technical terms appear on the slides (prompt v2, Python, multilingual, retrospective,
  PaddleOCR Light, tokens, schema, ...);
- slide 2 (summary) shows no accuracy figures; slide 3 has the chart with exactly the three overall figures;
- slide 4 shows every per-field figure, recomputed here from the saved detail.csv files;
- the limitation footnote ("not yet independently validated") is on slides 4 and 9 (removed from slide 3 in the PowerPoint edit of V13);
- slide 7 (doctor database proposal) has the three steps (OCR, regex search against ~40,000 registered doctor
  names, return matches and flag none or several for manual review), the four advantages, the main limitation
  (other fields need additional rules or AI), the benchmark comparison, 'not benchmarked' and the key
  takeaway verbatim; it does not present multiple doctor names as a limitation;
- the final slide (business value) keeps Azure DI + AOAI as the recommended approach, shows the flow (receipt ->
  extraction -> structured results -> authorized platform -> data analytics), lists potential audit tests, and
  states: only approved receipt data on Azure; claims, policy and historical data stay in another authorized
  system; the transfer method must be approved; not implemented or benchmarked; supporting evidence, not a
  final fraud or claim validity decision; it does not repeat the doctor database;
- slides 2 and 9 keep the Azure boundary (audit checks in another authorized system);
- no PaddleOCR Heavy, no original AOAI 88.2%, no English-only rule figures (37.3% / 41.2%), no tuned rule figures
  (86.3% overall, and tuned per-field figures that the three methods do not share), on slides or in notes.
Writes previews/deck_text.md (all slide text, chart data and notes). Exits non-zero on failure.
"""
import csv
import re
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
RES = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark" / "results" / "v2"
DECK = PROJECT / "current" / "OCR_Benchmark_V14.pptx"
FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]
NAMES = ("PaddleOCR + Rules", "Azure DI + Rules", "Azure DI + AOAI")
RUNS = ((RES / "scores_multilingual" / "detail.csv", "paddle_light_multilingual"),
        (RES / "scores_multilingual" / "detail.csv", "azure_di_multilingual"),
        (RES / "scores_aoai_improved" / "detail.csv", "aoai_v2_rows"))


def rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def summary(path):
    return {r["approach"]: r for r in rows(path)}


num = lambda v: f"{float(v):.1f}"  # noqa: E731
SHOWN = {}  # per-field and overall figures for the three methods
for name, (path, approach) in zip(NAMES, RUNS):
    sel = [r for r in rows(path) if r["approach"] == approach and r["result"] in ("Correct", "Wrong")]
    for f in FIELDS + [None]:
        part = [r for r in sel if f is None or r["field"] == f]
        SHOWN[(name, f)] = num(100 * sum(r["result"] == "Correct" for r in part) / len(part))
OVERALL = {SHOWN[(n, None)] for n in NAMES}
SUM, SUM_V2 = summary(RES / "scores_improved" / "summary.csv"), summary(RES / "scores_aoai_improved" / "summary.csv")
OLD = {num(SUM[a]["accuracy_pct"]) for a in ("paddle_light_general", "azure_di_general", "azure_di_aoai")}
TUNED = {num(SUM[a]["accuracy_pct"]) for a in ("paddle_light_improved", "azure_di_improved")} | \
        {num(SUM_V2[a][f + "_accuracy_pct"]) for a in ("paddle_light_improved", "azure_di_improved") for f in FIELDS}
FORBIDDEN = (OLD | TUNED) - set(SHOWN.values())  # e.g. 37.3, 41.2, 88.2, 86.3
HEAVY = {num(r["accuracy_pct"]) for a, r in SUM.items() if "heavy" in a} - set(SHOWN.values())
TERMS = re.compile(r"(?i)prompt v2|\bv2\b|python|multilingual|retrospective|development result|paddleocr light|"
                   r"\btokens?\b|schema|heavy|original prompt|json")
FOOT = "not yet independently validated"
TAKEAWAY = ("OCR with regex and a doctor database is a practical approach for identifying registered doctor names and "
            "flagging exceptions. However, extracting other receipt information accurately still requires additional "
            "rules or AI.")

prs = Presentation(DECK)
problems, out = [], [f"# {DECK.name}: text, chart data and notes\n"]
if len(prs.slides) != 9:
    problems.append(f"expected 9 slides, found {len(prs.slides)}")
texts = []
for i, s in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}\n")
    paras, charts = [], []
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
                vals = [num(v) for v in ser.values]
                charts += vals
                out.append(f"  chart '{ser.name}': " + ", ".join(f"{c}={v}" for c, v in zip(cats, vals)))
    notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
    out.append(f"\n  Notes: {notes}")
    text = "\n".join(paras)
    texts.append(text)
    if not notes.strip():
        problems.append(f"slide {i}: no speaker notes")
    problems += [f"slide {i}: technical term {m.group(0)!r}" for m in TERMS.finditer(text)]
    for where, t in (("slide", text), ("notes", notes)):
        problems += [f"slide {i} {where}: forbidden figure {v}" for v in sorted(FORBIDDEN) if v in t]
        if "heavy" in t.lower() or any(v in t for v in HEAVY):
            problems.append(f"slide {i} {where}: mentions PaddleOCR Heavy or its results")
    if i == 2:
        problems += [f"slide 2: shows accuracy figure {v}" for v in sorted(set(SHOWN.values())) if v in text]
        if re.search(r"\d+(?:\.\d+)?%", text):
            problems.append("slide 2: shows a percentage")
    if i == 3 and sorted(charts) != sorted(OVERALL):
        problems.append(f"slide 3: chart values {charts} differ from {sorted(OVERALL)}")
    if i != 3 and charts:
        problems.append(f"slide {i}: unexpected chart")
    if i == 4:
        problems += [f"slide 4: missing {n} {f} {v}%" for (n, f), v in SHOWN.items() if f"{v}%" not in text]
    if i in (4, 9) and FOOT not in text:
        problems.append(f"slide {i}: missing the limitation footnote")
    if i in (2, 9) and "another authorized system" not in text:
        problems.append(f"slide {i}: missing the Azure boundary (another authorized system)")
    if i == 9:
        for need in ("recommended approach", "Azure DI + AOAI", "Medical receipt", "Structured results",
                     "Authorized platform", "Data analytics", "Approved transfer method", "Duplicates", "Amounts",
                     "processes only approved receipt data", "historical data stay in another authorized system",
                     "transfer method must be approved", "not implemented or benchmarked",
                     "supporting evidence, not a final fraud or claim validity decision",
                     "not only manually entered data"):
            if need not in text:
                problems.append(f"slide 9: missing {need!r}")
    if i == 9 and "doctor" in text.lower():
        problems.append("slide 9: still repeats the doctor database")
    if i == 7:
        for need in ("OCR reads the receipt", "Regex search", "40,000 registered doctor names", "manual review",
                     "Simple and practical to implement", "No AI needed for doctor name matching",
                     "Low additional cost", "Uncertain results flagged for manual review", "Main limitation",
                     "need additional extraction rules or AI",
                     "less accurate than Azure DI + AOAI on all six fields", "not benchmarked", TAKEAWAY):
            if need not in text:
                problems.append(f"slide 7: missing {need!r}")
        if re.search(r"(?i)several practitioners|multiple practitioners|limitations:", text):
            problems.append("slide 7: presents multiple doctor names as a limitation")

joined = "\n".join(texts)
problems += [f"method name {n!r} not found" for n in NAMES if n not in joined]

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides with notes; three method names; no figures on slide 2; chart = "
      f"{', '.join(sorted(OVERALL))}; all {len(SHOWN) - 3} per-field figures on slide 4; footnote on slides 4, 9; doctor database slide complete; business value slide with its guard rails; "
      f"no forbidden figures ({', '.join(sorted(FORBIDDEN))}), no Heavy, no technical terms; text in "
      "previews/deck_text.md")
