"""Generate the Version 15 medical receipt extraction deck (cover + 10 slides + 2 appendix) from the AIA template.

    python3 ppt/ocr_benchmark/scripts/generate_ppt_v15.py --force     (from the repository root)

Version 15 is a new management deck built from ppt/ocr_benchmark/deck_direction.md. It tells the story
problem -> solution -> audit value -> why AI -> governance and downstream use, for Internal Audit management and
business auditors. The current scope is receipt extraction and structured export; downstream audit tests are
future possibilities only. The benchmark figures appear once (main slide 5) with their qualification; the
per-field figures are in appendix A1.

Figures: PaddleOCR + rules and Azure DI + rules = the multilingual rules baseline
(results/v2/scores_multilingual); Azure DI + Azure OpenAI = the refined-instruction run
(results/v2/scores_aoai_improved, aoai_v2_rows). Every figure and receipt example is read from the saved results
and asserted at build time; receipt crops are placed with Azure DI text positions. Nothing in the benchmark
folder is written. generate_ppt_v14.py is kept unchanged to reproduce the archived Version 14 deck.
"""
import argparse
import copy
import csv
import json
import sys
from datetime import date
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageOps
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
BENCH = REPO / "python" / "receipt_ocr_benchmark"
RES = BENCH / "results" / "v2"
INPUTS = BENCH / "data" / "receipts_v2" / "benchmark_inputs"
ASSETS = PROJECT / "assets_v2"
PROTECTED = [PROJECT / d for d in ("archive", "template")]

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--template", type=Path, default=PROJECT / "template" / "aia_ppt_template.pptx")
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V15.pptx")
ap.add_argument("--force", action="store_true", help="overwrite the output file if it already exists")
args = ap.parse_args()
OUT = args.output.resolve()
if any(OUT.is_relative_to(p.resolve()) for p in PROTECTED):
    sys.exit(f"Refusing to write into a protected folder: {OUT}")
if OUT.exists() and not args.force:
    sys.exit(f"{OUT} already exists. Use --force to overwrite, or --output for a new path.")
OUT.parent.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(exist_ok=True)


# ===================================================================== benchmark data (source of truth)
def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


FIELD_NAMES = {"doctor_name": "Practitioner", "registration_number": "Registration no.", "patient_name": "Patient",
               "receipt_number": "Receipt no.", "service_date": "Treatment date", "total_amount": "Total amount"}
FIELDS = list(FIELD_NAMES)
M1, M2, M3 = "PaddleOCR + rules", "Azure DI + rules", "Azure DI + Azure OpenAI"
NAMES = (M1, M2, M3)
ML_CSV, AI_CSV = RES / "scores_multilingual", RES / "scores_aoai_improved"
RUNS = {M1: (ML_CSV, "paddle_light_multilingual", "extracted_multilingual_light"),
        M2: (ML_CSV, "azure_di_multilingual", "extracted_multilingual_azure_di"),
        M3: (AI_CSV, "aoai_v2_rows", "di_aoai_v2_rows")}

DETAIL, SUMMARY = {}, {}
for name, (folder, approach, _) in RUNS.items():
    SUMMARY[name] = next(r for r in read_csv(folder / "summary.csv") if r["approach"] == approach)
    for r in read_csv(folder / "detail.csv"):
        if r["approach"] == approach:
            DETAIL[(name, r["receipt"], r["field"])] = r
RECEIPTS = sorted({k[1] for k in DETAIL}, key=lambda s: int(s.replace("receipt", "")))
N_RECEIPTS = len(RECEIPTS)
assert N_RECEIPTS == 9, RECEIPTS
for n in NAMES:  # same receipts, fields and ground truth for every method
    assert {(k[1], k[2]): r["ground_truth"] for k, r in DETAIL.items() if k[0] == n} == \
           {(k[1], k[2]): r["ground_truth"] for k, r in DETAIL.items() if k[0] == M3}, n

SCORES = {}  # (method, field or None) -> (correct, applicable)
for n in NAMES:
    for f in FIELDS + [None]:
        sel = [r for k, r in DETAIL.items() if k[0] == n and (f is None or k[2] == f)
               and r["result"] in ("Correct", "Wrong")]
        SCORES[(n, f)] = (sum(r["result"] == "Correct" for r in sel), len(sel))
    c, a = SCORES[(n, None)]
    assert (c, a) == (int(SUMMARY[n]["correct"]), int(SUMMARY[n]["applicable"])), n
    assert f"{100 * c / a:.1f}" == f"{float(SUMMARY[n]['accuracy_pct']):.1f}", n
    assert sum(SCORES[(n, f)][0] for f in FIELDS) == c
PCT = {k: f"{100 * c / a:.1f}%" for k, (c, a) in SCORES.items()}
OVERALL = {n: SCORES[(n, None)] for n in NAMES}
APPLICABLE = OVERALL[M3][1]
NO_REG = N_RECEIPTS * len(FIELDS) - APPLICABLE
assert OVERALL[M1][0] < OVERALL[M2][0] < OVERALL[M3][0], "the deck says the AI approach was the most accurate"
for f in FIELDS:  # appendix A1 says the AI approach was the most accurate (or joint) on every field
    assert SCORES[(M3, f)][0] / SCORES[(M3, f)][1] > max(SCORES[(n, f)][0] / SCORES[(n, f)][1] for n in (M1, M2)), f
AI_WRONG = sorted((k[1], k[2]) for k, r in DETAIL.items() if k[0] == M3 and r["result"] == "Wrong")
assert AI_WRONG == [("receipt10", "service_date"), ("receipt9", "doctor_name")], AI_WRONG


def predicted(method, receipt, field):
    """Value from detail.csv, cross-checked against the saved extraction JSON."""
    row = DETAIL[(method, receipt, field)]
    j = json.loads((RES / RUNS[method][2] / f"{receipt}.json").read_text()).get(field)
    if ("" if j is None else str(j)) != row["predicted"]:
        sys.exit(f"Mismatch {method} {receipt} {field}: detail.csv vs extraction JSON")
    return row["predicted"], row["result"] == "Correct"


def show(field, v):
    if v in (None, ""):
        return "not found"
    if field == "service_date":
        return date.fromisoformat(str(v)).strftime("%-d %b %Y")
    if field == "total_amount":
        return f"HK${float(v):,.0f}"
    return str(v)


# The AI's own miss on receipt 9: the OCR text already held the misread name (speaker note and slide line).
R9_AI, _ = predicted(M3, "receipt9", "doctor_name")
assert R9_AI.startswith("Dr. ") and R9_AI[4:] in (RES / "azure_di" / "receipt9.json").read_text(), \
    "the deck says the AI returned a name the OCR had misread on receipt 9"


