"""Build the Version 18 deck from the manually edited Version 17 deck (cover + 11 slides + 2 appendix).

    python3 ppt/ocr_benchmark/scripts/make_v18_from_v17.py --force     (from the repository root)

Version 17 was edited by hand in PowerPoint (a new architecture slide with a flowchart image, and one word on the
privacy slide), so Version 18 is built by editing that file rather than regenerating it. Only slides 10-12 change:
- main 9 (deck slide 10): the architecture slide moves before the privacy slide, in the standard AIA layout with a
  red message line, a PROPOSED · NOT IMPLEMENTED tag and a grey footnote. The flowchart image is not edited: its
  own header (title, subtitle, labels) and its two bottom boxes are hidden with picture cropping, so the workflow
  itself is unchanged, and it is shown much larger. The bottom boxes' content moves to the privacy slide.
- main 10 (deck slide 11): the privacy slide drops its repeated data flow and focuses on the open decisions.
- main 11 (deck slide 12): the conclusion adds reviewing and approving the architecture and privacy controls.
- main 8 (deck slide 9): "another authorized platform" becomes "the Internal Data Platform", the name used in the
  flowchart, so the platform has one name across the deck. No other slide is touched.
Benchmark figures and receipt examples are not edited; check_deck_v18.py re-verifies them against saved results.
"""
import argparse
import copy
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

PROJECT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--input", type=Path, default=PROJECT / "archive" / "v17_final" / "OCR_Benchmark_V17.pptx")
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V18.pptx")
ap.add_argument("--force", action="store_true", help="overwrite the output file if it already exists")
args = ap.parse_args()
OUT = args.output.resolve()
if OUT.is_relative_to((PROJECT / "archive").resolve()) or OUT.is_relative_to((PROJECT.parent / "template").resolve()):
    sys.exit(f"Refusing to write into a protected folder: {OUT}")
if OUT.exists() and not args.force:
    sys.exit(f"{OUT} already exists. Use --force to overwrite, or --output for a new path.")
OUT.parent.mkdir(parents=True, exist_ok=True)

# ===================================================================== style (as generate_ppt_v17.py)
RED = RGBColor(0xD3, 0x11, 0x45)
CHAR = RGBColor(0x33, 0x3D, 0x47)
GREY_TXT = RGBColor(0x5F, 0x67, 0x70)
LIGHT = RGBColor(0xF2, 0xF2, 0xF2)
RED_TINT = RGBColor(0xFB, 0xE7, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT, FONT_ZH = "Arial", "Microsoft JhengHei"
X0, XW = 0.39, 12.55
PLATFORM = "Internal Data Platform"


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


def no_bullet(p):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", "0"); pPr.set("indent", "0")
    etree.SubElement(pPr, qn("a:buNone"))


def plain_shape(slide, x, y, w, h, fill, line=None, dash=False):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
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
        sh.line.color.rgb = line; sh.line.width = Pt(1.5)
        if dash:
            sh.line.dash_style = MSO_LINE.DASH
    return sh


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.0, fill=None, line=None, dash=False):
    box = plain_shape(slide, x, y, w, h, fill, line, dash) if (fill is not None or line is not None) else \
        slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(min(margin, 0.1)) if margin else 0
    tf.vertical_anchor = anchor
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        no_bullet(p)
        p.alignment = pd.get("align", PP_ALIGN.LEFT)
        p.space_after = Pt(pd.get("after", 0))
        for t, o in pd.get("runs") or [(pd["t"], {})]:
            r = p.add_run(); r.text = t
            style_run(r, o.get("size", pd.get("size", 16)), o.get("bold", pd.get("bold", False)),
                      o.get("color", pd.get("color", CHAR)), o.get("italic", pd.get("italic", False)))
    return box


def strip(s, label, body, y, h=0.55, size=13.5):
    return text(s, X0, y, XW, h, [dict(runs=[(label, dict(bold=True, color=RED)), (body, {})], size=size)],
                anchor=MSO_ANCHOR.MIDDLE, margin=0.2, fill=WHITE, line=RED)


def note(s, t, y):
    return text(s, X0, y, 11.6, 0.32, [dict(t=t, size=11, color=GREY_TXT, italic=True)])


def shape_with(slide, needle):
    hits = [sh for sh in slide.shapes if sh.has_text_frame and needle in sh.text_frame.text]
    if len(hits) != 1:
        sys.exit(f"Expected one shape containing {needle!r}, found {len(hits)}")
    return hits[0]


def replace_in_runs(shape, old, new):
    n = 0
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            if old in r.text:
                r.text = r.text.replace(old, new); n += 1
    if n != 1:
        sys.exit(f"Expected one run with {old!r} in {shape.text_frame.text[:40]!r}, found {n}")


def remove(shape):
    shape._element.getparent().remove(shape._element)


