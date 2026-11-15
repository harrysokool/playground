"""Generate the Version 13 Receipt OCR Benchmark deck (9 slides) from the AIA template.

    python3 ppt/ocr_benchmark/scripts/generate_ppt_v13.py --force     (from the repository root)

Version 13 = Version 12 with a new final slide on the business value (receipt data -> another authorized
platform -> potential data analytics tests); generate_ppt_v12.py is kept unchanged for the archived V12 deck.
Version 12 = Version 11 plus one slide on the doctor database proposal (slide 7). The deck is a simplified management deck:
which receipt extraction approach do we recommend, and why? Three method names only: PaddleOCR + Rules,
Azure DI + Rules, Azure DI + AOAI. Slides: title; summary (recommendation, no figures); overall accuracy
chart; accuracy by field; example 1 (receipt 5, PaddleOCR vs Azure DI text reading); example 2 (receipt 6,
rules vs AOAI); the doctor database proposal (not benchmarked; real and hypothetical edge cases);
advantages and disadvantages; business value (potential audit analytics, not implemented).

Figures: PaddleOCR + Rules and Azure DI + Rules = the multilingual rules baseline
(results/v2/scores_multilingual); Azure DI + AOAI = the refined-instruction run
(results/v2/scores_aoai_improved, aoai_v2_rows). Every figure and example value is read from the saved
results and asserted at build time. Limitation footnote: 9 test receipts; rules and AOAI instructions
developed with them; not independently validated. Technical details are kept to the speaker notes.
"""
import argparse
import copy
import csv
import json
import sys
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageOps
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent.parent
BENCH = REPO / "python" / "receipt_ocr_benchmark"
RES = BENCH / "results" / "v2"
ASSETS = PROJECT / "assets_v2"
PROTECTED = [PROJECT / d for d in ("archive", "template")]

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--template", type=Path, default=PROJECT / "template" / "aia_ppt_template.pptx")
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V13.pptx")
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
ORIG = {"light": "paddle_light_general", "di": "azure_di_general"}
IMPR = {"light": "paddle_light_improved", "di": "azure_di_improved"}
AOAI = "azure_di_aoai"
RESULT_DIR = {"paddle_light_general": "extracted_general_light", "paddle_light_improved": "extracted_improved_light",
              "azure_di_general": "extracted_general_azure_di", "azure_di_improved": "extracted_improved_azure_di",
              "azure_di_aoai": "di_aoai"}
FIELD_NAMES = {"doctor_name": "Doctor", "registration_number": "Reg. no.", "patient_name": "Patient",
               "receipt_number": "Receipt no.", "service_date": "Service date", "total_amount": "Total"}
FIELDS = list(FIELD_NAMES)

def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


# The historical scores_improved files also hold the discontinued PaddleOCR Heavy rows; they are not read.
SUM = {r["approach"]: r for r in read_csv(RES / "scores_improved" / "summary.csv") if r["approach"] in RESULT_DIR}
DETAIL = {(r["approach"], r["receipt"], r["field"]): r for r in read_csv(RES / "scores_improved" / "detail.csv")
          if r["approach"] in RESULT_DIR}
assert set(SUM) == set(RESULT_DIR), f"missing approaches in summary.csv: {sorted(set(RESULT_DIR) - set(SUM))}"
SUM_V2PROMPT = {r["approach"]: r for r in read_csv(RES / "scores_aoai_improved" / "summary.csv")}
AOAI_V2 = SUM_V2PROMPT["aoai_v2_rows"]
assert SUM_V2PROMPT["aoai_original"]["correct"] == SUM[AOAI]["correct"], "original AOAI result differs between files"
HELD = BENCH / "results" / "v1_heldout"
UNSEEN = ("receipt1", "receipt2", "receipt3", "receipt5")  # Version 1 receipts 4 and 6 = Version 2 receipts 9, 10
RECEIPTS = sorted({k[1] for k in DETAIL}, key=lambda s: int(s.replace("receipt", "")))
N_RECEIPTS, APPLICABLE = len(RECEIPTS), int(SUM[AOAI]["applicable"])
assert all(int(SUM[a]["applicable"]) == APPLICABLE for a in SUM)


def _row(a):
    return a if isinstance(a, dict) else SUM[a]


def acc(a):
    return f"{float(_row(a)['accuracy_pct']):.1f}%"


def count(a):
    return f"{int(_row(a)['correct'])}/{int(_row(a)['applicable'])}"


def secs(a):
    return f"{int(_row(a)['mean_ms_per_receipt']) / 1000:.1f} s"


def receipt_score(a, receipt):
    rows = [DETAIL[(a, receipt, f)] for f in FIELDS if DETAIL[(a, receipt, f)]["result"] in ("Correct", "Wrong")]
    return sum(r["result"] == "Correct" for r in rows), len(rows)


def json_value(approach, receipt, field):
    v = json.loads((RES / RESULT_DIR[approach] / f"{receipt}.json").read_text()).get(field)
    return "" if v is None else str(v)


def example(approach, receipt, field):
    """(value as extracted, correct?) from detail.csv, cross-checked against the extraction JSON."""
    row = DETAIL[(approach, receipt, field)]
    if json_value(approach, receipt, field) != row["predicted"]:
        sys.exit(f"Mismatch {approach} {receipt} {field}: detail.csv vs extraction JSON")
    return (row["predicted"] or "not found"), row["result"] == "Correct"


def truth(receipt, field):
    return DETAIL[(AOAI, receipt, field)]["ground_truth"]


def ocr_read(receipt, value, engines=("paddle_light", "azure_di")):
    """Stop the build unless every engine's raw OCR text contains `value` (backs 'the OCR read it')."""
    for e in engines:
        if value not in (RES / e / f"{receipt}.json").read_text():
            sys.exit(f"{e} OCR of {receipt} does not contain {value!r}; the slide statement would be wrong")


TOKENS_IN = round(int(SUM[AOAI]["aoai_input_tokens"]) / N_RECEIPTS)
TOKENS_OUT = round(int(SUM[AOAI]["aoai_output_tokens"]) / N_RECEIPTS)

# Label vocabulary sizes, counted from the two rule modules (constants only).
sys.path.insert(0, str(BENCH))
from receipt_bench import extraction_general as G  # noqa: E402
from receipt_bench import extraction_improved as I  # noqa: E402

VOCAB_ORIG = len({l for group in (G.DOCTOR_LABELS, G.PATIENT_LABELS, G.REG_LABELS, G.RECEIPT_LABELS,
                                  G.TOTAL_LABELS, G.PAID_LABELS, G.SUBTOTAL_LABELS, G.CHARGE_LABELS,
                                  G.BALANCE_LABELS) for l in group} | {l for g in G.DATE_LABELS for l in g})
VOCAB_IMPR = len({l for en, zh in I.LABELS.values() for l in en + zh})

# ===================================================================== receipt crops
INPUTS = BENCH / "data" / "receipts_v2" / "benchmark_inputs"