# ===================================================================== receipt crops (Azure DI positions)
def receipt_image(receipt):
    src = next(p for p in INPUTS.iterdir() if p.stem == receipt).resolve()
    return ImageOps.exif_transpose(Image.open(src)).convert("RGB")


def di_blocks(receipt):
    page = json.loads((RES / "azure_di" / f"{receipt}.json").read_text())["pages"][0]
    return page, [(b["text"], min(p[0] for p in b["polygon"]), min(p[1] for p in b["polygon"]),
                   max(p[0] for p in b["polygon"]), max(p[1] for p in b["polygon"])) for b in page["blocks"]]


def find_boxes(receipt, needles):
    page, blocks = di_blocks(receipt)
    boxes = []
    for n in needles:
        hit = next((b for b in blocks if n in b[0]), None)
        if hit is None:
            sys.exit(f"{receipt}: text {n!r} not found in Azure DI output; cannot place the crop")
        boxes.append(hit[1:])
    return (page["width"], page["height"]), boxes


def make_crop(receipt, needles, name, highlight, max_px=1600):
    img = receipt_image(receipt)
    (w, h), boxes = find_boxes(receipt, needles)
    if img.size != (w, h):
        sys.exit(f"{receipt}: image {img.size} does not match the Azure DI page {(w, h)}")
    m = int(0.025 * w)
    x0, y0 = max(0, min(b[0] for b in boxes) - m), max(0, min(b[1] for b in boxes) - m)
    x1, y1 = min(w, max(b[2] for b in boxes) + m), min(h, max(b[3] for b in boxes) + m)
    draw = ImageDraw.Draw(img)
    lw = max(4, w // 400)
    for b in find_boxes(receipt, highlight)[1]:
        draw.rectangle([b[0] - lw * 2, b[1] - lw * 2, b[2] + lw * 2, b[3] + lw * 2], outline=(211, 17, 69), width=lw)
    crop = img.crop((x0, y0, x1, y1))
    crop.thumbnail((max_px, max_px))
    path = ASSETS / f"{name}.jpg"
    crop.save(path, quality=90)
    return path


# ===================================================================== style (AIA template, plain)
RED = RGBColor(0xD3, 0x11, 0x45)
CHAR = RGBColor(0x33, 0x3D, 0x47)
GREY_TXT = RGBColor(0x5F, 0x67, 0x70)
MID_GREY = RGBColor(0x8C, 0x93, 0x9A)
PALE = RGBColor(0xC9, 0xCD, 0xD1)
LIGHT = RGBColor(0xF2, 0xF2, 0xF2)
RED_TINT = RGBColor(0xFB, 0xE7, 0xEC)
GOOD = RGBColor(0x1E, 0x7B, 0x4A)
GOOD_TINT = RGBColor(0xE6, 0xF2, 0xEA)
BAD_TINT = RGBColor(0xFB, 0xE7, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = "BFBFBF"
FONT, FONT_ZH = "Arial", "Microsoft JhengHei"
C = PP_ALIGN.CENTER
X0, XW = 0.39, 12.55  # content left edge and width

prs = Presentation(args.template)
for sh in prs.slide_master.shapes:  # keep the classification marking on one line (label applied in PowerPoint)
    nv = sh._element.find(".//" + qn("p:nvPr"))
    if sh.has_text_frame and nv is not None and "classification" in etree.tostring(nv).decode():
        sh.text_frame._txBody.find(qn("a:bodyPr")).set("wrap", "none")
        sh.width = Inches(1.4)
sldIdLst = prs.slides._sldIdLst
for sldId in list(sldIdLst):
    prs.part.drop_rel(sldId.rId)
    sldIdLst.remove(sldId)
L_TITLE, L_CONTENT = prs.slide_layouts[0], prs.slide_layouts[1]
SLDNUM_SP = [sh for sh in L_CONTENT.placeholders if sh.placeholder_format.idx == 4][0]._element


def ph(slide, idx):
    return [p for p in slide.placeholders if p.placeholder_format.idx == idx][0]


def style_run(r, size=None, bold=None, color=None, italic=None):
    f = r.font
    f.name = FONT
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    if color is not None: f.color.rgb = color
    rPr = r._r.get_or_add_rPr()
    for e in rPr.findall(qn("a:ea")):
        rPr.remove(e)
    etree.SubElement(rPr, qn("a:ea")).set("typeface", FONT_ZH)


def set_runs(tf, text_, size=None, bold=None, color=None):
    p = tf.paragraphs[0]
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    r = p.add_run()
    r.text = text_
    style_run(r, size, bold, color)


def bullet(p, indent=0.2):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent))))
    pPr.set("indent", str(-int(Inches(indent))))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for e in pPr.findall(qn(tag)):
            pPr.remove(e)
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", FONT)
    etree.SubElement(pPr, qn("a:buChar")).set("char", "•")


def no_bullet(p):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", "0"); pPr.set("indent", "0")
    etree.SubElement(pPr, qn("a:buNone"))


def plain_shape(slide, kind, x, y, w, h, fill, line=None, line_w=1.5, dash=False):
    """A shape with a flat fill and either no outline or a `line`-coloured one (no theme style)."""
    sh = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    st = sh._element.find(qn("p:style"))
    if st is not None:
        sh._element.remove(st)
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(line_w)
        if dash:
            from pptx.enum.dml import MSO_LINE
            sh.line.dash_style = MSO_LINE.DASH
    return sh


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.0, fill=None, line=None, dash=False):
    if fill is not None or line is not None:
        box = plain_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h, fill, line, dash=dash)
    else:
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(min(margin, 0.1)) if margin else 0
    tf.vertical_anchor = anchor
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        bullet(p) if pd.get("bullet") else no_bullet(p)
        p.alignment = pd.get("align", PP_ALIGN.LEFT)
        p.space_after = Pt(pd.get("after", 0))
        for t, o in pd.get("runs") or [(pd["t"], {})]:
            r = p.add_run(); r.text = t
            style_run(r, o.get("size", pd.get("size", 16)), o.get("bold", pd.get("bold", False)),
                      o.get("color", pd.get("color", CHAR)), o.get("italic", pd.get("italic", False)))
    return box