def title_of(slide):
    return slide.shapes.title.text if slide.shapes.title is not None else \
        [sh for sh in slide.placeholders if sh.placeholder_format.idx == 10][0].text_frame.text


prs = Presentation(args.input)
slides = list(prs.slides)
TITLES = [title_of(s) for s in slides]
assert len(slides) == 14 and TITLES[9] == "Privacy and Governance" and \
    TITLES[10] == "Proposed Architecture and Data Flow" and TITLES[11] == "Conclusion and Next Steps", TITLES
s9, priv, arch, concl = slides[8], slides[9], slides[10], slides[11]
TAG_TEMPLATE = shape_with(priv, "TO BE AGREED")          # red outlined pill, top right
MSG_TEMPLATE = shape_with(priv, "Extraction would run on Azure")  # red 17 pt message line

# ===================================================================== main 8: one platform name
replace_in_runs(shape_with(s9, "Specific audit tests"), "on another authorized platform.", f"on the {PLATFORM}.")
replace_in_runs(shape_with(s9, "Later, on another"), "Later, on another authorized platform: ", f"Later, on the {PLATFORM}: ")
nf = s9.notes_slide.notes_text_frame
assert nf.text.count("on another authorized internal platform") == 1
nf.text = nf.text.replace("on another authorized internal platform", f"on the {PLATFORM}")

# ===================================================================== main 9: proposed architecture
pics = [sh for sh in arch.shapes if sh.shape_type == 13]
assert len(pics) == 1 and pics[0].image.size == (1520, 829), "the architecture image changed; re-check the crop"
pic = pics[0]
# Hide the image's own header (eyebrow label, title, subtitle, status pill: y < 158 px) and its two bottom boxes
# (y > 700 px, now on the privacy slide). The three platform columns and steps 1-8 are untouched.
W_PX, H_PX, TOP_PX, BOT_PX = 1520, 829, 158, 700
pic.crop_top, pic.crop_bottom = TOP_PX / H_PX, (H_PX - BOT_PX) / H_PX
ar = W_PX / (BOT_PX - TOP_PX)
w = XW
h = w / ar
pic.left, pic.top, pic.width, pic.height = Inches(X0), Inches(1.88), Inches(w), Inches(h)
remove(shape_with(arch, "The benchmark used unmasked OCR text"))
tag = copy.deepcopy(TAG_TEMPLATE._element)
arch.shapes._spTree.append(tag)
tag_shape = shape_with(arch, "TO BE AGREED")
tag_shape.text_frame.paragraphs[0].runs[0].text = "PROPOSED · NOT IMPLEMENTED"
for sh in arch.placeholders:
    if sh.placeholder_format.idx == 10:
        sh.width = Inches(9.6)
msg = copy.deepcopy(MSG_TEMPLATE._element)
arch.shapes._spTree.append(msg)
replace_in_runs(shape_with(arch, "Extraction would run on Azure"),
                "Extraction would run on Azure; claims, policy and historical records stay on an internal platform.",
                "A proposed design, not yet implemented: only masked OCR text would reach Azure OpenAI.")
note(arch, "The benchmark sent unmasked OCR text to Azure OpenAI, so accuracy on masked text is not yet tested. "
           "Masking, transfers and controls still need approval.", y=1.88 + h + 0.08)
arch.notes_slide.notes_text_frame.text = (
    "This slide shows a proposed architecture for future use; it is not implemented or approved. It is different "
    "from the benchmark workflow, where Azure Document Intelligence read the receipt images and the unmasked OCR text "
    f"went straight to Azure OpenAI. The proposed flow has three areas: the {PLATFORM}, an authorized internal "
    "environment; SharePoint, a controlled file exchange; and Azure for OCR and AI processing. (1) Approved receipt "
    "images are uploaded to SharePoint. (2) Azure Document Intelligence reads the original images, which requires PII "
    "approval, and (3) returns the OCR text, which is unmasked and may contain personal information. (4) The "
    f"{PLATFORM} retrieves the text and masks personal information; customer, claims and policy records stay "
    "internal. (5) The masked text is uploaded and (6) Azure OpenAI extracts the fields from masked text only. (7) The "
    f"results return to SharePoint and (8) the {PLATFORM} retrieves them and links them to the original receipts for "
    "audit tests against claims and records. The benchmark used unmasked OCR text, so accuracy on masked text still "
    "needs testing. The masking method, data transfers and security controls still require review and approval; "
    "the open decisions are on the next slide.")

# ===================================================================== main 10: privacy and governance
for needle in ("On Azure: receipt extraction", "Receipt image sent to Azure DI", "Another authorized internal platform",
               "Claims, policy and historical records stay here", "The design difficulty", "Still to be agreed",
               "PII protection", "Storage", "Access controls", "Transfer and linkage"):
    remove(shape_with(priv, needle))
