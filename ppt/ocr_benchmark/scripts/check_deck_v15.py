"""Check the generated Version 15 deck against deck_direction.md and the benchmark results; dump its text for review.

    python3 ppt/ocr_benchmark/scripts/check_deck_v15.py      (after generate_ppt_v15.py)

Checks (deck slide numbers: 1 = cover, 2-11 = main slides 1-10, 12-13 = appendix A1-A2):
- 13 slides, every slide has speaker notes;
- status tags: current scope (main 1), future possibility (main 2 and 8), tested on the development set (main 5
  and 6), open requirement (main 9);
- the benchmark statistics appear once: the chart on main slide 5 holds exactly the three overall figures, and no
  other main slide shows a percentage or an 'n of 51' / 'n/51' count; appendix A1 shows every per-field figure,
  recomputed here from the saved detail.csv files;
- main slide 5 carries the dataset wording ("a small development set of 9 receipts, mainly fictional mock
  receipts"), 'directional', 'production accuracy' and the independent validation set;
- main slide 3 shows ~25 only as an illustrative example;
- main slide 4 marks structured export as part of the extraction scope and audit testing / review as the future
  stage;
- main slide 6 has exactly three receipt examples whose values match the saved results, and the AI-is-not-perfect
  line; any HK$ amount in the deck is one of the receipt 5 values;
- main slide 7 has the brief, fair OCR + regex + doctor database alternative marked 'not benchmarked', and no full
  doctor-database slide exists;
- main slide 8: 'not being built now' and 'not an audit finding';
- main slide 9: PII is an open design decision (no masking method presented as chosen or implemented);
- main slide 10: the recommendation subject to independent validation and governance approval, six next steps;
- 'avoid' statements from deck_direction.md are absent (AI replaces auditors, complete coverage, production
  readiness, AI eliminates maintenance, OCR unnecessary, data always correct, every red flag is a finding, the
  application already performs the tests); no old or tuned figures (88.2, 37.3, 41.2, 86.3), no PaddleOCR Heavy,
  no technical jargon (prompt v2, Python, JSON, tokens, multilingual) on the slides; no cost or savings figures.
Writes previews/deck_text.md (all slide text, chart data and notes). Exits non-zero on failure.
"""
import csv
import re
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
RES = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark" / "results" / "v2"
DECK = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "current" / "OCR_Benchmark_V15.pptx"
FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]
NAMES = ("PaddleOCR + rules", "Azure DI + rules", "Azure DI + Azure OpenAI")
RUNS = ((RES / "scores_multilingual" / "detail.csv", "paddle_light_multilingual"),
        (RES / "scores_multilingual" / "detail.csv", "azure_di_multilingual"),
        (RES / "scores_aoai_improved" / "detail.csv", "aoai_v2_rows"))
DATASET = "a small development set of 9 receipts, mainly fictional mock receipts"


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
FORBIDDEN_FIGURES = {"88.2", "37.3", "41.2", "86.3"}

# deck_direction.md, section 5 "Avoid this" (checked on slides and notes).
AVOID = [r"(?i)\breplac\w* (the )?auditors?\b", r"(?i)complete (audit )?coverage", r"(?i)full audit coverage",
         r"(?i)production[- ]ready", r"(?i)ready for production", r"(?i)proves? production",
         r"(?i)eliminat\w* (the need for )?maintenance", r"(?i)no maintenance", r"(?i)OCR is unnecessary",
         r"(?i)always correct", r"(?i)every red flag is", r"(?i)red flags? (is|are) (an )?audit findings?",
         r"(?i)already performs", r"(?i)fraud decision", r"(?i)\bguarantee[sd]?\b"]
JARGON = re.compile(r"(?i)prompt v2|\bv2\b|python|\bjson\b|\btokens?\b|multilingual|retrospective|heavy|"
                    r"paddleocr light|original prompt")
MONEY = re.compile(r"HK\$\d[\d,]*\d|US\$|\$\s?\d|\bcost per\b|\bhours? saved\b|\bFTE\b")

prs = Presentation(DECK)
problems, out = [], [f"# {DECK.name}: text, chart data and notes\n"]
if len(prs.slides) != 13:
    problems.append(f"expected 13 slides (cover + 10 + 2 appendix), found {len(prs.slides)}")