def receipt_image(receipt):
    src = next(p for p in INPUTS.iterdir() if p.stem == receipt).resolve()
    return ImageOps.exif_transpose(Image.open(src)).convert("RGB")


def find_boxes(receipt, needles):
    page = json.loads((RES / "azure_di" / f"{receipt}.json").read_text())["pages"][0]
    blocks = [(b["text"], min(p[0] for p in b["polygon"]), min(p[1] for p in b["polygon"]),
               max(p[0] for p in b["polygon"]), max(p[1] for p in b["polygon"])) for b in page["blocks"]]
    boxes = []
    for n in needles:
        hit = next((b for b in blocks if n in b[0]), None)
        if hit is None:
            sys.exit(f"{receipt}: text {n!r} not found in Azure DI output; cannot place the crop")
        boxes.append(hit[1:])
    return (page["width"], page["height"]), boxes


def make_crop(receipt, needles, name, highlight, max_px=2000):
    img = receipt_image(receipt)
    (w, h), boxes = find_boxes(receipt, needles)
    if img.size != (w, h):
        sys.exit(f"{receipt}: image {img.size} does not match the Azure DI page {(w, h)}")
    m = int(0.025 * w)
    x0, y0 = max(0, min(b[0] for b in boxes) - m), max(0, min(b[1] for b in boxes) - m)
    x1, y1 = min(w, max(b[2] for b in boxes) + m), min(h, max(b[3] for b in boxes) + m)
    draw = ImageDraw.Draw(img)
    lw = max(3, w // 500)
    for b in find_boxes(receipt, highlight)[1]:
        draw.rectangle([b[0] - lw * 2, b[1] - lw * 2, b[2] + lw * 2, b[3] + lw * 2], outline=(211, 17, 69), width=lw)
    crop = img.crop((x0, y0, x1, y1))
    crop.thumbnail((max_px, max_px))
    path = ASSETS / f"{name}.jpg"
    crop.save(path, quality=90)
    return path


def make_thumb(receipt, name, max_px=1000):
    img = receipt_image(receipt)
    img.thumbnail((max_px, max_px))
    path = ASSETS / f"{name}.jpg"
    img.save(path, quality=88)
    return path


# ===================================================================== style (AIA template, plain)
RED = RGBColor(0xD3, 0x11, 0x45)
CHAR = RGBColor(0x33, 0x3D, 0x47)
GREY_TXT = RGBColor(0x5F, 0x67, 0x70)
LIGHT = RGBColor(0xF2, 0xF2, 0xF2)
GOOD = RGBColor(0x1E, 0x7B, 0x4A)
GOOD_TINT = RGBColor(0xE6, 0xF2, 0xEA)
BAD_TINT = RGBColor(0xFB, 0xE7, 0xEC)
LINE = "BFBFBF"
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT, FONT_ZH = "Arial", "Microsoft JhengHei"

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


def plain_shape(slide, kind, x, y, w, h, fill, line=None, line_w=2.0):
    """A shape with a flat fill and either no outline or a `line`-coloured one (no theme style)."""
    sh = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    st = sh._element.find(qn("p:style"))
    if st is not None:
        sh._element.remove(st)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(line_w)
    return sh


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.0, fill=None, line=None):
    if fill is not None:
        box = plain_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h, fill, line)
    else:
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
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
        for t, o in pd.get("runs") or [(pd["t"], {})]:
            r = p.add_run(); r.text = t
            style_run(r, o.get("size", pd.get("size", 16)), o.get("bold", pd.get("bold", False)),
                      o.get("color", pd.get("color", CHAR)), o.get("italic", pd.get("italic", False)))
    return box


TAGS = {"before": ("MEASURED · BEFORE TUNING", CHAR), "dev": ("MEASURED · DEVELOPMENT SET", CHAR),
        "potential": ("POTENTIAL · NOT YET TESTED", RED), "retro": ("MEASURED · RETROSPECTIVE", CHAR),
        "proposal": ("PROPOSAL · NOT BENCHMARKED", CHAR), "plan": ("PLANNED WORKFLOW · NOT BUILT", CHAR)}


def content_slide(title, message, notes, tag=None):
    s = prs.slides.add_slide(L_CONTENT)
    for idx in (15, 16):
        e = ph(s, idx)._element; e.getparent().remove(e)
    s.shapes._spTree.append(copy.deepcopy(SLDNUM_SP))
    t = ph(s, 10)
    t.left, t.top, t.width, t.height = Inches(0.39), Inches(0.55), Inches(9.6 if tag else 12.2), Inches(0.62)
    if tag:  # evidence tag, top right: what kind of result this slide shows
        label, colour = TAGS[tag]
        pill = plain_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 10.25, 0.66, 2.69, 0.36, WHITE, line=colour, line_w=1.25)
        tf = pill.text_frame
        tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = label; style_run(r, 10.5, True, colour)
    t.text_frame.margin_left = 0
    set_runs(t.text_frame, title, size=28, bold=True, color=CHAR)
    text(s, 0.39, 1.22, 12.55, 0.5, [dict(t=message, size=17, color=RED)])
    s.notes_slide.notes_text_frame.text = notes
    return s


def note(s, t, y=6.15):
    text(s, 0.39, y, 12.0, 0.35, [dict(t=t, size=11, color=GREY_TXT, italic=True)])


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
    cell.margin_top = cell.margin_bottom = Inches(0.05)
    cell.vertical_anchor = anchor
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = pd.get("align", PP_ALIGN.LEFT)
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


def header_row(tbl, heads, size=13, align=None):
    for c, hd in enumerate(heads):
        fill_cell(tbl.cell(0, c), [dict(t=hd, size=size, bold=True, color=WHITE,
                                        align=(align[c] if align else PP_ALIGN.LEFT))], fill=CHAR)
        cell_border(tbl.cell(0, c), sides="")


def picture(s, path, x, y, max_w, max_h):
    with Image.open(path) as im:
        ar = im.width / im.height
    w, h = (max_w, max_w / ar) if max_w / ar <= max_h else (max_h * ar, max_h)
    pic = s.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.line.color.rgb = RGBColor(0xBF, 0xBF, 0xBF)
    pic.line.width = Pt(0.75)
    return x, y, w, h


def example_table(s, x, y, receipt, fields, col_w, row_h=0.72, size=14):
    """Correct value vs original rules vs improved rules (PaddleOCR Light) vs DI + AOAI."""
    tbl = table(s, x, y, list(col_w), [0.62] + [row_h] * len(fields))
    header_row(tbl, ["Field", "Correct", "Original rules", "Improved rules", "DI + AOAI"], size=12.5)
    for i, f in enumerate(fields, start=1):
        fill_cell(tbl.cell(i, 0), [dict(t=FIELD_NAMES[f], size=size, bold=True)])
        fill_cell(tbl.cell(i, 1), [dict(t=truth(receipt, f), size=size)])
        for c, a in enumerate((ORIG["light"], IMPR["light"], AOAI), start=2):
            v, ok = example(a, receipt, f)
            fill_cell(tbl.cell(i, c), [dict(runs=[("✓ " if ok else "✗ ", dict(bold=True, color=GOOD if ok else RED)),
                                                  (v, dict(color=CHAR if v != "not found" else GREY_TXT))],
                                            size=size)], fill=GOOD_TINT if ok else BAD_TINT)
        for c in range(len(col_w)):
            cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
    return tbl