arrows = [sh for sh in priv.shapes if sh.has_text_frame and sh.text_frame.text.strip() == "→"]
assert len(arrows) == 1
remove(arrows[0])
replace_in_runs(shape_with(priv, "Extraction would run on Azure"),
                "Extraction would run on Azure; claims, policy and historical records stay on an internal platform.",
                "Masking and data handling must be agreed and approved before real receipts are processed.")
REQ = [("Masking must keep required fields",
        "Patient and practitioner names are required fields. Masking must protect personal data without losing "
        f"them, or they must be linked back on the {PLATFORM}."),
       ("Azure DI receives original images",
        "The full receipt image, which can show diagnosis and contact details, goes to Azure DI. This needs approved "
        "data handling controls."),
       ("SharePoint may hold unmasked text",
        "OCR text returned by Azure DI may sit unmasked in SharePoint before masking. This needs approved data "
        "handling controls.")]
RW, RG = 4.05, 0.2
for k, (head_, body) in enumerate(REQ):
    x = X0 + k * (RW + RG)
    text(priv, x, 1.9, RW, 0.55, [dict(t=head_, size=14.5, bold=True, color=WHITE)], anchor=MSO_ANCHOR.MIDDLE,
         margin=0.2, fill=RED if k == 0 else CHAR)
    text(priv, x, 2.45, RW, 1.4, [dict(t=body, size=13)], anchor=MSO_ANCHOR.MIDDLE, margin=0.2,
         fill=RED_TINT if k == 0 else LIGHT)
strip(priv, "Benchmark note: ", "the benchmark used unmasked OCR text. Accuracy on masked text must be re-tested.", 4.05, h=0.55, size=13.5)
text(priv, X0, 4.8, XW, 0.36, [dict(t="Still to be agreed and approved", size=15, bold=True)],
     anchor=MSO_ANCHOR.MIDDLE)
AGREE = [("PII masking method", "Not yet chosen or approved"),
         ("Storage and retention", "Where data is kept, including SharePoint, and for how long"),
         ("Access controls", "Who can see receipts, OCR text and results"),
         ("Transfer and linkage", "How results move and link back to audit records")]
for k, (head_, body) in enumerate(AGREE):
    text(priv, X0 + k * 3.18, 5.2, 3.0, 1.0, [dict(t=head_, size=14, bold=True, color=RED, after=2),
                                             dict(t=body, size=12)],
         anchor=MSO_ANCHOR.MIDDLE, margin=0.16, fill=WHITE, line=RED, dash=True)
priv.notes_slide.notes_text_frame.text = (
    "These are the privacy and governance decisions still open for the proposed architecture. Nothing here is "
    "implemented or approved, and no masking or redaction method has been chosen. First, masking must keep what the "
    "extraction needs: patient and practitioner names are required fields, and the practitioner name is where the AI "
    "used context in our examples. The design must protect personal data without losing those fields, or they must "
    f"be linked back on the {PLATFORM} after extraction. Second, Azure Document Intelligence receives the original "
    "receipt images, which can show diagnosis, the patient's name and contact details; this needs approved data "
    "handling controls. Third, the OCR text returned to SharePoint is unmasked until masking, so SharePoint may "
    "temporarily hold personal information; this also needs approved controls. The benchmark used unmasked OCR "
    "text, so extraction accuracy on masked text must be re-tested. Still to be agreed and approved: the PII masking "
    "method; where data is stored, including SharePoint, and for how long; who can access receipts, OCR text and "
    f"results; and how results are transferred and linked back to audit records on the {PLATFORM}, where claims, "
    "policy and historical records stay.")

# ===================================================================== main 11: conclusion
box3 = shape_with(concl, "Agree privacy and governance")
replace_in_runs(box3, "Agree privacy and governance", "Approve architecture and privacy")
replace_in_runs(box3, "PII protection, storage, access, transfer and linkage.",
                "Review and approve the proposed architecture, PII masking, storage, access, transfer and linkage.")
replace_in_runs(shape_with(concl, "Support requested"),
                "and agree the privacy and governance design.",
                "and review and approve the proposed architecture and privacy controls.")
nf = concl.notes_slide.notes_text_frame
for old, new in (("(3) Agree privacy and governance: PII protection, storage, access, transfer and linkage.",
                  "(3) Approve architecture and privacy: Review and approve the proposed architecture, PII masking, "
                  "storage, access, transfer and linkage."),
                 ("and agree the privacy and governance design.",
                  "and review and approve the proposed architecture and privacy controls.")):
    assert nf.text.count(old) == 1, old
    nf.text = nf.text.replace(old, new)

# ===================================================================== order: architecture before privacy
lst = prs.slides._sldIdLst
ids = list(lst)
lst.remove(ids[10])
lst.insert(9, ids[10])

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
