"""Check the generated Version 10 deck against the benchmark results, and dump its text for review.

    python3 ppt/ocr_benchmark/scripts/check_deck_v10.py      (after generate_ppt_v10.py)

Checks:
- 11 slides, every slide has speaker notes;
- Azure data boundary: the executive summary, scope and recommendation slides say only approved receipt data is
  on Azure; the scope slide says what is never uploaded and that the transfer is not yet designed;
- the scope slide separates existing from planned validation; "not a production approval" (or "not production")
  appears on the executive summary and the recommendation;
- no paragraph claims that extraction decides authenticity, medical necessity or coverage (only negated forms);
- no absolute claim that every new layout or label needs new rules (slides or notes); claims that AOAI handles
  unfamiliar layouts are qualified ("often", "not guaranteed", "not yet tested");
- the doctor database slide says it is not benchmarked, keeps hypothetical cases separate, and states that
  matching depends on the OCR reading the name and the registry containing it;
- no slide shows the original AOAI 88.2% or the English-only rule figures (37.3% / 41.2%);
- PaddleOCR Heavy and its figures appear nowhere;
- no tuned rule accuracy anywhere (slides, tables, charts, notes): not the overall 86.3%, not the tuned
  rules' per-field figures that no AOAI run shares (e.g. 77.8%), and 88.2% never in a paragraph that
  talks about tuned / improved / adapted rules (88.2% is also the original AOAI result);
- chart values are only the initial results (37.3%, 41.2%, 88.2%) and the retrospective multilingual
  baseline (51.0%, 70.6%); a slide showing a multilingual figure also says "retrospective";
- the initial results and the prompt v2 result appear; a slide with an original rule figure mentions the
  missing Chinese support; a slide with 96.1% says "development";
- the receipt-fields slide separates benchmarked from not-yet-tested fields and marks analytics as potential.
Writes previews/deck_text.md (all slide text, chart data and notes). Exits non-zero on failure.
"""
import csv
import re
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
RES = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark" / "results" / "v2"
DECK = PROJECT / "current" / "OCR_Benchmark_V10.pptx"
FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]


def summary(path):
    with open(path, newline="") as fh:
        return {r["approach"]: r for r in csv.DictReader(fh)}


SUM, SUM_V2 = summary(RES / "scores_improved" / "summary.csv"), summary(RES / "scores_aoai_improved" / "summary.csv")
num = lambda v: f"{float(v):.1f}"  # noqa: E731
AOAI, AOAI_V2 = num(SUM["azure_di_aoai"]["accuracy_pct"]), num(SUM_V2["aoai_v2_rows"]["accuracy_pct"])
INITIAL = {num(SUM[a]["accuracy_pct"]) for a in ("paddle_light_general", "azure_di_general")}
TUNED_RULES = {num(SUM[a]["accuracy_pct"]) for a in ("paddle_light_improved", "azure_di_improved")}
AOAI_FIELD = {num(SUM_V2[a][f + "_accuracy_pct"]) for a in ("aoai_original", "aoai_v2_rows") for f in FIELDS}
TUNED_FIELD = {num(SUM_V2[a][f + "_accuracy_pct"]) for a in ("paddle_light_improved", "azure_di_improved")
               for f in FIELDS}
FORBIDDEN = (TUNED_RULES | TUNED_FIELD) - AOAI_FIELD - INITIAL - {AOAI, AOAI_V2}  # e.g. 86.3, 77.8
HEAVY = {num(r["accuracy_pct"]) for a, r in SUM.items() if "heavy" in a} - INITIAL - {AOAI, AOAI_V2}
SUM_ML = summary(RES / "scores_multilingual" / "summary.csv")
MULTI = {num(SUM_ML[a]["accuracy_pct"]) for a in ("paddle_light_multilingual", "azure_di_multilingual")}
FORBIDDEN -= MULTI
CHART_OK = {round(float(v), 1) for v in MULTI | {AOAI_V2}}
ABSOLUTE = re.compile(r"(?i)\bevery new\b|\beach new (?:label|layout)|need code and a full retest|"
                      r"written and maintained for every")
VERDICT = re.compile(r"(?i)\b(?:determin|decid|verif|confirm|prov|judg)\w*\b[^.]*\b(?:authentic|genuine|necess|cover)")
NEGATION = re.compile(r"(?i)\bnot\b|cannot|n't|\bno\b|remain auditor")
AOAI_LAYOUT = re.compile(r"(?i)aoai[^.]*(?:unfamiliar|unseen|new) layouts?[^.]*")
TUNING_WORDS = re.compile(r"tuned|improved|adapted|after tuning", re.I)

