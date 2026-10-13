"""Generate the Receipt OCR Benchmark comparison deck from the AIA template.

Usage (from ppt/ocr_benchmark/):
    python3 scripts/generate_ppt.py                     # writes current/<DECK_NAME>.pptx
    python3 scripts/generate_ppt.py --output out.pptx   # write elsewhere, e.g. to check reproduction

Every benchmark number is read from the committed results of python/receipt_ocr_benchmark
(results/scores_all/summary.csv and detail.csv, results/di_aoai/*.json), not typed in by hand.
An existing output file is never overwritten unless --force is given, and the archive/ and
template/ folders are always refused as output locations. Requires python-pptx.
"""
import argparse
import copy
import csv
import json
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent.parent
BENCH = REPO / "python" / "receipt_ocr_benchmark" / "results"
DECK_NAME = "OCR_Benchmark_Comparison"
PROTECTED = [PROJECT / d for d in ("archive", "template")]

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--template", type=Path, default=PROJECT / "template" / "aia_ppt_template.pptx")
ap.add_argument("--output", type=Path, default=PROJECT / "current" / f"{DECK_NAME}.pptx")
ap.add_argument("--force", action="store_true", help="overwrite the output file if it already exists")
args = ap.parse_args()

OUT = args.output.resolve()
if any(OUT.is_relative_to(p.resolve()) for p in PROTECTED):
    sys.exit(f"Refusing to write into a protected folder: {OUT}")
if OUT.exists() and not args.force:
    sys.exit(f"{OUT} already exists. Use --force to overwrite, or --output for a new path.")
OUT.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- benchmark data (source of truth)
APPROACHES = ["paddle_light", "paddle_heavy", "azure_di", "azure_di_aoai"]
NAMES = {"paddle_light": "PaddleOCR Light", "paddle_heavy": "PaddleOCR Heavy",
         "azure_di": "Azure DI", "azure_di_aoai": "Azure DI + AOAI"}
FIELDS = ["doctor_name", "patient_name", "receipt_number", "service_date", "total_amount", "registration_number"]
FIELD_NAMES = {"doctor_name": "Doctor name", "patient_name": "Patient name", "receipt_number": "Receipt number",
               "service_date": "Service date", "total_amount": "Total amount",
               "registration_number": "Registration number"}

summary = {r["approach"]: r for r in csv.DictReader(open(BENCH / "scores_all" / "summary.csv"))}
detail = list(csv.DictReader(open(BENCH / "scores_all" / "detail.csv")))
assert list(summary) == APPROACHES, f"unexpected approaches in summary.csv: {list(summary)}"

N_RECEIPTS = len({r["receipt"] for r in detail})
ACC = {a: float(summary[a]["accuracy_pct"]) for a in APPROACHES}
CORRECT = {a: int(summary[a]["correct"]) for a in APPROACHES}
APPLICABLE = {a: int(summary[a]["applicable"]) for a in APPROACHES}
INVENTED = {a: int(summary[a]["invented"]) for a in APPROACHES}
PROCESSED = {a: N_RECEIPTS - int(summary[a]["no_result_receipts"]) for a in APPROACHES}
SECONDS = {a: int(summary[a]["mean_ms_per_receipt"]) / 1000 for a in APPROACHES}
FIELD_SCORE = {}  # (approach, field) -> (correct, applicable)
for a in APPROACHES:
    for f in FIELDS:
        rows = [r for r in detail if r["approach"] == a and r["field"] == f and r["result"] in ("Correct", "Wrong")]
        FIELD_SCORE[a, f] = (sum(r["result"] == "Correct" for r in rows), len(rows))
TOTAL_CELLS = len([r for r in detail if r["approach"] == APPROACHES[0]])

aoai = [json.load(open(p)) for p in sorted((BENCH / "di_aoai").glob("receipt*.json"))]
assert len(aoai) == N_RECEIPTS and all(r["status"] == "ok" for r in aoai)
IN_TOK = sum(r["aoai"]["usage"]["prompt_tokens"] for r in aoai) / len(aoai)
OUT_TOK = sum(r["aoai"]["usage"]["completion_tokens"] for r in aoai) / len(aoai)
DI_S = sum(r["timings"]["di_ms"] for r in aoai) / len(aoai) / 1000
AOAI_S = sum(r["timings"]["aoai_ms"] for r in aoai) / len(aoai) / 1000
AOAI_WRONG = APPLICABLE["azure_di_aoai"] - CORRECT["azure_di_aoai"]
# wrong dates where the extracted year is DI's misread 2020 and the receipt says 2026
YEAR_ERRORS = sum(1 for r in detail if r["approach"] == "azure_di_aoai" and r["field"] == "service_date"
                  and r["result"] == "Wrong" and r["predicted"].startswith("2020") and r["ground_truth"].startswith("2026"))


