"""Check the Version 18 deck against the benchmark results, the V18 brief and the manually edited V17 deck.

    python3 ppt/ocr_benchmark/scripts/check_deck_v18.py [deck.pptx]     (after make_v18_from_v17.py)

Deck slide numbers: 1 = cover, 2-12 = main slides 1-11, 13-14 = appendix A1-A2. Checks:
- 14 slides with notes in the V18 order (architecture before privacy); the status tags;
- slides 1-8 and 13-14: text and speaker notes identical to the manually edited V17 deck; slide 9 differs only by
  the platform name;
- every Version 17 content check still holds: the receipt 8 output, the chart (only on main slide 5), every
  per-field figure in appendix A1, the receipt examples, the time estimate only in the notes, 500 to 1,000 only as
  a proposed volume to be confirmed, no avoid-list wording, old figures, jargon or cost figures;
- main 9 (architecture): one picture, its header and bottom boxes cropped and nearly full width; tagged proposed
  and not implemented; the benchmark used unmasked OCR text;
- main 10 (privacy): no repeated data flow; masking keeps patient and practitioner names; Azure DI receives the
  original images; SharePoint may hold unmasked OCR text; approved data handling controls; masking not chosen or
  approved, never presented as implemented;
- main 11 (conclusion): reviewing and approving the proposed architecture and privacy controls;
- one platform name: "Internal Data Platform", never "another authorized platform".
Writes previews/deck_text.md (all slide text, chart data and notes). Exits non-zero on failure.
"""
import csv
import json
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

PROJECT = Path(__file__).resolve().parent.parent
RES = PROJECT.parent.parent / "python" / "receipt_ocr_benchmark" / "results" / "v2"
DECK = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "current" / "OCR_Benchmark_V18.pptx"
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
ALLOWED_HKD = {4: {DEMO_VALUES[-1]}, 7: {"HK$1,750", "HK$1,575"}}  # deck slide -> amounts
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
if len(prs.slides) != 14:
    problems.append(f"expected 14 slides (cover + 11 + 2 appendix), found {len(prs.slides)}")
T, N, CHARTS, TITLES = {}, {}, {}, {}
for i, s in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}" + (" (cover)" if i == 1 else f" (main slide {i - 1})" if i <= 12 else
                                    f" (appendix A{i - 12})") + "\n")
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
    TITLES[i] = paras[0] if paras else ""
    if not notes.strip():
        problems.append(f"slide {i}: no speaker notes")

ORDER = ["AI-Assisted Medical Receipt Extraction", "Manual Receipt Review Limits Audit Coverage",
         "The Business Value We Are Working Toward", "Our Working Solution", "Why We Tested Three Approaches",
         "Benchmark Results", "Why Context Matters: Receipt Examples", "Advantages, Limitations and Alternatives",
         "Future Audit Analytics: Example Tests", "Proposed Architecture and Data Flow", "Privacy and Governance",
         "Conclusion and Next Steps",
         "Appendix A1: Accuracy by Field", "Appendix A2: How the Benchmark Was Run"]
for i, t in enumerate(ORDER, 1):
    if t not in T.get(i, ""):
        problems.append(f"slide {i}: expected the slide titled {t!r}")

for i in T:
    text, notes = T[i], N[i]
    problems += [f"slide {i}: technical term {m.group(0)!r}" for m in JARGON.finditer(text)]
    for where, t in (("slide", text), ("notes", notes)):
        problems += [f"slide {i} {where}: avoid-list wording {m.group(0)!r}" for p in AVOID for m in re.finditer(p, t)]
        problems += [f"slide {i} {where}: old or tuned figure {v}" for v in sorted(FORBIDDEN_FIGURES) if v in t]
        problems += [f"slide {i} {where}: unexpected money or savings figure {m.group(0)!r}"
                     for m in MONEY.finditer(t) if m.group(0) not in ALLOWED_HKD.get(i, set())]
        if "500 to 1,000" in t:  # a proposed validation volume, to be confirmed, on the conclusion only
            if i != 12:
                problems.append(f"slide {i} {where}: 500 to 1,000 receipts outside the conclusion")
            if not re.search(r"(?i)proposed", t) or not re.search(r"(?i)to be confirmed", t):
                problems.append(f"slide {i} {where}: 500 to 1,000 without 'proposed ... to be confirmed'")
    if re.search(r"(?i)\d+\s*(–|-|to)\s*\d+\s*min|minutes per receipt|hours of reading", text):
        problems.append(f"slide {i}: unmeasured time estimate on the slide (keep it in the notes)")
    if re.search(r"(?i)innovation idea|merely an idea|not a finished product", text + notes):
        problems.append(f"slide {i}: describes the active project as only an idea")
    if CHARTS[i] and i != 6:
        problems.append(f"slide {i}: unexpected chart")
    if 2 <= i <= 12 and i != 6:
        stats = re.findall(r"\d+(?:\.\d+)?%", text.replace("10% member discount", "")) + \
                re.findall(r"\b\d+ ?(?:of|/) ?51\b", text)
        if stats:
            problems.append(f"slide {i}: shows benchmark statistics outside main slide 5: {stats}")


