"""Generate the Version 4 Receipt OCR Benchmark deck (12 slides) from the AIA template.

    python3 ppt/ocr_benchmark/scripts/generate_ppt_v4.py --force     (from the repository root)

Version 4 is a redesign around one question: can OCR with extraction rules replace Azure OpenAI
for medical receipts, and if not, why is AOAI needed? Answer first, then the evidence:
initial results, results after tuning (development set), accuracy by field, what prompt v2 changed,
a side-by-side scorecard, the diagnosis-comment experiment, what AOAI could add beyond the six
fields (potential only, not measured), limitations, and a recommendation.

Every slide carries an evidence tag: measured before tuning, measured on the development set
(changes made after reviewing these receipts), or potential (not tested). PaddleOCR Heavy is
excluded. generate_ppt_v3.py is kept unchanged for the archived Version 3 deck.

Reads committed results only (no OCR, scoring or Azure calls):
- results/v2/scores_improved and scores_aoai_improved (summary.csv, detail.csv): every accuracy,
  time and token figure, per-field counts, and the fields each change fixed or broke;
- results/v2/<approach>/receiptN.json: example values and the model's raw replies;
- results/v2/azure_di raw OCR: the medical details quoted on the "beyond six fields" slide;
- results/v1_heldout: the held-out Version 1 receipts (limitations slide);
- results/diagnosis/scores/summary.csv and the diagnosis AOAI runs: the diagnosis experiment;
- receipt_bench/di_aoai.py: prompt v1 and v2 text (quotes are checked against it);
- receipt_bench/extraction_general.py and extraction_improved.py: label vocabulary sizes.

Receipt crops go to ppt/ocr_benchmark/assets_v2/. Never writes into archive/ or template/.
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
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V4.pptx")
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
        "potential": ("POTENTIAL · NOT YET TESTED", RED)}


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
RANGE_TUNED = f"{acc(IMPR['di'])[:-1]}–{acc(IMPR['light'])}"
assert pct(ORIG["light"]) < pct(ORIG["di"]) and pct(IMPR["di"]) < pct(IMPR["light"])

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

# ===================================================================== 1. title
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Can OCR Rules Replace Azure OpenAI?")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(0.39), Inches(4.9), Inches(6.6), Inches(0.9)
set_runs(sub.text_frame, "Medical receipt extraction benchmark")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = f"{N_RECEIPTS} receipts · 6 fields · 3 approaches · plus a diagnosis-comment test"; style_run(r)
s.notes_slide.notes_text_frame.text = (
    "Question: can traditional OCR with hand-written extraction rules replace Azure OpenAI (AOAI) for medical "
    "receipts, and if not, why is AOAI needed? Every number in this deck comes from the saved benchmark results. "
    + SOURCE)

# ===================================================================== 2. the answer in brief
s = content_slide(
    "The Answer in Brief",
    "Rules can replace AOAI only for simple, clearly labelled tasks.",
    f"Before tuning: rules {RANGE_INIT}, AOAI {AOAI_ACC}. After tuning on the same {N_RECEIPTS} receipts "
    f"(development results): rules {RANGE_TUNED}, AOAI prompt v2 {AOAI_V2_ACC}; the rules needed {VOCAB_ORIG} -> "
    f"{VOCAB_IMPR} label phrases written by hand, AOAI one prompt revision. Diagnosis-comment check: all three "
    f"methods {DIAG_SUM['aoai_v2']['correct']}/{DIAG_N}. None of this is validated on unseen receipts. " + SOURCE)
text(s, 0.39, 1.95, 4.3, 3.95, [
    dict(t="Not as a general replacement.", size=24, bold=True, color=WHITE, after=14),
    dict(t="Rules can match AI on simple, labelled checks, after manual work.", size=15, color=WHITE, after=10),
    dict(t="AOAI is needed when receipt layouts vary and when richer medical information is wanted.", size=15,
         color=WHITE)], anchor=MSO_ANCHOR.MIDDLE, margin=0.3, fill=CHAR)
findings = [(f"{AOAI_ACC} vs {RANGE_INIT}", "Before any tuning, AOAI was far ahead. The first rules had no Chinese "
                                           "labels."),
            (f"{AOAI_V2_ACC} vs {RANGE_TUNED}", f"After tuning on the same receipts (development results). Rules needed "
                                               f"{VOCAB_ORIG} → {VOCAB_IMPR} label phrases; AOAI one prompt "
                                               "revision."),
            (f"{DIAG_SUM['aoai_v2']['correct']}/{DIAG_N} for all", "On a yes/no diagnosis-comment check with clear "
                                                                 "labels, rules matched AOAI.")]
for k, (big, small) in enumerate(findings):
    y = 1.95 + k * 1.34
    text(s, 4.95, y, 3.7, 1.2, [dict(t=big, size=20, bold=True, color=RED)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2,
         fill=LIGHT)
    text(s, 8.85, y, 4.09, 1.2, [dict(t=small, size=14)], anchor=MSO_ANCHOR.MIDDLE)
note(s, "Development results are not independent validation; a test on 30+ unseen real receipts is still needed.",
     y=6.05)

# ===================================================================== 3. what we compared
s = content_slide(
    "What We Compared",
    "Three ways to turn a receipt photo into six fields. Only the extraction step differs between rules and AI.",
    f"{N_RECEIPTS} receipts: 7 printed, fictional test receipts photographed with a phone (English, bilingual and "
    "Traditional Chinese layouts) and 2 receipts from the first benchmark round. Six fields: doctor, registration "
    f"number, patient, receipt number, service date, total; {APPLICABLE} fields are printed on the receipts and "
    "scored. Azure OpenAI deployment: gpt-5-mini. " + SOURCE)
lanes = [("PaddleOCR Light + rules", "PaddleOCR Light", "open source, own compute", "Hand-written rules", False),
         ("Azure DI + rules", "Azure Document Intelligence", "cloud OCR", "Hand-written rules", False),
         ("Azure DI + AOAI", "Azure Document Intelligence", "cloud OCR", "Azure OpenAI prompt", True)]
for k, (name, ocr, ocr_sub, extract, ai) in enumerate(lanes):
    y = 1.95 + k * 0.82
    text(s, 0.39, y, 2.75, 0.66, [dict(t=name, size=15, bold=True, color=RED if ai else CHAR)],
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 3.2, y, 3.55, 0.66, [dict(t=ocr, size=13.5, bold=True), dict(t=ocr_sub, size=11, color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.15, fill=LIGHT)
    plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 6.85, y + 0.2, 0.4, 0.26, MID_GREY)
    text(s, 7.35, y, 3.3, 0.66, [dict(t=extract, size=13.5, bold=True, color=RED if ai else CHAR)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.15, fill=WHITE if ai else LIGHT, line=RED if ai else None)
    plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 10.75, y + 0.2, 0.4, 0.26, MID_GREY)
    text(s, 11.25, y, 1.69, 0.66, [dict(t="6 fields", size=13.5, bold=True, align=C)], anchor=MSO_ANCHOR.MIDDLE,
         fill=LIGHT)
text(s, 3.2, 1.62, 3.55, 0.3, [dict(t="1. Read the text (OCR)", size=11.5, color=GREY_TXT, bold=True)])
text(s, 7.35, 1.62, 3.3, 0.3, [dict(t="2. Find the fields", size=11.5, color=GREY_TXT, bold=True)])
for i, (rcpt, label) in enumerate((("receipt1", "English"), ("receipt3", "Bilingual"), ("receipt4", "Chinese"))):
    x, y, w, h = picture(s, make_thumb(rcpt, f"thumb_{rcpt}"), 0.39 + i * 1.3, 4.5, 1.15, 1.45)
    text(s, x, y + h + 0.03, 1.2, 0.25, [dict(t=label, size=10.5, color=GREY_TXT)])
text(s, 4.4, 4.5, 8.54, 1.45, [
    dict(runs=[(f"{N_RECEIPTS} receipts", dict(bold=True)), (": 7 printed test receipts (English, bilingual, Chinese "
                                                          "layouts) and 2 from the first benchmark round.", {})],
         size=14, after=8),
    dict(runs=[(f"{APPLICABLE} fields scored", dict(bold=True)), (": doctor, registration no., patient, receipt no., "
                                                                 "service date, total.", {})], size=14)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.25, fill=LIGHT)

# ===================================================================== 4. before tuning
for v in ("蔡嘉穎",):
    ocr_read("receipt8", v)
v8, ok8 = example(ORIG["light"], "receipt8", "patient_name")
assert v8 == "病人" and not ok8
s = content_slide(
    "Before Tuning: AOAI Was Far Ahead",
    "Out of the box, AI extraction found more than twice as many fields as the first rule sets.",
    f"Accuracy = correct fields / {APPLICABLE} on the {N_RECEIPTS} receipts, before anything was changed for them. "
    "The AOAI prompt was written before these receipts existed. The original rules knew English labels only; on "
    "the Chinese and bilingual receipts the OCR read the values but the rules could not find them, e.g. receipt 8: "
    "the OCR read the patient name 蔡嘉穎 but the rules returned the label 病人 ('patient'). So this compares initial "
    "implementations, not the maximum capability of each approach. " + SOURCE, tag="before")
bar_chart(s, 0.39, 1.85, 6.9, 4.1,
          [f"PaddleOCR Light + rules\n{count(ORIG['light'])}", f"Azure DI + rules\n{count(ORIG['di'])}",
           f"Azure DI + AOAI\n{count(AOAI)}"],
          [("Accuracy", (pct(ORIG["light"]), pct(ORIG["di"]), pct(AOAI)))], [[MID_GREY, MID_GREY, RED]])
text(s, 7.6, 1.95, 5.34, 1.75, [
    dict(t="Why the rules scored low", size=15, bold=True, color=RED, after=4),
    dict(t="The first rules knew English labels only: no Chinese or bilingual labels.", size=13, bullet=True,
         after=3),
    dict(t="So this compares first versions, not the best each approach can do.", size=13, bullet=True, bold=True)],
    margin=0.2, fill=LIGHT)
crop = make_crop("receipt8", ["Patient 病人", "蔡嘉穎"], "crop_receipt8_patient", ["Patient 病人", "蔡嘉穎"])
x, y, w, h = picture(s, crop, 7.6, 3.9, 2.4, 1.9)
text(s, x + w + 0.2, 3.9, 12.94 - x - w - 0.2, 1.9, [
    dict(t="The OCR read the name 蔡嘉穎.", size=13, after=6),
    dict(runs=[("The first rules returned the label ", {}), ("病人", dict(bold=True)), (" (\"patient\") instead.", {})],
         size=13)], anchor=MSO_ANCHOR.MIDDLE)
note(s, f"Accuracy = correct fields out of {APPLICABLE} on {N_RECEIPTS} receipts. Receipt shown: bilingual medical "
        "centre receipt, PaddleOCR Light text.", y=6.05)

# ===================================================================== 5. after tuning
s = content_slide(
    "After Tuning: All Improved, at Very Different Cost",
    "Rules closed most of the gap, but only by being rewritten by hand for these receipts.",
    f"Development results: every change was made after reviewing the errors on these {N_RECEIPTS} receipts, so the "
    f"scores are not independent validation. Rules: label phrases {VOCAB_ORIG} -> {VOCAB_IMPR} (Chinese and "
    f"bilingual labels, distractor labels, layout handling); fixed {FIX_LIGHT[0]} fields and broke {FIX_LIGHT[1]} "
    f"on PaddleOCR Light text, fixed {FIX_DI[0]} and broke {FIX_DI[1]} on Azure DI text. AOAI: prompt v2 with "
    f"clearer field definitions; fixed {FIX_PROMPT[0]}, broke {FIX_PROMPT[1]}. " + HELD_NOTE + " " + SOURCE,
    tag="dev")
bar_chart(s, 0.39, 1.8, 7.4, 4.15,
          ["PaddleOCR Light + rules", "Azure DI + rules", "Azure DI + AOAI"],
          [("Before tuning", (pct(ORIG["light"]), pct(ORIG["di"]), pct(AOAI))),
           ("After tuning (development)", (pct(IMPR["light"]), pct(IMPR["di"]), pct(AOAI_V2)))],
          [PALE, [CHAR, CHAR, RED]], legend=True)
card(s, 8.1, 1.95, 4.84, 1.85, "Rules: rewritten by hand",
     [f"{VOCAB_ORIG}\u00a0→\u00a0{VOCAB_IMPR} label phrases: Chinese, bilingual, layouts",
      "Code changes, then a retest of every receipt",
      f"Fixed {FIX_LIGHT[0]} fields, broke {FIX_LIGHT[1]} that was correct"], head_colour=CHAR)
card(s, 8.1, 3.95, 4.84, 1.85, "AOAI: one prompt revision",
     ["Clearer definition of each field", "Plain-language edits, then a rerun",
      f"Fixed {FIX_PROMPT[0]} fields, broke {FIX_PROMPT[1]}"], fill=WHITE, line=RED)
note(s, f"Development results: changes made after reviewing these {N_RECEIPTS} receipts; not independent "
        "validation. Rule figures shown for PaddleOCR Light.", y=6.05)

# ===================================================================== 6. accuracy by field
TUNED = {"PaddleOCR Light + rules": "paddle_light_improved", "Azure DI + rules": "azure_di_improved",
         "Azure DI + AOAI, prompt v2": "aoai_v2_rows"}


def field_score(approach, field):
    """(correct, applicable) counted from detail.csv, checked against the per-field % in summary.csv."""
    rows = [r for k, r in V2_DETAIL.items() if k[0] == approach and k[2] == field and r["result"] in ("Correct", "Wrong")]
    c, n = sum(r["result"] == "Correct" for r in rows), len(rows)
    if f"{100 * c / n:.1f}" != f"{float(SUM_V2PROMPT[approach][field + '_accuracy_pct']):.1f}":
        sys.exit(f"{approach} {field}: detail.csv {c}/{n} disagrees with summary.csv")
    return c, n


FIELD_SCORES = {(a, f): field_score(a, f) for a in TUNED.values() for f in FIELDS}
for a in TUNED.values():
    assert sum(FIELD_SCORES[(a, f)][0] for f in FIELDS) == int(SUM_V2PROMPT[a]["correct"])
APPLIC = {f: FIELD_SCORES[("aoai_v2_rows", f)][1] for f in FIELDS}
assert all(FIELD_SCORES[(a, f)][1] == APPLIC[f] for a in TUNED.values() for f in FIELDS)
REG_N = APPLIC["registration_number"]
WRONG = {a: {(k[1], k[2]) for k, r in V2_DETAIL.items() if k[0] == a and r["result"] == "Wrong"} for a in TUNED.values()}
assert set.intersection(*WRONG.values()) == {("receipt9", "doctor_name"), ("receipt10", "service_date")}
s = content_slide(
    "Where Errors Remain: Accuracy by Field",
    "All three miss the same two fields; the rules also miss patients and receipt numbers.",
    f"Development results after tuning on these {N_RECEIPTS} receipts. Counts from scores_aoai_improved/detail.csv, "
    f"checked against summary.csv. Registration number is printed on {REG_N} of the {N_RECEIPTS} receipts; every "
    "other field on all of them. All three miss the vet invoice's doctor (two practitioners; the OCR misread the "
    "signature) and the pharmacy receipt's service date (print date vs item date, an open ground-truth question). "
    "The rules also miss patient and receipt number on the vet invoice and the pharmacy receipt (a stray mark on "
    "the label, a payment receipt number, no labels); Azure DI + rules also misses one total. " + SOURCE, tag="dev")
names = list(TUNED)
tbl = table(s, 0.39, 1.95, [2.75, 1.55, 2.75, 2.75, 2.75], [0.6] + [0.52] * len(FIELDS))
header_row(tbl, ["Field", "Receipts"] + names, size=13, align=[PP_ALIGN.LEFT] + [C] * 4)
for i, f in enumerate(FIELDS, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=FIELD_NAMES[f].replace("Reg. no.", "Registration no."), size=14, bold=True)])
    fill_cell(tbl.cell(i, 1), [dict(t=f"{APPLIC[f]}" + ("*" if f == "registration_number" else ""), size=14,
                                    color=GREY_TXT, align=C)])
    for c, a in enumerate(TUNED.values(), start=2):
        k, n = FIELD_SCORES[(a, f)]
        full = k == n
        fill_cell(tbl.cell(i, c), [dict(runs=[(f"{100 * k / n:.1f}%", dict(size=16, bold=full,
                                                                          color=GOOD if full else CHAR)),
                                              (f"  ({k}/{n})", dict(size=11, color=GREY_TXT))], align=C)],
                  fill=GOOD_TINT if full else None)
    for c in range(5):
        cell_border(tbl.cell(i, c), sides="B")
note(s, f"Development results after tuning. * Registration number is printed on {REG_N} of the {N_RECEIPTS} "
        f"receipts; every other field on all {N_RECEIPTS}.", y=5.8)

# ===================================================================== 7. what prompt v2 changed
V2_RUNS = {"plain": "aoai_v2_plain", "rows": "aoai_v2_rows", "image": "aoai_v2_rows_image"}
assert len({SUM_V2PROMPT[r]["correct"] for r in V2_RUNS.values()}) == 1


def raw_reply(run_dir, receipt, field):
    j = json.loads((RES / run_dir / f"{receipt}.json").read_text())
    return str((j.get("raw_fields") or {}).get(field))


def validation_changes(run_dir):
    n = 0
    for p in (RES / run_dir).glob("receipt*.json"):
        j = json.loads(p.read_text())
        for f in ("doctor_name", "registration_number", "patient_name", "receipt_number"):
            raw = j["raw_fields"].get(f)
            n += isinstance(raw, str) and raw.strip() not in ("", j.get(f))
    return n


VALIDATION_CHANGES = sum(validation_changes(d) for d in ("di_aoai_v2_plain", "di_aoai_v2_rows",
                                                         "di_aoai_v2_rows_image"))
PROMPT_FIXES = [("registration_number", "receipt1", "GP receipt", "the identifier only, without its label"),
                ("doctor_name", "receipt5", "Dental receipt", "Leave out qualifications and post-nominals"),
                ("doctor_name", "receipt10", "Pharmacy receipt", "clinic, hospital or practice names"),
                ("total_amount", "receipt9", "Vet invoice", "after any discounts, rounding or other adjustments")]
actual = {(k[1], k[2]) for k, r in V2_DETAIL.items()
          if k[0] == "aoai_original" and r["result"] == "Wrong" and V2_DETAIL[("aoai_v2_rows", k[1], k[2])]["result"]
          == "Correct"}
assert {(r, f) for f, r, _, _ in PROMPT_FIXES} == actual and len(actual) == FIX_PROMPT[0]
prompt_flat, prompt_v1 = " ".join(di_aoai.SYSTEM_PROMPT_V2.split()), " ".join(di_aoai.SYSTEM_PROMPT.split())
for f, r, _, quote in PROMPT_FIXES:
    assert quote in prompt_flat and quote not in prompt_v1, f"not a prompt v2 change: {quote}"
    assert all(V2_DETAIL[(run, r, f)]["result"] == "Correct" for run in V2_RUNS.values())
s = content_slide(
    "What Prompt V2 Changed",
    "Four fields fixed, all by clearer wording. Code checks, layout and photos added nothing.",
    f"Original prompt {AOAI_ACC} ({count(AOAI)}); prompt v2 {AOAI_V2_ACC} ({count(AOAI_V2)}), a development result "
    "because prompt v2 was written after reviewing these errors. The four fixes are in the model's own reply, "
    "before any Python check, in all three prompt v2 runs. The Python checks changed "
    f"{VALIDATION_CHANGES} values; plain-text OCR input ({count(SUM_V2PROMPT['aoai_v2_plain'])}) scores the same as "
    f"the row layout ({count(AOAI_V2)}) and as attaching the photo ({count(SUM_V2PROMPT['aoai_v2_rows_image'])}). "
    "Still wrong: the vet invoice doctor (two practitioners; OCR misread the signature) and the pharmacy service date "
    "(open ground-truth question). Prompt text: receipt_bench/di_aoai.py, commit 034d7d5. " + SOURCE, tag="dev")
tbl = table(s, 0.39, 1.95, [2.0, 3.85, 4.1, 2.6], [0.55] + [0.62] * len(PROMPT_FIXES))
header_row(tbl, ["Field fixed", "Original prompt replied", "Prompt v2 wording added", "Prompt v2 replied"], size=13)
for i, (f, r, where, quote) in enumerate(PROMPT_FIXES, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=FIELD_NAMES[f].replace("Reg. no.", "Registration no."), size=13, bold=True),
                               dict(t=where, size=11, color=GREY_TXT)])
    fill_cell(tbl.cell(i, 1), [dict(runs=[("✗ ", dict(bold=True, color=RED)), (raw_reply("di_aoai", r, f), {})],
                                    size=12.5)], fill=BAD_TINT)
    fill_cell(tbl.cell(i, 2), [dict(t=f"“{quote}”", size=12.5, italic=True)])
    fill_cell(tbl.cell(i, 3), [dict(runs=[("✓ ", dict(bold=True, color=GOOD)),
                                          (raw_reply("di_aoai_v2_rows", r, f), {})], size=12.5)], fill=GOOD_TINT)
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
parts = [("Prompt wording", f"{len(PROMPT_FIXES)} fields fixed", True),
         ("Python checks", f"changed {VALIDATION_CHANGES} values", False),
         ("OCR row layout", f"plain text also {count(SUM_V2PROMPT['aoai_v2_plain'])}", False),
         ("Photo attached", f"also {count(SUM_V2PROMPT['aoai_v2_rows_image'])}", False)]
pw = (12.55 - 3 * 0.2) / 4
for k, (head, body, credit) in enumerate(parts):
    text(s, 0.39 + k * (pw + 0.2), 5.15, pw, 0.75, [dict(t=head, size=14, bold=True, color=RED if credit else CHAR,
                                                         after=2),
                                                    dict(t=body, size=12.5, color=CHAR if credit else GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.16, fill=WHITE if credit else LIGHT, line=RED if credit else None)
note(s, "Development result: prompt v2 was written after reviewing these errors. Still wrong: the vet invoice doctor "
        "and the pharmacy service date.", y=6.05)

# ===================================================================== 8. side-by-side scorecard
s = content_slide(
    "Rules vs. AOAI: Side by Side",
    "AOAI wins on accuracy and effort; rules win on cost and control. New layouts are untested.",
    f"Accuracy: before tuning rules {RANGE_INIT}, AOAI {AOAI_ACC}; after tuning (development results) rules "
    f"{RANGE_TUNED}, AOAI {AOAI_V2_ACC}. Speed = average per receipt: PaddleOCR Light {secs(ORIG['light'])} on Azure "
    f"ML CPU compute, Azure DI {secs(ORIG['di'])}, Azure DI + AOAI {secs(AOAI)} (API time incl. network). Tokens = "
    f"average per receipt with the original prompt ({TOKENS_IN} input, {TOKENS_OUT} output); Document Intelligence "
    "and gpt-5-mini prices are not yet confirmed. Effort and side effects measured on the development set. New "
    "layouts and control are expectations, not measurements. " + SOURCE)
score_rows = [
    ("Accuracy*", f"{RANGE_INIT} first; {RANGE_TUNED} after tuning", f"{AOAI_ACC} first; {AOAI_V2_ACC} after "
                                                                     "prompt v2", "Measured", "ai"),
    ("Speed per receipt", f"{secs(ORIG['light'])} PaddleOCR (CPU) · {secs(ORIG['di'])} Azure DI", f"{secs(AOAI)}",
     "Measured", None),
    ("Running cost", "PaddleOCR: own compute, no API fee · Azure DI: page fee",
     f"Azure DI page fee + ~{TOKENS_IN} input / {TOKENS_OUT} output tokens", "Prices to confirm", "rules"),
    ("Development effort", f"Rules rewritten by hand ({VOCAB_ORIG} → {VOCAB_IMPR} label phrases)",
     "One prompt revision", "Measured", "ai"),
    ("Side effects of changes", f"{FIX_LIGHT[1]} correct field broken by the rule changes",
     f"{FIX_PROMPT[1]} broken by the prompt revision", "Measured", "ai"),
    ("New receipt layouts", "New labels and rules for each layout or language",
     "Expected to adapt without code changes", "Expected", None),
    ("Control and audit", "Deterministic; every decision traceable", "Depends on model and prompt; needs monitoring",
     "Expected", "rules")]
tbl = table(s, 0.39, 1.95, [2.55, 4.3, 4.15, 1.55], [0.5] + [0.5] * len(score_rows))
header_row(tbl, ["", "OCR + rules", "Azure DI + AOAI", "Evidence"], size=14)
for i, (label, rules, ai, ev, better) in enumerate(score_rows, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=label, size=13, bold=True)])
    fill_cell(tbl.cell(i, 1), [dict(t=rules, size=12.5)], fill=GOOD_TINT if better == "rules" else None)
    fill_cell(tbl.cell(i, 2), [dict(t=ai, size=12.5)], fill=GOOD_TINT if better == "ai" else None)
    fill_cell(tbl.cell(i, 3), [dict(t=ev, size=11.5, italic=ev != "Measured", color=GREY_TXT if ev != "Measured"
                                    else CHAR)])
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B")
note(s, "* First = before tuning (the first rules had no Chinese labels); after tuning = development results. "
        "Green = stronger side. Expected = not measured.", y=6.02)

# ===================================================================== 9. diagnosis comment: when rules are enough
s = content_slide(
    "When Rules Are Enough: Diagnosis Check",
    "For a simple yes/no question with clear labels, rules matched AOAI on every receipt.",
    f"Question: does the receipt contain a written comment about the patient's condition, symptoms or diagnosis? "
    f"Ground truth for {DIAG_N} receipts: {DIAG_PRESENT} with a comment, {DIAG_EMPTY} with an empty label. Results "
    "(results/diagnosis/scores): " + ", ".join(f"{k} {v['correct']}/{v['receipts']}" for k, v in DIAG_SUM.items())
    + f". Development result: the rules and the prompt addition were written after reading these receipts. AOAI quoted "
    f"'{LINE_ITEM}' (a condition written as a line item) on one receipt; the rules reached the same answer from a "
    f"'Notes' comment. Adding the check raised AOAI input tokens by about {DIAG_TOKENS_PCT}% and changed none of the "
    "six fields. Details: python/receipt_ocr_benchmark/docs/DIAGNOSIS_COMMENT.md.", tag="dev")
card(s, 0.39, 1.95, 3.7, 3.85, "The question",
     "Does the receipt contain a written comment about the patient's condition, symptoms or diagnosis?",
     head_colour=CHAR, size=15)
text(s, 0.59, 3.45, 3.3, 1.5, [
    dict(t=f"{DIAG_N} receipts", size=14, bold=True, after=2),
    dict(t=f"{DIAG_PRESENT} with a comment", size=13, bullet=True, after=2),
    dict(t=f"{DIAG_EMPTY} with an empty label", size=13, bullet=True, after=2),
    dict(t="English and Chinese labels", size=13, bullet=True)])
for k, (name, key) in enumerate((("PaddleOCR Light + rules", "rules_paddle_light"),
                                 ("Azure DI + rules", "rules_azure_di"), ("Azure DI + AOAI", "aoai_v2"))):
    y = 1.95 + k * 1.3
    r = DIAG_SUM[key]
    text(s, 4.35, y, 3.6, 1.15, [dict(t=f"{r['correct']}/{r['receipts']}", size=30, bold=True,
                                      color=RED if key == "aoai_v2" else CHAR),
                                 dict(t=name, size=12.5, color=GREY_TXT)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2,
         fill=LIGHT)
card(s, 8.2, 1.95, 4.74, 3.85, "What it tells us", [
    "Rules are enough when the answer sits under a clear label (Diagnosis:, Notes:, 診斷) and the question is "
    "yes/no.",
    f"AOAI also spotted a condition written as a line item (\"{LINE_ITEM}\"): unlabelled detail rules cannot see.",
    f"Adding the check to AOAI cost about {DIAG_TOKENS_PCT}% more input tokens and changed none of the six fields.",
    f"But the test was easy for both: only {DIAG_PRESENT} receipts had a comment, all under a label."],
    head_colour=RED, fill=WHITE, line=RED)
note(s, "Development result: rules and prompt written after reading these receipts. Only 3 receipts had a comment.",
     y=6.0)

# ===================================================================== 10. beyond six fields (potential)
EVIDENCE = [("Diagnoses and symptoms", [("receipt9", "Colitis"), ("receipt9", "diarrhoea")], "vet invoice"),
            ("Treatments and tests", [("receipt3", "Chest X-ray"), ("receipt3", "Blood test (CBC)"),
                                      ("receipt4", "針灸"), ("receipt5", "Scaling and polishing")],
             "hospital, Chinese medicine, dental"),
            ("Medications", [("receipt10", "Omeprazole 20mg Capsules"), ("receipt9", "Metronidazole 50mg Tablet")],
             "pharmacy, vet invoice")]
for _, items, _ in EVIDENCE:
    for rcpt, v in items:
        ocr_read(rcpt, v, engines=("azure_di",))
s = content_slide(
    "Beyond Six Fields: What AOAI Could Add",
    "Our receipts already carry medical details that rules ignore. AOAI could turn them into data.",
    "Potential only: we have not built or measured extraction of these fields. The examples are text that Azure DI "
    "already read from our benchmark receipts (checked in the saved OCR output): " + "; ".join(
        f"{h}: " + ", ".join(v for _, v in items) for h, items, _ in EVIDENCE) + ". 針灸 = acupuncture. Possible "
    "uses depend on a pilot with ground truth, accuracy targets, privacy review and cost checks.", tag="potential")
paras = [dict(t="Already in our receipts' OCR text", size=15, bold=True, color=CHAR, after=6)]
for head, items, where in EVIDENCE:
    paras.append(dict(t=head, size=13, bold=True, after=1))
    paras.append(dict(t=" · ".join(v + (" (acupuncture)" if v == "針灸" else "") for _, v in items), size=12.5,
                      after=1))
    paras.append(dict(t=where, size=10.5, color=GREY_TXT, italic=True, after=7))
text(s, 0.39, 1.95, 4.45, 3.65, paras, margin=0.2, fill=LIGHT)
plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 4.95, 3.55, 0.45, 0.4, MID_GREY)
card(s, 5.5, 1.95, 3.1, 3.65, "AOAI could return",
     ["Diagnosis", "Symptoms", "Treatment or procedure", "Medication and dose", "Cost per item"],
     head_colour=RED, fill=WHITE, line=RED, size=15)
plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 8.7, 3.55, 0.45, 0.4, MID_GREY)
card(s, 9.25, 1.95, 3.69, 3.65, "Which could enable",
     ["Claims analytics by diagnosis and treatment", "Cost benchmarks per treatment and provider",
      "Medication patterns", "Consistency checks: treatment vs diagnosis vs amount", "Faster triage for reviewers"],
     head_colour=CHAR, size=13)
text(s, 0.39, 5.72, 12.55, 0.48, [dict(runs=[("Not yet tested. ", dict(bold=True, color=RED)),
                                            ("We have not built or measured extraction of these fields. A pilot needs "
                                             "ground truth, accuracy targets, a privacy review and cost checks.", {})],
                                       size=13)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)

# ===================================================================== 11. limitations
s = content_slide(
    "Limits of What We Know",
    "The evidence points one way, but it is not yet proof.",
    f"{N_RECEIPTS} receipts and {APPLICABLE} fields; 7 are printed, fictional test receipts. The original rules had no "
    "Chinese labels, so the initial gap overstates what rules can do. Rules and prompt v2 were tuned on the same "
    f"receipts, so their later scores are development results. Unseen test: {N_UNSEEN} handwritten Version 1 "
    f"receipts not used for tuning ({N_V1} receipts in all); on all {N_UNSEEN}, Azure DI read the handwritten year "
    "2026 as 2020 (checked in results/v1_heldout), an OCR error that no extraction step can fix. Prices are not "
    "confirmed. " + SOURCE)
limits = [("Small sample", f"{N_RECEIPTS} receipts, {APPLICABLE} fields. 7 are printed test receipts."),
          ("Rules started without Chinese", f"The first gap ({RANGE_INIT} vs {AOAI_ACC}) overstates what rules can "
                                            "do."),
          ("Tuned on the same receipts", f"Later scores (rules {RANGE_TUNED}, AOAI {AOAI_V2_ACC}) are development "
                                         "results."),
          ("Little unseen testing", f"Only {N_UNSEEN} unseen handwritten receipts: too few to compare. On all "
                                    f"{N_UNSEEN}, Azure DI misread the year 2026 as 2020."),
          ("Costs not confirmed", "Token counts are measured; Document Intelligence and gpt-5-mini prices are not.")]
cw = (12.55 - 2 * 0.3) / 3
for k, (head, body) in enumerate(limits):
    row, col = divmod(k, 3)
    x = 0.39 + col * (cw + 0.3) + (row * (cw + 0.3) / 2)
    text(s, x, 1.95 + row * 2.0, cw, 1.8, [dict(t=f"{k + 1}", size=26, bold=True, color=RED, after=2),
                                          dict(t=head, size=15, bold=True, after=4),
                                          dict(t=body, size=13)], margin=0.22, fill=LIGHT)

# ===================================================================== 12. recommendation
s = content_slide(
    "Recommendation",
    "Not a general replacement: rules for simple, labelled tasks; AOAI where receipts vary or richer data is needed.",
    "Rules are sufficient where the task is simple and labelled and the layouts are known and stable (shown on the "
    "diagnosis-comment check and, after tuning, on the six fields of these receipts). AOAI adds value where layouts "
    "and languages vary, where fields have no consistent labels, and for richer medical information (potential, not "
    "yet tested). Next steps: freeze the improved rules and prompt v2; test on 30+ unseen, real, anonymised "
    "receipts and count the rule changes needed; pilot the extra medical fields with ground truth; confirm prices. "
    + SOURCE)
card(s, 0.39, 1.95, 6.12, 2.3, "Simple OCR rules are sufficient when…", [
    "Layouts are few, known and stable",
    "Fields have clear printed labels",
    "The question is simple, e.g. is a diagnosis comment present?",
    "No API fee or fully deterministic output is required"], head_colour=GOOD, fill=GOOD_TINT, size=14)
card(s, 6.82, 1.95, 6.12, 2.3, "AOAI adds real value when…", [
    "Many providers, layouts and languages (Chinese, bilingual)",
    "Fields lack consistent labels: names with titles, totals vs subtotals",
    "New fields should be added by changing a prompt, not code",
    "Richer medical data is wanted (potential, not yet tested)"], head_colour=RED, fill=WHITE, line=RED, size=14)
steps = [("1. Freeze", "the improved rules and AOAI prompt v2"),
         ("2. Test unseen", "30+ real, anonymised receipts; count rule changes"),
         ("3. Pilot extra fields", "diagnoses, treatments, medications with ground truth"),
         ("4. Confirm cost", "Document Intelligence pages and gpt-5-mini tokens")]
sw = (12.55 - 3 * 0.25) / 4
for i, (head, desc) in enumerate(steps):
    text(s, 0.39 + i * (sw + 0.25), 4.5, sw, 1.1, [dict(t=head, size=15, bold=True, color=RED, after=3),
                                                   dict(t=desc, size=12.5)], margin=0.18, fill=LIGHT)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
