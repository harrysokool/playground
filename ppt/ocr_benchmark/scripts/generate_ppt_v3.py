"""Generate the Version 3 Receipt OCR Benchmark deck (12 slides) from the AIA template.

    python3 ppt/ocr_benchmark/scripts/generate_ppt_v3.py --force     (from the repository root)

Version 3 cleans up Version 2 (generate_ppt_v2.py, kept unchanged for the archived deck) and tells
the story in two steps:
- slide 3, initial results: every approach before any tuning on these receipts (the original rules
  had no Chinese labels, so this compares initial implementations, not maximum capability);
- slide 4, how accuracy was improved: what was changed in each approach and the resulting
  development scores (rules tuned, prompt v2), with the effort each change took;
- slide 5, accuracy by field: the three tuned approaches per field (development results);
- slide 6, what changed in prompt v2: the four fields it fixed, the prompt wording behind each
  (checked against SYSTEM_PROMPT_V2), and that the Python checks, row layout and photo changed none.
The later slides do not repeat these figures. PaddleOCR Heavy (discontinued) is removed everywhere.
The small held-out Version 1 check is mentioned only in the notes, and is not used to say that
either approach generalises better.

Reads committed results only (no OCR, scoring or Azure calls):
- python/receipt_ocr_benchmark/results/v2/scores_improved/summary.csv and detail.csv: times, the
  original AOAI accuracy, and every value shown in the receipt examples;
- results/v2/scores_aoai_improved/summary.csv and detail.csv: the prompt v2 (aoai_v2_rows) development
  result and the fields it fixed or broke;
- results/v1_heldout/di_aoai_v2_rows: how many held-out Version 1 receipts there are (speaker notes only);
- results/v2/<approach dir>/receiptN.json: each example value is cross-checked against these files,
  and the build stops if they disagree with detail.csv;
- results/v2/paddle_light and azure_di raw OCR: statements that "the OCR read the value" are
  checked against them;
- results/v2/azure_di/receiptN.json text positions: used to crop and highlight the receipt photos
  (data/receipts_v2/benchmark_inputs, turned upright via EXIF as the benchmark inputs were);
- receipt_bench/extraction_general.py and extraction_improved.py: label vocabulary sizes (constants
  only; no extraction is run).

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
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V3.pptx")
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


def content_slide(title, message, notes):
    s = prs.slides.add_slide(L_CONTENT)
    for idx in (15, 16):
        e = ph(s, idx)._element; e.getparent().remove(e)
    s.shapes._spTree.append(copy.deepcopy(SLDNUM_SP))
    t = ph(s, 10)
    t.left, t.top, t.width, t.height = Inches(0.39), Inches(0.55), Inches(12.2), Inches(0.62)
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

# ===================================================================== 1. title
s = prs.slides.add_slide(L_TITLE)
set_runs(ph(s, 10).text_frame, "Medical Receipt OCR Benchmark")
sub = ph(s, 1)
sub.left, sub.top, sub.width, sub.height = Inches(0.39), Inches(4.5), Inches(6.6), Inches(0.9)
set_runs(sub.text_frame, "Can Azure OpenAI replace hand-written extraction rules?")
p = sub.text_frame.add_paragraph()
r = p.add_run(); r.text = f"{N_RECEIPTS} receipts · 6 fields · manual rules vs AI extraction"; style_run(r)
s.notes_slide.notes_text_frame.text = (
    "Objective: compare hand-written extraction rules with AI extraction (Azure OpenAI) for six fields on medical "
    "receipts: the development effort, the maintenance, and the ability to handle different receipt layouts. "
    + SOURCE)

# ===================================================================== 2. what we tested
s = content_slide(
    "What We Tested",
    f"{N_RECEIPTS} receipts with different layouts and languages. Each approach reads the text, then finds 6 fields.",
    f"Receipts: English, bilingual and Traditional Chinese layouts. Fields: doctor, registration number, patient, "
    f"receipt number, service date, total. {APPLICABLE} fields were present on the receipts and scored. "
    "Step 1 (text recognition, OCR) turns the photo into text; step 2 (field extraction) picks the six values "
    "from that text, either with hand-written rules or with Azure OpenAI. " + SOURCE)
for i, (rcpt, label) in enumerate((("receipt1", "English"), ("receipt3", "Bilingual"), ("receipt4", "Chinese"))):
    x, y, w, h = picture(s, make_thumb(rcpt, f"thumb_{rcpt}"), 0.39 + i * 2.25, 1.95, 2.1, 3.7)
    text(s, x, y + h + 0.08, 2.1, 0.3, [dict(t=label, size=12, color=GREY_TXT)])
tbl = table(s, 7.25, 1.95, [2.15, 1.85, 1.69], [0.62, 0.78, 0.78, 0.78])
header_row(tbl, ["Approach", "1. Read text", "2. Find fields"])
for i, row in enumerate([("PaddleOCR Light", "Open-source OCR", "Rules"),
                         ("Azure DI", "Azure OCR", "Rules"),
                         ("Azure DI + AOAI", "Azure OCR", "Azure OpenAI")], start=1):
    for c, v in enumerate(row):
        fill_cell(tbl.cell(i, c), [dict(t=v, size=14, bold=(c == 0))])
        cell_border(tbl.cell(i, c), sides="B")
text(s, 7.25, 5.05, 5.69, 0.8, [dict(t=f"Fields: doctor, registration no., patient, receipt no., service date, total. "
                                       f"{APPLICABLE} fields scored.", size=13, color=GREY_TXT)])



# ===================================================================== 3. initial results
C = PP_ALIGN.CENTER
s = content_slide(
    "Initial Results",
    f"Before any tuning on these {N_RECEIPTS} receipts, AI extraction was far ahead of the first rule sets.",
    f"Accuracy = correct fields / {APPLICABLE} fields present on the {N_RECEIPTS} Version 2 receipts, before anything "
    "was changed for them. The original extraction rules knew English labels only, with no Chinese or bilingual "
    "labels, although four of the receipts are Chinese or bilingual. On those receipts the OCR read the values but "
    "the rules could not find them (see example 1). The AOAI prompt was written before these receipts existed. "
    "So this compares initial implementations, not the maximum capability of each approach. Time = average per "
    "receipt (PaddleOCR: CPU on Azure ML compute; Azure: API call time incl. network). " + SOURCE)
tbl = table(s, 0.39, 1.95, [3.55, 2.45, 1.85], [0.62, 0.9, 0.9, 0.9])
header_row(tbl, ["Approach", "Accuracy", "Time / receipt"], size=15, align=[PP_ALIGN.LEFT, C, C])
for i, (name, a) in enumerate((("PaddleOCR Light + rules", ORIG["light"]), ("Azure DI + rules", ORIG["di"]),
                               ("Azure DI + AOAI", AOAI)), start=1):
    ai = a == AOAI
    fill_cell(tbl.cell(i, 0), [dict(t=name, size=17, bold=True)], fill=LIGHT if ai else None)
    fill_cell(tbl.cell(i, 1), [dict(runs=[(acc(a), dict(size=24, bold=True, color=RED if ai else CHAR)),
                                          (f"  ({count(a)})", dict(size=12, color=GREY_TXT))], align=C)],
              fill=LIGHT if ai else None)
    fill_cell(tbl.cell(i, 2), [dict(t=secs(a), size=18, align=C)], fill=LIGHT if ai else None)
    for c in range(3):
        cell_border(tbl.cell(i, c), sides="B")
text(s, 8.55, 1.95, 4.39, 3.32, [
    dict(t="Why the rules scored low", size=16, bold=True, color=RED, after=8),
    dict(t="The original rules knew English labels only: no Chinese or bilingual labels.", size=14, bullet=True,
         after=6),
    dict(t="On Chinese and bilingual receipts the OCR read the values, but the rules could not find them.",
         size=14, bullet=True, after=6),
    dict(t="So this compares initial implementations, not the best each approach can do.", size=14, bullet=True,
         bold=True),
], margin=0.25, fill=LIGHT)
note(s, f"Accuracy = correct fields out of {APPLICABLE}. The AOAI prompt was written before these receipts. All "
        f"approaches processed all {N_RECEIPTS} receipts.", y=5.55)

# ===================================================================== 4. how we improved accuracy
s = content_slide(
    "How We Improved Accuracy",
    "Both approaches improved after reviewing these receipts. Changing rules took far more work than changing a "
    "prompt.",
    f"All changes were made after reviewing the errors on these {N_RECEIPTS} receipts, so the scores are development "
    f"results, not independent validation. Rules: rewritten by hand (label phrases {VOCAB_ORIG} to {VOCAB_IMPR}: "
    f"Chinese and bilingual labels, distractor labels, layout handling); on PaddleOCR Light text this fixed "
    f"{FIX_LIGHT[0]} fields and broke {FIX_LIGHT[1]}, on Azure DI text it fixed {FIX_DI[0]} and broke {FIX_DI[1]}. "
    f"AOAI: prompt v2 with clearer field definitions fixed {FIX_PROMPT[0]} fields and broke {FIX_PROMPT[1]}. The "
    "row layout and Python checks added at the same time changed no result (see the prompt v2 slide). "
    + HELD_NOTE + " " + SOURCE)
tbl = table(s, 0.39, 1.95, [3.05, 5.55, 2.05, 1.9], [0.62, 0.78, 0.62, 0.78])
header_row(tbl, ["Approach", "What we changed", "Development score", "Fixed / broke"], size=14,
           align=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, C, C])
rows = [("PaddleOCR Light + rules", f"Rewrote the rules by hand: Chinese and bilingual labels, distractor labels, "
                                    f"layouts ({VOCAB_ORIG} → {VOCAB_IMPR} label phrases)", IMPR["light"],
         FIX_LIGHT),
        ("Azure DI + rules", "The same rule changes, on Azure DI text", IMPR["di"], FIX_DI),
        ("Azure DI + AOAI, prompt v2", "Revised the prompt wording: clearer definitions of each field", AOAI_V2,
         FIX_PROMPT)]
for i, (name, what, a, (fixed, broke)) in enumerate(rows, start=1):
    ai = a is AOAI_V2
    fill_cell(tbl.cell(i, 0), [dict(t=name, size=15, bold=True)], fill=LIGHT if ai else None)
    fill_cell(tbl.cell(i, 1), [dict(t=what, size=13)], fill=LIGHT if ai else None)
    fill_cell(tbl.cell(i, 2), [dict(runs=[(acc(a), dict(size=20, bold=True, color=RED if ai else CHAR)),
                                          (f"  ({count(a)})", dict(size=11, color=GREY_TXT))], align=C)],
              fill=LIGHT if ai else None)
    fill_cell(tbl.cell(i, 3), [dict(runs=[(f"+{fixed}", dict(color=GOOD, bold=True)), (" / ", {}),
                                          (f"−{broke}", dict(color=RED if broke else CHAR, bold=bool(broke)))],
                                    size=16, align=C)], fill=LIGHT if ai else None)
    for c in range(4):
        cell_border(tbl.cell(i, c), sides="B")
for k, (head, body) in enumerate([
        ("Changing rules", "Code and vocabulary for every new wording or language, then a retest of every receipt. "
                           "One change broke a receipt that was already correct."),
        ("Changing the AI prompt", "Plain-language edits to one prompt, then a rerun. No field broke on these "
                                   "receipts.")]):
    text(s, 0.39 + k * 6.4, 4.95, 6.15, 0.95, [dict(t=head, size=15, bold=True, color=RED, after=3),
                                               dict(t=body, size=13)], margin=0.2, fill=LIGHT)
note(s, f"Development results: every change was made after reviewing these {N_RECEIPTS} receipts, so these scores "
        "are not independent validation.", y=6.02)

# ===================================================================== 5. accuracy by field (development results)
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
for a in TUNED.values():  # the per-field counts add up to the overall score
    assert sum(FIELD_SCORES[(a, f)][0] for f in FIELDS) == int(SUM_V2PROMPT[a]["correct"])
APPLIC = {f: {FIELD_SCORES[(a, f)][1] for a in TUNED.values()} for f in FIELDS}
assert all(len(v) == 1 for v in APPLIC.values())
APPLIC = {f: v.pop() for f, v in APPLIC.items()}
REG_N = APPLIC["registration_number"]
assert REG_N < N_RECEIPTS and all(APPLIC[f] == N_RECEIPTS for f in FIELDS if f != "registration_number")
WRONG = {a: {(k[1], k[2]) for k, r in V2_DETAIL.items() if k[0] == a and r["result"] == "Wrong"} for a in TUNED.values()}
SHARED = set.intersection(*WRONG.values())
assert SHARED == {("receipt9", "doctor_name"), ("receipt10", "service_date")}, SHARED
s = content_slide(
    "Accuracy by Field (Development Results)",
    "After tuning, all three approaches miss the same two fields; the rules also miss patient and receipt numbers.",
    f"Development results after tuning on these {N_RECEIPTS} receipts, not independent validation. Counts from "
    "results/v2/scores_aoai_improved/detail.csv, checked against the per-field percentages in summary.csv. "
    f"Registration number is printed on {REG_N} of the {N_RECEIPTS} receipts, so it has {REG_N} applicable receipts; "
    f"every other field has {N_RECEIPTS}. All three approaches miss the vet invoice's doctor (two practitioners, and "
    "the OCR misread the signature) and the pharmacy receipt's service date (print date vs item date, an open "
    "ground-truth question). The rules also miss patient and receipt number on the vet invoice and the pharmacy "
    "receipt (an OCR artefact on the label, a payment receipt number, no labels); Azure DI + rules also misses one "
    "total. " + SOURCE)
names = list(TUNED)
tbl = table(s, 0.39, 1.95, [2.75, 1.55, 2.75, 2.75, 2.75], [0.62] + [0.5] * len(FIELDS))
header_row(tbl, ["Field", "Receipts"] + names, size=13, align=[PP_ALIGN.LEFT] + [C] * 4)
for i, f in enumerate(FIELDS, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=FIELD_NAMES[f].replace("Reg. no.", "Registration no."), size=14, bold=True)])
    fill_cell(tbl.cell(i, 1), [dict(t=f"{APPLIC[f]}" + ("*" if f == "registration_number" else ""), size=14,
                                    color=GREY_TXT, align=C)])
    for c, a in enumerate(TUNED.values(), start=2):
        k, n = FIELD_SCORES[(a, f)]
        full = k == n
        fill_cell(tbl.cell(i, c), [dict(runs=[(f"{100 * k / n:.1f}%", dict(size=16, bold=full, color=GOOD if full
                                                                            else CHAR)),
                                              (f"  ({k}/{n})", dict(size=11, color=GREY_TXT))], align=C)],
                  fill=GOOD_TINT if full else None)
    for c in range(5):
        cell_border(tbl.cell(i, c), sides="B")
note(s, f"Development results after tuning on these {N_RECEIPTS} receipts, not independent validation. "
        f"* Registration number is printed on {REG_N} of the {N_RECEIPTS} receipts; every other field on all "
        f"{N_RECEIPTS}.", y=5.65)

# ===================================================================== 6. what changed in AOAI prompt v2
from receipt_bench import di_aoai  # noqa: E402  (prompt text only; nothing is called)

V2_RUNS = {"plain": "aoai_v2_plain", "rows": "aoai_v2_rows", "image": "aoai_v2_rows_image"}
assert len({SUM_V2PROMPT[r]["correct"] for r in V2_RUNS.values()}) == 1, "the slide says the variants score the same"


def raw_reply(run_dir, receipt, field):
    j = json.loads((RES / run_dir / f"{receipt}.json").read_text())
    return str((j.get("raw_fields") or {}).get(field))


def validation_changes(run_dir):
    """Values the Python checks changed (model reply vs saved value) in one prompt v2 run."""
    n = 0
    for p in (RES / run_dir).glob("receipt*.json"):
        j = json.loads(p.read_text())
        for f in ("doctor_name", "registration_number", "patient_name", "receipt_number"):
            raw = j["raw_fields"].get(f)
            n += isinstance(raw, str) and raw.strip() not in ("", j.get(f))
    return n


VALIDATION_CHANGES = sum(validation_changes(d) for d in ("di_aoai_v2_plain", "di_aoai_v2_rows",
                                                         "di_aoai_v2_rows_image"))
# Each fix: field, receipt, the prompt v2 wording that targets it (must be in SYSTEM_PROMPT_V2).
PROMPT_FIXES = [("registration_number", "receipt1", "GP receipt", "the identifier only, without its label"),
                ("doctor_name", "receipt5", "Dental receipt", "Leave out qualifications and post-nominals"),
                ("doctor_name", "receipt10", "Pharmacy receipt", "clinic, hospital or practice names"),
                ("total_amount", "receipt9", "Vet invoice", "after any discounts, rounding or other adjustments")]
fixed_keys = {(r, f) for f, r, _, _ in PROMPT_FIXES}
actual = {(k[1], k[2]) for k, r in V2_DETAIL.items()
          if k[0] == "aoai_original" and r["result"] == "Wrong" and V2_DETAIL[("aoai_v2_rows", k[1], k[2])]["result"]
          == "Correct"}
assert fixed_keys == actual and len(actual) == FIX_PROMPT[0], f"fixes differ from the scores: {sorted(actual)}"
prompt_flat = " ".join(di_aoai.SYSTEM_PROMPT_V2.split())
for f, r, _, quote in PROMPT_FIXES:
    assert quote in prompt_flat and quote not in " ".join(di_aoai.SYSTEM_PROMPT.split()), f"not a v2 change: {quote}"
    for run in V2_RUNS.values():  # already right in the model's reply, in every prompt v2 variant
        assert V2_DETAIL[(run, r, f)]["result"] == "Correct"
s = content_slide(
    "What Changed in AOAI Prompt V2",
    f"{AOAI_ACC} → {AOAI_V2_ACC}: four fields fixed, all by clearer prompt wording. Nothing else changed a result.",
    f"Original prompt {AOAI_ACC} ({count(AOAI)}); prompt v2 {AOAI_V2_ACC} ({count(AOAI_V2)}), a development result "
    "because prompt v2 was written after reviewing these errors. The four fixes are in the model's own reply (before "
    "any Python check) in all three prompt v2 runs. Credit: prompt wording only. The Python checks changed "
    f"{VALIDATION_CHANGES} values; plain-text OCR input ({count(SUM_V2PROMPT['aoai_v2_plain'])}) scores the same as "
    f"the row layout ({count(AOAI_V2)}); attaching the photo also scores {count(SUM_V2PROMPT['aoai_v2_rows_image'])}. "
    "Remaining errors: the vet invoice doctor (two practitioners; OCR misread the signature) and the pharmacy "
    "service date (open ground-truth question). Prompt text: receipt_bench/di_aoai.py (SYSTEM_PROMPT and "
    "SYSTEM_PROMPT_V2, commit 034d7d5). " + SOURCE)
tbl = table(s, 0.39, 1.95, [2.0, 3.85, 4.1, 2.6], [0.55] + [0.62] * len(PROMPT_FIXES))
header_row(tbl, ["Field fixed", "Original prompt replied", "Prompt v2 wording added", "Prompt v2 replied"], size=13)
for i, (f, r, where, quote) in enumerate(PROMPT_FIXES, start=1):
    fill_cell(tbl.cell(i, 0), [dict(t=FIELD_NAMES[f].replace("Reg. no.", "Registration no."), size=13, bold=True),
                               dict(t=where, size=11, color=GREY_TXT)])
    fill_cell(tbl.cell(i, 1), [dict(runs=[("✗ ", dict(bold=True, color=RED)), (raw_reply("di_aoai", r, f), {})],
                                    size=12.5)], fill=BAD_TINT)
    fill_cell(tbl.cell(i, 2), [dict(t=f"“{quote}”", size=12.5, italic=True)])
    fill_cell(tbl.cell(i, 3), [dict(runs=[("✓ ", dict(bold=True, color=GOOD)), (raw_reply("di_aoai_v2_rows", r, f), {})],
                                    size=12.5)], fill=GOOD_TINT)
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

# ===================================================================== 5. bilingual example: the rule layer failed
for v in ("蔡嘉穎", "Dr. Siu Ka Wai"):
    ocr_read("receipt8", v)
a8 = receipt_score(AOAI, "receipt8")
s = content_slide(
    "Example 1: The OCR Was Right, the Rules Were Wrong",
    "Both OCR engines read the names. The original rules took the label 病人 as the patient's name.",
    "Receipt 8 (medical centre). Both OCR engines read the patient name and the doctor's name (checked in the raw "
    "OCR). The original rules matched 'Patient' and took the Chinese half of the label, 病人, as the name. The "
    "improved rules needed bilingual labels added by hand. AOAI, with its original prompt, read the fields correctly "
    f"({a8[0]} of {a8[1]} fields on this receipt). Values: rules on PaddleOCR Light text; detail.csv, checked "
    "against the extraction JSON. " + SOURCE)
crop = make_crop("receipt8", ["Patient 病人", "蔡嘉穎", "Attending Doctor", "Dr. Siu Ka Wai"], "crop_receipt8",
                 ["Patient 病人", "蔡嘉穎", "Attending Doctor", "Dr. Siu Ka Wai"])
picture(s, crop, 0.39, 1.95, 5.6, 3.9)
example_table(s, 6.3, 1.95, "receipt8", ["patient_name", "doctor_name"], col_w=(1.15, 1.4, 1.35, 1.35, 1.39))
text(s, 6.3, 4.25, 6.64, 1.6, [
    dict(t="Original rules: took the Chinese label 病人 (\"patient\") as the patient's name.", size=14, bullet=True,
         after=6),
    dict(t="Improved rules: fixed by adding bilingual labels by hand.", size=14, bullet=True, after=6),
    dict(t="AOAI: correct with its original prompt; no change needed.", size=14, bullet=True),
])
note(s, "Bilingual medical centre receipt. Rules shown on PaddleOCR Light text; Azure DI with the original rules "
        "made the same patient error. DI + AOAI = original prompt.")

# ===================================================================== 6. the maintenance cost of rules
for v in ("麥詠琳", "葉卓謙", "2026年6月9日"):
    ocr_read("receipt4", v)
o4, i4, a4 = (receipt_score(a, "receipt4") for a in (ORIG["light"], IMPR["light"], AOAI))
reg_o, ok_o = example(ORIG["light"], "receipt9", "receipt_number")
reg_i, ok_i = example(IMPR["light"], "receipt9", "receipt_number")
assert ok_o and not ok_i, "expected the receipt9 receipt-number regression"
s = content_slide(
    "Example 2: Every New Layout Meant Manual Rule Work",
    "Each label wording was added by hand, and one change broke a receipt that was already correct.",
    f"Receipt 4 (Chinese medicine): the OCR read every value, but the original rules only knew English labels "
    f"({o4[0]} of {o4[1]} fields). After adding Chinese labels by hand: {i4[0]} of {i4[1]}. DI + AOAI with its "
    f"original prompt: {a4[0]} of {a4[1]}. The label vocabulary grew from {VOCAB_ORIG} to {VOCAB_IMPR} phrases "
    f"(counted in extraction_general.py and extraction_improved.py). On the vet invoice (receipt 9) the original "
    f"rules found receipt number {reg_o}; after the changes they return {reg_i}. Whether AOAI needs less maintenance "
    "on new layouts has not been tested yet. " + SOURCE)
crop = make_crop("receipt4", ["病人姓名", "麥詠琳", "診症日期", "2026年6月9日", "主診中醫師", "葉卓謙"],
                 "crop_receipt4", ["麥詠琳", "2026年6月9日", "葉卓謙"])
picture(s, crop, 0.39, 1.95, 4.6, 2.75)
text(s, 0.39, 4.8, 4.6, 0.75, [dict(t=f"Chinese medicine receipt: original rules {o4[0]}/{o4[1]} fields; after "
                                      f"Chinese labels were added by hand {i4[0]}/{i4[1]}; DI + AOAI {a4[0]}/{a4[1]} "
                                      "(original prompt).", size=12, color=GREY_TXT)])
for k, (big, small) in enumerate([(f"{VOCAB_ORIG} → {VOCAB_IMPR}", "label phrases in the rules, added by hand after "
                                                                  "reviewing the errors"),
                                  (f"{reg_o} → {reg_i}", "vet invoice receipt number: correct before the changes, "
                                                         "wrong after (a regression)"),
                                  ("New layouts", "will likely need more rule changes and a retest of every receipt")]):
    text(s, 5.3 + k * 2.6, 1.95, 2.45, 2.75, [dict(t=big, size=22, bold=True, color=RED, after=8),
                                             dict(t=small, size=13)], margin=0.2, fill=LIGHT)
text(s, 5.3, 4.85, 7.64, 1.1, [
    dict(t="With its original prompt, DI + AOAI needed none of these changes for these receipts. Whether that holds "
           "for new layouts still needs to be tested.", size=14),
])

# ===================================================================== 7. AOAI still makes mistakes
ocr_read("receipt9", "FPatient")
assert V2_DETAIL[("aoai_v2_rows", "receipt9", "total_amount")]["result"] == "Correct", "expected prompt v2 to fix it"
s = content_slide(
    "Example 3: AOAI Still Makes Mistakes",
    "On the vet invoice, the improved rules and AOAI each got a different field wrong.",
    "Receipt 9 (vet invoice). The improved rules now take the payment table's 'Receipt #' (380048) instead of the "
    "invoice number. Both OCR engines read 'FPatient:' (a stray mark merged into the label), so no rule matched the "
    "patient label; AOAI still found the name. AOAI with the original prompt chose the sub total (1361.50) instead "
    "of the total (1361.00). Prompt v2 returns the correct total, but it was written after reviewing this error. "
    "Values: detail.csv, checked against the extraction JSON. " + SOURCE)
top = make_crop("receipt9", ["Invoice No", "FClinician"], "crop_receipt9_top", ["Invoice No", "FClinician"])
pay = make_crop("receipt9", ["Sub Total", "HKD 1361.50", "Total Amount", "HKD 1361.00", "Details of Payments Received",
                             "Receipt #", "380048"], "crop_receipt9_pay",
                ["Sub Total", "HKD 1361.50", "Total Amount", "HKD 1361.00", "Receipt #", "380048"])
_, _, _, h1 = picture(s, top, 0.39, 1.95, 5.6, 1.0)
picture(s, pay, 0.39, 1.95 + h1 + 0.15, 5.6, 3.95 - h1 - 0.15)
example_table(s, 6.3, 1.95, "receipt9", ["receipt_number", "patient_name", "total_amount"],
              col_w=(1.15, 1.4, 1.35, 1.35, 1.39), row_h=0.68)
text(s, 6.3, 4.75, 6.64, 1.2, [
    dict(t="Improved rules: picked the payment receipt number.", size=13, bullet=True, after=4),
    dict(t="Rules: the OCR read \"FPatient:\", so the patient label was missed.", size=13, bullet=True, after=4),
    dict(t="AOAI (original prompt): picked the sub total instead of the total.", size=13, bullet=True),
])

# ===================================================================== 8. effort and maintenance
s = content_slide(
    "Development Effort and Maintenance",
    "The difference is the manual work to handle each layout, and to keep it working.",
    f"Effort: the rules were rewritten by hand after reviewing the errors on these receipts (label phrases "
    f"{VOCAB_ORIG} to {VOCAB_IMPR}); the AOAI prompt was revised once. Side effects on these receipts: the rule "
    f"changes broke {FIX_LIGHT[1]} correct field on PaddleOCR Light text, the prompt revision broke {FIX_PROMPT[1]}. "
    "Lower maintenance for AOAI on new layouts is the key implication of this benchmark, not a result proven in "
    f"production. Running cost: DI page plus about {TOKENS_IN} input / {TOKENS_OUT} output gpt-5-mini tokens per "
    "receipt (original prompt); prices are not yet confirmed. " + SOURCE)
tbl = table(s, 0.39, 1.95, [3.0, 4.75, 4.8], [0.6] + [0.62] * 5)
header_row(tbl, ["", "PaddleOCR Light + rules", "Azure DI + AOAI"], size=15)
comp = [("Effort to improve", "Rules rewritten by hand after reviewing errors on these receipts",
         "One prompt revision after reviewing errors"),
        ("What a change looks like", f"Code and label lists ({VOCAB_ORIG} → {VOCAB_IMPR} phrases)",
         "Prompt wording and a few general checks"),
        ("Side effects seen", f"{FIX_LIGHT[1]} correct field broken by the rule changes",
         f"{FIX_PROMPT[1]} correct fields broken by the prompt revision"),
        ("New receipt layouts", "Likely more rule updates and a regression test of every receipt",
         "Possibly no change; not yet tested"),
        ("Time and running cost", f"{secs(IMPR['light'])}, own compute, no API fee",
         f"{secs(AOAI)}, Azure fees per receipt (to confirm)")]
for i, row in enumerate(comp, start=1):
    for c, v in enumerate(row):
        fill_cell(tbl.cell(i, c), [dict(t=v, size=14, bold=(c == 0))])
        cell_border(tbl.cell(i, c), sides="B")
note(s, "The main question is not API price but who maintains the extraction logic as layouts change. Lower "
        "maintenance for AOAI is implied by this benchmark, not yet proven.", y=5.85)

# ===================================================================== 9. pros and cons
ocr_read("receipt9", "1361.00", engines=("azure_di",))  # AOAI's wrong total came from correct OCR text
tot_a, ok_tot_a = example(AOAI, "receipt9", "total_amount")
assert not ok_tot_a, "expected the AOAI total error on the vet invoice"
s = content_slide(
    "Manual Rules vs. AI Extraction: Pros and Cons",
    "\"Measured\" = this benchmark; the rest is expected.",
    f"Measured: rules grew from {VOCAB_ORIG} to {VOCAB_IMPR} label phrases while being tuned on these {N_RECEIPTS} "
    f"receipts; vet invoice receipt number {reg_o} correct before tuning, {reg_i} after. Azure DI + AOAI had the "
    f"highest accuracy before any tuning; it still made mistakes, e.g. vet invoice total {tot_a} although the Azure "
    f"DI text contains the correct 1361.00; {secs(AOAI)} vs {secs(IMPR['light'])} per receipt. Expected, not "
    "measured: that new formats need rule updates, that AOAI needs less rule maintenance, control, API fees and the "
    "upkeep AOAI still needs (validation, monitoring, prompt). AOAI is not maintenance free. Prices are not yet "
    "confirmed. " + SOURCE)


def pros_cons(x, w, heading, summary, pros, cons):
    text(s, x, 1.95, w, 0.45, [dict(t=heading, size=16, bold=True, color=WHITE)], anchor=MSO_ANCHOR.MIDDLE,
         margin=0.18, fill=CHAR)
    text(s, x, 2.48, w, 0.62, [dict(t=summary, size=13, bold=True)], anchor=MSO_ANCHOR.MIDDLE)
    for k, (label, items, colour, tint) in enumerate((("Pros", pros, GOOD, GOOD_TINT), ("Cons", cons, RED, BAD_TINT))):
        paras = [dict(t=label, size=15, bold=True, color=colour, after=4)]
        for i, (measured, t) in enumerate(items):
            runs = ([("Measured: ", dict(bold=True))] if measured else []) + [(t, {})]
            paras.append(dict(runs=runs, size=13, bullet=True, after=0 if i == len(items) - 1 else 3))
        text(s, x, 3.18 + k * 1.42, w, 1.34, paras, margin=0.18, fill=tint)


COL_W = (12.55 - 0.3) / 2
pros_cons(0.39, COL_W, "Manual extraction rules (PaddleOCR Light)",
          "New formats need manual rule updates, which can break working cases and add maintenance and testing.",
          [(False, "Full control; transparent and predictable on formats the rules know."),
           (False, "No API fees: open-source OCR on our own compute."),
           (True, "the OCR read the values; the misses were missing labels.")],
          [(False, "Each new format or language needs rule updates by hand."),
           (True, "a rule change broke a receipt that was already correct."),
           (True, f"{VOCAB_ORIG} → {VOCAB_IMPR} label phrases added by hand.")])
pros_cons(0.39 + COL_W + 0.3, COL_W, "AI extraction (Azure DI + AOAI)",
          "Less rule maintenance expected: accuracy depends mainly on the AI model, OCR output and prompt.",
          [(True, "highest accuracy before any tuning on these receipts."),
           (False, "Reads varied formats using existing model capabilities."),
           (True, f"faster, {secs(AOAI)} vs {secs(IMPR['light'])} per receipt.")],
          [(True, "still makes mistakes, e.g. a sub total taken as the total."),
           (False, "Less direct control: results depend on model, OCR, prompt."),
           (False, "API fees; needs validation, monitoring and prompt upkeep.")])
text(s, 0.39, 6.0, 11.6, 0.45, [dict(runs=[
    ("Neither is maintenance free. ", dict(bold=True)),
    ("The difference is where the effort sits: rules for every layout, or one prompt plus validation.", {})],
    size=14)], anchor=MSO_ANCHOR.MIDDLE, margin=0.18, fill=LIGHT)

# ===================================================================== 10. conclusion
s = content_slide(
    "Conclusion and Next Steps",
    "The real trade-off: maintain extraction rules ourselves, or let AI replace that layer.",
    f"Initial implementations: Azure DI + AOAI {AOAI_ACC}, rules {acc(ORIG['light'])} and {acc(ORIG['di'])}, the gap "
    f"mostly from missing Chinese support in the rules. After reviewing these receipts: rules {acc(IMPR['light'])} "
    f"and {acc(IMPR['di'])}, AOAI prompt v2 {AOAI_V2_ACC}, all development results. The benchmark is small "
    f"({N_RECEIPTS} receipts), so this is not a production decision. " + HELD_NOTE + " " + SOURCE)
text(s, 0.39, 1.95, 12.55, 1.75, [
    dict(t="Initial implementations: AI extraction led by a wide margin, mainly because the first rules had no "
           "Chinese support.", size=16, bullet=True, after=6),
    dict(t="After reviewing these receipts both improved. Rules needed code and vocabulary changes; AI needed one "
           "prompt revision. Neither is validated on unseen receipts.", size=16, bullet=True, after=6),
    dict(t="So the choice is whether to keep writing and maintaining extraction rules, or to use AI for that "
           "layer.", size=16, bullet=True, bold=True),
], margin=0.3, fill=LIGHT)
steps = [("1. Freeze both", "Lock the improved rules and AOAI prompt v2."),
         ("2. Test on unseen receipts", "30+ real, anonymised receipts. Measure accuracy and count the rule "
                                        "changes needed."),
         ("3. Then compare cost", "Compute, Document Intelligence pages and gpt-5-mini tokens.")]
sw = (12.55 - 2 * 0.3) / 3
for i, (head, desc) in enumerate(steps):
    text(s, 0.39 + i * (sw + 0.3), 3.95, sw, 1.4, [dict(t=head, size=16, bold=True, color=RED, after=6),
                                                  dict(t=desc, size=14)], margin=0.22, fill=LIGHT)
note(s, f"Limitation: {N_RECEIPTS} receipts, mostly printed mock receipts; the rules and prompt v2 were tuned on them. "
        "AOAI still makes mistakes and has not been tested on a large unseen set.", y=5.6)

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides); fixed/broken: light {FIX_LIGHT}, DI {FIX_DI}, prompt {FIX_PROMPT}")