SOURCE = ("Source: python/receipt_ocr_benchmark/results/v2/scores_improved and scores_aoai_improved (summary.csv, "
          "detail.csv), results/v1_heldout, and extraction JSON.")
AOAI_ACC, AOAI_V2_ACC = acc(AOAI), acc(AOAI_V2)
# Held-out Version 1 check: speaker notes only, too small to compare the approaches.
N_UNSEEN, N_V1 = len(UNSEEN), len(list((HELD / "di_aoai_v2_rows").glob("receipt*.json")))
V2_DETAIL = {(r["approach"], r["receipt"], r["field"]): r
             for r in read_csv(RES / "scores_aoai_improved" / "detail.csv")}


def changes(detail, before, after):
    """(fields fixed, fields broken) between two runs of the same approach on these receipts."""
    keys = [k[1:] for k in detail if k[0] == before and detail[k]["result"] in ("Correct", "Wrong")]
    fixed = sum(detail[(before, *k)]["result"] == "Wrong" and detail[(after, *k)]["result"] == "Correct" for k in keys)
    broken = sum(detail[(before, *k)]["result"] == "Correct" and detail[(after, *k)]["result"] == "Wrong" for k in keys)
    return fixed, broken


FIX_LIGHT, FIX_DI = changes(DETAIL, ORIG["light"], IMPR["light"]), changes(DETAIL, ORIG["di"], IMPR["di"])
FIX_PROMPT = changes(V2_DETAIL, "aoai_original", "aoai_v2_rows")
HELD_NOTE = (f"A small held-out check on Version 1 receipts ({N_UNSEEN}-{N_V1} receipts, mostly handwritten) is too "
             "small to say whether either approach generalises better, so it is not shown on the slides.")


from pptx.chart.data import CategoryChartData  # noqa: E402
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION  # noqa: E402
from receipt_bench import di_aoai  # noqa: E402  (prompt text only; nothing is called)

C = PP_ALIGN.CENTER
MID_GREY = RGBColor(0x8C, 0x93, 0x9A)
PALE = RGBColor(0xC9, 0xCD, 0xD1)


def bar_chart(s, x, y, w, h, cats, series, colours, legend=False):
    """Native column chart, values in %, labels on the bars, no value axis. `colours[i]` is one colour
    for series i or a list with one colour per category."""
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.font.name, ch.font.size, ch.font.color.rgb = FONT, Pt(12), CHAR
    ch.has_title = False
    ch.has_legend = legend
    if legend:
        ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
        ch.legend.font.size = Pt(12)
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale, va.has_major_gridlines, va.visible = 0, 100, False, False
    ca = ch.category_axis
    ca.format.line.color.rgb = PALE
    ca.tick_labels.font.size = Pt(12)
    plot = ch.plots[0]
    plot.gap_width, plot.overlap = 55, -8
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = '0.0"%"', False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.bold = Pt(15), True
    for ser, col in zip(plot.series, colours):
        ser.format.fill.solid()  # series colour: what the legend shows
        ser.format.fill.fore_color.rgb = col[0] if isinstance(col, list) else col
        for i in range(len(cats)):
            pt = ser.points[i].format.fill
            pt.solid(); pt.fore_color.rgb = col[i] if isinstance(col, list) else col
    return ch


def pct(a):
    return round(float(_row(a)["accuracy_pct"]), 1)


def card(s, x, y, w, h, head, body, head_colour=RED, fill=LIGHT, line=None, size=13):
    paras = [dict(t=head, size=15, bold=True, color=head_colour, after=4)]
    paras += [dict(t=b, size=size, bullet=True, after=3) for b in body] if isinstance(body, list) else \
        [dict(t=body, size=size)]
    return text(s, x, y, w, h, paras, margin=0.2, fill=fill, line=line)


RANGE_INIT = f"{acc(ORIG['light'])[:-1]}–{acc(ORIG['di'])}"
assert pct(ORIG["light"]) < pct(ORIG["di"])
# Tuned rule accuracies (rules adapted by hand to these receipts) are deliberately never shown.

# Retrospective multilingual baseline: original rules + common Chinese labels (results/v2/scores_multilingual).
SUM_ML = {r["approach"]: r for r in read_csv(RES / "scores_multilingual" / "summary.csv")}
ML = {"light": SUM_ML["paddle_light_multilingual"], "di": SUM_ML["azure_di_multilingual"]}
assert (SUM_ML["paddle_light_original"]["correct"], SUM_ML["azure_di_original"]["correct"],
        SUM_ML["aoai_original"]["correct"]) == (SUM[ORIG["light"]]["correct"], SUM[ORIG["di"]]["correct"],
                                                SUM[AOAI]["correct"]), "multilingual scores use different baselines"
assert pct(ML["light"]) < pct(ML["di"]) < pct(AOAI), "the slides say the baseline still trails AOAI"
RANGE_ML = f"{acc(ML['light'])[:-1]}–{acc(ML['di'])}"
ML_DETAIL = {(r["approach"], r["receipt"], r["field"]): r["result"]
             for r in read_csv(RES / "scores_multilingual" / "detail.csv")}
ML_FIX = {e: changes({k: {"result": v} for k, v in ML_DETAIL.items()}, f"{n}_original", f"{n}_multilingual")
          for e, n in (("light", "paddle_light"), ("di", "azure_di"))}
assert ML_FIX["light"][1] == 0 and ML_FIX["di"][1] == 0, "the slides say nothing was broken"
RETRO = ("Retrospective: Chinese labels added after these receipts were examined (rules fixed before scoring); "
         "not an independent test.")

# Diagnosis experiment (results/diagnosis): ground truth, scores, AOAI evidence and token cost.
DIAG = BENCH / "results" / "diagnosis"
DIAG_GT = read_csv(BENCH / "data" / "diagnosis" / "ground_truth.csv")
DIAG_SUM = {r["approach"]: r for r in read_csv(DIAG / "scores" / "summary.csv")}
DIAG_N = len(DIAG_GT)
DIAG_PRESENT = sum(r["diagnosis_comment"] == "present" for r in DIAG_GT)
DIAG_EMPTY = sum(r["diagnosis_comment"] == "missing" and "label" in r["note"].lower() for r in DIAG_GT)
assert all(int(r["receipts"]) == DIAG_N for r in DIAG_SUM.values())
LINE_ITEM = json.loads((DIAG / "v1" / "aoai_v2_rows" / "receipt1.json").read_text())["diagnosis"]["evidence"]
assert LINE_ITEM == "broken ribs.", LINE_ITEM


def mean_usage(d, key):
    rs = [json.loads(p.read_text()) for p in sorted(d.glob("receipt*.json"))]
    return sum(r["aoai"]["usage"][key] for r in rs) / len(rs)


