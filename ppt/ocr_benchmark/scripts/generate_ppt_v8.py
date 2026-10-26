"""Generate the Version 8 Receipt OCR Benchmark deck (8 slides) from the AIA template.

    python3 ppt/ocr_benchmark/scripts/generate_ppt_v8.py --force     (from the repository root)

Version 8 = Version 7 made shorter (generate_ppt_v7.py, kept unchanged for the archived deck):
- executive summary: AOAI prompt v2 96.1% vs multilingual OCR rules 51.0-70.6%, small labels, no caveat bar;
- comparison slide: multilingual rules vs AOAI prompt v2 only (no English-only rules, no original prompt);
- maintenance slide without the "Not guaranteed" box (the caveat moves to the notes);
- a redesigned "beyond six fields" slide: receipt -> structured data (illustration) -> analytics;
- the limitations slide is removed; its points are in the speaker notes and a short line on the
  recommendation slide. AOAI speed and tokens are from the prompt v2 run.

Version 7 = Version 6 simplified (generate_ppt_v6.py, kept unchanged for the archived deck):
- slide 2 is a short executive summary: AOAI prompt v2 96.1% (development result) vs OCR + general
  multilingual rules 51.0-70.6% (retrospective), without the 88.2% figure;
- slide 3 has a plainer subtitle and a small note on why 51 of 54 fields are scored;
- slide 4 shows only the fairer comparison (multilingual rules vs AOAI with its original prompt);
- the "Improving AOAI" slide is removed; English-only rule figures are no longer shown.

Version 6 = Version 5 plus the retrospective multilingual rules baseline (results/v2/scores_multilingual;
docs/MULTILINGUAL_BASELINE.md) next to the initial results: the original rules plus common Chinese labels,
fixed before scoring but written after these receipts were examined, so it is labelled retrospective, not
an independent test. generate_ppt_v5.py is kept unchanged for the archived Version 5 deck.

Version 5 was a shorter management version of Version 4 (generate_ppt_v4.py, kept unchanged for the
archived deck). The question: is OCR with hand-written extraction rules enough to replace Azure OpenAI,
and what value does AOAI add?
- Initial results only for the rules (37.3% / 41.2%; the first rules had no Chinese labels). Accuracy
  after tuning the rules is never shown: the rules were adapted by hand to these receipts, so it says
  nothing about new formats.
- AOAI: 88.2% before tuning and 96.1% with prompt v2, labelled as a development result, with the four
  fields the clearer instructions fixed and the AOAI accuracy per field.
- The maintenance difference, balanced pros and cons, the potential beyond six fields (not yet
  benchmarked), limitations and a recommendation. Diagnosis-comment detection is a short example only.

Every slide that shows results carries an evidence tag. All figures are read from committed results
and asserted at build time; no OCR, scoring or Azure calls. PaddleOCR Heavy is excluded.
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
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V8.pptx")
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
        "potential": ("POTENTIAL · NOT YET TESTED", RED), "retro": ("MEASURED · RETROSPECTIVE", CHAR)}


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

# ===================================================================== 1. title
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Can OCR Rules Replace Azure OpenAI?")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(0.39), Inches(4.9), Inches(6.6), Inches(0.9)
set_runs(sub.text_frame, "Medical receipt extraction benchmark")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = f"{N_RECEIPTS} receipts · 6 fields · rules vs AI extraction"; style_run(r)
s.notes_slide.notes_text_frame.text = (
    "Question: is OCR with hand-written extraction rules enough to replace Azure OpenAI (AOAI) for medical "
    "receipts, and what value does AOAI add? Every number comes from the saved benchmark results. " + SOURCE)

# Scored fields: 9 receipts x 6 fields, minus the fields not printed on a receipt (all registration numbers).
NA_FIELDS = [(r["receipt"], r["field"]) for r in read_csv(RES / "scores_improved" / "detail.csv")
             if r["approach"] == AOAI and r["result"].startswith("N/A")]
POSSIBLE = N_RECEIPTS * len(FIELDS)
assert POSSIBLE - len(NA_FIELDS) == APPLICABLE and {f for _, f in NA_FIELDS} == {"registration_number"}
N_NO_REG = len(NA_FIELDS)

LIMITS = (f"Limits of this evidence: {N_RECEIPTS} receipts and {APPLICABLE} fields, 7 of them printed, fictional test "
          f"receipts. {AOAI_V2_ACC} (prompt v2) is a development result: the prompt was refined after reviewing these "
          f"receipts. {RANGE_ML} (multilingual rules) is a retrospective baseline: common Chinese labels were added "
          f"after these receipts were examined, though fixed before scoring. Neither is independent validation: only "
          f"{N_UNSEEN} unseen handwritten receipts exist, and on all {N_UNSEEN} Azure DI misread the year 2026 as 2020. "
          "Prices are not confirmed.")
V2_SECS = secs(AOAI_V2)
V2_TOKENS_IN = round(int(AOAI_V2["aoai_input_tokens"]) / N_RECEIPTS)
V2_TOKENS_OUT = round(int(AOAI_V2["aoai_output_tokens"]) / N_RECEIPTS)

# ===================================================================== 2. executive summary
s = content_slide(
    "Executive Summary",
    "OCR + rules is not enough to replace AOAI across varied receipts.",
    f"Azure DI + AOAI with prompt v2: {AOAI_V2_ACC} ({count(AOAI_V2)}). OCR + general multilingual rules: "
    f"{acc(ML['light'])} with PaddleOCR Light and {acc(ML['di'])} with Azure DI ({count(ML['light'])} and "
    f"{count(ML['di'])}). Rules must be written and maintained for every new label, language and layout; AOAI works "
    "from plain-language instructions and could extract further fields (potential, not yet benchmarked). " + LIMITS
    + " " + SOURCE)
for k, (big, head, subs, colour, fill, line) in enumerate([
        (AOAI_V2_ACC, "Azure DI + AOAI (prompt v2)", ["Development result"], RED, WHITE, RED),
        (RANGE_ML, "OCR + multilingual rules",
         [f"{acc(ML['light'])} PaddleOCR Light · {acc(ML['di'])} Azure DI", "Retrospective baseline"], CHAR, LIGHT,
         None)]):
    text(s, 0.39 + k * 4.0, 1.95, 3.8, 3.3, [dict(t=big, size=46 if k == 0 else 36, bold=True, color=colour, after=8),
                                             dict(t=head, size=16, bold=True, after=6)]
         + [dict(t=x, size=12.5, color=GREY_TXT, italic=x.endswith(("result", "baseline")), after=2) for x in subs],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.25, fill=fill, line=line)
text(s, 8.45, 1.95, 4.49, 3.3, [
    dict(t="Why AOAI may still be needed", size=16, bold=True, color=RED, after=10),
    dict(t="Fewer rules to write and maintain for new layouts and scenarios", size=15, bullet=True, after=8),
    dict(t="Can potentially extract more fields for analytics (not yet benchmarked)", size=15, bullet=True,
         after=8),
    dict(t="Rules remain fine for simple, clearly labelled checks", size=15, bullet=True)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.22)

# ===================================================================== 3. what we compared
s = content_slide(
    "What We Compared",
    f"For each of the {N_RECEIPTS} receipts, we extract {len(FIELDS)} key fields and compare the results across "
    "3 approaches.",
    f"{N_RECEIPTS} receipts: 7 printed, fictional test receipts photographed with a phone (English, bilingual and "
    "Traditional Chinese layouts) and 2 receipts from the first benchmark round. Six fields: doctor, registration "
    f"number, patient, receipt number, service date, total. {APPLICABLE} of {POSSIBLE} possible fields were scored: "
    f"{N_NO_REG} receipts do not contain a doctor registration number, so those fields were excluded. Azure OpenAI "
    "deployment: gpt-5-mini. " + SOURCE)
for k, (name, ocr, ocr_sub, extract, ai) in enumerate([
        ("PaddleOCR Light + rules", "PaddleOCR Light", "open source, own compute", "Hand-written rules", False),
        ("Azure DI + rules", "Azure Document Intelligence", "cloud OCR", "Hand-written rules", False),
        ("Azure DI + AOAI", "Azure Document Intelligence", "cloud OCR", "Azure OpenAI instructions", True)]):
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
text(s, 4.4, 4.5, 8.54, 1.2, [
    dict(runs=[(f"{N_RECEIPTS} receipts", dict(bold=True)), (": 7 printed test receipts (English, bilingual, Chinese "
                                                          "layouts) and 2 from the first benchmark round.", {})],
         size=14, after=8),
    dict(runs=[(f"{len(FIELDS)} fields", dict(bold=True)), (": doctor, registration no., patient, receipt no., "
                                                          "service date, total.", {})], size=14)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.25, fill=LIGHT)
text(s, 4.4, 5.75, 8.54, 0.3, [dict(t=f"{APPLICABLE} of {POSSIBLE} possible fields were scored. {N_NO_REG} receipts do "
                                      "not contain a doctor registration number, so those fields were excluded.",
                                    size=10.5, color=GREY_TXT, italic=True)])

# ===================================================================== 4. comparison
s = content_slide(
    "Rules vs AOAI on the Same Receipts",
    f"Multilingual OCR rules reached {RANGE_ML}; Azure DI + AOAI reached {AOAI_V2_ACC}.",
    f"Accuracy = correct fields / {APPLICABLE} on the {N_RECEIPTS} receipts. Multilingual rules = general extraction "
    "rules with common Traditional and Simplified Chinese labels and basic bilingual handling "
    "(python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md); a retrospective baseline. AOAI = prompt v2, a "
    "development result: the prompt was refined after reviewing these receipts. Remaining rule errors need new label "
    "types, labels inside lines, layout logic or OCR-tolerant matching; PaddleOCR Light also loses fields because its "
    "OCR glues words and mixes characters in bilingual labels. " + LIMITS + " " + SOURCE, tag="dev")
bar_chart(s, 0.39, 1.85, 7.3, 4.05,
          [f"PaddleOCR Light\n+ multilingual rules*\n{count(ML['light'])}",
           f"Azure DI\n+ multilingual rules*\n{count(ML['di'])}",
           f"Azure DI + AOAI\nprompt v2†\n{count(AOAI_V2)}"],
          [("Accuracy", (pct(ML["light"]), pct(ML["di"]), pct(AOAI_V2)))], [[MID_GREY, CHAR, RED]])
card(s, 8.0, 1.95, 4.94, 1.75, "Multilingual rules*", [
    "General rules with common Chinese labels",
    "No receipt-specific rules"], head_colour=CHAR, size=13.5)
card(s, 8.0, 3.85, 4.94, 1.6, "To close the gap, rules would need", [
    "New labels and layouts written by hand",
    "Retesting every receipt after each change"], head_colour=RED, fill=WHITE, line=RED, size=13.5)
note(s, "* Retrospective baseline   † Development result (prompt refined on these receipts)   "
        f"Neither is independent validation. {N_RECEIPTS} receipts, {APPLICABLE} fields.", y=6.02)

# ===================================================================== 5. the key difference: maintenance
s = content_slide(
    "The Key Difference: Maintenance",
    "Rules need us to anticipate every case in code. AOAI can often cope through plain-language instructions.",
    f"Rules: to handle these {N_RECEIPTS} receipts the label vocabulary grew from {VOCAB_ORIG} to {VOCAB_IMPR} "
    f"hand-written phrases (Chinese and bilingual labels, distractor labels, layout handling), and one change broke "
    f"{FIX_LIGHT[1]} field that was already correct. AOAI: one prompt revision fixed {FIX_PROMPT[0]} fields and broke "
    f"{FIX_PROMPT[1]}. Whether AOAI copes with layouts it has not seen is expected, not proven: it has not been "
    f"tested on enough unseen receipts, still makes mistakes and needs testing and monitoring. Diagnosis-comment check (results/diagnosis): rules matched AOAI on "
    f"{DIAG_SUM['rules_paddle_light']['correct']}/{DIAG_N} receipts, because the comments sat under clear labels. "
    + SOURCE, tag="dev")
flows = [("Manual extraction rules", CHAR, LIGHT, None,
          ["A new label, language or layout appears", "A developer anticipates it and writes rule code",
           "Retest every receipt; a change can break a working one"],
          [f"{VOCAB_ORIG} → {VOCAB_IMPR} label phrases written by hand",
           f"{FIX_LIGHT[1]} correct field broken by a rule change"]),
         ("AOAI extraction", RED, WHITE, RED,
          ["New wording appears", "Often handled by the existing instructions",
           "If not: refine the instructions in plain language, rerun"],
          [f"One prompt revision: {FIX_PROMPT[0]} fields fixed, {FIX_PROMPT[1]} broken"])]
for k, (head, colour, fill, line, steps, evidence) in enumerate(flows):
    x0 = 0.39 + k * 6.4
    text(s, x0, 1.95, 6.15, 0.42, [dict(t=head, size=16, bold=True, color=WHITE)], anchor=MSO_ANCHOR.MIDDLE,
         margin=0.18, fill=colour)
    bw = (6.15 - 2 * 0.35) / 3
    for j, st in enumerate(steps):
        bx = x0 + j * (bw + 0.35)
        text(s, bx, 2.55, bw, 1.4, [dict(t=st, size=13.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.12, fill=fill,
             line=line)
        if j:
            plain_shape(s, MSO_SHAPE.RIGHT_ARROW, bx - 0.3, 3.13, 0.25, 0.24, MID_GREY)
    text(s, x0, 4.1, 6.15, 0.9, [dict(t="Seen in this benchmark", size=12, bold=True, color=GREY_TXT, after=2)]
         + [dict(t=e, size=12.5, bullet=True, after=2) for e in evidence], margin=0.15)
text(s, 0.39, 5.15, 12.55, 0.55, [dict(runs=[("Where rules were enough: ", dict(bold=True)),
                                            (f"a yes/no check for a diagnosis comment under clear labels. Rules "
                                             f"matched AOAI on {DIAG_SUM['rules_paddle_light']['correct']}/{DIAG_N} "
                                             "receipts (development result).", {})], size=13)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=LIGHT)

# ===================================================================== 6. pros and cons
s = content_slide(
    "Advantages and Disadvantages",
    "Rules win on cost, auditability and predictability; AOAI on accuracy, maintenance and flexibility.",
    f"Measured: accuracy (multilingual rules {RANGE_ML}, retrospective baseline; AOAI prompt v2 {AOAI_V2_ACC}, "
    f"development result); speed per receipt (PaddleOCR Light {secs(ORIG['light'])} on Azure ML CPU, Azure DI "
    f"{secs(ORIG['di'])}, Azure DI + AOAI prompt v2 {V2_SECS} incl. network); AOAI prompt v2 tokens per receipt "
    f"({V2_TOKENS_IN} input, {V2_TOKENS_OUT} output); rule effort ({VOCAB_ORIG} -> {VOCAB_IMPR} label phrases) and the vet invoice sub-total "
    "error. Prices are not confirmed. Flexibility, auditability and model-update effects are expectations. " + LIMITS
    + " " + SOURCE)
rows = [("Cost", "+ PaddleOCR: own compute, no API fee (Azure DI: page fee)",
         f"− Azure DI page fee + ~{V2_TOKENS_IN} input / {V2_TOKENS_OUT} output tokens per receipt", "rules",
         "Prices to confirm"),
        ("Speed", f"PaddleOCR {secs(ORIG['light'])} (CPU) · Azure DI {secs(ORIG['di'])}",
         f"{V2_SECS} per receipt", None, "Measured"),
        ("Accuracy", f"− {RANGE_ML} with multilingual rules (retrospective)",
         f"+ {AOAI_V2_ACC} with prompt v2 (development result)", "ai", "Measured"),
        ("Maintenance", "− New labels, languages and layouts need code and a full retest",
         "+ Many changes made in plain-language instructions; still retest", "ai", "Measured / expected"),
        ("Flexibility", "− Finds only what it was written for",
         "+ New fields can be requested in the prompt (not yet benchmarked)", "ai", "Expected"),
        ("Auditability", "+ Every result traceable to a rule",
         "− Harder to explain; keep quoted evidence and logs", "rules", "Expected"),
        ("Reliability", "+ Same input, same output",
         "− Can return a confident wrong value (e.g. a sub total as the total); model updates need retesting",
         "rules", "Measured / expected")]
tbl = table(s, 0.39, 1.95, [1.75, 4.65, 4.65, 1.5], [0.48] + [0.5] * len(rows))
header_row(tbl, ["", "OCR + rules", "Azure DI + AOAI", "Evidence"], size=14)
for i, (label, rules_t, ai_t, better, ev) in enumerate(rows, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=label, size=13, bold=True)])
    fill_cell(tbl.cell(i, 1), [dict(t=rules_t, size=12)], fill=GOOD_TINT if better == "rules" else None)
    fill_cell(tbl.cell(i, 2), [dict(t=ai_t, size=12)], fill=GOOD_TINT if better == "ai" else None)
    fill_cell(tbl.cell(i, 3), [dict(t=ev, size=11, italic=ev != "Measured", color=CHAR if ev == "Measured"
                                    else GREY_TXT)])
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B")
note(s, "Green = stronger side. Multilingual rules include common Chinese labels (retrospective baseline). "
        "Expected = not measured here.", y=6.0)

# ===================================================================== 7. beyond six fields (potential)
ITEMS = [("Specialist outpatient consultation", "Consultation", "950.00"), ("Chest X-ray", "Test", "620.00"),
         ("Blood test (CBC)", "Test", "380.00"), ("Drugs", "Medication", "245.50")]
for name, _, amount in ITEMS:  # the illustration uses text Azure DI really read from this receipt
    ocr_read("receipt3", name, engines=("azure_di",))
    ocr_read("receipt3", amount, engines=("azure_di",))
crop = make_crop("receipt3", [n for n, _, _ in ITEMS], "crop_receipt3_items", [n for n, _, _ in ITEMS])
s = content_slide(
    "Beyond Six Fields: From Receipts to Insights",
    "Today we extract 6 fields. AOAI could also capture what was treated, tested and prescribed.",
    "Potential only: extracting these details has not been built or tested. Left: a real line-item section of a "
    "hospital receipt in our benchmark. Middle: an illustration of the structured data AOAI could return, typed by "
    "us from that receipt's OCR text (checked in the saved Azure DI output); it is not AOAI output. Where receipts "
    "show them, diagnoses and symptoms could be captured the same way. Rules would need new labels and logic for "
    "each such detail. Right: examples of analytics this would enable. A pilot would need ground truth, accuracy "
    "targets, a privacy review and cost checks.", tag="potential")
heads = [("1. What the receipt shows", 0.39, 3.95), ("2. What AOAI could extract", 4.75, 4.0),
         ("3. What we could analyse", 9.15, 3.79)]
for h, x, w in heads:
    text(s, x, 1.85, w, 0.36, [dict(t=h, size=14, bold=True, color=CHAR)], anchor=MSO_ANCHOR.MIDDLE)
picture(s, crop, 0.39, 2.3, 3.95, 2.9)
plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 4.38, 3.45, 0.33, 0.36, MID_GREY)
tbl = table(s, 4.75, 2.3, [1.8, 1.35, 0.85], [0.46] + [0.5] * len(ITEMS))
header_row(tbl, ["Item", "Type", "HK$"], size=12, align=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT])
for i, (name, kind, amount) in enumerate(ITEMS, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=name.replace("Specialist outpatient consultation", "Specialist consultation"),
                                    size=12)])
    fill_cell(tbl.cell(i, 1), [dict(t=kind, size=12, bold=True, color=RED)])
    fill_cell(tbl.cell(i, 2), [dict(t=amount, size=12, align=PP_ALIGN.RIGHT)])
    for c in range(3):
        cell_border(tbl.cell(i, c), sides="B")
text(s, 4.75, 4.85, 4.0, 0.35, [dict(t="Illustration typed from the receipt text, not AOAI output", size=10.5,
                                     italic=True, color=GREY_TXT)])
plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 8.79, 3.45, 0.33, 0.36, MID_GREY)
for k, (head, body) in enumerate([("Cost by treatment", "Spend on consultations, tests and medicines"),
                                  ("Provider comparison", "Typical charges per test across providers"),
                                  ("Trends over time", "Which treatments and medicines are rising"),
                                  ("Unusual claims", "Combinations or amounts that stand out")]):
    text(s, 9.15, 2.3 + k * 0.74, 3.79, 0.66, [dict(t=head, size=13, bold=True, after=1),
                                              dict(t=body, size=11.5, color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.14, fill=LIGHT)
text(s, 0.39, 5.5, 12.55, 0.5, [dict(runs=[("Potential, not yet tested. ", dict(bold=True, color=RED)),
                                          ("Only the 6 current fields have been benchmarked. Diagnoses, symptoms, "
                                           "treatments and medications would need a pilot.", {})], size=13)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)

# ===================================================================== 8. recommendation
s = content_slide(
    "Recommendation",
    "Use rules for simple, labelled checks. Use AOAI where receipts vary or richer data is needed.",
    "Rules are sufficient where layouts are few and stable, fields have clear labels and the question is simple "
    "(for example whether a diagnosis comment is present). AOAI adds value where providers, layouts and languages "
    "vary, where fields lack consistent labels, and potentially for richer medical data (not yet benchmarked). Next "
    "steps: freeze the rules and prompt v2; test on 30+ unseen, real, anonymised receipts and count the rule changes "
    "needed; pilot medications, treatments, symptoms and diagnoses with ground truth; confirm prices. " + LIMITS
    + " " + SOURCE)
card(s, 0.39, 1.95, 6.12, 2.3, "Simple OCR rules are sufficient when…", [
    "Layouts are few, known and stable",
    "Fields have clear printed labels",
    "The question is simple, e.g. is a diagnosis comment present?",
    "No API fee and fully traceable output are required"], head_colour=GOOD, fill=GOOD_TINT, size=14)
card(s, 6.82, 1.95, 6.12, 2.3, "AOAI adds real value when…", [
    "Providers, layouts and languages vary (Chinese, bilingual)",
    "Fields lack consistent labels: names with titles, totals vs subtotals",
    "We want less scenario-specific code to maintain",
    "Richer medical data is wanted (potential, not yet benchmarked)"], head_colour=RED, fill=WHITE, line=RED,
     size=14)
steps = [("1. Freeze", "the rules and AOAI prompt v2"),
         ("2. Validate", "30+ unseen, real, anonymised receipts; count rule changes"),
         ("3. Pilot extra fields", "medications, treatments, symptoms, diagnoses with ground truth"),
         ("4. Confirm cost", "Document Intelligence pages and gpt-5-mini tokens")]
sw = (12.55 - 3 * 0.25) / 4
for i, (head, desc) in enumerate(steps):
    text(s, 0.39 + i * (sw + 0.25), 4.5, sw, 1.15, [dict(t=head, size=15, bold=True, color=RED, after=3),
                                                   dict(t=desc, size=12.5)], margin=0.18, fill=LIGHT)
note(s, f"Evidence so far: {N_RECEIPTS} receipts; results are development or retrospective, not yet validated on "
        "unseen receipts.", y=5.85)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