T, N, CHARTS = {}, {}, {}
for i, s in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}" + (" (cover)" if i == 1 else f" (main slide {i - 1})" if i <= 11 else
                                    f" (appendix A{i - 11})") + "\n")
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
                     for m in MONEY.finditer(t) if m.group(0) not in ("HK$1,750", "HK$1,575")]
        if i != 7 and "HK$" in t:
            problems.append(f"slide {i} {where}: receipt amount outside the examples slide")
    if CHARTS[i] and i != 6:
        problems.append(f"slide {i}: unexpected chart")
    # benchmark statistics once: no percentages or field counts on other main slides
    if 2 <= i <= 11 and i != 6:
        stats = re.findall(r"\d+(?:\.\d+)?%", text.replace("10% member discount", "")) + \
                re.findall(r"\b\d+ ?(?:of|/) ?51\b", text)
        if stats:
            problems.append(f"slide {i}: shows benchmark statistics outside main slide 5: {stats}")


def need(i, *phrases):
    T.setdefault(i, ""); N.setdefault(i, ""); CHARTS.setdefault(i, [])
    for p in phrases:
        if p not in T[i]:
            problems.append(f"slide {i}: missing {p!r}")


TAG = {2: "CURRENT PROJECT SCOPE", 3: "FUTURE POSSIBILITY", 6: "TESTED · DEVELOPMENT SET",
       7: "TESTED · DEVELOPMENT SET", 9: "FUTURE POSSIBILITY", 10: "OPEN REQUIREMENT", 12: "APPENDIX", 13: "APPENDIX"}
for i, tag in TAG.items():
    need(i, tag)
need(2, "Azure Document Intelligence", "Azure OpenAI", "exported", "later stage")
need(4, "~25", "Illustrative example only, not a confirmed audit sample size.")
if re.search(r"~25|\b25\b", "\n".join(T[k] + N[k] for k in T if k != 4)):
    problems.append("~25 appears outside main slide 3")
need(5, "Proposed extraction scope", "Structured dataset", "Future stage (not being built now)", "Audit testing",
     "Auditor review")
if sorted(CHARTS[6]) != OVERALL:
    problems.append(f"slide 6: chart values {CHARTS[6]} differ from {OVERALL}")
need(6, DATASET, "Directional only", "production accuracy", "independent, representative validation set", *NAMES)
need(7, "Who treated the patient?", "Which date is the treatment?", "What was actually charged?",
     "CHEUNG Hoi Ying", "Dr. Kwok Man Hin", "16 Jul 2026", "17 Jul 2026", "HK$1,575", "HK$1,750",
     "still need validation")
if T[7].count("Correct value") != 3:
    problems.append("slide 7: expected exactly three receipt examples")
need(8, "OCR + regex + doctor database", "not benchmarked", "registered doctor names", "manual review",
     "prices to be confirmed")
if sum("doctor database" in T[i] for i in T if i not in (8, 13)):
    problems.append("the doctor database appears outside main slide 7 and appendix A2")
need(9, "These tests are not being built now", "not an audit finding", "not yet extracted or tested")
need(10, "design to be agreed", "decisions still to make", "not yet chosen", "approved method to be agreed")
if re.search(r"(?i)\b(is|are) (masked|redacted)\b|masking (is|has been) (in place|implemented|applied)", T[10] + N[10]):
    problems.append("slide 10: presents PII masking as implemented")
need(11, "subject to independent", "validation and governance approval", "Next steps")
if len(re.findall(r"(?m)^[1-6]$", T[11])) != 6:
    problems.append("slide 11: expected six numbered next steps")
problems += [f"slide 12: missing {n} {f} {v}% {COUNTS[(n, f)]}" for (n, f), v in SHOWN.items()
             if f"{v}%" not in T[12] or COUNTS[(n, f)] not in T[12]]
need(13, DATASET[0].upper() + DATASET[1:], "Not yet tested")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides with notes; status tags; chart = {', '.join(OVERALL)} on main "
      f"slide 5 only; all {len(SHOWN)} per-field and overall figures in appendix A1; three receipt examples match the "
      "results; doctor database brief and not benchmarked; PII open; no avoid-list wording, old figures, jargon or "
      "cost figures; text in previews/deck_text.md")