DIAG_TOKENS_PCT = round(100 * (mean_usage(DIAG / "v2" / "aoai_v2_rows", "prompt_tokens")
                               / mean_usage(RES / "di_aoai_v2_rows", "prompt_tokens") - 1))
for p in sorted((DIAG / "v2" / "aoai_v2_rows").glob("receipt*.json")):  # the six fields did not change
    a, b = json.loads(p.read_text()), json.loads((RES / "di_aoai_v2_rows" / p.name).read_text())
    assert all(a[f] == b[f] for f in FIELDS), f"six fields changed with --diagnosis on {p.name}"

# Held-out Version 1 receipts: the handwritten year misread by Azure DI (limitations slide).
V1_GT = {r["receipt"]: r for r in read_csv(HELD / "scores" / "detail.csv")
         if r["approach"] == "aoai_v2_rows" and r["field"] == "service_date"}
for r in UNSEEN:
    j = json.loads((HELD / "di_aoai_v2_rows" / f"{r}.json").read_text())
    assert V1_GT[r]["ground_truth"].startswith("2026") and j["service_date"].startswith("2020"), r


AOAI_ORIG = "aoai_original"
PER_FIELD = {(a, f): (sum(r["result"] == "Correct" for r in rows), len(rows))
             for a in (AOAI_ORIG, "aoai_v2_rows") for f in FIELDS
             for rows in [[r for k, r in V2_DETAIL.items() if k[0] == a and k[2] == f
                           and r["result"] in ("Correct", "Wrong")]]}
for (a, f), (c, n) in PER_FIELD.items():  # counts agree with the per-field % in summary.csv
    assert f"{100 * c / n:.1f}" == f"{float(SUM_V2PROMPT[a][f + '_accuracy_pct']):.1f}", (a, f)
REG_N = PER_FIELD[(AOAI_ORIG, "registration_number")][1]

# Prompt v2: the four fixes and the wording behind each (checked against the prompt text).
V2_RUNS = ("aoai_v2_plain", "aoai_v2_rows", "aoai_v2_rows_image")
assert len({SUM_V2PROMPT[r]["correct"] for r in V2_RUNS}) == 1, "the slide says layout and photo add nothing"


def raw_reply(run_dir, receipt, field):
    return str((json.loads((RES / run_dir / f"{receipt}.json").read_text()).get("raw_fields") or {}).get(field))


def validation_changes(run_dir):
    n = 0
    for p in (RES / run_dir).glob("receipt*.json"):
        j = json.loads(p.read_text())
        for f in ("doctor_name", "registration_number", "patient_name", "receipt_number"):
            raw = j["raw_fields"].get(f)
            n += isinstance(raw, str) and raw.strip() not in ("", j.get(f))
    return n


assert sum(validation_changes(d) for d in ("di_aoai_v2_plain", "di_aoai_v2_rows", "di_aoai_v2_rows_image")) == 0
PROMPT_FIXES = [("registration_number", "receipt1", "GP", "the identifier only, without its label"),
                ("doctor_name", "receipt5", "Dental", "Leave out qualifications and post-nominals"),
                ("doctor_name", "receipt10", "Pharmacy", "clinic, hospital or practice names"),
                ("total_amount", "receipt9", "Vet", "after any discounts, rounding or other adjustments")]
fixed = {(k[1], k[2]) for k, r in V2_DETAIL.items() if k[0] == AOAI_ORIG and r["result"] == "Wrong"
         and V2_DETAIL[("aoai_v2_rows", k[1], k[2])]["result"] == "Correct"}
assert fixed == {(r, f) for f, r, _, _ in PROMPT_FIXES} and FIX_PROMPT == (4, 0)
P1, P2 = (" ".join(p.split()) for p in (di_aoai.SYSTEM_PROMPT, di_aoai.SYSTEM_PROMPT_V2))
for f, r, _, quote in PROMPT_FIXES:
    assert quote in P2 and quote not in P1, quote
    assert all(V2_DETAIL[(run, r, f)]["result"] == "Correct" for run in V2_RUNS)


NAMES = ("PaddleOCR + Rules", "Azure DI + Rules", "Azure DI + AOAI")
RUNS = ((RES / "scores_multilingual" / "detail.csv", "paddle_light_multilingual"),
        (RES / "scores_multilingual" / "detail.csv", "azure_di_multilingual"),
        (RES / "scores_aoai_improved" / "detail.csv", "aoai_v2_rows"))
SCORES = {}  # (method, field or None) -> (correct, applicable)
for name, (path, approach) in zip(NAMES, RUNS):
    rows = [r for r in read_csv(path) if r["approach"] == approach and r["result"] in ("Correct", "Wrong")]
    for f in FIELDS + [None]:
        sel = [r for r in rows if f is None or r["field"] == f]
        SCORES[(name, f)] = (sum(r["result"] == "Correct" for r in sel), len(sel))
OVERALL = {n: SCORES[(n, None)] for n in NAMES}
assert [c for c, _ in OVERALL.values()] == [int(ML["light"]["correct"]), int(ML["di"]["correct"]),
                                            int(AOAI_V2["correct"])], "overall figures differ from summary.csv"
for n in NAMES:  # the per-field counts add up to the overall score
    assert sum(SCORES[(n, f)][0] for f in FIELDS) == OVERALL[n][0]
PCT = {k: f"{100 * c / n:.1f}%" for k, (c, n) in SCORES.items()}
assert all(SCORES[(NAMES[2], f)][0] >= SCORES[(NAMES[1], f)][0] >= SCORES[(NAMES[0], f)][0] for f in FIELDS)
FOOT = (f"{N_RECEIPTS} test receipts. The rules and AOAI instructions were developed with these receipts; results are "
        "not yet independently validated.")
NOTE_DETAIL = ("Detail for questions: PaddleOCR + Rules and Azure DI + Rules use the multilingual rules (general "
               "rules plus common Chinese labels, written after these receipts were examined, fixed before scoring). "
               "Azure DI + AOAI uses instructions refined after reviewing errors on these receipts. Only 4 unseen "
               "receipts exist, too few to validate. " + SOURCE)

# ===================================================================== 1. title
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Medical Receipt Extraction: Which Approach?")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(0.39), Inches(4.9), Inches(6.6), Inches(0.9)
set_runs(sub.text_frame, " · ".join(NAMES))
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = f"{N_RECEIPTS} test receipts · {len(FIELDS)} fields"; style_run(r)
s.notes_slide.notes_text_frame.text = (
    "We compared three ways of extracting information from medical receipts and recommend Azure DI + AOAI. "
    + NOTE_DETAIL)

# ===================================================================== 2. summary
s = content_slide(
    "Summary",
    "We recommend Azure DI + AOAI for receipt information extraction.",
    "Three reasons: it was the most accurate overall and on every field; it uses the context of the receipt to pick "
    "the right name, date or amount where fixed rules pick the wrong one; and new layouts and fields can often be "
    "handled through its instructions instead of new hand-written rules (not guaranteed). Receipt extraction runs on "
    "Azure; audit checks happen in another authorized system. " + NOTE_DETAIL)