# Status tags: what kind of statement each slide makes (point 3 of the direction: tested vs future).
TAGS = {"scope": ("CURRENT PROJECT SCOPE", CHAR), "tested": ("TESTED · DEVELOPMENT SET", CHAR),
        "future": ("FUTURE POSSIBILITY", RED), "open": ("OPEN REQUIREMENT", RED), "appendix": ("APPENDIX", GREY_TXT)}


def content_slide(title, message, notes, tag=None):
    s = prs.slides.add_slide(L_CONTENT)
    for idx in (15, 16):
        e = ph(s, idx)._element; e.getparent().remove(e)
    s.shapes._spTree.append(copy.deepcopy(SLDNUM_SP))
    t = ph(s, 10)
    t.left, t.top, t.width, t.height = Inches(X0), Inches(0.55), Inches(9.6 if tag else 12.2), Inches(0.62)
    if tag:
        label, colour = TAGS[tag]
        pill = plain_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 10.25, 0.66, 2.69, 0.36, WHITE, line=colour, line_w=1.25)
        tf = pill.text_frame
        tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = C
        r = p.add_run(); r.text = label; style_run(r, 10.5, True, colour)
    t.text_frame.margin_left = 0
    set_runs(t.text_frame, title, size=28, bold=True, color=CHAR)
    text(s, X0, 1.22, XW, 0.5, [dict(t=message, size=17, color=RED)])
    s.notes_slide.notes_text_frame.text = notes
    return s


def note(s, t, y):
    text(s, X0, y, 11.6, 0.32, [dict(t=t, size=11, color=GREY_TXT, italic=True)])


def strip(s, label, body, y, h=0.55, size=13.5):
    """A full-width callout: bold red label + body, white with a red outline."""
    return text(s, X0, y, XW, h, [dict(runs=[(label, dict(bold=True, color=RED)), (body, {})], size=size)],
                anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)


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
            etree.SubElement(sf, qn("a:srgbClr")).set("val", color)
        else:
            ln.set("w", "0"); etree.SubElement(ln, qn("a:noFill"))
    for f in [e for e in tcPr if e.tag in (qn("a:solidFill"), qn("a:noFill"))]:
        tcPr.remove(f); tcPr.append(f)


def fill_cell(cell, paras, fill=None, anchor=MSO_ANCHOR.MIDDLE):
    tf = cell.text_frame
    tf.word_wrap = True
    cell.margin_left = cell.margin_right = Inches(0.1)
    cell.margin_top = cell.margin_bottom = Inches(0.04)
    cell.vertical_anchor = anchor
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = pd.get("align", PP_ALIGN.LEFT)
        p.space_after = Pt(pd.get("after", 0))
        for t, o in pd.get("runs") or [(pd["t"], {})]:
            r = p.add_run(); r.text = t
            style_run(r, o.get("size", pd.get("size", 14)), o.get("bold", pd.get("bold", False)),
                      o.get("color", pd.get("color", CHAR)), o.get("italic", pd.get("italic", False)))
    if fill is None:
        cell.fill.background()
    else:
        cell.fill.solid(); cell.fill.fore_color.rgb = fill


def table(s, x, y, col_w, row_h):
    tbl = s.shapes.add_table(len(row_h), len(col_w), Inches(x), Inches(y), Inches(sum(col_w)),
                             Inches(sum(row_h))).table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0"); tblPr.set("bandRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for i, rh in enumerate(row_h):
        tbl.rows[i].height = Inches(rh)
    return tbl


def header_row(tbl, heads, size=13, align=None, fill=CHAR):
    for c, hd in enumerate(heads):
        fill_cell(tbl.cell(0, c), [dict(t=hd, size=size, bold=True, color=WHITE,
                                        align=(align[c] if align else PP_ALIGN.LEFT))],
                  fill=fill[c] if isinstance(fill, list) else fill)
        cell_border(tbl.cell(0, c), sides="")


def picture(s, path, x, y, max_w, max_h):
    """Fit the image in the box, centred."""
    with Image.open(path) as im:
        ar = im.width / im.height
    w, h = (max_w, max_w / ar) if max_w / ar <= max_h else (max_h * ar, max_h)
    pic = s.shapes.add_picture(str(path), Inches(x + (max_w - w) / 2), Inches(y + (max_h - h) / 2),
                               Inches(w), Inches(h))
    pic.line.color.rgb = RGBColor(0xBF, 0xBF, 0xBF)
    pic.line.width = Pt(0.75)
    return pic


def bar_chart(s, x, y, w, h, cats, values, colours):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("Accuracy", values)
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.font.name, ch.font.size, ch.font.color.rgb = FONT, Pt(12), CHAR
    ch.has_title = False
    ch.has_legend = False
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale, va.has_major_gridlines, va.visible = 0, 100, False, False
    ca = ch.category_axis
    ca.format.line.color.rgb = PALE
    ca.tick_labels.font.size = Pt(12)
    plot = ch.plots[0]
    plot.gap_width = 60
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = '0.0"%"', False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.bold = Pt(16), True
    ser = plot.series[0]
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = colours[-1]
    for i, col in enumerate(colours):
        pt = ser.points[i].format.fill
        pt.solid(); pt.fore_color.rgb = col
    return ch


def number_box(s, x, y, n, size=15, fill=RED, w=0.42, h=0.42):
    text(s, x, y, w, h, [dict(t=str(n), size=size, bold=True, color=WHITE, align=C)], anchor=MSO_ANCHOR.MIDDLE,
         fill=fill)


DATASET = f"a small development set of {N_RECEIPTS} receipts, mainly fictional mock receipts"
SOURCE = ("Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved "
          "(summary.csv, detail.csv) and the saved extraction results.")
METHOD_NOTE = ("Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese "
               "labels, written after these receipts were examined and fixed before scoring. The AI instructions were "
               "refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to "
               "validate. " + SOURCE)

# ===================================================================== cover
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Medical Receipt Data Extraction for Internal Audit")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(X0), Inches(4.9), Inches(6.6), Inches(0.9)
set_runs(sub.text_frame, "Turning medical receipts into structured, reusable audit data")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = "Proposed approach, evidence and next steps"; style_run(r)
s.notes_slide.notes_text_frame.text = (
    "This deck explains the receipt-data problem, the proposed extraction solution, the value it could bring to "
    "Internal Audit, why we prefer the AI approach, and how the solution and later audit tests would be governed. "
    "The current priority is reliable extraction of important receipt information into structured data. "
    "Downstream audit tests are possible later uses of that data, not the current scope.")

