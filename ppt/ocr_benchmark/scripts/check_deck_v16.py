"""Check the generated Version 16 deck against the benchmark results and the V16 brief; dump its text for review.

    python3 ppt/ocr_benchmark/scripts/check_deck_v16.py [deck.pptx]     (after generate_ppt_v16.py)

Deck slide numbers: 1 = cover, 2-9 = main slides 1-8, 10-11 = appendix A1-A2. Checks:
- 11 slides, every slide has speaker notes; the status tags;
- main 1: ~25 receipts and 5-10 minutes per receipt, labelled as estimates (not measured); the checklist areas;
- main 2: the workflow, the extracted output for receipt 8 matching the saved result, the three benefits, and the
  500 to 1,000 receipt target marked as not yet demonstrated;
- main 3: the chart holds exactly the three overall figures, labelled development results from nine receipts,
  not production accuracy; no other main slide shows a benchmark percentage or 'n of 51' count;
- main 4: the three receipt examples and the "AI can also make mistakes" point;
- main 5: the OCR + regex + doctor database alternative, marked not benchmarked;
- main 6: the four analytics examples, on another authorized platform, not implemented;
- main 7: approved receipt data only on Azure; claims/policy/historical records internal; PII, storage, access
  and transfer still to be agreed; masking never presented as implemented or approved;
- main 8: what we demonstrated, why it matters, three priorities;
- appendix A1: every per-field figure, recomputed from detail.csv;
- the 500 to 1,000 target only next to 'not yet demonstrated' / 'future' wording; no avoid-list wording (AI
  replaces auditors, production ready, savings achieved, masking implemented, a request to approve a production
  system ...), no old or tuned figures, no technical jargon on slides, no cost or savings figures; HK$ amounts only
  the saved receipt values on main slides 2 and 4.
Writes previews/deck_text.md (all slide text, chart data and notes). Exits non-zero on failure.
"""
import csv
import json
import re
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
RES = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark" / "results" / "v2"
DECK = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "current" / "OCR_Benchmark_V16.pptx"
FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]
NAMES = ("PaddleOCR + rules", "Azure DI + rules", "Azure DI + Azure OpenAI")
RUNS = ((RES / "scores_multilingual" / "detail.csv", "paddle_light_multilingual"),
        (RES / "scores_multilingual" / "detail.csv", "azure_di_multilingual"),
        (RES / "scores_aoai_improved" / "detail.csv", "aoai_v2_rows"))


def rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


num = lambda v: f"{float(v):.1f}"  # noqa: E731
SHOWN, COUNTS = {}, {}
for name, (path, approach) in zip(NAMES, RUNS):
    sel = [r for r in rows(path) if r["approach"] == approach and r["result"] in ("Correct", "Wrong")]
    for f in FIELDS + [None]:
        part = [r for r in sel if f is None or r["field"] == f]
        c = sum(r["result"] == "Correct" for r in part)
        SHOWN[(name, f)] = num(100 * c / len(part))
        COUNTS[(name, f)] = f"({c}/{len(part)})"
OVERALL = sorted(SHOWN[(n, None)] for n in NAMES)
DEMO = json.loads((RES / "di_aoai_v2_rows" / "receipt8.json").read_text())
DEMO_VALUES = [DEMO["doctor_name"], DEMO["registration_number"], DEMO["patient_name"], DEMO["receipt_number"],
               "3 Sep 2026", f"HK${DEMO['total_amount']:,.0f}"]
assert DEMO["service_date"] == "2026-09-03"
ALLOWED_HKD = {2 + 1: {DEMO_VALUES[-1]}, 4 + 1: {"HK$1,750", "HK$1,575"}}  # deck slide -> amounts
FORBIDDEN_FIGURES = {"88.2", "37.3", "41.2", "86.3"}
AVOID = [r"(?i)\breplac\w* (the )?auditors?\b", r"(?i)complete (audit )?coverage", r"(?i)production[- ]ready",
         r"(?i)ready for production", r"(?i)proves? production", r"(?i)eliminat\w* (the need for )?maintenance",
         r"(?i)always correct", r"(?i)every red flag is", r"(?i)already (performs|runs|processes)",
         r"(?i)\bguarantee[sd]?\b", r"(?i)\bwill save\b", r"(?i)\bsaves? \d", r"(?i)\bsaved \d",
         r"(?i)approv\w* (of |for |a )*(the )?production", r"(?i)request\w* approval",
         r"(?i)masking (is|has been) (in place|implemented|applied|approved)", r"(?i)\b(is|are) (masked|redacted)\b",
         r"(?i)we (have )?processed (500|1,000)"]
JARGON = re.compile(r"(?i)prompt v2|\bv2\b|python|\bjson\b|\btokens?\b|multilingual|retrospective|heavy|"
                    r"paddleocr light|original prompt|schema")
MONEY = re.compile(r"HK\$\d[\d,]*\d|US\$|\$\s?\d|\bcost per\b|\bhours? saved\b|\bFTE\b")

prs = Presentation(DECK)
problems, out = [], [f"# {DECK.name}: text, chart data and notes\n"]
if len(prs.slides) != 11:
    problems.append(f"expected 11 slides (cover + 8 + 2 appendix), found {len(prs.slides)}")
