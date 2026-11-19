"""Generate the Version 16 medical receipt extraction deck (cover + 8 slides + 2 appendix) from the AIA template.

    python3 ppt/ocr_benchmark/scripts/generate_ppt_v16.py --force     (from the repository root)

Version 16 is a shorter version of Version 15 for senior management screening an AI innovation idea. The story:
we identified repetitive manual audit work, demonstrated a working Azure DI + Azure OpenAI receipt extraction
workflow, compared three approaches, and explored how structured receipt data could improve Internal Audit.
Manual-review figures (about 25 receipts per sample, 5 to 10 minutes per receipt) are the team's estimates; the
500 to 1,000 receipt target, broader fields, automated audit checks and time savings are future goals.

Figures: PaddleOCR + rules and Azure DI + rules = the multilingual rules baseline
(results/v2/scores_multilingual); Azure DI + Azure OpenAI = the refined-instruction run
(results/v2/scores_aoai_improved, aoai_v2_rows). Every figure, receipt example and the extracted output on main
slide 2 are read from the saved results and asserted at build time; receipt crops are placed with Azure DI text
positions. Nothing in the benchmark folder is written. generate_ppt_v15.py is kept unchanged to reproduce the
archived Version 15 deck.
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
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V16.pptx")
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


DATASET = f"{N_RECEIPTS} development receipts, mainly fictional mock receipts"
SOURCE = ("Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual and scores_aoai_improved "
          "(summary.csv, detail.csv) and the saved extraction results.")
METHOD_NOTE = ("Benchmark detail for questions: the two rule methods use the same general rules plus common Chinese "
               "labels, written after these receipts were examined and fixed before scoring. The AI instructions were "
               "refined after reviewing errors on these receipts. Only 4 unseen receipts exist, too few to "
               "validate. " + SOURCE)
TAGS.update({"estimate": ("ESTIMATES · NOT MEASURED", CHAR), "demo": ("WORKING DEMONSTRATION", CHAR),
             "dev": ("DEVELOPMENT RESULTS", CHAR), "future": ("FUTURE · NOT IMPLEMENTED", RED),
             "agree": ("TO BE AGREED", RED)})
# Manual-review estimates given by the team (not measured): receipts per sample and minutes per receipt.
SAMPLE, MIN_LO, MIN_HI = 25, 5, 10
HOURS_LO, HOURS_HI = SAMPLE * MIN_LO / 60, SAMPLE * MIN_HI / 60
assert (round(HOURS_LO), round(HOURS_HI)) == (2, 4)
TARGET = "500 to 1,000 receipts"


def make_full(receipt, name, max_px=1400):
    """The whole receipt: the image cropped to the area of all Azure DI text blocks, plus a margin."""
    img = receipt_image(receipt)
    page, blocks = di_blocks(receipt)
    if img.size != (page["width"], page["height"]):
        sys.exit(f"{receipt}: image {img.size} does not match the Azure DI page")
    m = int(0.03 * page["width"])
    box = (max(0, min(b[1] for b in blocks) - m), max(0, min(b[2] for b in blocks) - m),
           min(img.width, max(b[3] for b in blocks) + m), min(img.height, max(b[4] for b in blocks) + m))
    crop = img.crop(box)
    crop.thumbnail((max_px, max_px))
    path = ASSETS / f"{name}.jpg"
    crop.save(path, quality=90)
    return path


# ===================================================================== cover
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "AI-Assisted Medical Receipt Extraction")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(X0), Inches(4.9), Inches(6.6), Inches(0.9)
set_runs(sub.text_frame, "An Internal Audit AI innovation idea")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = "What we built, what we tested and where it could go"; style_run(r)
s.notes_slide.notes_text_frame.text = (
    "This is an AI innovation idea from our team. We identified repetitive manual audit work, demonstrated a working "
    "receipt extraction workflow with Azure Document Intelligence and Azure OpenAI, compared three approaches, and "
    "explored how structured receipt data could improve Internal Audit. We are sharing what we built and learned "
    "and its potential value; this is an exploration, not a finished product.")

# ===================================================================== 1. the problem
s = content_slide(
    "The Problem: Manual Receipt Reviews Take Time",
    "Reading receipts by hand takes auditor time, which limits how many claims we can cover.",
    f"For each audit sample, business auditors review around {SAMPLE} receipts by hand. Each receipt takes an "
    f"estimated {MIN_LO} to {MIN_HI} minutes, roughly {HOURS_LO:.0f} to {HOURS_HI:.0f} hours of reading per sample "
    f"({SAMPLE} x {MIN_LO}-{MIN_HI} minutes). These are the team's estimates, not measured figures. The checks come "
    "from the business auditor checklist: authenticity (letterhead with the provider's legal name, address and "
    "registration or licence number; signature and company stamp; no unauthorised alteration); data integrity "
    "(claimant name, provider name, treatment date, diagnosis code, receipt amount and claimed amount against the "
    "claims system); coverage (date of service within the policy period, diagnosis within coverage, charges within "
    "agreed fees); and fraud, waste and abuse indicators such as duplicate receipts by receipt number, treatment date, "
    "amount and provider. The bottleneck is auditor time and effort, which keeps coverage to a small sample.",
    tag="estimate")
text(s, X0, 1.9, 4.0, 3.65, [
    dict(t=f"~{SAMPLE}", size=54, bold=True, color=WHITE), dict(t="receipts per sample", size=17, bold=True,
                                                                 color=WHITE, after=14),
    dict(t=f"{MIN_LO}–{MIN_HI} min", size=40, bold=True, color=WHITE),
    dict(t="per receipt", size=17, bold=True, color=WHITE, after=14),
    dict(t=f"≈ {HOURS_LO:.0f}–{HOURS_HI:.0f} hours of reading per sample. Team estimates, not measured.", size=12.5,
         color=WHITE, italic=True)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.3, fill=RED)
text(s, 4.65, 1.9, 8.29, 0.42, [dict(runs=[("What auditors check on each receipt", dict(bold=True)),
                                          ("   from the business auditor checklist", dict(size=12, color=GREY_TXT,
                                                                                         italic=True))], size=16)],
     anchor=MSO_ANCHOR.MIDDLE)
CHECKS = [("Authenticity", "Letterhead, provider registration number, signature and stamp"),
          ("Data integrity", "Claimant, provider, treatment date, diagnosis and amounts vs the claims system"),
          ("Coverage", "Service date within the policy period; diagnosis covered; charges within agreed fees"),
          ("Fraud indicators", "Duplicate receipts by receipt number, treatment date, amount and provider")]
for k, (head_, body) in enumerate(CHECKS):
    y = 2.4 + k * 0.82
    text(s, 4.65, y, 8.29, 0.72, [dict(runs=[(head_ + ":  ", dict(bold=True)), (body, {})], size=14.5)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=LIGHT)
strip(s, "The bottleneck: ", "auditor time and effort. Reading each receipt by hand keeps coverage to a small "
                             "sample.", 5.75, h=0.5)

# ===================================================================== 2. solution and value
DEMO = "receipt8"
demo_rows = []
for f in FIELDS:
    v, ok = predicted(M3, DEMO, f)
    assert ok, (DEMO, f)
    demo_rows.append((FIELD_NAMES[f], show(f, float(v) if f == "total_amount" else v)))
assert DETAIL[(M3, DEMO, "total_amount")]["ground_truth"] in ("795", "795.0", "795.00")
demo_text = json.loads((RES / RUNS[M3][2] / f"{DEMO}.json").read_text())["input_text"]
assert "Nurse" in demo_text and "Covered by plan" in demo_text  # distractors named in the notes
demo_img = make_full(DEMO, "full_v16_receipt8")

s = content_slide(
    "Our AI Solution and Business Value",
    "We built a working workflow that turns a receipt photo into structured data.",
    "The workflow runs today on our benchmark receipts: Azure Document Intelligence reads the receipt text and "
    "layout, Azure OpenAI selects the audit-relevant fields, and the result is structured data. The example is "
    "benchmark receipt 8, a fictional bilingual medical-centre receipt that was printed and photographed. The output "
    "shown is the saved extraction result; all six fields match the ground truth. The receipt also names a nurse "
    "and an amount covered by the health plan; the AI returned the attending doctor and the receipt total. "
    "Potential benefits: less manual reading and transcription, wider coverage than a small sample, and data that "
    f"can be reused across audit tests. Our initial future target is {TARGET} and more fields from the auditor "
    "checklist, such as diagnosis, clinic name and itemised charges. That target has not been demonstrated; so far "
    f"the workflow has been run on {N_RECEIPTS} development receipts for six fields.", tag="demo")
FLOW2 = [("Receipt photo", LIGHT, CHAR), ("Azure DI reads the text", RED, WHITE),
         ("Azure OpenAI selects the fields", RED, WHITE), ("Structured data", CHAR, WHITE)]
FW, FG = 2.85, 0.383
for k, (t_, fill, colour) in enumerate(FLOW2):
    x = X0 + k * (FW + FG)
    text(s, x, 1.85, FW, 0.5, [dict(t=t_, size=13, bold=True, color=colour, align=C)], anchor=MSO_ANCHOR.MIDDLE,
         fill=fill)
    if k < len(FLOW2) - 1:
        text(s, x + FW, 1.85, FG, 0.5, [dict(t="→", size=18, bold=True, color=GREY_TXT, align=C)],
             anchor=MSO_ANCHOR.MIDDLE)
picture(s, demo_img, X0, 2.55, 2.75, 2.75)
text(s, X0 + 2.8, 3.6, 0.4, 0.5, [dict(t="→", size=22, bold=True, color=RED, align=C)], anchor=MSO_ANCHOR.MIDDLE)
tbl = table(s, 3.6, 2.55, [1.75, 2.35], [0.41] + [0.39] * len(demo_rows))
header_row(tbl, ["Extracted output", ""], size=13)
for i, (lab, v) in enumerate(demo_rows, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=lab, size=12, color=GREY_TXT)], fill=LIGHT)
    fill_cell(tbl.cell(i, 1), [dict(t=v, size=13, bold=True)], fill=LIGHT)
    for c in range(2):
        cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
note(s, "Benchmark receipt 8 (fictional) and its saved output.", y=5.38)
BEN = [("Less manual work", "Less reading and retyping of receipt details by hand."),
       ("Wider coverage", "Check far more receipts than a small manual sample."),
       ("Reusable data", "The same structured data can feed many audit tests.")]
for k, (head_, body) in enumerate(BEN):
    y = 2.55 + k * 0.94
    text(s, 8.0, y, 4.94, 0.84, [dict(t=head_, size=15, bold=True, color=RED, after=2), dict(t=body, size=12.5)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=RED_TINT)
strip(s, "Initial future target: ", f"{TARGET} and more fields from the auditor checklist. Not yet demonstrated.",
      5.7, h=0.5)

# ===================================================================== 3. three approaches
s = content_slide(
    "Three Approaches Tested",
    f"{M3} was the most accurate of the three approaches.",
    f"We ran three approaches on the same {N_RECEIPTS} receipts and scored six fields: practitioner, registration "
    f"number, patient, receipt number, treatment date and total amount. Accuracy = correct fields out of "
    f"{APPLICABLE} ({N_RECEIPTS} receipts x 6 fields, less {NO_REG} receipts with no registration number). "
    + "; ".join(f"{n}: {OVERALL[n][0]}/{OVERALL[n][1]} ({PCT[(n, None)]})" for n in NAMES) + ". "
    "These are development results from nine receipts, mainly fictional mock receipts: seven printed and "
    "photographed, two carried over from an earlier test round. They are not production accuracy. Accuracy by "
    "field is in appendix A1. " + METHOD_NOTE, tag="dev")
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
    dict(t="Development results, not production accuracy", size=13.5, bold=True, color=RED, after=4),
    dict(t=f"Measured on {DATASET}. Accuracy on new, representative receipts still needs independent "
           "validation.", size=12.5)],
    margin=0.18, fill=RED_TINT)

# ===================================================================== 4. why AI
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
    "Why AI Instead of OCR and Rules?",
    "OCR reads the text; AI uses the context to pick the correct field.",
    "Three examples from the benchmark receipts. Receipt 6 (physiotherapy): both rule methods took the referring "
    "doctor, Dr. Kwok Man Hin, as the practitioner, and the date the receipt was issued (17 Jul 2026) as the treatment "
    "date; the AI returned the treating physiotherapist, CHEUNG Hoi Ying, and the session date, 16 Jul 2026. Receipt "
    "5 (dental): both rule methods returned HK$1,750, the amount before the 10% member discount; the AI returned the "
    "HK$1,575 actually charged. In each case the text was read correctly; the difference is understanding what the "
    "text means. On the same dental receipt PaddleOCR also misread several labels, so the rules missed further "
    "fields; Azure DI read them correctly. The AI also makes mistakes: on receipt 9 (a vet invoice) the OCR misread a "
    f"clinician's name and the AI returned the misread name ({R9_AI}); on receipt 10 it returned the wrong date. "
    "Extracted values still need validation. " + METHOD_NOTE, tag="dev")
CW, CG = 4.05, 0.2
for k, (rc, f, head_, why, crop, gt, vals) in enumerate(ex_rows):
    x = X0 + k * (CW + CG)
    text(s, x, 1.85, CW, 0.42, [dict(runs=[(f"{k + 1}  ", dict(color=RED)), (head_, {})], size=15, bold=True)],
         anchor=MSO_ANCHOR.MIDDLE)
    picture(s, crop, x, 2.3, CW, 1.3)
    tbl = table(s, x, 3.68, [2.1, 1.95], [0.34] * 4)
    fill_cell(tbl.cell(0, 0), [dict(t="Correct value", size=12, bold=True)], fill=LIGHT)
    fill_cell(tbl.cell(0, 1), [dict(t=gt, size=12.5, bold=True)], fill=LIGHT)
    for i, (n, v, ok) in enumerate(vals, start=1):
        fill_cell(tbl.cell(i, 0), [dict(t=n, size=11, color=GREY_TXT)])
        fill_cell(tbl.cell(i, 1), [dict(runs=[("✓ " if ok else "✗ ", dict(bold=True, color=GOOD if ok else RED)),
                                              (v, {})], size=12.5)], fill=GOOD_TINT if ok else BAD_TINT)
    for i in range(4):
        for c in range(2):
            cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
    text(s, x, 5.08, CW, 0.55, [dict(t=why, size=12.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.15, fill=WHITE,
         line=PALE)
strip(s, "AI can also make mistakes: ", "on one receipt it returned a doctor's name the OCR had misread. "
                                        "Extracted values still need checking.", 5.75, h=0.48, size=13)

# ===================================================================== 5. advantages, limitations, alternatives
s = content_slide(
    "Advantages, Limitations and Alternatives",
    "Each approach has trade-offs; AI handled varied receipts best in our test.",
    "PaddleOCR + rules runs in-house with transparent rules, but was the least accurate in our test and its rules "
    "break when layouts or labels change. Azure DI + rules reads text better and gives predictable, explainable "
    "results, but the rules must be written and maintained for each new receipt format. Azure DI + Azure OpenAI was "
    "the most accurate and uses context, with fewer format-specific rules, but it can still make mistakes and needs "
    "validation, monitoring and confirmed Azure costs (prices not yet confirmed). Alternative: OCR + regex + the "
    "doctor database. OCR reads the receipt and a regex search looks for registered doctor names (about 40,000 in "
    "the database); no match or several matches go to manual review. It is a feasible, low-cost way to match "
    "registered doctor names and flag exceptions, but it does not extract the other receipt fields, and it was not "
    "benchmarked.")
TRADE = [(M1, "Runs in-house; transparent rules",
          "Least accurate in our test; rules break when layouts or labels change"),
         (M2, "Better text reading; predictable, explainable results",
          "Rules must be written and maintained for each new receipt format"),
         (M3, "Most accurate in our test; uses context; fewer format-specific rules",
          "Can still make mistakes; needs validation, monitoring and confirmed costs")]
tbl = table(s, X0, 1.9, [3.05, 4.6, 4.9], [0.46] + [0.78] * len(TRADE))
header_row(tbl, ["Approach", "Advantages", "Limitations"], size=14)
for i, (n, adv, lim) in enumerate(TRADE, start=1):
    ai = n == M3
    fill_cell(tbl.cell(i, 0), [dict(t=n, size=14, bold=True, color=RED if ai else CHAR)],
              fill=RED_TINT if ai else None)
    fill_cell(tbl.cell(i, 1), [dict(runs=[("+ ", dict(bold=True, color=GOOD)), (adv, {})], size=14)],
              fill=RED_TINT if ai else None)
    fill_cell(tbl.cell(i, 2), [dict(runs=[("− ", dict(bold=True, color=RED)), (lim, {})], size=14)],
              fill=RED_TINT if ai else None)
    for c in range(3):
        cell_border(tbl.cell(i, c), sides="B")
text(s, X0, 4.85, XW, 1.05, [
    dict(runs=[("Feasible alternative: OCR + regex + doctor database  ", dict(bold=True)),
               ("(not benchmarked)", dict(italic=True, color=GREY_TXT))], size=14.5, after=4),
    dict(t="Matches registered doctor names and flags no-match or multiple-match receipts for manual review. "
           "It does not extract the other receipt fields, such as patient, dates and amounts.", size=13.5)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.22, fill=LIGHT)

# ===================================================================== 6. future audit analytics
s = content_slide(
    "Future Audit Analytics",
    "Extracted receipt data could support practical audit tests later.",
    "Examples that use extracted receipt information, drawn from the business auditor checklist. Receipt amount "
    "versus the claimed amount. Treatment date versus the claim and the policy coverage period. Duplicate receipts: "
    "the same receipt number, treatment date, amount and provider across claims. Unusual provider fees: charges far "
    "from the usual range for a treatment. These tests would run later on another authorized internal platform, where "
    "the receipt data can be joined with claims and policy data. They are not implemented yet. Some need fields "
    "beyond the six we tested, such as clinic name and itemised charges. Any flag would still need auditor review "
    "before it supports a finding.", tag="future")
ANALYTICS = [("Receipt amount vs claim", "Does the claimed amount match the amount on the receipt?",
              "Receipt total, claimed amount"),
             ("Treatment dates", "Does the treatment date match the claim and fall within the policy period?",
              "Treatment date, claim and policy dates"),
             ("Duplicate receipts", "Has the same receipt been used for more than one claim?",
              "Receipt number, date, amount, provider"),
             ("Unusual provider fees", "Are charges far from the usual range for the treatment?",
              "Itemised charges, provider")]
for k, (head_, q, uses) in enumerate(ANALYTICS):
    x, y = X0 + (k % 2) * 6.375, 1.9 + (k // 2) * 1.68
    number_box(s, x, y, k + 1, size=20, w=0.65, h=1.52)
    text(s, x + 0.65, y, 5.525, 1.52, [dict(t=head_, size=16, bold=True, after=4), dict(t=q, size=13.5, after=4),
                                       dict(runs=[("Uses: ", dict(bold=True)), (uses, {})], size=11.5,
                                            color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.22, fill=LIGHT)
strip(s, "Later, on another authorized platform: ", "joined with claims data. Not implemented yet; any flag still "
                                                    "needs auditor review.", 5.4)
note(s, "Some tests need fields beyond the six tested, such as clinic name and itemised charges.", y=6.03)

# ===================================================================== 7. privacy and platform design
s = content_slide(
    "Privacy and Platform Design",
    "Only approved receipt data goes to Azure; claims, policy and historical records stay internal.",
    "Azure would process only approved receipt data: reading the receipt and extracting the fields. Claims records, "
    "policy information and historical data stay on another authorized internal platform, where any future audit "
    "analytics would run. Still to be agreed: how personal information is protected (no masking or redaction method "
    "has been chosen or approved), where data is stored and for how long, who can access it, and the approved "
    "method for transferring structured results between the two platforms.", tag="agree")
text(s, X0, 1.9, 6.0, 0.34, [dict(t="Azure: approved receipt data only", size=13.5, bold=True, color=RED)],
     anchor=MSO_ANCHOR.MIDDLE)
text(s, X0, 2.28, 6.0, 1.45, [dict(t="Receipt  →  Azure DI  →  Azure OpenAI  →  Structured data", size=13.5, bold=True,
                                   color=WHITE, align=C, after=4),
                              dict(t="Reads receipts and extracts the fields", size=12.5, color=WHITE, align=C)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.15, fill=RED)
text(s, 6.39, 2.28, 0.55, 1.45, [dict(t="→", size=24, bold=True, color=RED, align=C)], anchor=MSO_ANCHOR.MIDDLE)
text(s, 6.94, 1.9, 6.0, 0.34, [dict(t="Another authorized internal platform", size=13.5, bold=True, color=CHAR)],
     anchor=MSO_ANCHOR.MIDDLE)
text(s, 6.94, 2.28, 6.0, 1.45, [dict(t="Claims, policy and historical records", size=15, bold=True, color=WHITE,
                                     align=C, after=4),
                                dict(t="Future audit analytics would run here", size=12.5, color=WHITE, align=C)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.15, fill=CHAR)
text(s, X0, 4.0, XW, 0.38, [dict(t="Still to be agreed", size=15, bold=True)], anchor=MSO_ANCHOR.MIDDLE)
AGREE = [("PII protection", "Method not yet chosen or approved"), ("Storage", "Where data is kept, and for how long"),
         ("Access controls", "Who can see receipts and results"), ("Approved transfer", "How results move between "
                                                                                       "platforms")]
for k, (head_, body) in enumerate(AGREE):
    x = X0 + k * 3.18
    text(s, x, 4.45, 3.0, 1.3, [dict(t=head_, size=15, bold=True, color=RED, after=4), dict(t=body, size=13)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED, dash=True)

# ===================================================================== 8. conclusion
PRIORITIES = [("Expand receipt extraction", f"More fields from the auditor checklist, working toward {TARGET}."),
              ("Validate independently", "Test accuracy and practical time benefits on new, representative "
                                         "receipts."),
              ("Confirm privacy and platform design", "Agree PII protection, storage, access and the approved "
                                                      "transfer.")]
s = content_slide(
    "Conclusion and Next Steps",
    "A working AI extraction workflow, with clear next steps to test its value.",
    f"What we demonstrated: a working receipt extraction workflow with Azure Document Intelligence and Azure OpenAI, "
    f"and a comparison of three approaches on {N_RECEIPTS} development receipts, where the AI approach was the most "
    "accurate and handled context the rules missed. Why it matters: structured receipt data could reduce manual "
    "reading, widen coverage beyond a small sample, and be reused for audit analytics. What needs validation next: "
    + " ".join(f"({i}) {h}: {b}" for i, (h, b) in enumerate(PRIORITIES, 1)) + " Processing "
    f"{TARGET}, broader field extraction, automated audit checks and time savings are future goals, not yet "
    "demonstrated.")
for k, (head_, items, fill, colour) in enumerate([
        ("What we demonstrated", ["A working receipt-to-structured-data workflow",
                                  "Three approaches compared; AI was the most accurate",
                                  "AI handled context that fixed rules missed"], LIGHT, CHAR),
        ("Why it matters", ["Less manual reading of receipts", "Wider coverage than a small sample",
                            "Reusable data for future audit analytics"], LIGHT, CHAR)]):
    x = X0 + k * 6.375
    text(s, x, 1.85, 6.175, 1.6, [dict(t=head_, size=16, bold=True, color=colour, after=6),
                                   *[dict(t=t, size=15, bullet=True, after=4) for t in items]],
         margin=0.22, fill=fill)
text(s, X0, 3.65, XW, 0.38, [dict(t="Next priorities: what needs validation", size=15, bold=True, color=RED)],
     anchor=MSO_ANCHOR.MIDDLE)
for k, (head_, body) in enumerate(PRIORITIES):
    x = X0 + k * 4.25
    number_box(s, x, 4.1, k + 1, size=20, w=0.6, h=1.5)
    text(s, x + 0.6, 4.1, 3.45, 1.5, [dict(t=head_, size=14.5, bold=True, after=4), dict(t=body, size=12.5)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.18, fill=RED_TINT)

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
note(s, f"Development results from {N_RECEIPTS} receipts, mainly fictional mock receipts; not production accuracy. Green = best for that field. The "
        f"registration number is printed on {SCORES[(M3, 'registration_number')][1]} of the {N_RECEIPTS} receipts.",
     y=5.65)

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
      ("Future goals, not yet tested", [
          "More fields from the auditor checklist, such as diagnosis, clinic name and itemised charges",
          f"Processing {TARGET}",
          "Automated audit checks and time savings",
          "The OCR + regex + doctor database alternative"])]
for k, (head_, items) in enumerate(A2):
    x = X0 + k * 4.25
    text(s, x, 1.9, 4.05, 3.75, [dict(t=head_, size=16, bold=True, color=RED if k == 1 else CHAR, after=8),
                                 *[dict(t=t, size=13.5, bullet=True, after=7) for t in items]],
         margin=0.22, fill=RED_TINT if k == 1 else LIGHT)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
