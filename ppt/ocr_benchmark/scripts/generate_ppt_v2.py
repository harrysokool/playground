"""Generate the Version 2 Receipt OCR Benchmark deck (12 slides) from the AIA template.

Run on Azure ML compute, from the repository root:
    python3 ppt/ocr_benchmark/scripts/generate_ppt_v2.py            # writes current/OCR_Benchmark_V2.pptx
    python3 ppt/ocr_benchmark/scripts/generate_ppt_v2.py --force    # overwrite an existing output

Source of truth (all committed under python/receipt_ocr_benchmark/):
- results/v2/scores_improved/summary.csv and detail.csv: every accuracy and timing figure, and every
  value shown in the receipt examples;
- results/v2/<approach dir>/receiptN.json: each example value is cross-checked against these files,
  and the build stops if they disagree with detail.csv;
- results/v2/azure_di/receiptN.json: Azure DI's text positions, used to crop and highlight the receipt
  areas (no hand-entered coordinates). The build stops if a crop's text is not found;
- data/receipts_v2/benchmark_inputs/ -> printable_images/: the receipt photos (turned upright with
  their EXIF orientation, as the benchmark inputs were).

Receipt crops and thumbnails are written to ppt/ocr_benchmark/assets_v2/ so the deck can be
reproduced and reviewed. Requires python-pptx and Pillow. The frozen Version 1 deck is in archive/v1/
and is never written to.
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
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent.parent
BENCH = REPO / "python" / "receipt_ocr_benchmark"
RES = BENCH / "results" / "v2"
ASSETS = PROJECT / "assets_v2"
DECK_NAME = "OCR_Benchmark_V2"
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
ASSETS.mkdir(exist_ok=True)

# ===================================================================== benchmark data (source of truth)
ORIG = {"light": "paddle_light_general", "heavy": "paddle_heavy_general", "di": "azure_di_general"}
IMPR = {"light": "paddle_light_improved", "heavy": "paddle_heavy_improved", "di": "azure_di_improved"}
AOAI = "azure_di_aoai"
ENGINE = {"light": "PaddleOCR Light", "heavy": "PaddleOCR Heavy", "di": "Azure DI"}
RESULT_DIR = {"paddle_light_general": "extracted_general_light", "paddle_light_improved": "extracted_improved_light",
              "paddle_heavy_general": "extracted_general_heavy", "paddle_heavy_improved": "extracted_improved_heavy",
              "azure_di_general": "extracted_general_azure_di", "azure_di_improved": "extracted_improved_azure_di",
              "azure_di_aoai": "di_aoai"}
FIELD_NAMES = {"doctor_name": "Doctor", "registration_number": "Reg. no.", "patient_name": "Patient",
               "receipt_number": "Receipt no.", "service_date": "Service date", "total_amount": "Total amount"}
FIELDS = list(FIELD_NAMES)

with open(RES / "scores_improved" / "summary.csv", newline="") as fh:
    SUM = {r["approach"]: r for r in csv.DictReader(fh)}
with open(RES / "scores_improved" / "detail.csv", newline="") as fh:
    DETAIL = {(r["approach"], r["receipt"], r["field"]): r for r in csv.DictReader(fh)}
assert set(SUM) == set(RESULT_DIR), f"unexpected approaches in summary.csv: {sorted(SUM)}"
RECEIPTS = sorted({k[1] for k in DETAIL}, key=lambda s: int(s.replace("receipt", "")))
N_RECEIPTS, APPLICABLE = len(RECEIPTS), int(SUM[AOAI]["applicable"])
assert all(int(SUM[a]["applicable"]) == APPLICABLE for a in SUM)


def acc(a):
    return float(SUM[a]["accuracy_pct"])


def correct(a):
    return int(SUM[a]["correct"])


def secs(a):
    return int(SUM[a]["mean_ms_per_receipt"]) / 1000


def processed(a):
    return N_RECEIPTS - int(SUM[a]["no_result_receipts"])


NEW = [r for r in RECEIPTS if r not in ("receipt9", "receipt10")]  # the seven photographed v2 receipts


def subset(a, receipts):
    rows = [DETAIL[(a, r, f)] for r in receipts for f in FIELDS if (a, r, f) in DETAIL]
    app = [x for x in rows if x["result"] in ("Correct", "Wrong")]
    return sum(x["result"] == "Correct" for x in app), len(app)


def field_score(a, f):
    rows = [DETAIL[(a, r, f)] for r in RECEIPTS if DETAIL[(a, r, f)]["result"] in ("Correct", "Wrong")]
    return sum(x["result"] == "Correct" for x in rows), len(rows)


def json_value(approach, receipt, field):
    data = json.loads((RES / RESULT_DIR[approach] / f"{receipt}.json").read_text())
    v = data.get(field)
    return "" if v is None else str(v)


def example(approach, receipt, field):
    """(shown value, correct?) from detail.csv, cross-checked against the extraction JSON."""
    row = DETAIL[(approach, receipt, field)]
    jv = json_value(approach, receipt, field)
    if jv != row["predicted"]:
        sys.exit(f"Mismatch {approach} {receipt} {field}: detail.csv {row['predicted']!r} vs JSON {jv!r}")
    return (row["predicted"] or "(not found)"), row["result"] == "Correct"


def truth(receipt, field):
    return DETAIL[(AOAI, receipt, field)]["ground_truth"]


TOKENS_IN = int(SUM[AOAI]["aoai_input_tokens"]) / N_RECEIPTS
TOKENS_OUT = int(SUM[AOAI]["aoai_output_tokens"]) / N_RECEIPTS
def _mean_extract_ms(kind):
    ms = [json.loads(p.read_text())["timings"]["extract_ms"]
          for d in (f"extracted_{kind}_light", f"extracted_{kind}_heavy", f"extracted_{kind}_azure_di")
          for p in sorted((RES / d).glob("receipt*.json"))]
    return sum(ms) / len(ms)


EXTRACT_MS = {"original": _mean_extract_ms("general"), "improved": _mean_extract_ms("improved")}
EXTRACT_TXT = f"{min(EXTRACT_MS.values()):.0f}–{max(EXTRACT_MS.values()):.0f} ms"
HEAVY_BLOCKS = {r: len(json.loads((RES / "paddle_heavy" / f"{r}.json").read_text())["pages"][0]["blocks"])
                for r in ("receipt2", "receipt5")}

# ===================================================================== receipt images and crops
INPUTS = BENCH / "data" / "receipts_v2" / "benchmark_inputs"


def receipt_image(receipt: str) -> Image.Image:
    src = next(p for p in INPUTS.iterdir() if p.stem == receipt).resolve()
    return ImageOps.exif_transpose(Image.open(src)).convert("RGB")


def di_blocks(receipt: str):
    page = json.loads((RES / "azure_di" / f"{receipt}.json").read_text())["pages"][0]
    blocks = [(b["text"], min(p[0] for p in b["polygon"]), min(p[1] for p in b["polygon"]),
               max(p[0] for p in b["polygon"]), max(p[1] for p in b["polygon"])) for b in page["blocks"]]
    return (page["width"], page["height"]), blocks


def find_boxes(receipt: str, needles):
    (w, h), blocks = di_blocks(receipt)
    boxes = []
    for n in needles:
        hit = next((b for b in blocks if n in b[0]), None)
        if hit is None:
            sys.exit(f"{receipt}: text {n!r} not found in Azure DI output; cannot place the crop")
        boxes.append(hit[1:])
    return (w, h), boxes


def make_crop(receipt: str, needles, name: str, highlight=None, max_px=1800):
    """Crop around the DI boxes of `needles` (union + margin), outline the `highlight` boxes, save JPEG."""
    img = receipt_image(receipt)
    (w, h), boxes = find_boxes(receipt, needles)
    if img.size != (w, h):
        sys.exit(f"{receipt}: image {img.size} does not match the Azure DI page {(w, h)}")
    m = int(0.03 * w)
    x0, y0 = max(0, min(b[0] for b in boxes) - m), max(0, min(b[1] for b in boxes) - m)
    x1, y1 = min(w, max(b[2] for b in boxes) + m), min(h, max(b[3] for b in boxes) + m)
    draw = ImageDraw.Draw(img)
    lw = max(3, w // 500)
    for b in (find_boxes(receipt, highlight)[1] if highlight else []):
        draw.rectangle([b[0] - lw * 2, b[1] - lw * 2, b[2] + lw * 2, b[3] + lw * 2], outline=(211, 17, 69), width=lw)
    crop = img.crop((x0, y0, x1, y1))
    crop.thumbnail((max_px, max_px))
    path = ASSETS / f"{name}.jpg"
    crop.save(path, quality=90)
    return path, (x0, y0, x1, y1)


def make_thumb(receipt: str, name: str, regions=(), max_px=900):
    """Whole receipt, with the cropped regions outlined."""
    img = receipt_image(receipt)
    draw = ImageDraw.Draw(img)
    lw = max(6, img.width // 150)
    for r in regions:
        draw.rectangle(r, outline=(211, 17, 69), width=lw)
    img.thumbnail((max_px, max_px))
    path = ASSETS / f"{name}.jpg"
    img.save(path, quality=88)
    return path


# ===================================================================== style (as the Version 1 deck)
RED = RGBColor(0xD3, 0x11, 0x45)
CHAR = RGBColor(0x33, 0x3D, 0x47)
GREY_TXT = RGBColor(0x5F, 0x67, 0x70)
MID_GREY = RGBColor(0xA6, 0xAB, 0xB0)
LIGHT = RGBColor(0xF2, 0xF2, 0xF2)
TINT = RGBColor(0xFB, 0xE7, 0xEC)
GOOD = RGBColor(0x1E, 0x7B, 0x4A)
GOOD_TINT = RGBColor(0xE6, 0xF2, 0xEA)
LINE = "BFBFBF"
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT, FONT_ZH = "Arial", "Microsoft JhengHei"

prs = Presentation(args.template)
for sh in prs.slide_master.shapes:  # keep the sensitivity marking on one line (label applied in PowerPoint)
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
    rPr = r._r.get_or_add_rPr()  # Traditional Chinese glyphs: an East Asian font
    for e in rPr.findall(qn("a:ea")):
        rPr.remove(e)
    ea = etree.SubElement(rPr, qn("a:ea"))
    ea.set("typeface", FONT_ZH)


def set_runs(tf, text_, size=None, bold=None, color=None):
    p = tf.paragraphs[0]
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    r = p.add_run()
    r.text = text_
    style_run(r, size, bold, color)
    return r


def bullet(p, indent=0.18):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent))))
    pPr.set("indent", str(-int(Inches(indent))))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for e in pPr.findall(qn(tag)):
            pPr.remove(e)
    bf = etree.SubElement(pPr, qn("a:buFont")); bf.set("typeface", FONT)
    bc = etree.SubElement(pPr, qn("a:buChar")); bc.set("char", "•")


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


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.0, fill=None):
    box = plain_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h, fill) if fill is not None else \
        slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
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
            style_run(r, o.get("size", pd.get("size", 13)), o.get("bold", pd.get("bold", False)),
                      o.get("color", pd.get("color", CHAR)), o.get("italic", pd.get("italic", False)))
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


def footnote(s, t, y=6.2, w=11.6):
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
        tcPr.remove(f); tcPr.append(f)


def fill_cell(cell, paras, fill=None, anchor=MSO_ANCHOR.MIDDLE):
    tf = cell.text_frame
    tf.word_wrap = True
    cell.margin_left = cell.margin_right = Inches(0.08)
    cell.margin_top = cell.margin_bottom = Inches(0.05)
    cell.vertical_anchor = anchor
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = pd.get("align", PP_ALIGN.LEFT)
        for t, o in pd.get("runs") or [(pd["t"], {})]:
            r = p.add_run(); r.text = t
            style_run(r, o.get("size", pd.get("size", 12)), o.get("bold", pd.get("bold", False)),
                      o.get("color", pd.get("color", CHAR)), o.get("italic", pd.get("italic", False)))
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
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for i, rh in enumerate(row_h):
        tbl.rows[i].height = Inches(rh)
    return tbl


def chart(s, x, y, w, h, categories, series, number_format, horizontal=False, legend=False, max_value=None):
    """series: list of (name, values, color). A single series may be a list of colors (one per bar)."""
    data = CategoryChartData()
    data.categories = categories
    for name, values, _ in series:
        data.add_series(name, values)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    ch = s.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), data).chart
    ch.has_title = False
    ch.font.name = FONT; ch.font.size = Pt(12); ch.font.color.rgb = CHAR
    ch.has_legend = legend
    if legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(12)
    plot = ch.plots[0]
    plot.gap_width = 60 if len(series) == 1 else 50
    plot.overlap = 0 if len(series) > 1 else plot.overlap
    plot.vary_by_categories = False
    for ser, (_, values, color) in zip(plot.series, series):
        if not isinstance(color, list):  # series colour drives the legend marker
            ser.format.fill.solid(); ser.format.fill.fore_color.rgb = color
        colors = color if isinstance(color, list) else [color] * len(values)
        for i, c in enumerate(colors):
            if values[i] is None:
                continue
            pt = ser.points[i]
            pt.format.fill.solid(); pt.format.fill.fore_color.rgb = c
            pt.format.line.fill.background()
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = number_format
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(13); dl.font.bold = True; dl.font.name = FONT; dl.font.color.rgb = CHAR
    va = ch.value_axis
    va.visible = False
    va.has_major_gridlines = False
    va.minimum_scale = 0
    va.maximum_scale = max_value
    ca = ch.category_axis
    ca.format.line.color.rgb = MID_GREY
    ca.tick_labels.font.size = Pt(12); ca.tick_labels.font.name = FONT
    if horizontal:
        ca.reverse_order = True
    return ch


def picture(s, path, x, y, max_w, max_h):
    """Image fitted inside (max_w x max_h) inches, keeping its aspect ratio; returns its box."""
    with Image.open(path) as im:
        ar = im.width / im.height
    w, h = (max_w, max_w / ar) if max_w / ar <= max_h else (max_h * ar, max_h)
    pic = s.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.line.color.rgb = RGBColor(0xBF, 0xBF, 0xBF)
    pic.line.width = Pt(0.75)
    return x, y, w, h


def mark(ok: bool):
    return ("✓ ", dict(bold=True, color=GOOD)) if ok else ("✗ ", dict(bold=True, color=RED))


def example_table(s, x, y, receipt, fields, engine="light", col_w=(1.0, 1.15, 1.3, 1.3, 1.45), row_h=0.55):
    """Ground truth vs original rules vs improved rules vs DI + AOAI, values from detail.csv."""
    tbl = table(s, x, y, list(col_w), [0.62] + [row_h] * len(fields))
    heads = ["Field", "Correct value", f"Original rules\n({ENGINE[engine]})", f"Improved rules\n({ENGINE[engine]})",
             "Azure DI + AOAI"]
    for c, hd in enumerate(heads):
        fill_cell(tbl.cell(0, c), [dict(t=hd, size=10, bold=True, color=WHITE)], fill=CHAR)
        cell_border(tbl.cell(0, c), sides="")
    for i, f in enumerate(fields, start=1):
        fill_cell(tbl.cell(i, 0), [dict(t=FIELD_NAMES[f], size=10.5, bold=True)])
        fill_cell(tbl.cell(i, 1), [dict(t=truth(receipt, f), size=10.5)])
        for c, a in enumerate((ORIG[engine], IMPR[engine], AOAI), start=2):
            v, ok = example(a, receipt, f)
            fill_cell(tbl.cell(i, c), [dict(runs=[mark(ok), (v, dict(color=CHAR if v != "(not found)" else GREY_TXT))],
                                            size=10.5)], fill=GOOD_TINT if ok else TINT)
        for c in range(5):
            cell_border(tbl.cell(i, c), sides="B", color="FFFFFF", w=19050)
    return tbl


SOURCE = "Source: python/receipt_ocr_benchmark/results/v2/scores_improved (detail.csv, summary.csv) and extraction JSON."

# ===================================================================== slide 1: title
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Medical Receipt OCR Benchmark")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(0.39), Inches(4.5), Inches(6.3), Inches(0.9)
set_runs(sub.text_frame, "Traditional OCR with rules vs Azure AI extraction")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = f"Version 2 results · {N_RECEIPTS} receipts · {APPLICABLE} scored fields"; style_run(r)
s.notes_slide.notes_text_frame.text = (
    "Purpose: decide whether Azure Document Intelligence plus Azure OpenAI is worth its cost and complexity "
    "compared with OCR plus fixed rules. All figures come from the Version 2 benchmark results. " + SOURCE)

# ===================================================================== slide 2: business problem
s = content_slide(
    "Business Problem and Objective",
    "Every medical claim needs the same few fields from a receipt; we tested how well that can be automated.",
    "We focus on six fields a claim needs. The question is not only accuracy but also cost, speed, reliability "
    "and how much ongoing effort each option needs.")
text(s, 0.39, 2.0, 5.6, 3.2, [
    dict(t="THE QUESTION", size=11, bold=True, color=GREY_TXT, after=10),
    dict(t="Is Azure Document Intelligence + Azure OpenAI worth its extra cost and complexity?", size=21,
         bold=True, color=RED, after=14),
    dict(t="Compared with open-source OCR plus fixed extraction rules that run on our own compute.", size=14),
], margin=0.28, fill=LIGHT)
fields_txt = ["Doctor name", "Registration number", "Patient name", "Receipt number", "Service date", "Total amount"]
text(s, 6.29, 2.0, 3.0, 3.2, [dict(t="SIX FIELDS PER RECEIPT", size=11, bold=True, color=GREY_TXT, after=10)] +
     [dict(t=f, size=14, bullet=True, after=6) for f in fields_txt], margin=0.28, fill=LIGHT)
text(s, 9.59, 2.0, 3.35, 3.2, [dict(t="JUDGED ON", size=11, bold=True, color=GREY_TXT, after=10)] +
     [dict(t=f, size=14, bullet=True, after=6) for f in
      ("Accuracy", "Speed", "Reliability", "Cost", "Maintenance effort")], margin=0.28, fill=LIGHT)

# ===================================================================== slide 3: methodology
s = content_slide(
    "Methodology",
    "Two steps per receipt: read the text (OCR), then find the six fields. We changed one step at a time.",
    f"{N_RECEIPTS} receipts, {APPLICABLE} fields that exist on them (fields not printed on a receipt are excluded). "
    "Three OCR engines feed the same fixed rules; the fourth approach replaces the rules with Azure OpenAI. "
    "The improved rules were written after examining these receipts, so their scores are tuned results. " + SOURCE)
rows3 = [("1", "PaddleOCR Light", "Open-source OCR, small model", "Rules: original, then improved"),
         ("2", "PaddleOCR Heavy", "Open-source OCR, large model", "Rules: original, then improved"),
         ("3", "Azure DI", "Cloud OCR (prebuilt-read)", "Rules: original, then improved"),
         ("4", "Azure DI + AOAI", "Cloud OCR (prebuilt-read)", "Azure OpenAI gpt-5-mini (prompt unchanged)")]
text(s, 2.95, 1.9, 4.2, 0.3, [dict(t="STEP 1 · READ THE TEXT (OCR)", size=11, bold=True, color=GREY_TXT)])
text(s, 7.45, 1.9, 4.2, 0.3, [dict(t="STEP 2 · FIND THE SIX FIELDS", size=11, bold=True, color=GREY_TXT)])
for i, (num, name, ocr, ext) in enumerate(rows3):
    y = 2.3 + i * 0.86
    c = plain_shape(s, MSO_SHAPE.OVAL, 0.39, y + 0.15, 0.42, 0.42, CHAR)
    set_runs(c.text_frame, num, size=14, bold=True, color=WHITE); c.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    text(s, 0.95, y, 1.9, 0.72, [dict(t=name, size=14, bold=True)], anchor=MSO_ANCHOR.MIDDLE)
    cloud_ocr, cloud_ext = num in ("3", "4"), num == "4"
    for bx, label, cloud in ((2.95, ocr, cloud_ocr), (7.45, ext, cloud_ext)):
        text(s, bx, y, 4.2, 0.72, [dict(t=label, size=13, bold=cloud, color=WHITE if cloud else CHAR)],
             anchor=MSO_ANCHOR.MIDDLE, margin=0.16, fill=RED if cloud else LIGHT)
    plain_shape(s, MSO_SHAPE.CHEVRON, 7.18, y + 0.2, 0.22, 0.32, MID_GREY)
text(s, 11.9, 2.3, 1.05, 3.3, [dict(t=f"{N_RECEIPTS} receipts", size=13, bold=True, after=6),
                               dict(t=f"{APPLICABLE} fields scored", size=13, bold=True, after=6),
                               dict(t="Red = paid Azure call", size=11, color=GREY_TXT)], margin=0.1)

# ===================================================================== slide 4: receipt diversity
show = [("receipt1", "GP clinic · English"), ("receipt3", "Hospital invoice · bilingual"),
        ("receipt4", "Chinese medicine · Chinese")]
s = content_slide(
    "The Receipts: Different Layouts and Languages",
    "Seven new printed receipts photographed by phone, plus two receipts carried over from Version 1.",
    "Shown: three of the nine benchmark images. The full set: GP clinic, specialist, hospital invoice, Chinese "
    "medicine, dental, physiotherapy, medical centre (new, photographed); a vet invoice and a New Zealand pharmacy "
    "receipt (from Version 1). Images: python/receipt_ocr_benchmark/data/receipts_v2/printable_images.")
for i, (rcpt, label) in enumerate(show):
    path = make_thumb(rcpt, f"thumb_{rcpt}")
    x, y, w, h = picture(s, path, 0.39 + i * 2.95, 1.95, 2.75, 3.75)
    text(s, x, y + h + 0.08, 2.75, 0.3, [dict(t=label, size=11, color=GREY_TXT)])
text(s, 9.3, 1.95, 3.64, 4.05, [
    dict(t="ALL NINE RECEIPTS", size=11, bold=True, color=GREY_TXT, after=8),
    dict(t="English: GP, specialist, physiotherapy", size=12.5, bullet=True, after=5),
    dict(t="Bilingual: hospital, dental, medical centre", size=12.5, bullet=True, after=5),
    dict(t="Traditional Chinese: Chinese medicine", size=12.5, bullet=True, after=5),
    dict(t="From Version 1: vet invoice, NZ pharmacy", size=12.5, bullet=True, after=12),
    dict(t="Several include distractors such as referring doctors, issue dates, patient numbers, insurer "
           "payments and balances.",
         size=12, color=GREY_TXT),
], margin=0.25, fill=LIGHT)

# ===================================================================== slide 5: original accuracy
orig4 = [ORIG["light"], ORIG["heavy"], ORIG["di"], AOAI]
names4 = ["PaddleOCR Light", "PaddleOCR Heavy", "Azure DI", "Azure DI + AOAI"]
s = content_slide(
    "Accuracy with the Original Rules",
    f"Azure DI + AOAI {acc(AOAI):.1f}%; the three rule-based approaches {min(acc(a) for a in orig4[:3]):.1f}–"
    f"{max(acc(a) for a in orig4[:3]):.1f}%.",
    "Accuracy = correct fields / fields that exist on the receipts. The OCR engines read most of the text "
    "correctly; the original fixed rules then failed to pick the fields on new, bilingual and Chinese layouts "
    "(see FINAL_ANALYSIS.md). " + SOURCE)
chart(s, 0.39, 1.95, 7.6, 4.15, [f"{n}\n{correct(a)}/{APPLICABLE}" for n, a in zip(names4, orig4)],
      [("Accuracy", [acc(a) / 100 for a in orig4], [MID_GREY, MID_GREY, MID_GREY, RED])], "0.0%", max_value=1.0)
text(s, 8.3, 2.0, 4.64, 3.95, [
    dict(t="TWO DIFFERENT STEPS", size=11, bold=True, color=GREY_TXT, after=8),
    dict(t="Text recognition (OCR)", size=15, bold=True, after=2),
    dict(t="Azure DI and PaddleOCR Light read almost every value correctly on the new receipts.", size=12.5,
         after=12),
    dict(t="Field extraction", size=15, bold=True, after=2),
    dict(t="The original rules only knew English labels and missed bilingual and Chinese layouts. "
           "This is where most errors came from.", size=12.5),
], margin=0.25, fill=LIGHT)
footnote(s, f"{N_RECEIPTS} receipts, {APPLICABLE} applicable fields. " + SOURCE)

# ===================================================================== slides 6, 7, 9: receipt examples


def example_slide(title, message, notes, receipt, crop_needles, highlight, fields, crops_extra=None):
    s = content_slide(title, message, notes)
    crop, region = make_crop(receipt, crop_needles, f"crop_{receipt}", highlight)
    regions = [region]
    extra = None
    if crops_extra:
        extra, region2 = make_crop(receipt, crops_extra[0], f"crop_{receipt}_b", crops_extra[1])
        regions.append(region2)
    thumb = make_thumb(receipt, f"thumb_{receipt}_marked", regions)
    picture(s, thumb, 0.39, 1.95, 1.25, 4.1)
    if extra:
        _, _, _, h1 = picture(s, crop, 1.84, 1.95, 4.7, 1.3)
        picture(s, extra, 1.84, 1.95 + h1 + 0.15, 4.7, 4.1 - h1 - 0.15)
    else:
        picture(s, crop, 1.84, 1.95, 4.7, 4.1)
    example_table(s, 6.74, 1.95, receipt, fields)
    return s


s = example_slide(
    "Example 1: Bilingual Labels (Medical Centre)",
    "The original rules read the Chinese half of a label as the value; the improved rules and AOAI do not.",
    "Receipt8 (medical centre). Labels such as 'Patient 病人' put the value in a separate block. The original "
    "rules took the Chinese label '病人' as the patient's name and missed other fields; Azure DI with the original "
    "rules also returned '主診醫生' as the doctor. The improved rules strip label translations; AOAI read the text "
    "correctly with its unchanged prompt. Values from detail.csv, checked against the extraction JSON. " + SOURCE,
    "receipt8",
    ["Patient 病人", "蔡嘉穎", "Attending Doctor", "Dr. Siu Ka Wai"],
    ["Patient 病人", "蔡嘉穎", "Attending Doctor", "Dr. Siu Ka Wai"],
    ["patient_name", "doctor_name", "registration_number", "receipt_number", "service_date"])
footnote(s, "Rules shown on PaddleOCR Light text; Azure DI with the original rules made the same patient error. "
            "✓ correct · ✗ wrong or missing.")

s = example_slide(
    "Example 2: Chinese-Only Receipt (Chinese Medicine)",
    "The original rules found nothing; the improved rules and AOAI found all six fields.",
    "Receipt4 (Traditional Chinese medicine). Every value was read correctly by the OCR, but the original rules "
    "only knew English labels. The improved rules add Traditional Chinese labels (病人姓名, 主診中醫師, 註冊中醫編號, "
    "診症日期, 合計) and Chinese dates. AOAI's date is shown as it returned it (2026年6月9日); the scorer reads it as "
    "the same date. " + SOURCE,
    "receipt4",
    ["收據編號", "病人姓名", "診症日期", "主診中醫師", "註冊中醫編號", "006821", "合計", "$790.00"],
    ["麥詠琳", "葉卓謙", "006821", "2026年6月9日", "$790.00"],
    ["patient_name", "doctor_name", "registration_number", "service_date", "total_amount"])
footnote(s, "Rules shown on PaddleOCR Light text; Azure DI and Heavy behaved the same. ✓ correct · ✗ wrong or missing.")

# ===================================================================== slide 8: before vs after
s = content_slide(
    "Accuracy Before and After Improving the Rules",
    f"Improved rules lifted PaddleOCR Light to {acc(IMPR['light']):.1f}% and Azure DI to {acc(IMPR['di']):.1f}% "
    f"— on the receipts they were tuned on.",
    "Original vs improved rules on the same OCR text; Azure DI + AOAI is unchanged. The improved rules were "
    "written after examining these nine receipts, so their scores are tuned results, not accuracy on unseen "
    "receipts. The AOAI prompt was not changed. " + SOURCE)
cats = ["PaddleOCR Light", "PaddleOCR Heavy", "Azure DI", "Azure DI + AOAI"]
chart(s, 0.39, 1.9, 7.8, 4.2, cats, [
    ("Original rules", [acc(ORIG["light"]) / 100, acc(ORIG["heavy"]) / 100, acc(ORIG["di"]) / 100, None], MID_GREY),
    ("Improved rules (tuned on these receipts)", [acc(IMPR["light"]) / 100, acc(IMPR["heavy"]) / 100,
                                                  acc(IMPR["di"]) / 100, None], RED),
    ("AOAI (unchanged prompt)", [None, None, None, acc(AOAI) / 100], CHAR),
], "0.0%", legend=True, max_value=1.0)
new_rows = [(ENGINE["light"] + " (improved)", subset(IMPR["light"], NEW)), (ENGINE["di"] + " (improved)",
            subset(IMPR["di"], NEW)), (ENGINE["heavy"] + " (improved)", subset(IMPR["heavy"], NEW)),
            ("Azure DI + AOAI", subset(AOAI, NEW))]
tbl = table(s, 8.45, 2.0, [2.9, 1.6], [0.5] + [0.45] * 4)
fill_cell(tbl.cell(0, 0), [dict(t=f"{len(NEW)} new receipts", size=11, bold=True, color=WHITE)], fill=CHAR)
fill_cell(tbl.cell(0, 1), [dict(t="Correct", size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)], fill=CHAR)
for i, (n, (k, t_)) in enumerate(new_rows, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=n, size=11.5)])
    fill_cell(tbl.cell(i, 1), [dict(t=f"{k}/{t_}", size=12, bold=True, align=PP_ALIGN.CENTER)])
    for c in (0, 1):
        cell_border(tbl.cell(i, c), sides="B")
text(s, 8.45, 4.55, 4.5, 1.45, [
    dict(t="Read with care", size=12, bold=True, color=RED, after=4),
    dict(t="Equal scores here do not mean equal accuracy on unfamiliar receipts: the rules were tuned on these "
           "receipts, the AOAI prompt was not.", size=11.5),
], margin=0.18, fill=TINT)
footnote(s, f"{APPLICABLE} applicable fields per approach. " + SOURCE)

# ===================================================================== slide 9: limitations example
s = example_slide(
    "Example 3: What Still Goes Wrong (Vet Invoice)",
    "Each approach fails differently: a rule change picked the wrong number, AOAI picked the subtotal.",
    "Receipt9 (vet invoice carried over from Version 1). The improved rules now reach the 'Receipt #' column in "
    "the payments table (380048) instead of the invoice number; the ground truth uses the invoice number (an open "
    "policy question). The OCR glued a stray 'F' to 'FClinician' and 'FPatient', so no rule recognises those "
    "labels. AOAI chose the sub total 1361.50 instead of the total 1361.00, and both clinicians are expected by "
    f"the ground truth. Separately, PaddleOCR Heavy detected only {HEAVY_BLOCKS['receipt2']} and "
    f"{HEAVY_BLOCKS['receipt5']} text blocks on receipts 2 and 5, so no rule could help there. " + SOURCE,
    "receipt9",
    ["Invoice No", "FClinician"], ["Invoice No", "FClinician"],
    ["receipt_number", "patient_name", "doctor_name", "total_amount"],
    crops_extra=(["Sub Total", "HKD 1361.50", "Total Amount", "HKD 1361.00", "Details of Payments Received",
                  "Receipt #", "380048"],
                 ["Sub Total", "HKD 1361.50", "Total Amount", "HKD 1361.00", "Receipt #", "380048"]))
footnote(s, f"PaddleOCR Heavy also found almost no text on two photos ({HEAVY_BLOCKS['receipt2']} and "
            f"{HEAVY_BLOCKS['receipt5']} text blocks): an OCR failure no rule can fix. ✓ correct · ✗ wrong or missing.")

# ===================================================================== slide 10: speed, reliability, cost
speed = [IMPR["light"], IMPR["heavy"], IMPR["di"], AOAI]
s = content_slide(
    "Speed, Reliability and Cost",
    f"Azure DI is fastest ({secs(IMPR['di']):.1f} s); every approach processed all {N_RECEIPTS} receipts.",
    f"Average seconds per receipt. PaddleOCR = CPU on Azure ML compute; Azure = API call time including network. "
    f"Rule extraction adds {EXTRACT_TXT} (original rules {EXTRACT_MS['original']:.1f} ms, improved "
    f"{EXTRACT_MS['improved']:.1f} ms on average). AOAI tokens are averages over the {N_RECEIPTS} receipts. "
    "Prices (compute, Document Intelligence pages, gpt-5-mini tokens) are not yet confirmed. " + SOURCE)
chart(s, 0.39, 1.9, 7.6, 4.2, names4, [("Seconds", [round(secs(a), 1) for a in speed],
                                        [RED, MID_GREY, RED, RED])], '0.0" s"', horizontal=True,
      max_value=max(secs(a) for a in speed) * 1.2)
all_ok = all(processed(a) == N_RECEIPTS for a in SUM)
text(s, 8.3, 1.95, 4.64, 1.55, [
    dict(t="RELIABILITY", size=11, bold=True, color=GREY_TXT, after=4),
    dict(t=f"{N_RECEIPTS} / {N_RECEIPTS}" if all_ok else "see notes", size=30, bold=True, color=RED, after=2),
    dict(t="receipts processed by every approach, no failed requests", size=12),
], margin=0.22, fill=LIGHT)
text(s, 8.3, 3.7, 4.64, 2.3, [
    dict(t="COST DRIVERS (MEASURED)", size=11, bold=True, color=GREY_TXT, after=6),
    dict(t=f"Rules: {EXTRACT_TXT} of CPU per receipt", size=12, bullet=True, after=4),
    dict(t="PaddleOCR: CPU time on our compute; no per-call fee", size=12, bullet=True, after=4),
    dict(t=f"AOAI: about {TOKENS_IN:.0f} input + {TOKENS_OUT:.0f} output tokens per receipt", size=12,
         bullet=True, after=4),
    dict(t="Prices still to be confirmed", size=12, bold=True, color=RED),
], margin=0.22, fill=LIGHT)
footnote(s, "Times measure different things (CPU vs API call incl. network); receipts were processed one at a time.")

# ===================================================================== slide 11: findings and tradeoffs
s = content_slide(
    "Key Findings and Trade-offs",
    "Most errors came from field extraction, not OCR; better rules close the gap on known layouts.",
    "Findings from FINAL_ANALYSIS.md and RULES_COMPARISON.md in python/receipt_ocr_benchmark/results/v2. " + SOURCE)
findings = [
    ("OCR was mostly right", "On the new receipts, Azure DI and PaddleOCR Light read almost every value."),
    ("Original rules were weak", f"English-only labels: {acc(ORIG['light']):.1f}–{acc(ORIG['di']):.1f}% for "
                                 "Light and DI."),
    ("Rules can be improved", f"Tuned rules: Light {acc(IMPR['light']):.1f}%, DI {acc(IMPR['di']):.1f}%; "
                              "label vocabulary grew about 3×."),
    ("AOAI handled new layouts as-is", f"{acc(AOAI):.1f}% with a prompt never tuned to these receipts."),
    ("Heavy adds nothing", f"Lowest accuracy and slowest ({secs(IMPR['heavy']):.1f} s); OCR failed on two photos."),
]
for i, (head, desc) in enumerate(findings):
    y = 2.0 + i * 0.8
    c = plain_shape(s, MSO_SHAPE.OVAL, 0.39, y + 0.08, 0.4, 0.4, RED)
    set_runs(c.text_frame, str(i + 1), size=13, bold=True, color=WHITE)
    c.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    text(s, 0.95, y, 6.3, 0.72, [dict(t=head, size=14, bold=True, after=2), dict(t=desc, size=12, color=GREY_TXT)])
tbl = table(s, 7.55, 2.0, [1.55, 1.9, 1.94], [0.5, 0.75, 0.75, 0.75, 0.75])
for c, hd in enumerate(["", "PaddleOCR Light + improved rules", "Azure DI + AOAI"]):
    fill_cell(tbl.cell(0, c), [dict(t=hd, size=11, bold=True, color=WHITE)], fill=CHAR)
    cell_border(tbl.cell(0, c), sides="")
trade = [("Runs where", "Our compute, offline", "Azure cloud services"),
         ("Per-request fee", "None (compute only)", "DI pages + AOAI tokens"),
         ("New layouts", "Needs new rules", "Handled by the prompt"),
         ("Main risk", "Rule maintenance", "Cost, model variability")]
for i, row in enumerate(trade, start=1):
    for c, v in enumerate(row):
        fill_cell(tbl.cell(i, c), [dict(t=v, size=11.5, bold=(c == 0))])
        cell_border(tbl.cell(i, c), sides="B")

# ===================================================================== slide 12: recommendation
s = content_slide(
    "Recommendation and Next Steps",
    "Keep two candidates and decide on a larger set of receipts that neither has seen.",
    f"Nine receipts ({APPLICABLE} fields) are not enough for a production decision, and the improved rules were "
    "tuned on them. A fair comparison freezes both candidates first, then tests on unseen, representative "
    "receipts and also counts the effort to keep rules working on new layouts. " + SOURCE)
half = (12.55 - 0.3) / 2
text(s, 0.39, 2.0, half, 1.6, [
    dict(t="CANDIDATE 1", size=11, bold=True, color=GREY_TXT, after=6),
    dict(runs=[("PaddleOCR Light + improved rules  ", dict(bold=True, color=RED, size=15)),
               (f"{acc(IMPR['light']):.1f}% (tuned) · {secs(IMPR['light']):.1f} s", dict(bold=True, size=12.5))],
         after=6),
    dict(t="Offline, no per-request charges; needs rules maintained for each new layout.", size=12.5),
], margin=0.25, fill=TINT)
text(s, 0.39 + half + 0.3, 2.0, half, 1.6, [
    dict(t="CANDIDATE 2", size=11, bold=True, color=GREY_TXT, after=6),
    dict(runs=[("Azure DI + AOAI  ", dict(bold=True, color=RED, size=15)),
               (f"{acc(AOAI):.1f}% · {secs(AOAI):.1f} s", dict(bold=True, size=12.5))], after=6),
    dict(t="Flexible on varied layouts with an unchanged prompt; API costs and run-to-run variability.", size=12.5),
], margin=0.25, fill=TINT)
text(s, 0.39, 3.9, 12.55, 0.5, [dict(runs=[
    ("Limitation:  ", dict(bold=True, color=WHITE)),
    (f"{N_RECEIPTS} receipts, mostly mock and printed; the improved rules were tuned on them.", dict(color=WHITE))],
    size=13.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=CHAR)
steps = [("Freeze both", "Lock the improved rules and the AOAI prompt before any new test"),
         ("Test on unseen receipts", "30+ real, anonymised receipts; count rule fixes needed per new layout"),
         ("Confirm prices", "Compute rate, Document Intelligence pages, gpt-5-mini tokens")]
sw = (12.55 - 2 * 0.3) / 3
for i, (head, desc) in enumerate(steps):
    text(s, 0.39 + i * (sw + 0.3), 4.65, sw, 1.2, [
        dict(t=f"NEXT STEP {i + 1}", size=10, bold=True, color=GREY_TXT, after=4),
        dict(t=head, size=14, bold=True, after=3), dict(t=desc, size=12, color=GREY_TXT)], margin=0.2, fill=LIGHT)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides); receipt crops in {ASSETS}")