T, N, CHARTS = {}, {}, {}
for i, s in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}" + (" (cover)" if i == 1 else f" (main slide {i - 1})" if i <= 9 else
                                    f" (appendix A{i - 9})") + "\n")
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
    T[i], N[i], CHARTS[i] = "\n".join(paras), notes, charts
    if not notes.strip():
        problems.append(f"slide {i}: no speaker notes")

for i in T:
    text, notes = T[i], N[i]
    problems += [f"slide {i}: technical term {m.group(0)!r}" for m in JARGON.finditer(text)]
    for where, t in (("slide", text), ("notes", notes)):
        problems += [f"slide {i} {where}: avoid-list wording {m.group(0)!r}" for p in AVOID for m in re.finditer(p, t)]
        problems += [f"slide {i} {where}: old or tuned figure {v}" for v in sorted(FORBIDDEN_FIGURES) if v in t]
        problems += [f"slide {i} {where}: unexpected money or savings figure {m.group(0)!r}"
                     for m in MONEY.finditer(t) if m.group(0) not in ALLOWED_HKD.get(i, set())]
        for m in re.finditer(r"500 to 1,000", t):  # the target is always marked as not yet demonstrated
            if not re.search(r"(?i)not (yet )?(been )?demonstrated|future|target|working toward", t):
                problems.append(f"slide {i} {where}: 500 to 1,000 receipts without the future/target wording")
    if CHARTS[i] and i != 4:
        problems.append(f"slide {i}: unexpected chart")
    if 2 <= i <= 9 and i != 4:
        stats = re.findall(r"\d+(?:\.\d+)?%", text.replace("10% member discount", "")) + \
                re.findall(r"\b\d+ ?(?:of|/) ?51\b", text)
        if stats:
            problems.append(f"slide {i}: shows benchmark statistics outside main slide 3: {stats}")


def need(i, *phrases):
    T.setdefault(i, ""); N.setdefault(i, ""); CHARTS.setdefault(i, [])
    for p in phrases:
        if p not in T[i]:
            problems.append(f"slide {i}: missing {p!r}")


for i, tag in {2: "ESTIMATES · NOT MEASURED", 3: "WORKING DEMONSTRATION", 4: "DEVELOPMENT RESULTS",
               5: "DEVELOPMENT RESULTS", 7: "FUTURE · NOT IMPLEMENTED", 8: "TO BE AGREED", 10: "APPENDIX",
               11: "APPENDIX"}.items():
    need(i, tag)
need(2, "~25", "receipts per sample", "5–10 min", "per receipt", "estimates, not measured", "auditor checklist",
     "Authenticity", "Data integrity", "Coverage", "Fraud indicators", "auditor time and effort")
if re.search(r"~25|\b25\b", "\n".join(T[k] for k in T if k != 2)):
    problems.append("~25 appears outside main slide 1")
need(3, "Receipt photo", "Azure DI reads the text", "Azure OpenAI selects the fields", "Structured data",
     "Less manual work", "Wider coverage", "Reusable data", "500 to 1,000 receipts", "Not yet demonstrated",
     *DEMO_VALUES)
if sorted(CHARTS[4]) != OVERALL:
    problems.append(f"slide 4: chart values {CHARTS[4]} differ from {OVERALL}")
need(4, "Development results, not production accuracy", "9 development receipts", *NAMES)
need(5, "Who treated the patient?", "Which date is the treatment?", "What was actually charged?",
     "CHEUNG Hoi Ying", "Dr. Kwok Man Hin", "16 Jul 2026", "17 Jul 2026", "HK$1,575", "HK$1,750",
     "AI can also make mistakes")
if T[5].count("Correct value") != 3:
    problems.append("slide 5: expected exactly three receipt examples")
need(6, "OCR + regex + doctor database", "not benchmarked", "registered doctor names", "manual review", *NAMES)
if sum("doctor database" in T[i] for i in T if i not in (6, 11)):
    problems.append("the doctor database appears outside main slide 5 and appendix A2")
need(7, "Receipt amount vs claim", "Treatment dates", "Duplicate receipts", "Unusual provider fees",
     "another authorized platform", "Not implemented yet", "auditor review")
need(8, "approved receipt data only", "Claims, policy and historical records", "Still to be agreed",
     "PII protection", "not yet chosen or approved", "Storage", "Access controls", "Approved transfer")
need(9, "What we demonstrated", "Why it matters", "Expand receipt extraction", "Validate independently",
     "Confirm privacy and platform design")
problems += [f"slide 10: missing {n} {f} {v}% {COUNTS[(n, f)]}" for (n, f), v in SHOWN.items()
             if f"{v}%" not in T[10] or COUNTS[(n, f)] not in T[10]]
need(11, "9 development receipts, mainly fictional mock receipts", "Future goals, not yet tested",
     "Automated audit checks and time savings")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides with notes; status tags; estimates labelled; receipt 8 output "
      f"matches the saved result; chart = {', '.join(OVERALL)} on main slide 3 only; all {len(SHOWN)} per-field and "
      "overall figures in appendix A1; three receipt examples; doctor database brief and not benchmarked; analytics "
      "not implemented; privacy items to be agreed; 500 to 1,000 only as a future target; no avoid-list wording, "
      "old figures, jargon or cost figures; text in previews/deck_text.md")