for k, (head_, body) in enumerate([
        ("Most accurate", "Highest accuracy overall and on every one of the six fields (slides 3 and 4)."),
        ("Reads the context", "Picks the right name, date or amount where fixed rules pick the wrong one (slide 6)."),
        ("Easier to extend", "New layouts and fields can often be handled through instructions, with fewer "
                             "hand-written rules to maintain.")]):
    x = 0.39 + k * (4.05 + 0.2)
    text(s, x, 2.0, 4.05, 0.7, [dict(t=str(k + 1), size=28, bold=True, color=RED)], anchor=MSO_ANCHOR.MIDDLE,
         margin=0.25, fill=LIGHT)
    text(s, x, 2.7, 4.05, 1.9, [dict(t=head_, size=19, bold=True, after=8), dict(t=body, size=14.5)], margin=0.25,
         fill=LIGHT)
text(s, 0.39, 4.85, 12.55, 0.6, [dict(runs=[("Where it runs: ", dict(bold=True)),
                                           ("receipts are processed on Azure; audit checks happen in another "
                                            "authorized system (slide 9).", {})], size=14)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.22, fill=WHITE, line=CHAR)

# ===================================================================== 3. overall accuracy
s = content_slide(
    "Overall Accuracy",
    f"Azure DI + AOAI extracted {OVERALL[NAMES[2]][0]} of {OVERALL[NAMES[2]][1]} fields correctly.",
    "Accuracy = correct fields out of " + str(APPLICABLE) + " (9 receipts, 6 fields; 3 receipts have no registration "
    "number). " + "; ".join(f"{n}: {PCT[(n, None)]} ({OVERALL[n][0]}/{OVERALL[n][1]})" for n in NAMES) + ". "
    + NOTE_DETAIL)
bar_chart(s, 0.39, 1.85, 7.6, 4.05, [f"{n}\n{OVERALL[n][0]}/{OVERALL[n][1]}" for n in NAMES],
          [("Accuracy", tuple(round(100 * OVERALL[n][0] / OVERALL[n][1], 1) for n in NAMES))],
          [[MID_GREY, CHAR, RED]])
for k, (n, how) in enumerate(zip(NAMES, ("Open-source text reading, then hand-written rules",
                                         "Azure text reading, then the same rules",
                                         "Azure text reading, then AI extraction"))):
    ai = k == 2
    text(s, 8.3, 2.0 + k * 1.15, 4.64, 1.0, [dict(t=n, size=15, bold=True, color=RED if ai else CHAR, after=3),
                                            dict(t=how, size=12.5, color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE if ai else LIGHT, line=RED if ai else None)
note(s, FOOT, y=6.05)

# ===================================================================== 4. accuracy by field
s = content_slide(
    "Accuracy by Field",
    "Azure DI + AOAI was the most accurate on every field, with the biggest gains on doctor and registration no.",
    "Correct fields per field, from the saved results: " + "; ".join(
        f"{FIELD_NAMES[f]}: " + ", ".join(f"{n} {SCORES[(n, f)][0]}/{SCORES[(n, f)][1]}" for n in NAMES)
        for f in FIELDS) + ". Registration number is printed on 6 of the 9 receipts. " + NOTE_DETAIL)
tbl = table(s, 0.39, 1.85, [3.1, 3.15, 3.15, 3.15], [0.5] + [0.47] * (len(FIELDS) + 1))
header_row(tbl, ["Field"] + list(NAMES), size=14, align=[PP_ALIGN.LEFT, C, C, C])
for i, f in enumerate(FIELDS + [None], start=1):
    total = f is None
    label = "All fields" if total else FIELD_NAMES[f].replace("Reg. no.", "Registration no.")
    fill_cell(tbl.cell(i, 0), [dict(t=label, size=14, bold=True)], fill=LIGHT if total else None)
    best = max(SCORES[(n, f)][0] / SCORES[(n, f)][1] for n in NAMES)
    for c, n in enumerate(NAMES, start=1):
        k, m = SCORES[(n, f)]
        top = k / m == best
        fill_cell(tbl.cell(i, c), [dict(runs=[(PCT[(n, f)], dict(size=16, bold=top or total,
                                                                  color=GOOD if top else CHAR)),
                                              (f"  ({k}/{m})", dict(size=11, color=GREY_TXT))], align=C)],
                  fill=GOOD_TINT if top else (LIGHT if total else None))
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B")
note(s, FOOT + " Green = best for that field. Registration number is printed on 6 of the 9 receipts.", y=5.85)

# data for example 1 (receipt 5), verified
ML_ROWS = {(r["approach"], r["receipt"], r["field"]): r for r in read_csv(RES / "scores_multilingual" / "detail.csv")}
LIGHT_ONLY = {(k[1], k[2]) for k, r in ML_ROWS.items() if k[0] == "paddle_light_multilingual" and r["result"] == "Wrong"
              and ML_ROWS[("azure_di_multilingual", k[1], k[2])]["result"] == "Correct"}
DI_ONLY = {(k[1], k[2]) for k, r in ML_ROWS.items() if k[0] == "azure_di_multilingual" and r["result"] == "Wrong"
           and ML_ROWS[("paddle_light_multilingual", k[1], k[2])]["result"] == "Correct"}
# Every PaddleOCR-only error, by how PaddleOCR wrote the label (checked against the photos in Phase 1).
OCR_CAUSE = {("receipt5", "patient_name"): "glued", ("receipt5", "registration_number"): "glued",
             ("receipt5", "service_date"): "glued", ("receipt8", "service_date"): "glued",
             ("receipt8", "doctor_name"): "glued", ("receipt3", "receipt_number"): "glued+char",
             ("receipt8", "registration_number"): "glued+char", ("receipt5", "receipt_number"): "char",
             ("receipt8", "receipt_number"): "char", ("receipt2", "total_amount"): "currency"}
assert set(OCR_CAUSE) == LIGHT_ONLY and not DI_ONLY, (sorted(LIGHT_ONLY), sorted(DI_ONLY))
N_LIGHT_ONLY = len(LIGHT_ONLY)
CAUSE_N = {c: sum(v == c for v in OCR_CAUSE.values()) for c in ("glued", "glued+char", "char", "currency")}


def ocr_block(engine, receipt, startswith):
    """The OCR block of `engine` that starts with `startswith` (the build stops if there is none)."""
    page = json.loads((RES / engine / f"{receipt}.json").read_text())["pages"][0]
    hit = next((b["text"] for b in page["blocks"] if b["text"].startswith(startswith)), None)
    if hit is None:
        sys.exit(f"{engine} {receipt}: no block starting with {startswith!r}")
    return hit


def ml_value(engine_dir, receipt, field):
    return json.loads((RES / engine_dir / f"{receipt}.json").read_text()).get(field)


# Receipt 5: label as printed (Azure DI text) vs PaddleOCR, and what each engine's rules returned.
# The patient label also ran together ("Patient病人"), but on a slide that gap is invisible between scripts,
# so the table shows the three fields where the problem is visible and the patient is named in the summary.
assert ("receipt5", "patient_name") in LIGHT_ONLY
R5 = [("Registration no.", "registration_number", "Reg. No.", "Reg.No.", "words run together"),
      ("Treatment date", "service_date", "Treatment Date", "TreatmentDate", "words run together"),
      ("Receipt no.", "receipt_number", "Receipt No.", "Receipt No.", "wrong character (simplified 编)")]
r5_rows = []
for label, f, di_start, light_start, why in R5:
    di_t, li_t = ocr_block("azure_di", "receipt5", di_start), ocr_block("paddle_light", "receipt5", light_start)
    di_v, li_v = ml_value("extracted_multilingual_azure_di", "receipt5", f), ml_value("extracted_multilingual_light",
                                                                                      "receipt5", f)
    gt = ML_ROWS[("azure_di_multilingual", "receipt5", f)]["ground_truth"]
    assert li_v is None and ("receipt5", f) in LIGHT_ONLY and ML_ROWS[("azure_di_multilingual", "receipt5", f)][
        "result"] == "Correct", f
    if f == "service_date":
        from datetime import date as _d
        gt = _d.fromisoformat(gt).strftime("%d/%m/%Y")
    r5_rows.append((label, di_t, li_t, why, di_v, gt))
R5_LOST = sorted(f for rc, f in LIGHT_ONLY if rc == "receipt5")
assert len(R5_LOST) == 4
crop5 = make_crop("receipt5", ["Receipt No. 收據編號", "Patient 病人:", "馮浩霖", "Reg. No. 註冊編號", "D03158",
                               "Treatment Date 治療日期", "27/06/2026"], "crop_receipt5_labels",
                  ["Receipt No. 收據編號", "Patient 病人:", "Reg. No. 註冊編號", "Treatment Date 治療日期"])

s = content_slide(
    "Example 1: Why Azure DI + Rules Beat PaddleOCR + Rules",
    "Same rules on both. PaddleOCR misread the labels, so the rules could not find the values.",
    f"Both methods use exactly the same rules; only the text reading differs. PaddleOCR + Rules made {N_LIGHT_ONLY} "
    "more errors than Azure DI + Rules, every one from misreading a label (words run together, a wrong character, a "
    "misread HK$ sign), checked against the receipt photos. On this dental receipt it lost four fields. "
    + NOTE_DETAIL)
picture(s, crop5, 0.39, 1.9, 7.6, 1.95)
text(s, 8.25, 1.9, 4.69, 1.95, [
    dict(runs=[(f"{N_LIGHT_ONLY} ", dict(size=30, bold=True, color=RED)),
               ("more errors with PaddleOCR", dict(size=15, bold=True))], after=4),
    dict(t="All from misreading label text. The rules were the same.", size=13.5, after=4),
    dict(t=f"On this receipt: {len(R5_LOST)} fields lost", size=12, color=GREY_TXT)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.22, fill=LIGHT)
tbl = table(s, 0.39, 4.1, [1.85, 1.75, 5.15, 3.8], [0.42] + [0.46] * len(r5_rows))
header_row(tbl, ["Field", "Correct value", "PaddleOCR + Rules read the label as…", "Azure DI + Rules read it as…"],
           size=12.5)
for i, (label, di_t, li_t, why, di_v, gt) in enumerate(r5_rows, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=label, size=12.5, bold=True)])
    fill_cell(tbl.cell(i, 1), [dict(t=gt, size=12.5)])
    fill_cell(tbl.cell(i, 2), [dict(runs=[("✗ ", dict(bold=True, color=RED)), (li_t.split(":")[0].split("：")[0], {}),
                                          (f"  {why} → not found", dict(size=10.5, color=GREY_TXT, italic=True))],
                                    size=12)], fill=BAD_TINT)
    fill_cell(tbl.cell(i, 3), [dict(runs=[("✓ ", dict(bold=True, color=GOOD)), (di_t.split(":")[0], {}),
                                          ("  → found", dict(size=10.5, color=GREY_TXT, italic=True))], size=12)],
              fill=GOOD_TINT)
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
note(s, "Receipt 5, a bilingual dental receipt. Same rules on both methods; only the text reading differs.", y=6.05)

# data for example 2 (receipts 6 and 5), verified
R6 = [("receipt6", "Practitioner", "doctor_name", "took the referring doctor"),
      ("receipt6", "Service date", "service_date", "took the date the receipt was issued"),
      ("receipt6", "Total", "total_amount", "could not read the card layout"),
      ("receipt5", "Total", "total_amount", "added up the items, ignored the discount")]


def show(field, v):
    if v in (None, ""):
        return "not found"
    if field == "service_date":
        from datetime import date as _d
        return _d.fromisoformat(str(v)).strftime("%-d %b %Y")
    if field == "total_amount":
        return f"HK${float(v):,.0f}"
    return str(v)


r6_rows = []
for rc, label, f, why in R6:
    rule_v = ml_value("extracted_multilingual_azure_di", rc, f)
    gt = ML_ROWS[("azure_di_multilingual", rc, f)]["ground_truth"]
    assert ML_ROWS[("azure_di_multilingual", rc, f)]["result"] == "Wrong", (rc, f)
    for run in ("aoai_original", "aoai_v2_rows"):  # right with the original prompt, so not due to prompt tuning
        assert V2_DETAIL[(run, rc, f)]["result"] == "Correct", (run, rc, f)
    aoai_v = json_value(AOAI, rc, f)
    r6_rows.append((rc, label, f, why, show(f, gt if f != "total_amount" else float(gt)), show(f, rule_v),
                    show(f, aoai_v)))
crop6 = make_crop("receipt6", ["Date Issued", "PHYSIOTHERAPIST", "CHEUNG Hoi Ying", "Referred by", "Dr. Kwok Man Hin",
                               "Session Date", "HK$1,200.00", "Outstanding Balance"], "crop_receipt6",
                  ["Dr. Kwok Man Hin", "CHEUNG Hoi Ying", "Date Issued", "Session Date", "HK$1,200.00"])

s = content_slide(
    "Example 2: Why Azure DI + AOAI Beat Azure DI + Rules",
    "Both read the same Azure DI text. AOAI understood the context; the rules followed fixed patterns.",
    "Same Azure DI text for both. On receipt 6 (physiotherapy) the rules took the referring doctor as the "
    "practitioner, the issue date as the session date, and could not read the total from the card row. On receipt 5 "
    "the rules added up the items and missed the 10% discount. AOAI got all four right, and already did so before "
    "its instructions were refined. " + NOTE_DETAIL)
picture(s, crop6, 0.39, 1.9, 4.3, 3.15)
tbl = table(s, 4.95, 1.9, [1.35, 1.95, 2.45, 2.24], [0.42] + [0.66] * len(r6_rows))
header_row(tbl, ["Field", "Correct", "Azure DI + Rules", "Azure DI + AOAI"], size=13)
for i, (rc, label, f, why, gt, rule_v, aoai_v) in enumerate(r6_rows, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=label, size=12.5, bold=True),
                               dict(t=f"Receipt {rc[-1]}", size=10, color=GREY_TXT)])
    fill_cell(tbl.cell(i, 1), [dict(t=gt, size=12.5)])
    fill_cell(tbl.cell(i, 2), [dict(runs=[("✗ ", dict(bold=True, color=RED)), (rule_v, {})], size=12.5),
                               dict(t=why, size=10, color=GREY_TXT, italic=True)], fill=BAD_TINT)
    fill_cell(tbl.cell(i, 3), [dict(runs=[("✓ ", dict(bold=True, color=GOOD)), (aoai_v, {})], size=12.5)],
              fill=GOOD_TINT)
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
text(s, 0.39, 5.2, 12.55, 0.6, [dict(runs=[("Why it matters: ", dict(bold=True)),
                                          ("rules need a new hand-written rule for each case like this; AOAI used "
                                           "the context it was given.", {})], size=13.5)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)
note(s, "AOAI got these right even before its instructions were refined.", y=6.0)

# ===================================================================== 7. the doctor database proposal
# every real example below is checked against the saved OCR text and ground truth
for rc, needle in [("receipt6", "Referred by"), ("receipt6", "Dr. Kwok Man Hin"), ("receipt6", "CHEUNG Hoi Ying"),
                   ("receipt9", "Clinician: Angel Tseng"), ("receipt9", "Dr. Lok Vichol")]:
    ocr_read(rc, needle, engines=("azure_di",))
assert ml_value("extracted_multilingual_azure_di", "receipt6", "doctor_name") == "Dr. Kwok Man Hin"
assert "CHEUNG Hoi Ying" in ML_ROWS[("azure_di_multilingual", "receipt6", "doctor_name")]["ground_truth"]
assert ML_ROWS[("azure_di_multilingual", "receipt9", "doctor_name")]["ground_truth"] == "Angel Tseng, Lok Yi Choi"
assert "Lok Yi Choi" not in (RES / "azure_di" / "receipt9.json").read_text()  # so an exact match finds nothing
s = content_slide(
    "Manager's Proposal: The Doctor Database",
    "Exact matching can find registered doctor names, but cannot reliably tell who treated the patient.",
    "Proposal: OCR reads the receipt, then the recognised text is matched against the registry of about 40,000 "
    "registered doctors (potentially about 80,000 English and Chinese name variants) using strict exact matching, "
    "without AOAI. Advantages: simple to implement, low additional cost, consistent results, and every match is "
    "easy to verify against the registry. Limitations, from our receipts: receipt 6 names a referring doctor "
    "(Dr. Kwok Man Hin) while the treatment was by physiotherapist CHEUNG Hoi Ying, and the rules already took the "
    "referring doctor; receipt 9 (a vet invoice) lists a clinician (Angel Tseng) and a signing vet (Dr. Lok Yi "
    "Choi); and Azure DI read 'Dr. Lok Yi Choi' as 'Dr. Lok Vichol', so an exact match finds nothing. "
    "Hypothetical, not in our receipts: a patient who is a registered doctor would match the registry. To be fair: "
    "if the requirement is only to know whether a registered doctor's name appears, exact matching may be "
    "sufficient. Matching also depends on the registry containing the practitioner (dentists, physiotherapists "
    "and vets may be on other registers). Not benchmarked; no implementation is planned for this deck. The names "
    "on our test receipts are fictional, so registry match rates were not measured.")
# left: the proposal as a three-step flow, then the advantages
text(s, 0.39, 1.85, 4.6, 0.38, [dict(t="How it works", size=15, bold=True)], anchor=MSO_ANCHOR.MIDDLE)
for k, (n, head_, sub) in enumerate([("1", "OCR reads the receipt", "Text from the receipt image"),
                                     ("2", "Look up the doctor registry", "~40,000 registered doctors · up to ~80,000 "
                                                                          "English and Chinese name variants"),
                                     ("3", "Strict exact match", "Names must match exactly · no AOAI")]):
    y = 2.28 + k * 0.74
    text(s, 0.39, y, 0.6, 0.66, [dict(t=n, size=20, bold=True, color=WHITE, align=C)], anchor=MSO_ANCHOR.MIDDLE,
         fill=CHAR)
    text(s, 1.07, y, 3.92, 0.66, [dict(t=head_, size=13.5, bold=True), dict(t=sub, size=10.5, color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.14, fill=LIGHT)
text(s, 0.39, 4.55, 4.6, 0.38, [dict(t="Advantages", size=15, bold=True, color=GOOD)], anchor=MSO_ANCHOR.MIDDLE)
for k, adv in enumerate(["Simple to implement", "Low additional cost", "Consistent matching", "Easy to verify"]):
    x, y = 0.39 + (k % 2) * 2.33, 4.95 + (k // 2) * 0.43
    text(s, x, y, 2.27, 0.37, [dict(runs=[("✓ ", dict(bold=True, color=GOOD)), (adv, {})], size=12.5)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.12, fill=GOOD_TINT)
# right: where a name match is not the treating practitioner
text(s, 5.3, 1.85, 7.64, 0.38, [dict(t="Limitations: a name match is not the treating practitioner", size=15,
                                     bold=True, color=RED)], anchor=MSO_ANCHOR.MIDDLE)
CASES = [("Referring doctor", "Receipt 6", "“Referred by Dr. Kwok Man Hin”, but the treatment was by "
                                           "physiotherapist CHEUNG Hoi Ying.", True),
         ("Several practitioners", "Receipt 9", "A clinician (Angel Tseng) and a signing vet (Dr. Lok Yi Choi). "
                                               "Which one treated?", True),
         ("OCR error", "Receipt 9", "“Dr. Lok Yi Choi” was read as “Dr. Lok Vichol”, so exact matching finds "
                                    "nothing.", True),
         ("Doctor is the patient", "Hypothetical", "The patient's own name could match the registry, although "
                                                   "they did not treat anyone.", False)]
for k, (head_, where, body, real) in enumerate(CASES):
    y = 2.28 + k * 0.74
    text(s, 5.3, y, 1.55, 0.66, [dict(t=where, size=11.5, bold=True, color=WHITE if real else GREY_TXT, align=C)],
         anchor=MSO_ANCHOR.MIDDLE, fill=RED if real else WHITE, line=None if real else MID_GREY)
    text(s, 6.93, y, 6.01, 0.66, [dict(t=head_, size=13, bold=True, after=1),
                                 dict(t=body, size=11, italic=not real, color=CHAR if real else GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.14, fill=BAD_TINT if real else LIGHT)
text(s, 5.3, 5.27, 7.64, 0.48, [dict(runs=[("To be fair: ", dict(bold=True)),
                                        ("if we only need to know whether a registered doctor appears, exact "
                                         "matching may be sufficient.", {})], size=12.5)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.16, fill=WHITE, line=CHAR)
note(s, "Proposal only: not benchmarked, and no implementation is needed now. Receipt names are fictional, so "
        "registry match rates were not measured.", y=5.95)

# ===================================================================== 8. advantages and disadvantages
s = content_slide(
    "Advantages and Disadvantages",
    "Azure DI + AOAI wins on accuracy and flexibility; rules win on cost and transparency.",
    "Accuracy as on slide 3. New layouts: rules may need new hand-written rules and retesting; AOAI can often "
    "handle varied wording through its instructions, not guaranteed. Cost: PaddleOCR runs on our own compute with no "
    "per-receipt fee; Azure services charge per receipt (prices to be confirmed). Transparency: every rule result can "
    "be traced to a rule; AOAI is harder to explain and can return a confident wrong value, so results still need "
    "checking. " + NOTE_DETAIL)
rows = [("Accuracy", "− Lower on every field (slides 3 and 4)", "+ Highest overall and on every field", "ai"),
        ("New receipt layouts", "− May need new hand-written rules", "+ Often handled through instructions", "ai"),
        ("Maintenance", "− Rules written and retested by hand", "+ Fewer rules to maintain; still tested", "ai"),
        ("Cost", "+ PaddleOCR: no per-receipt fee", "− Azure fees per receipt (to confirm)", "rules"),
        ("Transparency", "+ Every result traced to a rule", "− Harder to explain; can be confidently wrong", "rules")]
tbl = table(s, 0.39, 1.95, [2.75, 4.9, 4.9], [0.55] + [0.62] * len(rows))
header_row(tbl, ["", "PaddleOCR + Rules / Azure DI + Rules", "Azure DI + AOAI"], size=15)
for i, (label, rules_t, ai_t, better) in enumerate(rows, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=label, size=15, bold=True)])
    fill_cell(tbl.cell(i, 1), [dict(t=rules_t, size=14)], fill=GOOD_TINT if better == "rules" else None)
    fill_cell(tbl.cell(i, 2), [dict(t=ai_t, size=14)], fill=GOOD_TINT if better == "ai" else None)
    for c in range(3):
        cell_border(tbl.cell(i, c), sides="B")
note(s, "Green = stronger side. Azure prices are not yet confirmed.", y=5.75)

# ===================================================================== 9. business value
s = content_slide(
    "Business Value: From Receipts to Audit Analytics",
    "Azure DI + AOAI, our recommended approach, lets auditors check claims against what receipts actually show.",
    "Recommendation: Azure DI + AOAI for receipt information extraction. Business value: once structured information "
    "is extracted directly from the receipts, the results can be transferred securely to another authorized "
    "platform for data analytics and audit testing. Auditors can then compare what is printed on the receipts with "
    "what was submitted in the claims system, instead of relying only on manually entered claim data. Potential "
    "tests from the discussion with the business auditors: patient names and treatment dates against submitted "
    "claims; claimed amounts against receipt amounts; duplicate receipts used across claims; unusual treatment "
    "charges or provider fees; unusual diagnosis and treatment combinations; and unusual claim patterns across "
    "providers or agents (not shown, since it relies mainly on claims data). Boundary: Azure processes only approved "
    "receipt data; claims records, policy information and historical data remain in another authorized system; "
    "the transfer method must be approved and is not yet designed. These analytics are potential future uses, not "
    "implemented or benchmarked. Extraction provides supporting evidence, not a final fraud or claim validity "
    "decision. Next step: a pilot that tests more receipt fields on approved receipts. " + NOTE_DETAIL)
# zone labels over the flow
text(s, 0.39, 1.82, 7.37, 0.32, [dict(t="On Azure: approved receipt data only", size=12, bold=True, color=RED)],
     anchor=MSO_ANCHOR.MIDDLE)
text(s, 8.15, 1.82, 4.79, 0.32, [dict(t="Another authorized platform", size=12, bold=True, color=CHAR)], anchor=MSO_ANCHOR.MIDDLE)
FLOW = [("Medical receipt", "Approved receipts", LIGHT, CHAR),
        ("Azure DI + AOAI", "Extraction", RED, WHITE),
        ("Structured results", "Names, dates, amounts, items", LIGHT, CHAR),
        ("Authorized platform", "Joined with claims data", CHAR, WHITE),
        ("Data analytics", "Receipts vs claims, not only manually entered data", CHAR, WHITE)]
W, G = 2.206, 0.38
for k, (head_, sub, fill, colour) in enumerate(FLOW):
    x = 0.39 + k * (W + G)
    text(s, x, 2.17, W, 0.8, [dict(t=head_, size=13.5, bold=True, color=colour, align=C),
                              dict(t=sub, size=10.5, color=colour if colour == WHITE else GREY_TXT, align=C)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.08, fill=fill)
    if k < len(FLOW) - 1:
        text(s, x + W, 2.17, G, 0.8, [dict(t="→", size=20, bold=True, color=RED if k == 2 else GREY_TXT, align=C)],
             anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.39 + 3 * (W + G) - G / 2 - 1.6, 3.0, 3.2, 0.3,
     [dict(t="Approved transfer method (to be agreed)", size=10.5, italic=True, color=RED, align=C)],
     anchor=MSO_ANCHOR.MIDDLE)
# potential data analytics tests
text(s, 0.39, 3.38, 7.95, 0.36, [dict(runs=[("Potential audit tests", dict(bold=True)),
                                           ("  (from the business auditor discussion; not implemented)",
                                            dict(size=11.5, color=GREY_TXT, italic=True))], size=15)],
     anchor=MSO_ANCHOR.MIDDLE)
TESTS = [("Match to the claim", "Patient name and treatment date on the receipt vs the submitted claim"),
         ("Amounts", "Claimed amount vs the amount printed on the receipt"),
         ("Duplicates", "The same receipt used across more than one claim"),
         ("Unusual fees", "Treatment charges or provider fees far from the usual range"),
         ("Diagnosis vs treatment", "Unusual diagnosis and treatment combinations")]
for k, (head_, body) in enumerate(TESTS):
    y = 3.8 + k * 0.42
    text(s, 0.39, y, 0.42, 0.36, [dict(t=str(k + 1), size=13, bold=True, color=WHITE, align=C)],
         anchor=MSO_ANCHOR.MIDDLE, fill=RED)
    text(s, 0.87, y, 7.47, 0.36, [dict(runs=[(head_ + ": ", dict(bold=True)), (body, {})], size=12.5)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.12, fill=LIGHT)
# guard rails
text(s, 8.65, 3.38, 4.29, 2.44, [
    dict(t="Important", size=15, bold=True, color=RED, after=4),
    dict(t="• Azure processes only approved receipt data.", size=12, after=2),
    dict(t="• Claims records, policy information and historical data stay in another authorized system.",
         size=12, after=2),
    dict(t="• The transfer method must be approved.", size=12, after=2),
    dict(t="• Potential future uses: not implemented or benchmarked.", size=12, after=2),
    dict(t="• Extraction gives supporting evidence, not a final fraud or claim validity decision.", size=12)],
    margin=0.2, fill=WHITE, line=RED)
note(s, FOOT, y=5.95)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
