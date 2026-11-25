"""Check the Version 21 deck against the benchmark results, the V21 brief and the archived Version 20 deck.

    python3 ppt/ocr_benchmark/scripts/check_deck_v21.py [deck.pptx]     (after make_v21_from_v20.py)

Deck slide numbers: 1 = cover, 2-13 = main slides 1-12, 14-15 = appendix A1-A2. Checks:
- every Version 20 check (order, tags, figures, receipt examples, review wording, line item arithmetic, privacy
  requirements, timeline, one platform name, avoid-list wording, jargon, cost figures), renumbered;
- main 9 and 10 (deck slides 10 and 11): Option A (internal platform masking) and Option B (local LLM masking),
  each one Figma diagram, the internal-masking and local-LLM exports from assets_v2, with the diagram's own header
  cropped off, both tagged proposed and not implemented; Option B states the key benefit and that accuracy,
  feasibility and privacy controls still require validation;
- main 11 (deck slide 12): the privacy slide covers both options and says neither is selected;
- slide-number fields on every content slide; every other slide identical in text and notes to the archived
  Version 20 deck.
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
DECK = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "current" / "OCR_Benchmark_V21.pptx"
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
if len(prs.slides) != 15:
    problems.append(f"expected 15 slides (cover + 12 + 2 appendix), found {len(prs.slides)}")
T, N, CHARTS, TITLES = {}, {}, {}, {}
for i, s in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}" + (" (cover)" if i == 1 else f" (main slide {i - 1})" if i <= 13 else
                                    f" (appendix A{i - 13})") + "\n")
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
         "Future Audit Analytics: Example Tests", "Option A: Internal Platform Masking",
         "Option B: Local LLM Masking in Azure", "Privacy and Governance",
         "Project Timeline and Target Rollout",
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
            if i != 13:
                problems.append(f"slide {i} {where}: 500 to 1,000 receipts outside the conclusion")
            if not re.search(r"(?i)proposed", t) or not re.search(r"(?i)to be confirmed", t):
                problems.append(f"slide {i} {where}: 500 to 1,000 without 'proposed ... to be confirmed'")
    if re.search(r"(?i)\d+\s*(–|-|to)\s*\d+\s*min|minutes per receipt|hours of reading", text):
        problems.append(f"slide {i}: unmeasured time estimate on the slide (keep it in the notes)")
    if re.search(r"(?i)innovation idea|merely an idea|not a finished product", text + notes):
        problems.append(f"slide {i}: describes the active project as only an idea")
    if CHARTS[i] and i != 6:
        problems.append(f"slide {i}: unexpected chart")
    if 2 <= i <= 13 and i != 6:
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
               9: "FUTURE · NOT IMPLEMENTED", 10: "PROPOSED · NOT IMPLEMENTED", 11: "PROPOSED · NOT IMPLEMENTED",
               12: "TO BE AGREED", 13: "PLANNED DATES ARE TARGETS", 14: "APPENDIX", 15: "APPENDIX"}.items():
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
need(9, "Receipt amount vs claim", "Treatment dates", "Duplicate receipts",
     "Internal Data Platform", "Not implemented yet", "auditor review")
need(9, "Line item arithmetic", "Do the individual charges and discounts add up correctly to the final receipt total?",
     "Itemised charges, discounts and receipt total", "not among the six tested fields")
if "Unusual provider fees" in T.get(9, "") + N.get(9, ""):
    problems.append("slide 9: 'Unusual provider fees' should be replaced by line item arithmetic")
need(2, "Manually reviewing medical receipts takes significant auditor time and effort, limiting how many "
        "receipts can be checked.")
for i in T:
    for where, t in (("slide", T[i]), ("notes", N[i])):
        problems += [f"slide {i} {where}: claim about how auditors work {m.group(0)!r}"
                     for m in re.finditer(r"(?i)\bre-?typ\w*|\btranscri\w*|\bre-?key\w*|\bby hand\b", t)]
import hashlib  # noqa: E402

for i, asset in ((10, "architecture_internal_masking.png"), (11, "architecture_local_llm_masking.png")):
    pics = [sh for sh in prs.slides[i - 1].shapes if sh.shape_type == 13] if len(prs.slides) >= i else []
    if len(pics) != 1:
        problems.append(f"slide {i}: expected exactly one architecture diagram")
        continue
    pic = pics[0]
    want = hashlib.sha256((PROJECT / "assets_v2" / asset).read_bytes()).hexdigest()
    if hashlib.sha256(pic.image.blob).hexdigest() != want:
        problems.append(f"slide {i}: the diagram is not assets_v2/{asset}")
    if not pic.crop_top > 0.2:
        problems.append(f"slide {i}: the diagram's own title and subtitle are not cropped off")
    if pic.width < Inches(10.5) or pic.top + pic.height > Inches(6.3):
        problems.append(f"slide {i}: the diagram is too small or runs into the caption")
need(10, "Option A: Internal Platform Masking", "only masked text reaches Azure OpenAI", "not yet tested")
need(11, "Option B: Local LLM Masking in Azure", "Key benefit", "within Azure Compute",
     "one fewer SharePoint round trip", "Accuracy, feasibility and privacy controls still require validation")
for i in (10, 11):
    if "not implemented, approved or selected" not in N[i]:
        problems.append(f"slide {i} notes: should say the option is not implemented, approved or selected")
    if re.search(r"Proposed (Alternative )?Architecture and Data Flow|AIA INTERNAL AUDIT", T[i]):
        problems.append(f"slide {i}: duplicates the diagram's own title")
need(12, "Neither masking option is selected", "Masking must keep required fields", "Patient and practitioner names",
     "Internal Data Platform", "Azure DI receives original images", "approved data handling controls",
     "Where masking happens is open", "Option A", "Option B", "SharePoint may first hold unmasked OCR text",
     "Benchmark note: ", "re-tested for either option", "Still to be agreed and approved", "PII masking method",
     "Option A or B; not yet chosen or approved", "Storage and retention", "Access controls", "Transfer and linkage")
if re.search(r"Receipt image sent|Masked Text|stay here|→", T[12]):
    problems.append("slide 12: the repeated data flow is still on the privacy slide")
if re.search(r"(?i)option [ab] (is|has been) (selected|chosen|approved|preferred)", "\n".join(T.values()) +
             "\n".join(N.values())):
    problems.append("an option is presented as selected")
MILESTONES = ["Mid June 2026", "Mid July 2026", "Aug – Oct 2026", "Nov 2026", "Dec 2026", "Jan – Feb 2027",
              "Mar 2027", "Early Apr 2027"]
need(13, "PLANNED DATES ARE TARGETS", "COMPLETED", "PROPOSED TARGETS, NOT CONFIRMED", "TARGET ROLLOUT",
     "early April 2027", "proposed targets, not confirmed commitments", "Project kickoff",
     "MVP completed and presented to the Internal Audit team", "benchmarked", "Business auditors consulted",
     "Test real masked medical receipts", "complete application development",
     "user acceptance testing and required approvals", "For actual audit use", *MILESTONES)
pos = [T[13].find(m) for m in MILESTONES]
if -1 not in pos and pos != sorted(pos):
    problems.append("slide 13: milestones out of order")
if re.search(r"(?i)what we have achieved|support requested|future opportunities|conclusion", T[13] + N[13]):
    problems.append("slide 13: conclusion content remains")
if "proposed targets, not confirmed commitments" not in N[13]:
    problems.append("slide 13 notes: planned dates must be described as proposed targets")
problems += [f"slide 14: missing {n} {f} {v}% {COUNTS[(n, f)]}" for (n, f), v in SHOWN.items()
             if f"{v}%" not in T[14] or COUNTS[(n, f)] not in T[14]]
need(15, "9 development receipts, mainly fictional mock receipts", "Future goals, not yet tested",
     "Automated audit checks and time savings")
for i in T:
    if re.search(r"(?i)another authori[sz]ed( internal)? platform|an internal platform", T[i] + N[i]):
        problems.append(f"slide {i}: use the one platform name, 'Internal Data Platform'")
    if re.search(r"(?i)masking (is|has been) (chosen|selected|in place)", T[i] + N[i]):
        problems.append(f"slide {i}: masking presented as chosen or in place")

# Unchanged slides: identical text and notes to the archived Version 20 deck (page numbers aside).
V20 = Presentation(PROJECT / "archive" / "v20_final" / "OCR_Benchmark_V20.pptx")


def content(s):
    txt = [sh.text_frame.text for sh in s.shapes if sh.has_text_frame and not sh.text_frame.text.strip().isdigit()]
    txt += [" | ".join(c.text for r in sh.table.rows for c in r.cells) for sh in s.shapes if sh.has_table]
    return txt, s.notes_slide.notes_text_frame.text


if len(prs.slides) == 15:
    for new, old in [(i, i) for i in range(1, 10)] + [(13, 12), (14, 13), (15, 14)]:
        if content(prs.slides[new - 1]) != content(V20.slides[old - 1]):
            problems.append(f"slide {new}: changed from V20 slide {old} (it should be unchanged)")
    for i, s in enumerate(prs.slides, 1):  # page numbers are slide-number fields, so they renumber themselves
        if i > 1 and not s.shapes._spTree.xpath(".//a:fld[@type='slidenum']"):
            problems.append(f"slide {i}: no slide-number field")

(PROJECT / "previews").mkdir(exist_ok=True)
(PROJECT / "previews" / "deck_text.md").write_text("\n".join(out) + "\n")
if problems:
    sys.exit("Deck check FAILED:\n- " + "\n- ".join(problems))
print(f"Deck check passed: {len(prs.slides)} slides with notes; Option A and Option B diagrams from assets_v2, "
      "header cropped, proposed and not implemented, Option B benefit and validation caveat; privacy slide covers "
      "both options with neither selected; slide-number fields on every content slide; all other slides "
      f"unchanged from V20; receipt 8 output, chart = {', '.join(OVERALL)} on main slide 5 only, all {len(SHOWN)} "
      "per-field and overall figures; timeline and wording checks; text in previews/deck_text.md")