def pct(a):
    return f"{ACC[a]:.0f}%"


def score(a):
    return f"{CORRECT[a]}/{APPLICABLE[a]}"


def vm_hours(a):
    return SECONDS[a] * 1000 / 3600


# ---------------------------------------------------------------- style (as the contingent_worker deck)
RED = RGBColor(0xD3, 0x11, 0x45)
CHAR = RGBColor(0x33, 0x3D, 0x47)
GREY_TXT = RGBColor(0x5F, 0x67, 0x70)
MID_GREY = RGBColor(0xA6, 0xAB, 0xB0)
LIGHT = RGBColor(0xF2, 0xF2, 0xF2)
TINT = RGBColor(0xFB, 0xE7, 0xEC)
LINE = "BFBFBF"
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Arial"

prs = Presentation(args.template)

for sh in prs.slide_master.shapes:  # keep the sensitivity marking on one line (label applied in PowerPoint)
    nv = sh._element.find(".//" + qn("p:nvPr"))
    if sh.has_text_frame and nv is not None and "classification" in etree.tostring(nv).decode():
        sh.text_frame._txBody.find(qn("a:bodyPr")).set("wrap", "none")
        sh.width = Inches(1.4)

sldIdLst = prs.slides._sldIdLst  # remove the template's sample slides
for sldId in list(sldIdLst):
    prs.part.drop_rel(sldId.rId)
    sldIdLst.remove(sldId)

L_TITLE, L_CONTENT = prs.slide_layouts[0], prs.slide_layouts[1]
SLDNUM_SP = [sh for sh in L_CONTENT.placeholders if sh.placeholder_format.idx == 4][0]._element


def ph(slide, idx):
    return [p for p in slide.placeholders if p.placeholder_format.idx == idx][0]


def set_runs(tf, text_, size=None, bold=None, color=None):
    p = tf.paragraphs[0]
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    r = p.add_run()
    r.text = text_
    if size: r.font.size = Pt(size)
    if bold is not None: r.font.bold = bold
    if color is not None: r.font.color.rgb = color
    r.font.name = FONT
    return r


def bullet(p, char="•", indent=0.18):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent))))
    pPr.set("indent", str(-int(Inches(indent))))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for e in pPr.findall(qn(tag)):
            pPr.remove(e)
    bf = etree.SubElement(pPr, qn("a:buFont")); bf.set("typeface", FONT)
    bc = etree.SubElement(pPr, qn("a:buChar")); bc.set("char", char)


def no_bullet(p):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", "0"); pPr.set("indent", "0")
    etree.SubElement(pPr, qn("a:buNone"))


def plain_shape(slide, kind, x, y, w, h, fill):
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    st = shp._element.find(qn("p:style"))
    if st is not None:
        shp._element.remove(st)
    return shp


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.0, fill=None, name=None):
    """paras: list of dicts {t | runs:[(text, {bold,color,size,italic})], size, color, bold, bullet, after, align}"""
    box = plain_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h, fill) if fill is not None else \
        slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(min(margin, 0.12)) if margin else 0
    tf.vertical_anchor = anchor
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        bullet(p) if pd.get("bullet") else no_bullet(p)
        p.alignment = pd.get("align", PP_ALIGN.LEFT)
        p.space_after = Pt(pd.get("after", 0))
        p.space_before = Pt(pd.get("before", 0))
        for t, o in pd.get("runs") or [(pd["t"], {})]:
            r = p.add_run(); r.text = t
            f = r.font; f.name = FONT
            f.size = Pt(o.get("size", pd.get("size", 13)))
            f.bold = o.get("bold", pd.get("bold", False))
            f.italic = o.get("italic", pd.get("italic", False))
            f.color.rgb = o.get("color", pd.get("color", CHAR))
    return box