# ===================================================================== 1. problem and solution
s = content_slide(
    "The Problem and Our Proposed Solution",
    "Build a reliable receipt-data extraction layer so auditors can use receipt information at greater scale.",
    "Problem: important information is locked inside unstructured medical receipts. Business auditors read sampled "
    "receipts by hand and compare them with the claims system, which limits how many receipts can be reviewed. "
    "Solution: Azure Document Intelligence reads the receipt; Azure OpenAI identifies the audit-relevant fields and "
    "returns them in a fixed structure; the structured data is exported for later audit testing and analysis. The "
    "current project covers reading, extraction and structured export. Audit tests that use the data are a later "
    "stage.", tag="scope")
text(s, X0, 1.95, 5.85, 0.45, [dict(t="The problem", size=18, bold=True, color=CHAR)], anchor=MSO_ANCHOR.MIDDLE)
for k, body in enumerate(["Important information is locked inside unstructured medical receipts.",
                          "Business auditors read sampled receipts by hand and compare them with the claims "
                          "system.",
                          "Manual extraction limits how many receipts can be reviewed."]):
    text(s, X0, 2.5 + k * 1.0, 5.85, 0.88, [dict(t=body, size=15)], anchor=MSO_ANCHOR.MIDDLE, margin=0.22,
         fill=LIGHT)