prs = Presentation(DECK)
problems, out = [], [f"# {DECK.name}: text, chart data and notes\n"]
if len(prs.slides) != 11:
    problems.append(f"expected 11 slides, found {len(prs.slides)}")
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
                problems += [f"slide {i}: chart value {v} is not an initial or baseline result" for v in vals
                             if round(v, 1) not in CHART_OK]
    notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
    out.append(f"\n  Notes: {notes}")
    text = "\n".join(paras)
    slide_texts.append(text)
    low = text.lower()
    if not notes.strip():
        problems.append(f"slide {i}: no speaker notes")
    for where, t, units in (("slide", text, paras), ("notes", notes, re.split(r"(?<=[.;])\s+", notes))):
        if "heavy" in t.lower() or any(f"{v}%" in t for v in HEAVY):
            problems.append(f"slide {i} {where}: mentions PaddleOCR Heavy or its results")
        problems += [f"slide {i} {where}: shows tuned rule figure {v}" for v in sorted(FORBIDDEN) if v in t]
        problems += [f"slide {i} {where}: {AOAI}% next to tuned rules: {u[:90]!r}" for u in units
                     if AOAI in u and "rule" in u.lower() and TUNING_WORDS.search(u)]
    if any(v in text for v in INITIAL) and "chinese" not in low:
        problems.append(f"slide {i}: original rule figure without the missing Chinese support")
    for where, t in (("slide", text), ("notes", notes)):
        problems += [f"slide {i} {where}: absolute claim {m.group(0)!r}" for m in ABSOLUTE.finditer(t)]
    for para in paras:
        for m in AOAI_LAYOUT.finditer(para):
            if not re.search(r"(?i)often|may|not guaranteed|not yet|not been tested|expected|could", m.group(0)):
                problems.append(f"slide {i}: unqualified AOAI layout claim {m.group(0)!r}")
    if "doctor database" in low:
        for need in ("not benchmarked", "hypothetical", "only works if", "registry contains"):
            if need not in low:
                problems.append(f"slide {i}: doctor database slide lacks {need!r}")
    for v in sorted(INITIAL | {AOAI}):
        if v in text:
            problems.append(f"slide {i}: shows {v}% (original AOAI prompt or English-only rules)")
    if any(v in text for v in MULTI) and "retrospective" not in low:
        problems.append(f"slide {i}: multilingual baseline figure without a retrospective label")
    if AOAI_V2 in text and "development" not in low:
        problems.append(f"slide {i}: {AOAI_V2}% without a development label")
    for para in paras:
        if VERDICT.search(para) and not NEGATION.search(para):
            problems.append(f"slide {i}: possible claim that extraction decides authenticity/necessity/coverage: "
                            f"{para[:90]!r}")
    title = paras[0].lower() if paras else ""
    if title in ("executive summary", "scope and data boundary", "recommendation and next steps") or \
            "scope and data boundary" in low or "recommendation and next steps" in low or "executive summary" in low:
        if "approved receipt data" not in low and "receipt data only" not in low:
            problems.append(f"slide {i}: missing the 'only approved receipt data on Azure' boundary")
    if "scope and data boundary" in low:
        for need in ("never uploaded to azure", "to be designed", "planned", "existing"):
            if need not in low:
                problems.append(f"slide {i}: scope slide lacks {need!r}")
    if ("executive summary" in low or "recommendation and next steps" in low) and "not production" not in low \
            and "not a production approval" not in low:
        problems.append(f"slide {i}: missing 'not a production approval'")
    if "from audit needs to receipt fields" in low:
        for need in ("benchmarked", "not yet tested", "potential", "information, not a verdict"):
            if need not in low:
                problems.append(f"slide {i}: receipt-fields slide lacks {need!r}")

joined = "\n".join(slide_texts)
for needed in sorted(MULTI | {AOAI_V2}):
    if needed not in joined:
        problems.append(f"{needed} not found in slide text")
for must in ("executive summary", "scope and data boundary", "from audit needs to receipt fields",
             "recommendation and next steps", "doctor database"):
    if not any(must in t.lower() for t in slide_texts):
        problems.append(f"no slide containing {must!r}")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides; no Heavy; no tuned rule figures ({', '.join(sorted(FORBIDDEN))} "
      f"or {AOAI}% for rules); no 88.2% or English-only figures; charts show multilingual rules and prompt v2 only; multilingual and {AOAI_V2}% figures labelled; Azure boundary, scope and no-verdict wording present; text in "
      "previews/deck_text.md")