def content_slide(title, message, notes):
    s = prs.slides.add_slide(L_CONTENT)
    for idx in (15, 16):
        e = ph(s, idx)._element; e.getparent().remove(e)
    s.shapes._spTree.append(copy.deepcopy(SLDNUM_SP))
    t = ph(s, 10)
    t.left, t.top, t.width, t.height = Inches(0.39), Inches(0.55), Inches(12.2), Inches(0.62)
    t.text_frame.margin_left = 0
    set_runs(t.text_frame, title, size=28, bold=True, color=CHAR)
    text(s, 0.39, 1.22, 12.55, 0.5, [dict(t=message, size=16, color=RED)])
    s.notes_slide.notes_text_frame.text = notes
    return s


def footnote(s, t, y=6.2, w=11.5):
    text(s, 0.39, y, w, 0.3, [dict(t=t, size=10, color=GREY_TXT, italic=True)])


def cell_border(cell, sides="B", color=LINE, w=9525):
    tcPr = cell._tc.get_or_add_tcPr()
    for side in ("L", "R", "T", "B"):
        for e in tcPr.findall(qn(f"a:ln{side}")):
            tcPr.remove(e)
    for side in ("L", "R", "T", "B"):
        ln = etree.SubElement(tcPr, qn(f"a:ln{side}"))
        if side in sides:
            ln.set("w", str(w)); ln.set("cmpd", "sng")
            sf = etree.SubElement(ln, qn("a:solidFill"))
            c = etree.SubElement(sf, qn("a:srgbClr")); c.set("val", color)
        else:
            ln.set("w", "0"); etree.SubElement(ln, qn("a:noFill"))
    for f in [e for e in tcPr if e.tag in (qn("a:solidFill"), qn("a:noFill"))]:
        tcPr.remove(f); tcPr.append(f)  # schema order: borders before fill


def fill_cell(cell, paras, fill=None, anchor=MSO_ANCHOR.MIDDLE):
    tf = cell.text_frame
    tf.word_wrap = True
    cell.margin_left = cell.margin_right = Inches(0.1)
    cell.margin_top = cell.margin_bottom = Inches(0.06)
    cell.vertical_anchor = anchor
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = pd.get("align", PP_ALIGN.LEFT)
        for t, o in pd.get("runs") or [(pd["t"], {})]:
            r = p.add_run(); r.text = t
            f = r.font; f.name = FONT
            f.size = Pt(o.get("size", pd.get("size", 13)))
            f.bold = o.get("bold", pd.get("bold", False))
            f.italic = o.get("italic", pd.get("italic", False))
            f.color.rgb = o.get("color", pd.get("color", CHAR))
    if fill is None:
        cell.fill.background()
    else:
        cell.fill.solid(); cell.fill.fore_color.rgb = fill


def table(s, x, y, col_w, row_h):
    shp = s.shapes.add_table(len(row_h), len(col_w), Inches(x), Inches(y), Inches(sum(col_w)), Inches(sum(row_h)))
    tbl = shp.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0"); tblPr.set("bandRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for i, rh in enumerate(row_h):
        tbl.rows[i].height = Inches(rh)
    return tbl


def bar_chart(s, x, y, w, h, categories, values, colors, number_format, horizontal=False, name=None):
    data = CategoryChartData()
    data.categories = categories
    data.add_series("value", values)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    gf = s.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), data)
    if name:
        gf.name = name
    chart = gf.chart
    chart.has_legend = False
    chart.has_title = False
    chart.font.name = FONT
    chart.font.size = Pt(12)
    chart.font.color.rgb = CHAR
    plot = chart.plots[0]
    plot.gap_width = 60
    plot.vary_by_categories = False
    ser = plot.series[0]
    for i, c in enumerate(colors):
        pt = ser.points[i]
        pt.format.fill.solid(); pt.format.fill.fore_color.rgb = c
        pt.format.line.fill.background()
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = number_format
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(14); dl.font.bold = True; dl.font.name = FONT; dl.font.color.rgb = CHAR
    va = chart.value_axis
    va.visible = False
    va.has_major_gridlines = False
    va.minimum_scale = 0
    ca = chart.category_axis
    ca.format.line.color.rgb = MID_GREY
    ca.tick_labels.font.size = Pt(12); ca.tick_labels.font.name = FONT
    ca.has_major_gridlines = False
    if horizontal:
        ca.reverse_order = True  # first category at the top
        va.maximum_scale = max(values) * 1.18
    else:
        va.maximum_scale = 1.0
    return chart