text(s, 6.5, 1.95, 6.44, 0.45, [dict(t="Proposed solution", size=18, bold=True, color=RED)], anchor=MSO_ANCHOR.MIDDLE)
for k, (head_, body) in enumerate([("Read", "Azure Document Intelligence (DI) reads the receipt text and layout."),
                                   ("Extract", "Azure OpenAI identifies the audit-relevant fields and returns them in "
                                               "a fixed structure."),
                                   ("Export", "The structured data is exported for later audit testing and "
                                              "analysis.")]):
    y = 2.5 + k * 1.0
    number_box(s, 6.5, y, k + 1, size=20, w=0.6, h=0.88)
    text(s, 7.18, y, 5.76, 0.88, [dict(runs=[(head_ + ": ", dict(bold=True, color=RED)), (body, {})], size=15)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=RED_TINT)
strip(s, "Current focus: ", "reliable extraction and structured export. Audit tests that use the data are a "
                            "later stage.", 5.62)

# ===================================================================== 2. business value
s = content_slide(
    "What Reliable Receipt Data Could Bring",
    "Structured receipt data can widen coverage, reduce manual work and support new audit tests.",
    "Four areas of potential value. Broader coverage: move from a limited sample toward population-scale screening of "
    "the available and supported receipts. Improved efficiency: less manual reading, field identification and "
    "transcription, so auditors spend more time on exceptions and judgement. Automation of manual testing: "
    "structured receipt fields can later be compared automatically with claims-system and policy data. Additional "
    "insight: duplicate screening, practitioner checks, pattern analysis and other future tests. These are potential "
    "benefits: none has been measured yet, and the data does not provide full audit assurance. Auditors keep "
    "responsibility for judgement and conclusions.", tag="future")
VALUE = [("Broader coverage", "Move from a limited manual sample toward population-scale screening of available, "
                              "supported receipts."),
         ("Improved efficiency", "Less manual reading, field identification and transcription. More auditor time "
                                 "for exceptions and judgement."),
         ("Automation of manual testing", "Structured fields can later be compared automatically with claims-system "
                                          "and policy data."),
         ("Additional insight", "Supports duplicate screening, practitioner checks, pattern analysis and other future "
                                "tests.")]
for k, (head_, body) in enumerate(VALUE):
    x, y = X0 + (k % 2) * 6.375, 1.95 + (k // 2) * 1.75
    number_box(s, x, y, k + 1, size=22, w=0.75, h=1.6)
    text(s, x + 0.75, y, 5.425, 1.6, [dict(t=head_, size=18, bold=True, after=6), dict(t=body, size=14.5)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.25, fill=LIGHT)
strip(s, "Potential, not yet measured. ", "Auditors keep responsibility for judgement and conclusions.", 5.62)

# ===================================================================== 3. current limitations
s = content_slide(
    "Why the Current Process Does Not Scale",
    "The bottleneck is access to receipt data, not auditor effort.",
    "Today business auditors review a limited sample of receipts; around 25 is used here only as an illustrative "
    "example, not a confirmed audit sample size. Receipt formats vary across clinics, hospitals, practitioners, "
    "languages and layouts. Auditors identify the practitioner, patient, treatment date, diagnosis, treatment items "
    "and amount by hand, which is repetitive and time-consuming. The information stays unstructured and hard to "
    "reuse, and small samples limit cross-claim and population-level analysis. This is a data-access and "
    "scalability problem, not a criticism of the auditors' work.")
text(s, X0, 1.95, 3.7, 3.55, [dict(t="~25", size=60, bold=True, color=WHITE, after=2),
                              dict(t="receipts in a manual sample", size=18, bold=True, color=WHITE, after=14),
                              dict(t="Illustrative example only, not a confirmed audit sample size.", size=12.5,
                                   color=WHITE, italic=True)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.3, fill=RED)
LIMITS = [("Limited sample", "Only a small number of receipts can be read and checked by hand."),
          ("Varied formats", "Clinics, hospitals and practitioners use different languages, labels and layouts."),
          ("Manual identification", "Practitioner, patient, treatment date, diagnosis, treatment items and amount "
                                    "are found by eye."),
          ("Repetitive work", "The same reading and transcription is repeated for each receipt and procedure."),
          ("Not reusable", "Receipt information stays unstructured, so cross-claim and population analysis is "
                           "hard.")]
for k, (head_, body) in enumerate(LIMITS):
    y = 1.95 + k * 0.72
    text(s, 4.35, y, 8.59, 0.64, [dict(runs=[(head_ + ":  ", dict(bold=True)), (body, {})], size=14.5)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=LIGHT)
strip(s, "In short: ", "this is a data-access and scalability problem. Structured receipt data would let auditors "
                       "look further than a small sample.", 5.75)

# ===================================================================== 4. how AI changes the process
s = content_slide(
    "How AI Changes the Audit Process",
    "Extract once, then reuse the structured data across many audit tests.",
    "Future flow: medical receipts, then OCR (Azure Document Intelligence), then AI extraction (Azure OpenAI), then a "
    "structured receipt dataset that is exported. These first four steps, including the structured export, are the "
    "proposed extraction scope. Downstream audit testing and auditor review are a future stage. The table compares "
    "today's approach with what an AI-enabled approach could offer; the right-hand column describes potential, not "
    "results already achieved.")
FLOW = [("Medical receipts", "Images or PDFs", "scope"), ("OCR", "Azure DI reads the text", "scope"),
        ("AI extraction", "Azure OpenAI finds the fields", "scope"),
        ("Structured dataset", "Exported receipt data", "scope"),
        ("Audit testing", "Compare with claims and policy", "future"),
        ("Auditor review", "Exceptions and judgement", "future")]
W, G = 1.78, 0.374
text(s, X0, 1.85, 4 * W + 3 * G, 0.3, [dict(t="Proposed extraction scope", size=12.5, bold=True, color=RED, align=C)],
     anchor=MSO_ANCHOR.MIDDLE)
text(s, X0 + 4 * (W + G), 1.85, 2 * W + G, 0.3,
     [dict(t="Future stage (not being built now)", size=12.5, bold=True, color=GREY_TXT, align=C)],
     anchor=MSO_ANCHOR.MIDDLE)
for k, (head_, sub, kind) in enumerate(FLOW):
    x = X0 + k * (W + G)
    if kind == "scope":
        text(s, x, 2.2, W, 0.82, [dict(t=head_, size=13.5, bold=True, color=WHITE, align=C),
                                  dict(t=sub, size=10.5, color=WHITE, align=C)],
             anchor=MSO_ANCHOR.MIDDLE, margin=0.06, fill=RED if k < 3 else CHAR)
    else:
        text(s, x, 2.2, W, 0.82, [dict(t=head_, size=13.5, bold=True, color=GREY_TXT, align=C),
                                  dict(t=sub, size=10.5, color=GREY_TXT, align=C)],
             anchor=MSO_ANCHOR.MIDDLE, margin=0.06, fill=WHITE, line=MID_GREY, dash=True)
    if k < len(FLOW) - 1:
        text(s, x + W, 2.2, G, 0.82, [dict(t="→", size=18, bold=True, color=GREY_TXT, align=C)],
             anchor=MSO_ANCHOR.MIDDLE)
BEFORE_AFTER = [("Limited manual sample", "Potential population-scale receipt processing"),
                ("Manual reading and transcription", "Automated field extraction"),
                ("Receipt reviewed separately for each procedure", "Structured data reused across tests"),
                ("Auditor effort spent on normal and exceptional cases", "Greater focus on exceptions"),
                ("Limited cross-claim analysis", "Potential additional analytics and insights")]
tbl = table(s, X0, 3.3, [6.275, 6.275], [0.44] + [0.44] * len(BEFORE_AFTER))
header_row(tbl, ["Current approach", "AI-enabled approach"], size=14, fill=[CHAR, RED])
for i, (a, b) in enumerate(BEFORE_AFTER, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=a, size=14)], fill=LIGHT)
    fill_cell(tbl.cell(i, 1), [dict(t=b, size=14, bold=True)], fill=RED_TINT)
    for c in range(2):
        cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
note(s, "The current project covers extraction and structured export. Audit testing and review that use the data "
        "are a later stage.", y=6.0)

# ===================================================================== 5. benchmark results
s = content_slide(
    "Three Approaches Tested",
    f"{M3} was the most accurate approach on our development set.",
    f"We ran three approaches on the same {N_RECEIPTS} receipts and scored six fields: practitioner, registration "
    f"number, patient, receipt number, treatment date and total amount. Accuracy = correct fields out of "
    f"{APPLICABLE} ({N_RECEIPTS} receipts x 6 fields, less {NO_REG} receipts with no registration number). "
    + "; ".join(f"{n}: {OVERALL[n][0]}/{OVERALL[n][1]} ({PCT[(n, None)]})" for n in NAMES) + ". "
    f"The dataset is {DATASET}: seven fictional receipts printed and photographed with a phone, plus two sample "
    "receipts carried over from an earlier test round. The results are directional only and do not establish "
    "production accuracy. An independent and representative validation set is still required. Accuracy by field is "
    "in appendix A1. " + METHOD_NOTE, tag="tested")
bar_chart(s, X0, 1.85, 7.4, 4.1, [f"{n}\n{OVERALL[n][0]} of {OVERALL[n][1]} fields" for n in NAMES],
          tuple(round(100 * OVERALL[n][0] / OVERALL[n][1], 1) for n in NAMES), [MID_GREY, CHAR, RED])
for k, (n, how) in enumerate(zip(NAMES, ("Open-source text reading, then hand-written rules",
                                         "Azure text reading, then the same rules",
                                         "Azure text reading, then AI extraction"))):
    ai = k == 2
    text(s, 8.1, 1.95 + k * 0.82, 4.84, 0.72, [dict(t=n, size=14, bold=True, color=RED if ai else CHAR, after=2),
                                               dict(t=how, size=12, color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.18, fill=WHITE if ai else LIGHT, line=RED if ai else None)
text(s, 8.1, 4.45, 4.84, 1.5, [
    dict(t="How to read these results", size=13.5, bold=True, color=RED, after=4),
    dict(t=f"Measured on {DATASET}. Directional only: they do not establish production accuracy. An independent, "
           "representative validation set is still required.", size=12)],
    margin=0.18, fill=RED_TINT)

# ===================================================================== 6. receipt examples
EXAMPLES = [  # (receipt, field, heading, why it matters, crop anchors, highlight)
    ("receipt6", "doctor_name", "Who treated the patient?",
     "The rules took the referring doctor. The AI found the treating physiotherapist.",
     ["CLIENT", "PHYSIOTHERAPIST", "Referred by", "Dr. Kwok Man Hin", "Registered Physiotherapist", "PT004175"],
     ["Dr. Kwok Man Hin", "CHEUNG Hoi Ying"]),
    ("receipt6", "service_date", "Which date is the treatment?",
     "The rules took the date the receipt was issued, not the treatment date.",
     ["Receipt No. RCP-10388", "Date Issued", "Session Date", "Next Appointment"],
     ["Date Issued", "Session Date"]),
    ("receipt5", "total_amount", "What was actually charged?",
     "The rules took the amount before the 10% member discount.",
     ["Subtotal", "1,750.00", "Member discount", "-175.00", "Total 總額", "HK$1,575.00"],
     ["1,750.00", "HK$1,575.00"]),
]
assert any("Member discount 10%" in b[0] for b in di_blocks("receipt5")[1]), "receipt 5 discount label changed"
assert any(b[0] == "Date Issued 17 Jul 2026" for b in di_blocks("receipt6")[1])
assert any(b[0] == "Referred by" for b in di_blocks("receipt6")[1])
ex_rows = []
for rc, f, head_, why, needles, hl in EXAMPLES:
    gt = DETAIL[(M3, rc, f)]["ground_truth"]
    vals = [(n, *predicted(n, rc, f)) for n in NAMES]
    assert [ok for _, _, ok in vals] == [False, False, True], (rc, f, vals)
    crop = make_crop(rc, needles, f"crop_v15_{rc}_{f}", hl)
    ex_rows.append((rc, f, head_, why, crop, show(f, float(gt) if f == "total_amount" else gt),
                    [(n, show(f, v), ok) for n, v, ok in vals]))
assert ex_rows[0][6][0][1] == "Dr. Kwok Man Hin" and ex_rows[1][6][0][1] == "17 Jul 2026"
assert ex_rows[2][6][0][1] == "HK$1,750" and ex_rows[2][5] == "HK$1,575"

s = content_slide(
    "What the Differences Look Like on a Receipt",
    "Reading the text is not enough: extraction must understand what the text means.",
    "Three examples from the benchmark receipts. Receipt 6 (physiotherapy): both rule methods took the referring "
    "doctor, Dr. Kwok Man Hin, as the practitioner, and the date the receipt was issued (17 Jul 2026) as the treatment "
    "date; the AI returned the treating physiotherapist, CHEUNG Hoi Ying, and the session date, 16 Jul 2026. Receipt "
    "5 (dental): both rule methods returned HK$1,750, the amount before the 10% member discount; the AI returned the "
    "HK$1,575 actually charged. In each case the OCR read the text correctly; the difference is in understanding what "
    "the text means. Further detail for questions: on the same dental receipt PaddleOCR also misread labels (words "
    "run together, a wrong Chinese character), so the rules could not find the registration number, treatment date "
    "and receipt number; Azure DI read them correctly. The AI was not perfect: on receipt 9 (a vet invoice) the OCR "
    f"misread a clinician's name and the AI returned the misread name ({R9_AI}); on receipt 10 it returned the wrong "
    "date. Extracted values still need validation, especially missing, ambiguous or unsupported values. "
    + METHOD_NOTE, tag="tested")
CW, CG = 4.05, 0.2
for k, (rc, f, head_, why, crop, gt, vals) in enumerate(ex_rows):
    x = X0 + k * (CW + CG)
    text(s, x, 1.85, CW, 0.42, [dict(runs=[(f"{k + 1}  ", dict(color=RED)), (head_, {})], size=15, bold=True)],
         anchor=MSO_ANCHOR.MIDDLE)
    picture(s, crop, x, 2.3, CW, 1.45)
    tbl = table(s, x, 3.85, [2.1, 1.95], [0.34] * 4)
    fill_cell(tbl.cell(0, 0), [dict(t="Correct value", size=12, bold=True)], fill=LIGHT)
    fill_cell(tbl.cell(0, 1), [dict(t=gt, size=12.5, bold=True)], fill=LIGHT)
    for i, (n, v, ok) in enumerate(vals, start=1):
        fill_cell(tbl.cell(i, 0), [dict(t=n, size=11, color=GREY_TXT)])
        fill_cell(tbl.cell(i, 1), [dict(runs=[("✓ " if ok else "✗ ", dict(bold=True, color=GOOD if ok else RED)),
                                              (v, {})], size=12.5)], fill=GOOD_TINT if ok else BAD_TINT)
    for i in range(4):
        for c in range(2):
            cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
    text(s, x, 5.3, CW, 0.62, [dict(t=why, size=12.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.15, fill=WHITE,
         line=PALE)
note(s, "The AI is not perfect either: on one receipt it returned a practitioner name the OCR had misread, so "
        "extracted values still need validation.", y=6.05)

# ===================================================================== 7. trade-offs
s = content_slide(
    "Trade-offs and Scalability",
    "The AI approach is preferred, but no option is perfect.",
    "PaddleOCR + rules: low software dependency and transparent rules, but lower accuracy in the benchmark, more "
    "preprocessing, and rules that depend heavily on layout and wording. Azure DI + rules: stronger document reading, "
    "deterministic and explainable, but rules must be created and maintained as formats and labels change. Azure DI + "
    "Azure OpenAI: highest development-set accuracy, stronger contextual interpretation and less dependence on "
    "format-specific rules, but it requires prompt and schema governance, independent validation, monitoring, PII "
    "controls and Azure cost management; Azure prices are not yet confirmed. Scalability: rules-only approaches can "
    "require repeated maintenance for new receipt formats; contextual AI may adapt better to format variation, but it "
    "still needs controlled prompts, schemas, testing and monitoring. Alternative raised by management: OCR + regex + "
    "the doctor database. OCR reads the receipt and a regex search looks for registered doctor names (about 40,000 "
    "in the database); no match or several matches go to manual review. It is a simple, low-cost way to identify "
    "registered names and flag exceptions. It does not extract the other receipt fields (patient, dates, amounts, "
    "diagnosis), and it was not benchmarked.")
TRADE = [(M1, "Low software dependency; transparent rules",
          "Lower accuracy in the benchmark; more preprocessing; rules depend heavily on layout and wording"),
         (M2, "Stronger document reading; deterministic and explainable",
          "Rules must be created and maintained as formats and labels change"),
         (M3, "Highest development-set accuracy; stronger contextual interpretation; less dependence on "
              "format-specific rules",
          "Needs prompt and schema governance, independent validation, monitoring, PII controls and Azure cost "
          "management (prices to be confirmed)")]
tbl = table(s, X0, 1.85, [2.85, 4.55, 5.15], [0.42] + [0.72] * len(TRADE))
header_row(tbl, ["Approach", "Advantages", "Limitations"], size=13.5)
for i, (n, adv, lim) in enumerate(TRADE, start=1):
    ai = n == M3
    fill_cell(tbl.cell(i, 0), [dict(t=n, size=13.5, bold=True, color=RED if ai else CHAR)],
              fill=RED_TINT if ai else None)
    fill_cell(tbl.cell(i, 1), [dict(t=adv, size=12.5)], fill=RED_TINT if ai else None)
    fill_cell(tbl.cell(i, 2), [dict(t=lim, size=12.5)], fill=RED_TINT if ai else None)
    for c in range(3):
        cell_border(tbl.cell(i, c), sides="B")
text(s, X0, 4.5, XW, 0.72, [dict(runs=[("Scalability: ", dict(bold=True, color=RED)),
                                      ("rules-only approaches can require repeated maintenance for new receipt "
                                       "formats. Contextual AI may adapt better to format variation, but it still "
                                       "needs controlled prompts, schemas, testing and monitoring.", {})], size=13)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)
text(s, X0, 5.35, XW, 0.82, [
    dict(runs=[("Alternative raised: OCR + regex + doctor database  ", dict(bold=True)),
               ("(not benchmarked)", dict(italic=True, color=GREY_TXT))], size=13, after=3),
    dict(t="A simple, low-cost way to identify registered doctor names and flag no-match or multiple-match receipts "
           "for manual review. It does not extract the other receipt fields, such as patient, dates and amounts.",
         size=12.5)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=LIGHT)

# ===================================================================== 8. future audit tests
s = content_slide(
    "Future Audit Tests the Data Could Support",
    "Reliable extraction is the foundation for later tests. These tests are not being built now.",
    "Two kinds of possible future use. Tests of control or deterministic tests: required receipt information is "
    "present; the receipt amount matches the claimed amount; the treatment date matches the claims-system date; the "
    "service date falls within the policy period; the claim amount follows the approval-authority matrix. Red-flag "
    "tests: possible duplicate receipt; the practitioner cannot be matched or is ambiguous; diagnosis and treatment "
    "appear inconsistent; unusual claim, clinic, practitioner or receipt patterns. These downstream tests require "
    "separate business rules, internal data, validation and auditor review. An AI-generated red flag is not an "
    "audit finding. Diagnosis and treatment items were not part of the six-field benchmark, so they are not yet "
    "extracted or tested.", tag="future")
COLS = [("Possible tests of control (deterministic)", CHAR,
         ["Required receipt information is present", "Receipt amount matches the claimed amount",
          "Treatment date matches the claims-system date", "Service date falls within the policy period",
          "Claim amount follows the approval-authority matrix"]),
        ("Possible red-flag tests", RED,
         ["Possible duplicate receipt", "Practitioner cannot be matched or is ambiguous",
          "Diagnosis and treatment appear inconsistent", "Unusual claim, clinic, practitioner or receipt patterns"])]
for k, (head_, colour, items) in enumerate(COLS):
    x = X0 + k * 6.375
    text(s, x, 1.9, 6.175, 0.5, [dict(t=head_, size=15.5, bold=True, color=WHITE)], anchor=MSO_ANCHOR.MIDDLE,
         margin=0.22, fill=colour)
    text(s, x, 2.4, 6.175, 2.3, [dict(t=t, size=15.5, bullet=True, after=9) for t in items], margin=0.25,
         fill=LIGHT)
text(s, X0, 4.95, XW, 0.88, [
    dict(runs=[("Boundary: ", dict(bold=True, color=RED)),
               ("these tests need separate business rules, internal data, validation and auditor review. An "
                "AI-generated red flag is not an audit finding.", {})], size=13.5, after=3),
    dict(t="Diagnosis and treatment items are not yet extracted or tested.", size=12, color=GREY_TXT)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)

# ===================================================================== 9. governance, PII and platforms
s = content_slide(
    "Governance, PII Protection and Platform Design",
    "Run each activity on the platform best suited to its data, risk and control requirements.",
    "PII protection is a required design step, not a completed solution, and no masking method has been chosen. "
    "Decisions still to make: which receipt fields contain personal or sensitive medical information; which "
    "components need which fields (extraction may itself need names such as the patient and practitioner); the "
    "masking or redaction approach; how approved results stay linked to the correct audit record; and approved "
    "Azure services, access controls, retention and logging. Platform separation: reading, contextual extraction, "
    "PII controls, basic validation and structured export can run within the Azure application. Some downstream "
    "tests may need to run on another approved internal platform because they need internal data: claims-system "
    "records, policy coverage and benefit information, approval-authority tables, historical claims, and customer, "
    "provider, clinic or agent data. The transfer method between the two must be agreed and approved.", tag="open")
# zone A: Azure application
text(s, X0, 1.85, 7.3, 0.3, [dict(t="Azure application (proposed extraction scope)", size=12.5, bold=True, color=RED)],
     anchor=MSO_ANCHOR.MIDDLE)
ZA = [("Receipt", "Approved receipts"), ("Azure DI", "Reads the text"), ("Azure OpenAI", "Extracts the fields"),
      ("Structured output", "Validated, exported")]
ZW, ZG = 1.6, 0.3
for k, (head_, sub) in enumerate(ZA):
    x = X0 + k * (ZW + ZG)
    text(s, x, 2.2, ZW, 0.78, [dict(t=head_, size=13, bold=True, color=WHITE, align=C),
                               dict(t=sub, size=10.5, color=WHITE, align=C)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.05, fill=RED if k in (1, 2) else CHAR)
    if k < len(ZA) - 1:
        text(s, x + ZW, 2.2, ZG, 0.78, [dict(t="→", size=16, bold=True, color=GREY_TXT, align=C)],
             anchor=MSO_ANCHOR.MIDDLE)
text(s, X0, 3.06, 4 * ZW + 3 * ZG, 0.36,
     [dict(t="PII controls apply across these steps: design to be agreed", size=11.5, bold=True, color=RED,
           align=C)], anchor=MSO_ANCHOR.MIDDLE, fill=WHITE, line=RED, dash=True)
# transfer
TX = X0 + 4 * ZW + 3 * ZG
text(s, TX, 2.2, 0.55, 0.78, [dict(t="→", size=20, bold=True, color=RED, align=C)], anchor=MSO_ANCHOR.MIDDLE)
# zone B: internal platform
ZBX = TX + 0.55
ZBW = X0 + XW - ZBX
text(s, ZBX, 1.85, ZBW, 0.3, [dict(t="Approved internal platform (future stage)", size=12.5, bold=True,
                                   color=GREY_TXT)], anchor=MSO_ANCHOR.MIDDLE)
text(s, ZBX, 2.2, ZBW, 1.22, [dict(t="Join with internal data → audit tests → auditor review", size=13, bold=True,
                                   color=GREY_TXT, after=3),
                              dict(t="Claims, policy, approval-authority and historical data stay here.", size=11,
                                   color=GREY_TXT, after=3),
                              dict(t="Transfer from Azure: approved method to be agreed.", size=11, bold=True,
                                   color=RED)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.15, fill=WHITE, line=MID_GREY, dash=True)
# PII decisions and platform reasons
text(s, X0, 3.65, 6.175, 2.3, [
    dict(t="PII protection: decisions still to make", size=15, bold=True, color=RED, after=6),
    *[dict(t=t, size=13.5, bullet=True, after=4) for t in (
        "Which receipt fields contain personal or sensitive medical information",
        "Which components need which fields (extraction may need names)",
        "The masking or redaction method (not yet chosen)",
        "How results stay linked to the correct audit record",
        "Approved Azure services, access controls, retention and logging")]],
    margin=0.2, fill=RED_TINT)
text(s, X0 + 6.375, 3.65, 6.175, 2.3, [
    dict(t="Why some tests run on another platform", size=15, bold=True, color=CHAR, after=6),
    dict(t="They need internal data that does not belong in the extraction application:", size=13.5, after=4),
    *[dict(t=t, size=13.5, bullet=True, after=3) for t in (
        "Claims-system records", "Policy coverage and benefit information", "Approval-authority tables",
        "Historical claims; customer, provider, clinic or agent data")]],
    margin=0.2, fill=LIGHT)

# ===================================================================== 10. recommendation
STEPS = ["Finalise the required receipt fields and structured-output schema.",
         "Confirm the PII protection and data-flow design.",
         "Build an independent, representative validation dataset.",
         "Measure accuracy by field, including missing and ambiguous values.",
         "Define acceptance criteria for critical fields.",
         "Confirm which downstream tests run in Azure and which on other approved internal platforms."]
s = content_slide(
    "Recommendation and Next Steps",
    "Continue with Azure DI + Azure OpenAI as the preferred extraction approach.",
    "Recommendation: continue with Azure Document Intelligence plus Azure OpenAI as the preferred extraction approach, "
    "subject to independent validation and governance approval. First establish reliable, traceable receipt "
    "extraction. Then use the approved structured output to develop additional audit tests on the appropriate "
    "internal platforms. Next steps: " + " ".join(f"({i}) {t}" for i, t in enumerate(STEPS, 1)) + " "
    "Decision requested: agreement to continue on this basis and to proceed with these next steps.")
text(s, X0, 1.85, XW, 1.15, [
    dict(runs=[("Recommendation: ", dict(bold=True, color=RED)),
               ("continue with Azure DI + Azure OpenAI as the preferred extraction approach, subject to independent "
                "validation and governance approval.", dict(bold=True))], size=15, after=4),
    dict(t="First establish reliable, traceable receipt extraction. Then use the approved structured output to "
           "develop additional audit tests on the appropriate internal platforms.", size=13.5)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.22, fill=RED_TINT)
text(s, X0, 3.12, XW, 0.38, [dict(t="Next steps", size=15, bold=True)], anchor=MSO_ANCHOR.MIDDLE)
for k, t in enumerate(STEPS):
    x, y = X0 + (k // 3) * 6.375, 3.55 + (k % 3) * 0.86
    number_box(s, x, y, k + 1, size=17, w=0.6, h=0.76, fill=CHAR)
    text(s, x + 0.6, y, 5.575, 0.76, [dict(t=t, size=13.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.18, fill=LIGHT)

# ===================================================================== A1. accuracy by field
s = content_slide(
    "Appendix A1: Accuracy by Field",
    f"{M3} was the most accurate on every one of the six fields.",
    "Correct fields per field, from the saved results: " + "; ".join(
        f"{FIELD_NAMES[f]}: " + ", ".join(f"{n} {SCORES[(n, f)][0]}/{SCORES[(n, f)][1]}" for n in NAMES)
        for f in FIELDS) + f". The registration number is printed on {SCORES[(M3, 'registration_number')][1]} of the "
    f"{N_RECEIPTS} receipts. " + METHOD_NOTE, tag="appendix")
tbl = table(s, X0, 1.85, [3.1, 3.15, 3.15, 3.15], [0.5] + [0.45] * (len(FIELDS) + 1))
header_row(tbl, ["Field"] + list(NAMES), size=13.5, align=[PP_ALIGN.LEFT, C, C, C])
for i, f in enumerate(FIELDS + [None], start=1):
    total = f is None
    fill_cell(tbl.cell(i, 0), [dict(t="All fields" if total else FIELD_NAMES[f], size=14, bold=True)],
              fill=LIGHT if total else None)
    best = max(SCORES[(n, f)][0] / SCORES[(n, f)][1] for n in NAMES)
    for c, n in enumerate(NAMES, start=1):
        k, m = SCORES[(n, f)]
        top = k / m == best
        fill_cell(tbl.cell(i, c), [dict(runs=[(PCT[(n, f)], dict(size=15, bold=top or total,
                                                                  color=GOOD if top else CHAR)),
                                              (f"  ({k}/{m})", dict(size=11, color=GREY_TXT))], align=C)],
                  fill=GOOD_TINT if top else (LIGHT if total else None))
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B")
note(s, f"Measured on {DATASET}; directional only. Green = best for that field. The registration number is printed "
        f"on {SCORES[(M3, 'registration_number')][1]} of the {N_RECEIPTS} receipts.", y=5.65)

# ===================================================================== A2. how the benchmark was run
s = content_slide(
    "Appendix A2: How the Benchmark Was Run",
    "A small, controlled comparison to choose an extraction approach, not a production test.",
    "Dataset: seven fictional receipts printed and photographed with a phone (general practitioner, specialist, "
    "hospital, Chinese medicine, dental, physiotherapy and medical centre), plus two sample receipts carried over "
    "from an earlier test round (a vet invoice and a pharmacy receipt). A pharmacy till slip was not photographed and "
    "is not scored. All three approaches read the same image files. " + METHOD_NOTE, tag="appendix")
A2 = [("What was tested", [
          f"{DATASET[0].upper() + DATASET[1:]}: seven printed and photographed, two carried over from an earlier "
          "test round",
          "Six fields: practitioner, registration number, patient, receipt number, treatment date, total amount",
          f"{APPLICABLE} scored fields ({NO_REG} receipts have no registration number)",
          "The same receipt images for all three approaches"]),
      ("Why the results are directional", [
          "The rules were written after these receipts were examined (fixed before scoring)",
          "The AI instructions were refined after reviewing errors on these receipts",
          "Too few unseen receipts exist to validate any approach"]),
      ("Not yet tested", [
          "Diagnosis, treatment items and other receipt fields",
          "Real production receipts, handwriting and poor-quality images at volume",
          "The OCR + regex + doctor database alternative",
          "PII protection, cost and processing time at scale"])]
for k, (head_, items) in enumerate(A2):
    x = X0 + k * 4.25
    text(s, x, 1.9, 4.05, 3.75, [dict(t=head_, size=16, bold=True, color=RED if k == 1 else CHAR, after=8),
                                 *[dict(t=t, size=13.5, bullet=True, after=7) for t in items]],
         margin=0.22, fill=RED_TINT if k == 1 else LIGHT)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