def need(i, *phrases):
    T.setdefault(i, ""); N.setdefault(i, ""); CHARTS.setdefault(i, [])
    for p in phrases:
        if p not in T[i]:
            problems.append(f"slide {i}: missing {p!r}")


for i, tag in {2: "ESTIMATES · NOT MEASURED", 3: "POTENTIAL · NOT MEASURED", 4: "WORKING DEMONSTRATION",
               5: "BENCHMARK DESIGN", 6: "DEVELOPMENT RESULTS", 7: "DEVELOPMENT RESULTS",
               9: "FUTURE · NOT IMPLEMENTED", 10: "PROPOSED · NOT IMPLEMENTED", 11: "TO BE AGREED",
               13: "APPENDIX", 14: "APPENDIX"}.items():
    need(i, tag)
need(1, "progress update")
need(2, "~25", "typical audit sample", "team estimate", "not yet measured", "auditor checklist",
     "Authenticity", "Data integrity", "Coverage", "Fraud indicators", "auditor time and effort")
if not re.search(r"5 to 10 minutes", N[2]) or "not measured" not in N[2]:
    problems.append("slide 2 notes: the 5 to 10 minute estimate should be in the notes, marked not measured")
if re.search(r"~25|\b25\b", "\n".join(T[k] for k in T if k != 2)):
    problems.append("~25 appears outside main slide 1")
need(3, "Less manual effort", "Wider coverage", "Reusable structured data", "Focus on exceptions",
     "none has been measured yet")
if re.search(r"(?i)duplicate|claimed amount|provider fees|policy period", T[3]):
    problems.append("slide 3: specific audit tests belong on the analytics slide (main 8), not the value slide")
need(4, "Receipt photo", "Azure DI reads the text", "Azure OpenAI selects the fields", "Structured data",
     "Demonstrated so far", "not yet tested", *DEMO_VALUES)
if re.search(r"Less manual|Wider coverage|Reusable data", T[4]):
    problems.append("slide 4: benefit cards repeat the value slide")
need(5, "Step 1: read the text", "Step 2: pick the fields", "What the comparison shows", *NAMES)
if sorted(CHARTS[6]) != OVERALL:
    problems.append(f"slide 6: chart values {CHARTS[6]} differ from {OVERALL}")
need(6, "Development results, not production accuracy", "9 development receipts", "preferred approach", NAMES[2])
need(7, "Who treated the patient?", "Which date is the treatment?", "What was actually charged?",
     "CHEUNG Hoi Ying", "Dr. Kwok Man Hin", "16 Jul 2026", "17 Jul 2026", "HK$1,575", "HK$1,750",
     "AI can also make mistakes", "Independent validation and exception handling are required")
if T[7].count("Correct value") != 3:
    problems.append("slide 7: expected exactly three receipt examples")
need(8, "Limited-scope alternative: OCR + doctor-name matching", "not benchmarked", "doctor database",
     "not a substitute for multi-field receipt extraction", "ongoing updates", *NAMES)
if "each new receipt format" in T[8] + N[8]:
    problems.append("slide 8: overstated 'each new receipt format' rules wording")
if sum("doctor database" in T[i] for i in T if i != 8):
    problems.append("the doctor database appears on a slide other than main slide 7")