# ================================================================= Slide 1 - Title
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Receipt OCR Benchmark")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(0.39), Inches(4.5), Inches(6.3), Inches(0.9)
set_runs(sub.text_frame, "Comparing traditional OCR with Azure AI solutions")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = f"Results from {N_RECEIPTS} mock medical receipts · October 2026"; r.font.name = FONT
s.notes_slide.notes_text_frame.text = (
    "This deck answers one question: is Azure Document Intelligence plus Azure OpenAI worth its extra cost "
    "and complexity compared with simpler OCR options? All results come from a benchmark on six mock receipts.")

# ================================================================= Slide 2 - Objective and methodology
s = content_slide(
    "Objective and Methodology",
    "We tested four approaches on the same receipts, fields and scoring to support a build-or-buy decision.",
    "We want to know whether the more expensive Azure AI pipeline (Document Intelligence plus OpenAI) is "
    "justified. All four approaches read the same six mock receipts and were scored against one hand-checked "
    "answer key, field by field. We looked at accuracy, speed, reliability and cost.")

text(s, 0.39, 2.0, 3.75, 3.95, [
    dict(t="BUSINESS QUESTION", size=11, bold=True, color=GREY_TXT, after=10),
    dict(t="Is Azure Document Intelligence + Azure OpenAI worth its additional cost and complexity?",
         size=20, bold=True, color=RED, after=14),
    dict(t="Compared with simpler OCR solutions that run on our own compute.", size=14),
], margin=0.25, fill=LIGHT)

