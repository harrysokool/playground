"""Generate the Version 9 Receipt OCR Benchmark deck (10 slides) from the AIA template.

    python3 ppt/ocr_benchmark/scripts/generate_ppt_v9.py --force     (from the repository root)

Version 9 = Version 8 plus real-receipt examples: slide 5, why Azure DI beat PaddleOCR Light (receipt 5);
slide 6, why AOAI beat the rules (receipts 6 and 5), which now also carries the maintenance message (the
separate maintenance slide is gone); slide 7, the doctor database approach and its limits. generate_ppt_v8.py is kept unchanged for the archived Version 8 deck.

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
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V10.pptx")
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

# ===================================================================== 1. title
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Medical Receipt Extraction")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(0.39), Inches(4.9), Inches(6.6), Inches(0.9)
set_runs(sub.text_frame, "Benchmark results and pilot direction")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = f"OCR rules vs Azure OpenAI · {N_RECEIPTS} receipts · 6 fields"; style_run(r)
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
    "Recommendation: Azure DI + AOAI prompt v2 for the next receipt extraction pilot, not production.",
    f"Azure DI + AOAI with prompt v2: {AOAI_V2_ACC} ({count(AOAI_V2)}), a development result (prompt refined on these "
    f"receipts). OCR + general multilingual rules: {acc(ML['light'])} with PaddleOCR Light and {acc(ML['di'])} with "
    f"Azure DI ({count(ML['light'])} and {count(ML['di'])}), a retrospective baseline. Neither is independently "
    "validated. AOAI handles contextual extraction more flexibly and could extract further fields without manual "
    "rules for every layout (not guaranteed); ordinary Python validation stays for formats and missing fields. Scope: "
    "Azure processes approved receipt data only; claims records, policy data and the audit checks stay in another "
    "authorized system. This is a direction for further testing, not a production approval. " + LIMITS + " " + SOURCE)
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
    dict(t="What we recommend", size=16, bold=True, color=RED, after=10),
    dict(t="Azure DI + AOAI prompt v2 for the next extraction pilot", size=14.5, bullet=True, after=7),
    dict(t="Python validation: format checks today, missing-field checks planned", size=14.5, bullet=True, after=7),
    dict(t="Only approved receipt data on Azure; audit checks stay in another authorized system", size=14.5,
         bullet=True, after=7),
    dict(t="A pilot, not a production approval", size=14.5, bullet=True, bold=True)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.22)

# ===================================================================== 3. scope and data boundary
s = content_slide(
    "Scope and Data Boundary",
    "Azure only reads receipts and extracts data. Audit checks happen in another authorized system.",
    "Planned workflow, not yet built: a medical receipt enters the approved Azure environment; Azure Document "
    "Intelligence reads it; Azure OpenAI extracts structured information; Python checks validate the result (existing: "
    "date and amount normalisation, registration and doctor-name clean-up, review flags for values not found in the "
    "OCR text or a total equal to the subtotal, in receipt_bench/aoai_validation.py; planned: required-field checks "
    "and checks for new fields); the results are transferred, by an approved method that is not yet designed, to another "
    "authorized system, which holds the claims and policy data and performs the audit checks (claim comparison, "
    "policy checks, duplicate detection). Only approved receipt data is processed in Azure. Claims records, "
    "policyholder databases, policy documents and other sensitive business information are not uploaded to Azure. "
    "Neither the transfer nor the audit checks are being implemented yet.", tag="plan")
zone = plain_shape(s, MSO_SHAPE.RECTANGLE, 0.39, 1.95, 8.15, 2.85, WHITE, line=RED, line_w=1.75)
zone.line.dash_style = MSO_LINE.DASH
text(s, 0.55, 2.02, 7.85, 0.35, [dict(t="Approved Azure environment: receipt data only", size=13, bold=True, color=RED)],
     anchor=MSO_ANCHOR.MIDDLE)
steps = [("Medical receipt", "approved receipt only"), ("Azure DI", "reads the text"),
         ("Azure OpenAI", "extracts the fields"), ("Python checks", "existing: formats, review flags"),
         ("Structured results", "e.g. names, date, amounts")]
bw, gap = 1.36, 0.24
for k, (head, sub) in enumerate(steps):
    bx = 0.6 + k * (bw + gap)
    last = k == len(steps) - 1
    text(s, bx, 2.65, bw, 1.3, [dict(t=head, size=13, bold=True, color=WHITE if last else CHAR, after=3),
                                dict(t=sub, size=10.5, color=WHITE if last else GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.1, fill=CHAR if last else LIGHT)
    if k:
        plain_shape(s, MSO_SHAPE.RIGHT_ARROW, bx - gap + 0.03, 3.18, gap - 0.06, 0.24, MID_GREY)
text(s, 0.6, 4.05, 7.8, 0.65, [
    dict(runs=[("Today: ", dict(bold=True)), ("Azure DI + Azure OpenAI on 6 fields, with existing Python checks (date "
                                           "and amount formats, label clean-up, review flags).", {})], size=11,
         after=2),
    dict(runs=[("Planned: ", dict(bold=True)), ("required-field checks and checks for the new fields.", {})],
         size=11)], anchor=MSO_ANCHOR.MIDDLE)
plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 8.7, 3.1, 0.85, 0.45, RED)
text(s, 8.58, 2.35, 1.09, 0.7, [dict(t="Approved transfer", size=9.5, color=RED, bold=True, align=C),
                                dict(t="to be designed", size=9, color=RED, italic=True, align=C)],
     anchor=MSO_ANCHOR.BOTTOM)
text(s, 9.7, 1.95, 3.24, 2.85, [
    dict(t="Another authorized system", size=14, bold=True, color=WHITE, after=8),
    dict(t="Holds claims records, policy data and claim history", size=12, color=WHITE, bullet=True, after=4),
    dict(t="Runs the audit checks: claim comparison, policy checks, duplicates", size=12, color=WHITE, bullet=True)],
    margin=0.22, fill=CHAR)
text(s, 0.39, 5.0, 12.55, 0.55, [dict(runs=[("Never uploaded to Azure: ", dict(bold=True, color=RED)),
                                           ("claims records, policyholder databases, policy documents or other "
                                            "sensitive business information.", {})], size=13)],
     anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)
note(s, "Planned workflow. The transfer method must be approved before implementation; the integration and the "
        "audit checks are not being built yet.", y=5.7)

# ===================================================================== 4. benchmark: approaches and results
s = content_slide(
    "Benchmark: Three Approaches, Same 9 Receipts",
    f"Multilingual OCR rules reached {RANGE_ML}; Azure DI + AOAI reached {AOAI_V2_ACC}.",
    f"{N_RECEIPTS} receipts: 7 printed, fictional test receipts photographed with a phone (English, bilingual and "
    "Traditional Chinese layouts) and 2 from the first benchmark round. Six fields: doctor, registration number, "
    f"patient, receipt number, service date, total. {APPLICABLE} of {POSSIBLE} possible fields were scored: "
    f"{N_NO_REG} receipts have no doctor registration number. Accuracy = correct fields / {APPLICABLE}. Multilingual "
    "rules = general extraction rules with common Chinese labels and basic bilingual handling, a retrospective "
    "baseline (python/receipt_ocr_benchmark/docs/MULTILINGUAL_BASELINE.md). AOAI = prompt v2, a development result. "
    "Why the scores differ: slides 5 and 6. " + LIMITS + " " + SOURCE, tag="dev")
for k, (name, ocr, extract, ai) in enumerate([("PaddleOCR Light + rules", "Open-source OCR", "Hand-written rules", False),
                                              ("Azure DI + rules", "Azure OCR", "Hand-written rules", False),
                                              ("Azure DI + AOAI", "Azure OCR", "Azure OpenAI", True)]):
    y = 1.95 + k * 0.9
    text(s, 0.39, y, 4.75, 0.78, [dict(t=name, size=14.5, bold=True, color=RED if ai else CHAR, after=2),
                                  dict(t=f"{ocr}  →  {extract}", size=11.5, color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.18, fill=WHITE if ai else LIGHT, line=RED if ai else None)
text(s, 0.39, 4.75, 4.75, 1.1, [
    dict(runs=[(f"{N_RECEIPTS} receipts", dict(bold=True)), (" · English, bilingual, Chinese layouts", {})], size=12.5,
         after=4),
    dict(runs=[(f"{len(FIELDS)} fields", dict(bold=True)), (": doctor, registration no., patient, receipt no., date, "
                                                          "total", {})], size=12.5)], anchor=MSO_ANCHOR.MIDDLE,
     margin=0.18)
bar_chart(s, 5.45, 1.85, 7.5, 4.05,
          [f"PaddleOCR Light\n+ multilingual rules*\n{count(ML['light'])}",
           f"Azure DI\n+ multilingual rules*\n{count(ML['di'])}",
           f"Azure DI + AOAI\nprompt v2†\n{count(AOAI_V2)}"],
          [("Accuracy", (pct(ML["light"]), pct(ML["di"]), pct(AOAI_V2)))], [[MID_GREY, CHAR, RED]])
note(s, f"* Retrospective baseline   † Development result   Neither is independent validation. {APPLICABLE} of "
        f"{POSSIBLE} fields scored ({N_NO_REG} receipts have no registration number).", y=6.02)

# ===================================================================== 5. why Azure DI beat PaddleOCR Light
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
      ("Receipt no.", "receipt_number", "Receipt No.", "Receipt No.", "编 read for 編")]
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
    "Why Azure DI Beat PaddleOCR Light",
    "Same rules on both. PaddleOCR misread the labels, so the rules could not find the values.",
    f"Both engines ran exactly the same multilingual rules (retrospective baseline). PaddleOCR Light made "
    f"{N_LIGHT_ONLY} more errors than Azure DI ({acc(ML['light'])} vs {acc(ML['di'])}), and every one of them is a "
    f"text recognition problem on a label, checked against the receipt photos: {CAUSE_N['glued']} labels with words "
    f"run together, {CAUSE_N['glued+char']} run together and with a Simplified character, {CAUSE_N['char']} with a "
    f"wrong or missing character, and {CAUSE_N['currency']} 'HK$' read as 'HKS'. None comes from layout or from "
    "different rules. The errors both engines share come from the rules themselves (labels they do not know, layouts "
    "they cannot follow). Receipt 5 (dental) loses four fields this way. " + SOURCE, tag="retro")
picture(s, crop5, 0.39, 1.9, 7.6, 1.95)
text(s, 8.25, 1.9, 4.69, 1.95, [
    dict(runs=[(f"{N_LIGHT_ONLY} ", dict(size=30, bold=True, color=RED)),
               ("extra errors with PaddleOCR", dict(size=15, bold=True))], after=4),
    dict(t="All from reading the label text: words run together, wrong characters, a misread HK$ sign. "
           "None from the rules or the layout.", size=13, after=4),
    dict(t=f"On this receipt PaddleOCR lost {len(R5_LOST)} fields: patient, registration no., treatment date and "
           "receipt no.", size=11.5, color=GREY_TXT)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.22, fill=LIGHT)
tbl = table(s, 0.39, 4.1, [1.85, 1.75, 5.15, 3.8], [0.42] + [0.46] * len(r5_rows))
header_row(tbl, ["Field", "Correct value", "PaddleOCR read the label as…", "Azure DI read it as…"], size=12.5)
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
note(s, "Same multilingual rules (retrospective baseline) on both engines. Receipt 5 is a bilingual dental receipt.",
     y=6.05)

# ===================================================================== 6. why AOAI beat the rules
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
    "Why AOAI Beat the Rules",
    "Both read the same Azure DI text. AOAI used the context; the rules followed fixed patterns.",
    "Azure DI + multilingual rules (retrospective baseline) vs Azure DI + AOAI on the same OCR text. On receipt 6 "
    "(physiotherapy) the rules took the referring doctor as the practitioner, the issue date as the session date, "
    "and could not read the total from the card row (Total / Amount Paid / Outstanding Balance). On receipt 5 the "
    "rules summed the items (the subtotal) and missed the 10% member discount. AOAI got all four right with its "
    "original prompt, written before these receipts existed, and again with prompt v2, so these wins do not come "
    f"from prompt tuning. Of the {len([1 for k, r in ML_ROWS.items() if k[0] == 'azure_di_multilingual' and r['result'] == 'Wrong'])} "
    "fields Azure DI + rules got wrong, AOAI's original prompt got 11 right. Unfamiliar labels, layouts or scenarios "
    f"may need additional rules and retesting; the label vocabulary already grew from {VOCAB_ORIG} to {VOCAB_IMPR} phrases "
    f"when the rules were tuned, and one change broke {FIX_LIGHT[1]} correct field. One prompt revision fixed "
    f"{FIX_PROMPT[0]} fields and broke {FIX_PROMPT[1]}. Whether AOAI copes with layouts it has not seen is not yet "
    "tested. " + SOURCE, tag="retro")
picture(s, crop6, 0.39, 1.9, 4.3, 3.15)
tbl = table(s, 4.95, 1.9, [1.35, 1.95, 2.45, 2.24], [0.42] + [0.66] * len(r6_rows))
header_row(tbl, ["Field", "Correct", "Rules", "AOAI"], size=13)
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
for k, (head, body, colour, fill, line) in enumerate([
        ("Rules: logic written case by case", f"Unfamiliar labels, layouts or scenarios may need additional rules "
                                              f"and retesting (tuning these 9 grew the rules from {VOCAB_ORIG} to "
                                              f"{VOCAB_IMPR} label phrases).",
         CHAR, LIGHT, None),
        ("AOAI: plain-language instructions", f"Can often handle varied wording without new code (not guaranteed); "
                                              f"one prompt revision fixed "
                                              f"{FIX_PROMPT[0]} fields and broke none.", RED, WHITE, RED)]):
    text(s, 0.39 + k * 6.4, 5.2, 6.15, 0.78, [dict(t=head, size=13.5, bold=True, color=colour, after=2),
                                              dict(t=body, size=11.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.16,
         fill=fill, line=line)
note(s, "AOAI was right with its original prompt (written before these receipts) and with prompt v2. "
        "Rules = Azure DI + multilingual rules (retrospective baseline).", y=6.05)

# ===================================================================== 7. the doctor database approach
for rc, engine, needle in [("receipt6", "azure_di", "Referred by"), ("receipt6", "azure_di", "Dr. Kwok Man Hin"),
                           ("receipt2", "azure_di", "Referred by"), ("receipt2", "azure_di", "Dr. Lam Pui Shan"),
                           ("receipt2", "azure_di", "Dr. Ng Chun Yip"), ("receipt8", "azure_di", "Nurse"),
                           ("receipt8", "azure_di", "Wan Man Yi"), ("receipt9", "azure_di", "Dr. Lok Vichol"),
                           ("receipt9", "paddle_light", "Br.LokYi ehoi")]:
    ocr_read(rc, needle, engines=(engine,))  # the real examples below are in the saved OCR text
assert ml_value("extracted_multilingual_azure_di", "receipt6", "doctor_name") == "Dr. Kwok Man Hin"
assert "Lok Yi Choi" in ML_ROWS[("azure_di_multilingual", "receipt9", "doctor_name")]["ground_truth"]
s = content_slide(
    "The Doctor Database Approach",
    "Exact matching can identify registered doctor names in OCR text, but cannot determine who treated the patient.",
    "Proposal: read the receipt with OCR, then match the recognised names against the registry of about 40,000 "
    "doctors (about 80,000 English and Chinese name variants) using strict exact matching, with no fuzzy matching "
    "and no AI. This is technically straightforward, so it was not built or benchmarked. Benefits: little extra "
    "processing cost, deterministic results, and every match can be checked against the registry. Limitation: a "
    "match only says that a registered doctor's name appears somewhere on the receipt. Real examples from our "
    "receipts: receipt 6 names a referring doctor (Dr. Kwok Man Hin) while the treating practitioner is a "
    "physiotherapist, and our rules already took the referring doctor; receipt 2 shows a referring doctor (Dr. Lam "
    "Pui Shan) next to the attending doctor (Dr. Ng Chun Yip); receipt 8 lists a doctor and a nurse; the vet "
    "invoice names a clinician and a signing vet; and the signature 'Dr. Lok Yi Choi' was read as 'Dr. Lok Vichol' "
    "by Azure DI and 'Br.LokYi ehoi' by PaddleOCR, so an exact match would find nothing. Matching also depends on "
    "the registry containing the practitioner: our receipts include a dentist, a physiotherapist and a "
    "Chinese-medicine practitioner, who may be on other registers. Hypothetical cases, not in "
    "our receipts: a patient who is a registered doctor, and a clinic director named in the header. The names on "
    "our test receipts are fictional, so real registry match rates were not measured. AOAI reads context such as "
    "'Referred by' (slide 6), but it has not been tested on these edge cases.", tag="proposal")
text(s, 0.39, 1.9, 4.55, 0.4, [dict(t="The proposal", size=15, bold=True, color=CHAR)], anchor=MSO_ANCHOR.MIDDLE)
for k, (num, head, sub) in enumerate([("1", "OCR reads the receipt", "Azure DI or PaddleOCR"),
                                      ("2", "Match against the registry", "~40,000 doctors · ~80,000 English and "
                                                                          "Chinese name variants"),
                                      ("3", "Strict exact match", "No fuzzy matching, no AI")]):
    y = 2.35 + k * 0.72
    text(s, 0.39, y, 0.55, 0.62, [dict(t=num, size=20, bold=True, color=WHITE, align=C)], anchor=MSO_ANCHOR.MIDDLE,
         fill=CHAR)
    text(s, 1.02, y, 3.92, 0.62, [dict(t=head, size=13.5, bold=True), dict(t=sub, size=11, color=GREY_TXT)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.14, fill=LIGHT)
text(s, 0.39, 4.58, 4.55, 0.68, [
    dict(t="Straightforward; no experiment needed", size=12, bold=True, color=GOOD, after=2),
    dict(t="Low cost · Deterministic · Easy to verify", size=11.5)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.14, fill=GOOD_TINT)
text(s, 0.39, 5.33, 4.55, 0.55, [
    dict(runs=[("Only works if ", dict(bold=True)), ("the OCR reads the name exactly and the registry contains "
                                                       "that practitioner.", {})], size=11.5)],
    anchor=MSO_ANCHOR.MIDDLE, margin=0.14, fill=LIGHT)
text(s, 5.25, 1.9, 7.69, 0.4, [dict(t="But a name match is not the treating doctor", size=15, bold=True, color=RED)],
     anchor=MSO_ANCHOR.MIDDLE)


def case_table(y, title, rows, real):
    tbl = table(s, 5.25, y, [2.6, 5.09], [0.36] + [0.5] * len(rows))
    header_row(tbl, [title, ""], size=12)
    tbl.cell(0, 0).merge(tbl.cell(0, 1))  # the group title spans the table
    for i, (case, example) in enumerate(rows, start=1):
        fill_cell(tbl.cell(i, 0), [dict(t=case, size=12, bold=True)], fill=None if real else LIGHT)
        fill_cell(tbl.cell(i, 1), [dict(t=example, size=11, italic=not real, color=CHAR if real else GREY_TXT)],
                  fill=None if real else LIGHT)
        for c in range(2):
            cell_border(tbl.cell(i, c), sides="B")
    return y + 0.36 + 0.5 * len(rows)


y_end = case_table(2.35, "Seen in our receipts", [
    ("Referring doctor", "Receipt 6: \u201cReferred by Dr. Kwok Man Hin\u201d; the treatment was by a "
                         "physiotherapist (also receipt 2)"),
    ("Several doctors or staff", "Receipt 8: a doctor and a nurse. Vet invoice: a clinician and a signing vet"),
    ("OCR misreads the name", "Signature \u201cDr. Lok Yi Choi\u201d read as \u201cDr. Lok Vichol\u201d: "
                              "no exact match")], real=True)
case_table(y_end + 0.2, "Hypothetical (not in our receipts)", [
    ("Patient is a registered doctor", "The patient's own name matches the registry"),
    ("Clinic director in the header", "A director's name printed in the letterhead")], real=False)
note(s, "AOAI reads context such as \u201cReferred by\u201d (slide 6) but has not been tested on these cases. "
        "Names on our test receipts are fictional, so registry match rates were not measured.", y=6.0)

# ===================================================================== 8. pros and cons
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
        ("Maintenance", "− Unfamiliar labels or layouts may require additional rules and retesting",
         "+ Many changes made in plain-language instructions; still retest", "ai", "Measured / expected"),
        ("Flexibility", "− Finds only what it was written for",
         "+ New fields can be requested in the prompt (not yet benchmarked)", "ai", "Expected"),
        ("Auditability", "+ Every result traceable to a rule",
         "− Harder to explain; keep quoted evidence and logs", "rules", "Expected"),
        ("Reliability", "+ Same input, same output",
         "− Can return a confident wrong value (e.g. a sub total); needs Python validation and retesting",
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

# ===================================================================== 9. what the auditors check
AUDIT = [("Receipt authenticity", "Letterhead, provider details, signature, stamp, signs of alteration"),
         ("Data accuracy and identity", "Names, treatment date, diagnosis, amounts; the right patient"),
         ("Coverage and eligibility", "Policy coverage, waiting periods, deadlines, preapproval"),
         ("Necessity and fees", "Medically necessary treatment, agreed medical fees"),
         ("Assessment and fraud indicators", "Calculations and limits, approval authority, duplicates")]
s = content_slide(
    "What the Auditors Check",
    "We asked the business auditors what they check when sampling claims, and what information they need.",
    "From our discussion with the business auditors; not part of the benchmark data. When sampling receipts and "
    "claims they check: receipt authenticity (letterhead, provider details, signatures, stamps, possible "
    "alterations); data integrity (claimant and provider names, treatment date, diagnosis code, receipt and claimed "
    "amounts) and patient identity; policy coverage, treatment eligibility, waiting periods and submission "
    "deadlines; medical necessity and agreed fees; assessor calculations, deductibles, benefit limits and approval "
    "authority; duplicate receipts and other fraud, waste and abuse indicators; preapproval amounts versus actual "
    "charges. Much of this needs data from other authorized systems, not just the receipt (next slide).")
cw = (12.55 - 4 * 0.2) / 5
for k, (head, body) in enumerate(AUDIT):
    x = 0.39 + k * (cw + 0.2)
    text(s, x, 2.0, cw, 0.65, [dict(t=str(k + 1), size=26, bold=True, color=RED)], anchor=MSO_ANCHOR.MIDDLE,
         margin=0.2, fill=LIGHT)
    text(s, x, 2.65, cw, 1.8, [dict(t=head, size=15, bold=True, after=8), dict(t=body, size=12.5, color=GREY_TXT)],
         margin=0.2, fill=LIGHT)
text(s, 0.39, 4.7, 12.55, 0.55, [dict(runs=[("Why it matters: ", dict(bold=True)),
                                            ("these checks tell us which receipt information is worth extracting.",
                                             {})], size=13.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE,
     line=CHAR)
note(s, "Summarised from our discussion with the business auditors. Not every check uses receipt data.", y=5.4)

# ===================================================================== 10. from audit needs to receipt fields
CHECK_SHORT = {1: "Authenticity", 2: "Accuracy", 3: "Coverage", 4: "Necessity & fees", 5: "Fraud"}
RECEIPT_FIELDS = [  # (field, benchmark field or None, audit categories it supports)
    ("Patient name", "patient_name", (2,)), ("Doctor / practitioner name", "doctor_name", (2,)),
    ("Registration number", "registration_number", (1, 2)), ("Receipt number", "receipt_number", (5,)),
    ("Treatment date", "service_date", (3,)), ("Receipt total", "total_amount", (4, 5)),
    ("Clinic name and address", None, (1,)), ("Individual charges", None, (4, 5)),
    ("Diagnosis, symptoms (if stated)", None, (4,)), ("Treatments, tests, medicines", None, (4,)),
    ("Signature / stamp present", None, (1,))]
assert [f for _, f, _ in RECEIPT_FIELDS if f] == ["patient_name", "doctor_name", "registration_number",
                                                  "receipt_number", "service_date", "total_amount"]
assert sorted(f for _, f, _ in RECEIPT_FIELDS if f) == sorted(FIELDS), "the 6 benchmark fields"
s = content_slide(
    "From Audit Needs to Receipt Fields",
    "On Azure we extract what the receipt shows. Another authorized system adds the rest and runs the checks.",
    "Receipt extraction supplies information for the audit checks; it does not decide whether a receipt is genuine, "
    "whether treatment was medically necessary, or whether the policy covers the claim. "
    f"Receipt fields that could support the auditors' checks. The first 6 are the benchmark fields (Azure DI + AOAI "
    f"prompt v2: {AOAI_V2_ACC}, a development result, not independently validated). The others have not been "
    "extracted or tested yet; each appears only if it is printed or visible on the receipt, and a signature or stamp "
    "can only be reported as present, not as genuine. Information that must come from another authorized system: "
    "the claimant and policy, claimed amount, coverage and waiting periods, claim history and duplicates across "
    "claims, preapproval amounts, agreed fee schedules and assessor decisions. Whether a receipt is genuine and "
    "whether treatment was medically necessary remain auditor judgements. Only approved receipt data is processed "
    "on Azure; results go to the authorized system by an approved method that is not yet designed. Later, the "
    "extracted details (treatments, tests, medicines, charges) could also feed analytics in the authorized system, "
    "such as cost by treatment, provider comparisons, trends and unusual claims: potential, not yet tested.")
tbl = table(s, 0.39, 1.9, [3.05, 2.95, 1.8], [0.36] + [0.32] * len(RECEIPT_FIELDS))
header_row(tbl, ["On the receipt (extracted on Azure)", "Supports", "Status"], size=11.5)
for i, (name, bench, cats) in enumerate(RECEIPT_FIELDS, start=1):
    fill = GOOD_TINT if bench else None
    fill_cell(tbl.cell(i, 0), [dict(t=name, size=11.5, bold=bool(bench))], fill=fill)
    fill_cell(tbl.cell(i, 1), [dict(t=", ".join(CHECK_SHORT[c] for c in cats), size=10.5, color=GREY_TXT)], fill=fill)
    fill_cell(tbl.cell(i, 2), [dict(t="Benchmarked" if bench else "Not yet tested", size=10.5, bold=bool(bench),
                                    italic=not bench, color=GOOD if bench else GREY_TXT)], fill=fill)
    for c in range(3):
        cell_border(tbl.cell(i, c), sides="B", color="FFFFFF" if bench else LINE, w=12700)
plain_shape(s, MSO_SHAPE.RIGHT_ARROW, 8.3, 2.7, 0.5, 0.42, MID_GREY)
text(s, 8.25, 3.15, 0.62, 0.5, [dict(t="approved transfer", size=8.5, color=GREY_TXT, align=C)])
text(s, 8.95, 1.9, 3.99, 2.05, [
    dict(t="Another authorized system adds", size=13.5, bold=True, color=WHITE, after=5),
    dict(t="Claimant, policy and coverage", size=11, color=WHITE, bullet=True, after=1),
    dict(t="Claimed and preapproval amounts", size=11, color=WHITE, bullet=True, after=1),
    dict(t="Claim history, fee schedules, decisions", size=11, color=WHITE, bullet=True, after=5),
    dict(t="…and runs the audit checks", size=11.5, bold=True, color=WHITE)], margin=0.18, fill=CHAR)
text(s, 8.95, 4.05, 3.99, 0.9, [
    dict(t="Information, not a verdict", size=12, bold=True, color=RED, after=2),
    dict(t="Extraction does not decide whether a receipt is genuine, a treatment necessary, or a claim covered.",
         size=10.5)], margin=0.14, fill=WHITE, line=RED)
text(s, 8.95, 5.05, 3.99, 0.85, [
    dict(t="Later: analytics (potential)", size=12, bold=True, after=2),
    dict(t="Cost by treatment, provider comparison, trends, unusual claims", size=10.5, color=GREY_TXT)],
    margin=0.14, fill=LIGHT)
note(s, f"Green = the 6 benchmark fields ({AOAI_V2_ACC}, development result). Other fields are not yet tested and "
        "appear only if printed or visible on the receipt.", y=6.05)

# ===================================================================== 11. recommendation and next steps
s = content_slide(
    "Recommendation and Next Steps",
    "Pilot Azure DI + AOAI prompt v2 for receipt extraction, then grow the extracted fields step by step.",
    "Recommendation: Azure DI + AOAI prompt v2, with Python validation, for the next receipt extraction pilot. This is "
    "a direction for further testing, not a production approval. Simple, clearly labelled checks (for example "
    "whether a diagnosis comment is present) can still use rules. Next steps: define a structured extraction schema "
    "from the auditors' checklist; extend the existing prompt gradually, keeping the six benchmark fields stable; "
    "test each new field on approved receipt examples, including receipts not used for development; agree the "
    "approved transfer method before any integration; confirm Document Intelligence and gpt-5-mini costs. No new "
    "fields or audit checks are being implemented yet. " + LIMITS + " " + SOURCE)
text(s, 0.39, 1.95, 12.55, 1.15, [
    dict(t="Next extraction pilot: Azure DI + AOAI prompt v2, with Python validation", size=18, bold=True,
         color=RED, after=4),
    dict(t="A direction for further testing, not a production approval. Only approved receipt data on Azure.",
         size=13.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.25, fill=WHITE, line=RED)
steps = [("1. Define the schema", "Which receipt fields, formats and \u201cif printed\u201d rules, from the "
                                 "auditors' checklist"),
         ("2. Extend the prompt", "Add fields a few at a time; keep the 6 benchmark fields stable"),
         ("3. Test new fields", "On approved receipt examples, including receipts not used for development"),
         ("4. Prepare the hand-off", "Agree the approved transfer method; confirm costs")]
sw = (12.55 - 3 * 0.25) / 4
for i, (head, desc) in enumerate(steps):
    text(s, 0.39 + i * (sw + 0.25), 3.35, sw, 1.6, [dict(t=head, size=15, bold=True, color=CHAR, after=5),
                                                   dict(t=desc, size=12.5)], margin=0.2, fill=LIGHT)
text(s, 0.39, 5.15, 12.55, 0.5, [dict(runs=[("Rules still fit ", dict(bold=True)),
                                           ("simple, clearly labelled checks, e.g. whether a diagnosis comment is "
                                            "present.", {})], size=12.5)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2,
     fill=GOOD_TINT)
note(s, f"Evidence so far: {N_RECEIPTS} receipts; development and retrospective results, not independently validated. "
        "No new fields or audit checks are implemented yet.", y=5.85)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