need(9, "Receipt amount vs claim", "Treatment dates", "Duplicate receipts", "Unusual provider fees",
     "Internal Data Platform", "Not implemented yet", "auditor review")
pics = [sh for sh in prs.slides[9].shapes if sh.shape_type == 13] if len(prs.slides) >= 10 else []
if len(pics) != 1:
    problems.append("slide 10: expected exactly one architecture picture")
else:
    pic = pics[0]
    if not (pic.crop_top > 0.15 and pic.crop_bottom > 0.12):
        problems.append("slide 10: the image's own header and bottom boxes are not cropped")
    if pic.width < Inches(12):
        problems.append("slide 10: the architecture picture is not shown near full width")
need(10, "not yet implemented", "only masked OCR text would reach Azure OpenAI", "unmasked OCR text",
     "not yet tested", "still need approval")
need(11, "Masking must keep required fields", "Patient and practitioner names", "Internal Data Platform",
     "Azure DI receives original images", "SharePoint may hold unmasked text", "approved data handling controls",
     "used unmasked OCR text", "re-tested", "Still to be agreed and approved", "PII masking method",
     "Not yet chosen or approved", "Storage and retention", "Access controls", "Transfer and linkage")
if re.search(r"Receipt image sent|Masked Text|stay here|→", T[11]):
    problems.append("slide 11: the repeated data flow is still on the privacy slide")
need(12, "What we have achieved", "Future opportunities", "What still needs validation",
     "Expand receipt extraction", "Validate independently", "Approve architecture and privacy",
     "review and approve the proposed architecture and privacy controls", "Support requested", "500 to 1,000")
problems += [f"slide 13: missing {n} {f} {v}% {COUNTS[(n, f)]}" for (n, f), v in SHOWN.items()
             if f"{v}%" not in T[13] or COUNTS[(n, f)] not in T[13]]
need(14, "9 development receipts, mainly fictional mock receipts", "Future goals, not yet tested",
     "Automated audit checks and time savings")
for i in T:
    if re.search(r"(?i)another authori[sz]ed( internal)? platform|an internal platform", T[i] + N[i]):
        problems.append(f"slide {i}: use the one platform name, 'Internal Data Platform'")
    if re.search(r"(?i)masking (is|has been) (chosen|selected|in place)", T[i] + N[i]):
        problems.append(f"slide {i}: masking presented as chosen or in place")

# Unchanged slides: identical text and notes to the manually edited V17 deck (page numbers aside).
V17 = Presentation(PROJECT / "archive" / "v17_final" / "OCR_Benchmark_V17.pptx")


def content(s):
    txt = [sh.text_frame.text for sh in s.shapes if sh.has_text_frame and not sh.text_frame.text.strip().isdigit()]
    txt += [" | ".join(c.text for r in sh.table.rows for c in r.cells) for sh in s.shapes if sh.has_table]
    return txt, s.notes_slide.notes_text_frame.text


for new, old in [(i, i) for i in range(1, 9)] + [(13, 13), (14, 14)]:
    if new <= len(prs.slides) and content(prs.slides[new - 1]) != content(V17.slides[old - 1]):
        problems.append(f"slide {new}: changed from the V17 deck (it should be unchanged)")
if len(prs.slides) >= 9:
    t9, n9 = content(prs.slides[8])
    o9, on9 = content(V17.slides[8])
    norm = lambda x: x.replace("on the Internal Data Platform", "on another authorized platform").replace(  # noqa: E731
        "on another authorized platform internal", "")
    if [norm(t) for t in t9] != o9 or n9.replace("on the Internal Data Platform",
                                                 "on another authorized internal platform") != on9:
        problems.append("slide 9: changed beyond the platform name")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides with notes in the V18 order; slides 1-8 and the appendix "
      "unchanged from the edited V17 deck, slide 9 only renamed to the Internal Data Platform; receipt 8 output, "
      f"chart = {', '.join(OVERALL)} on main slide 5 only, all {len(SHOWN)} per-field and overall figures; "
      "architecture cropped, near full width, proposed and not implemented; privacy slide without the repeated flow, "
      "with the masking, Azure DI and SharePoint requirements; conclusion asks to review and approve the architecture "
      "and privacy controls; one platform name; text in previews/deck_text.md")