cards = [
    ("Dataset", [f"{N_RECEIPTS} mock medical receipts in 4 layouts", "4 handwritten, 2 printed"]),
    ("Fields evaluated", ["Doctor name, patient name, receipt number",
                          "Service date, total amount, registration number"]),
    ("Approaches compared", ["PaddleOCR Light and Heavy", "Azure DI, and Azure DI + Azure OpenAI"]),
    ("Evaluation criteria", ["Accuracy · Speed · Reliability · Cost"]),
]
GX, GW, GH, GAP = 4.44, (12.94 - 4.44 - 0.3) / 2, (3.95 - 0.3) / 2, 0.3
for i, (head, lines) in enumerate(cards):
    cx = GX + (i % 2) * (GW + GAP)
    cy = 2.0 + (i // 2) * (GH + GAP)
    text(s, cx, cy, GW, GH, [dict(t=head, size=15, bold=True, color=RED, after=8)] +
         [dict(t=l, size=13, bullet=True, after=4) for l in lines], margin=0.22, fill=LIGHT)

footnote(s, f"Every receipt × field was marked correct or wrong against one hand-checked answer key "
            f"({TOTAL_CELLS} cells; {APPLICABLE['paddle_light']} have a value on the receipt).")

# ================================================================= Slide 3 - The four approaches
s = content_slide(
    "Four Approaches Compared",
    "Each approach reads the receipt (OCR), then finds the six fields; they differ in where each step runs.",
    "Every approach has two steps: OCR turns the image into text, then an extraction step finds the six "
    "fields. The first three use the same fixed extraction rules, so they differ only in the OCR engine. "
    "The fourth replaces the rules with Azure OpenAI. Grey boxes run on our own compute with no per-call "
    "fee; red boxes are paid Azure API calls.")

rows = [
    ("1", "PaddleOCR Light", ("PaddleOCR Light", "Open-source OCR, small model"), ("General rules", "Same fixed rules")),
    ("2", "PaddleOCR Heavy", ("PaddleOCR Heavy", "Open-source OCR, large model"), ("General rules", "Same fixed rules")),
    ("3", "Azure DI", ("Azure Document Intelligence", "Cloud OCR (prebuilt-read)"), ("General rules", "Same fixed rules")),
    ("4", "Azure DI + AOAI", ("Azure Document Intelligence", "Cloud OCR (prebuilt-read)"),
     ("Azure OpenAI (gpt-5-mini)", "LLM reads the text")),
]
cloud = {("3", 0), ("4", 0), ("4", 1)}
X_NUM, X_NAME, W_NAME = 0.39, 0.95, 2.25
X_OCR, W_BOX, W_ARR, X_OUT, W_OUT = 3.4, 3.55, 0.32, 0, 1.75
X_EXT = X_OCR + W_BOX + 0.14 + W_ARR + 0.14
X_OUT = X_EXT + W_BOX + 0.14 + W_ARR + 0.14
W_OUT = 12.94 - X_OUT
text(s, X_OCR, 1.88, W_BOX, 0.3, [dict(t="STEP 1 · OCR: read the text", size=11, bold=True, color=GREY_TXT)])
text(s, X_EXT, 1.88, W_BOX, 0.3, [dict(t="STEP 2 · Extract the six fields", size=11, bold=True, color=GREY_TXT)])
text(s, X_OUT, 1.88, W_OUT, 0.3, [dict(t="RESULT", size=11, bold=True, color=GREY_TXT)])
RH, RG, RY = 0.76, 0.2, 2.25
for i, (num, name, ocr, ext) in enumerate(rows):
    y = RY + i * (RH + RG)
    circ = plain_shape(s, MSO_SHAPE.OVAL, X_NUM, y + (RH - 0.42) / 2, 0.42, 0.42, CHAR)
    tf = circ.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    set_runs(tf, num, size=14, bold=True, color=WHITE); tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    text(s, X_NAME, y, W_NAME, RH, [dict(t=name, size=15, bold=True)], anchor=MSO_ANCHOR.MIDDLE)
    for j, (bx, (head, desc)) in enumerate(((X_OCR, ocr), (X_EXT, ext))):
        is_cloud = (num, j) in cloud
        text(s, bx, y, W_BOX, RH, [dict(t=head, size=13, bold=True, color=WHITE if is_cloud else CHAR, after=2),
                                    dict(t=desc, size=12, color=WHITE if is_cloud else GREY_TXT)],
             anchor=MSO_ANCHOR.MIDDLE, margin=0.16, fill=RED if is_cloud else LIGHT)
        plain_shape(s, MSO_SHAPE.CHEVRON, bx + W_BOX + 0.14, y + (RH - 0.36) / 2, W_ARR, 0.36, MID_GREY)
    text(s, X_OUT, y, W_OUT, RH, [dict(t="6 fields", size=13, bold=True)], anchor=MSO_ANCHOR.MIDDLE,
         margin=0.16, fill=TINT)

LY = RY + 4 * (RH + RG) - 0.02
plain_shape(s, MSO_SHAPE.RECTANGLE, X_OCR, LY + 0.06, 0.22, 0.22, LIGHT).line.color.rgb = MID_GREY
text(s, X_OCR + 0.32, LY, 3.6, 0.34, [dict(t="Runs on our own compute (no per-call fee)", size=12, color=GREY_TXT)],
     anchor=MSO_ANCHOR.MIDDLE)
plain_shape(s, MSO_SHAPE.RECTANGLE, X_OCR + 4.3, LY + 0.06, 0.22, 0.22, RED)
text(s, X_OCR + 4.62, LY, 3.2, 0.34, [dict(t="Paid Azure API call", size=12, color=GREY_TXT)],
     anchor=MSO_ANCHOR.MIDDLE)

# ================================================================= Slide 4 - Accuracy
best = max(ACC.values())
tied = [a for a in APPROACHES if ACC[a] == best]
s = content_slide(
    "Accuracy Comparison",
    f"Three approaches tie at {best:.0f}% accuracy; Azure DI with rules alone is lowest at {pct('azure_di')}.",
    f"Accuracy is the share of fields that are present on the receipts and were extracted correctly. Of the "
    f"{TOTAL_CELLS} receipt-field combinations, {APPLICABLE['paddle_light']} have a value on the receipt; "
    f"the rest (for example registration number, which appears on none) are excluded. PaddleOCR Light, Heavy "
    f"and Azure DI + AOAI each got {CORRECT['paddle_light']} of {APPLICABLE['paddle_light']} right. "
    f"With only {N_RECEIPTS} receipts, one field is worth 4 percentage points, so the tie is not conclusive.")

cats = [f"{NAMES[a]}\n{score(a)}" for a in APPROACHES]
bar_chart(s, 0.39, 1.95, 7.7, 4.15, cats, [ACC[a] / 100 for a in APPROACHES],
          [RED if a in tied else MID_GREY for a in APPROACHES], '0%', name="Accuracy chart")

text(s, 8.44, 2.0, 4.5, 3.95, [
    dict(t="HOW ACCURACY IS MEASURED", size=11, bold=True, color=GREY_TXT, after=8),
    dict(t="Correct fields ÷ fields that exist on the receipts", size=15, bold=True, after=12),
    dict(t=f"{APPLICABLE['paddle_light']} of {TOTAL_CELLS} receipt-field cells have a value; fields not on "
           f"a receipt are excluded", size=13, bullet=True, after=8),
    dict(t="A missing value or a failed receipt counts as wrong", size=13, bullet=True, after=8),
    dict(t=f"Values given for fields not on the receipt are counted separately: "
           f"{INVENTED['azure_di_aoai']} for Azure DI + AOAI, 0 for the others", size=13, bullet=True),
], margin=0.25, fill=LIGHT)

footnote(s, f"Based on {N_RECEIPTS} mock receipts: one field = 4 percentage points, so small differences are not "
            f"conclusive.")

# ================================================================= Slide 5 - Field accuracy
s = content_slide(
    "Accuracy by Field",
    "Totals are solved by all four; Azure OpenAI finds more names and numbers, PaddleOCR reads handwritten dates.",
    "Total amount was extracted correctly by every approach on every receipt. Azure DI + AOAI found all four "
    "patient names and all three receipt numbers, including fields without a clear label. PaddleOCR read the "
    "handwritten dates correctly on five of six receipts. Both Azure DI approaches got only one date right "
    "because Azure DI read the handwritten year 2026 as 2020 on four receipts.")

SHOW = ["total_amount", "patient_name", "receipt_number", "doctor_name", "service_date"]
col_w = [2.2] + [1.42] * 4
tbl = table(s, 0.39, 2.0, col_w, [0.62] + [0.56] * len(SHOW) + [0.46])
fill_cell(tbl.cell(0, 0), [dict(t="Field", size=13, bold=True, color=WHITE)], fill=CHAR)
for c, a in enumerate(APPROACHES, start=1):
    fill_cell(tbl.cell(0, c), [dict(t=NAMES[a], size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)], fill=CHAR)
for r_i, f in enumerate(SHOW, start=1):
    fill_cell(tbl.cell(r_i, 0), [dict(t=FIELD_NAMES[f], size=13, bold=True)])
    rates = {a: FIELD_SCORE[a, f][0] / FIELD_SCORE[a, f][1] for a in APPROACHES}
    top = max(rates.values())
    for c, a in enumerate(APPROACHES, start=1):
        k, n = FIELD_SCORE[a, f]
        highlight = rates[a] == top and len(set(rates.values())) > 1
        fill_cell(tbl.cell(r_i, c), [dict(t=f"{k}/{n}", size=14, bold=highlight,
                                          color=RED if highlight else CHAR, align=PP_ALIGN.CENTER)],
                  fill=TINT if highlight else None)
    for c in range(5):
        cell_border(tbl.cell(r_i, c), sides="B")
last = len(SHOW) + 1
fill_cell(tbl.cell(last, 0), [dict(t=FIELD_NAMES["registration_number"], size=12, color=GREY_TXT)])
m = tbl.cell(last, 1); m.merge(tbl.cell(last, 4))
fill_cell(m, [dict(t="Not on any receipt, so not scored", size=12, italic=True, color=GREY_TXT,
                   align=PP_ALIGN.CENTER)])
for c in range(5):
    cell_border(tbl.cell(0, c), sides="")
    cell_border(tbl.cell(last, c), sides="")

k_a = FIELD_SCORE["azure_di_aoai", "patient_name"]
k_r = FIELD_SCORE["azure_di_aoai", "receipt_number"]
d_p = FIELD_SCORE["paddle_light", "service_date"]
d_d = FIELD_SCORE["azure_di", "service_date"]
text(s, 8.5, 2.0, 4.44, 4.0, [
    dict(t="WHAT STANDS OUT", size=11, bold=True, color=GREY_TXT, after=10),
    dict(t="Total amount: correct on all receipts for all four approaches", size=13, bullet=True, after=10),
    dict(t=f"Azure DI + AOAI found all {k_a[1]} patient names and all {k_r[1]} receipt numbers", size=13,
         bullet=True, after=10),
    dict(t=f"PaddleOCR read handwritten dates correctly ({d_p[0]}/{d_p[1]})", size=13, bullet=True, after=10),
    dict(t=f"Both Azure DI approaches: {d_d[0]}/{d_d[1]} dates, because Azure DI read the handwritten "
           f"year 2026 as 2020", size=13, bullet=True),
], margin=0.25, fill=LIGHT)

footnote(s, "Highlighted = best result for that field. Cells show correct / receipts where the field exists.")

# ================================================================= Slide 6 - Speed and reliability
fastest = min(APPROACHES, key=lambda a: SECONDS[a])
s = content_slide(
    "Processing Speed and Reliability",
    f"{NAMES[fastest]} is fastest; every approach processed all {N_RECEIPTS} receipts without errors.",
    f"Average seconds per receipt. PaddleOCR runs on a CPU on our Azure ML compute; the Azure services are "
    f"timed as the full API call including network. Azure DI + AOAI is {DI_S:.1f} s of OCR plus {AOAI_S:.1f} s "
    f"of OpenAI. PaddleOCR Heavy is about four times slower than Light for the same accuracy. Receipts were "
    f"processed one at a time, so this is not a test of throughput at volume. Earlier reliability problems "
    f"(a PaddleOCR Heavy crash and Azure OpenAI timeouts in an older version) were fixed before the final run.")

bar_chart(s, 0.39, 1.95, 7.7, 4.1, [NAMES[a] for a in APPROACHES], [round(SECONDS[a], 1) for a in APPROACHES],
          [MID_GREY if a == "paddle_heavy" else RED for a in APPROACHES], '0.0" s"', horizontal=True,
          name="Speed chart")
text(s, 0.39, 1.82, 7.7, 0.3, [dict(t="AVERAGE SECONDS PER RECEIPT", size=11, bold=True, color=GREY_TXT)])

all_ok = all(PROCESSED[a] == N_RECEIPTS for a in APPROACHES)
text(s, 8.44, 2.0, 4.5, 3.95, [
    dict(t="RELIABILITY", size=11, bold=True, color=GREY_TXT, after=6),
    dict(t=f"{N_RECEIPTS} / {N_RECEIPTS}" if all_ok else "see notes", size=40, bold=True, color=RED, after=2),
    dict(t="receipts processed by every approach, no errors or timeouts", size=14, after=14),
    dict(t="PaddleOCR Heavy needed a library version fix to run on Azure CPU", size=13, bullet=True, after=8),
    dict(t=f"Older Azure OpenAI setup timed out; the final version took {AOAI_S:.0f} s per call", size=13,
         bullet=True),
], margin=0.25, fill=LIGHT)

footnote(s, "Times reflect different methods: PaddleOCR = CPU time on Azure ML compute; Azure = API call incl. "
            "network. One receipt at a time; not measured at volume.", w=12.55)

# ================================================================= Slide 7 - Findings and cost
s = content_slide(
    "Main Findings and Cost Considerations",
    f"Azure OpenAI lifts Azure DI from {pct('azure_di')} to {pct('azure_di_aoai')}, but PaddleOCR Light reaches "
    f"the same accuracy without API calls.",
    "Five findings. Prices are not yet confirmed, so the cost table shows only what we measured: compute hours "
    "for PaddleOCR, pages for Azure DI, and tokens for Azure OpenAI per 1,000 receipts. Once we have our VM "
    "hourly rate, the Document Intelligence page price and the gpt-5-mini token prices, each cell becomes a "
    "simple multiplication.")

findings = [
    ("Heavy adds nothing", f"PaddleOCR Heavy matched Light at {pct('paddle_heavy')} but was about 4× slower."),
    ("Azure OpenAI helps DI", f"Accuracy rose from {pct('azure_di')} to {pct('azure_di_aoai')} over Azure DI alone."),
    ("Better on unclear layouts", "The LLM found names and numbers the fixed rules missed."),
    ("Limited by DI's OCR", f"{YEAR_ERRORS} of its {AOAI_WRONG} errors came from DI misreading handwritten years."),
    ("Light matches it", f"PaddleOCR Light: {pct('paddle_light')} with no paid API calls (compute still costs)."),
]
for i, (head, desc) in enumerate(findings):
    y = 2.0 + i * 0.8
    circ = plain_shape(s, MSO_SHAPE.OVAL, 0.39, y + 0.08, 0.4, 0.4, RED)
    tf = circ.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    set_runs(tf, str(i + 1), size=13, bold=True, color=WHITE); tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    text(s, 0.95, y, 5.85, 0.72, [dict(t=head, size=14, bold=True, after=2), dict(t=desc, size=12, color=GREY_TXT)])

text(s, 7.1, 1.92, 5.84, 0.32, [dict(t="COST DRIVERS PER 1,000 RECEIPTS (MEASURED)", size=11, bold=True,
                                     color=GREY_TXT)])
ctbl = table(s, 7.1, 2.28, [1.9, 2.42, 1.52], [0.44, 0.52, 0.52, 0.52, 0.72])
for c, h in enumerate(["Approach", "Usage", "Price"]):
    fill_cell(ctbl.cell(0, c), [dict(t=h, size=12, bold=True, color=WHITE)], fill=CHAR)
    cell_border(ctbl.cell(0, c), sides="")
cost_rows = [
    ("PaddleOCR Light", f"{vm_hours('paddle_light'):.1f} VM-hours"),
    ("PaddleOCR Heavy", f"{vm_hours('paddle_heavy'):.1f} VM-hours"),
    ("Azure DI", "1,000 DI pages"),
    ("Azure DI + AOAI", f"1,000 DI pages + {IN_TOK * 1000 / 1e6:.2f}M input / {OUT_TOK * 1000 / 1e6:.2f}M "
                        f"output tokens"),
]
for r_i, (a, u) in enumerate(cost_rows, start=1):
    fill_cell(ctbl.cell(r_i, 0), [dict(t=a, size=12, bold=True)])
    fill_cell(ctbl.cell(r_i, 1), [dict(t=u, size=12)])
    fill_cell(ctbl.cell(r_i, 2), [dict(t="Pending", size=12, bold=True, color=RED)])
    for c in range(3):
        cell_border(ctbl.cell(r_i, c), sides="B")
text(s, 7.1, 5.6, 5.84, 0.55, [dict(t="Prices needed: Azure ML VM hourly rate, Document Intelligence Read price "
                                      "per 1,000 pages, gpt-5-mini price per 1M tokens.", size=11,
                                      color=GREY_TXT, italic=True)])

# ================================================================= Slide 8 - Recommendation
s = content_slide(
    "Conclusion and Recommendation",
    "Keep two candidates and test them on a larger, representative set before choosing a production solution.",
    "On this evidence, Azure DI plus Azure OpenAI is not yet shown to be worth its extra cost: it ties with "
    "PaddleOCR Light. We recommend dropping PaddleOCR Heavy and Azure DI with rules alone, and testing the two "
    "remaining candidates on a larger, representative set of real, anonymised receipts once pricing is "
    "confirmed. Combining PaddleOCR Light with Azure OpenAI is an idea worth testing, but it has not been "
    "tested yet.")

half = (12.55 - 0.3) / 2


def option(name, stats, desc, color):
    return [dict(runs=[(name + "  ", dict(bold=True, color=color, size=15)), (stats, dict(bold=True, size=13))],
                 after=3),
            dict(t=desc, size=13, color=GREY_TXT, after=12)]


text(s, 0.39, 2.0, half, 1.95, [dict(t="KEEP AS CANDIDATES", size=11, bold=True, color=GREY_TXT, after=8)] +
     option("PaddleOCR Light", f"{pct('paddle_light')} · {SECONDS['paddle_light']:.1f} s",
            "No API fees, runs offline, best on handwritten dates", RED) +
     option("Azure DI + AOAI", f"{pct('azure_di_aoai')} · {SECONDS['azure_di_aoai']:.1f} s",
            "Best on names and receipt numbers; paid per receipt", RED), margin=0.25, fill=TINT)
text(s, 0.39 + half + 0.3, 2.0, half, 1.95, [dict(t="WEAKER ON THIS DATASET", size=11, bold=True, color=GREY_TXT,
                                                  after=8)] +
     option("PaddleOCR Heavy", f"{pct('paddle_heavy')} · {SECONDS['paddle_heavy']:.1f} s",
            "Same accuracy as Light, about 4× slower", CHAR) +
     option("Azure DI alone", f"{pct('azure_di')} · {SECONDS['azure_di']:.1f} s",
            "Fastest, but the lowest accuracy", CHAR), margin=0.25, fill=LIGHT)

text(s, 0.39, 4.2, 12.55, 0.5, [dict(runs=[
    ("Important:  ", dict(bold=True, color=WHITE)),
    (f"{N_RECEIPTS} mock receipts are not enough to select a production solution.", dict(color=WHITE))],
    size=14)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=CHAR)

steps = [
    ("Test on more receipts", "Run both candidates on a larger, representative set of real, anonymised receipts"),
    ("Confirm pricing", "VM rate, Document Intelligence page price and gpt-5-mini token prices"),
    ("Optional experiment", "PaddleOCR Light + Azure OpenAI: an idea, not yet tested"),
]
sw = (12.55 - 2 * 0.3) / 3
for i, (head, desc) in enumerate(steps):
    text(s, 0.39 + i * (sw + 0.3), 5.0, sw, 1.2, [
        dict(t=f"NEXT STEP {i + 1}", size=10, bold=True, color=GREY_TXT, after=4),
        dict(t=head, size=14, bold=True, after=3), dict(t=desc, size=12, color=GREY_TXT)], margin=0.2, fill=LIGHT)

prs.save(OUT)
print(f"Saved {OUT}")
