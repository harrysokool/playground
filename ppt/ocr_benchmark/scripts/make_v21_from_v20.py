"""Build the Version 21 deck from the archived Version 20 deck: two proposed masking architectures (cover + 12 + 2).

    python3 ppt/ocr_benchmark/scripts/make_v21_from_v20.py --force     (from the repository root)

The two diagrams were exported from Figma (assets_v2/architecture_internal_masking.png and
assets_v2/architecture_local_llm_masking.png, 4800 x 2700). Changes:
- Main 9 (deck slide 10) "Option A: Internal Platform Masking": the new internal-masking diagram replaces the old
  one. Picture cropping hides the diagram's own label, title, subtitle and status pill (the slide title and tag
  carry them), so nothing is duplicated; the red message line is dropped and the key point moves to a short line
  under the diagram, so the diagram can be as large as possible.
- Main 10 (deck slide 11, new) "Option B: Local LLM Masking in Azure": the local LLM masking alternative, laid out
  the same way. Key benefit: masking stays within Azure Compute, removing one SharePoint round trip. Its accuracy,
  feasibility and privacy controls still require validation.
- Main 11 (deck slide 12) Privacy and Governance: reflects both options; neither is assumed to be selected.
Every other slide is unchanged; page numbers are slide-number fields, so they renumber themselves.
check_deck_v21.py verifies all of this.
"""
import argparse
import copy
import sys
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

PROJECT = Path(__file__).resolve().parent.parent
ASSETS = PROJECT / "assets_v2"
ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--input", type=Path, default=PROJECT / "archive" / "v20_final" / "OCR_Benchmark_V20.pptx")
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V21.pptx")
ap.add_argument("--force", action="store_true", help="overwrite the output file if it already exists")
args = ap.parse_args()
OUT = args.output.resolve()
if OUT.is_relative_to((PROJECT / "archive").resolve()) or OUT.is_relative_to((PROJECT.parent / "template").resolve()):
    sys.exit(f"Refusing to write into a protected folder: {OUT}")
if OUT.exists() and not args.force:
    sys.exit(f"{OUT} already exists. Use --force to overwrite, or --output for a new path.")
OUT.parent.mkdir(parents=True, exist_ok=True)

RED = RGBColor(0xD3, 0x11, 0x45)
CHAR = RGBColor(0x33, 0x3D, 0x47)
GREY_TXT = RGBColor(0x5F, 0x67, 0x70)
FONT, FONT_ZH = "Arial", "Microsoft JhengHei"
X0, XW = 0.39, 12.55
PLATFORM = "Internal Data Platform"
DIAGRAM_A = ASSETS / "architecture_internal_masking.png"
DIAGRAM_B = ASSETS / "architecture_local_llm_masking.png"
# The diagram area of both exports (pixels): below the header band (label, title, subtitle, pill end at y 525)
# and inside the white margin around the panels (content spans x 144-4655, y 654-2573).
CROP = (110, 610, 4690, 2615)
Y_TOP, Y_BOTTOM = 1.3, 6.2  # inches available under the title for the diagram


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


def shape_with(slide, needle):
    hits = [sh for sh in slide.shapes if sh.has_text_frame and needle in sh.text_frame.text]
    if len(hits) != 1:
        sys.exit(f"Expected one shape containing {needle!r}, found {len(hits)}")
    return hits[0]


def remove(shape):
    shape._element.getparent().remove(shape._element)


def set_text(shape, new):
    """Replace a one-run paragraph's text, keeping its formatting."""
    p = shape.text_frame.paragraphs[0]
    p.runs[0].text = new
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)


def title_ph(slide):
    return [sh for sh in slide.placeholders if sh.placeholder_format.idx == 10][0]


def place_diagram(slide, path):
    """Add the diagram, cropped to its panels, centred and as large as the space under the title allows."""
    with Image.open(path) as im:
        assert im.size == (4800, 2700), (path, im.size)
        W, H = im.size
    x0, y0, x1, y1 = CROP
    ar = (x1 - x0) / (y1 - y0)
    h = Y_BOTTOM - Y_TOP
    w = min(XW, h * ar)
    h = w / ar
    pic = slide.shapes.add_picture(str(path), Inches(X0 + (XW - w) / 2), Inches(Y_TOP), Inches(w), Inches(h))
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = x0 / W, y0 / H, (W - x1) / W, (H - y1) / H
    return pic


def caption(slide, key, rest):
    """One short line under the diagram: the key point in red, the caveat in grey."""
    box = slide.shapes.add_textbox(Inches(X0), Inches(Y_BOTTOM + 0.1), Inches(11.6), Inches(0.5))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    for t, bold, colour, italic in ((key + "  ", True, RED, False), (rest, False, GREY_TXT, True)):
        r = p.add_run(); r.text = t
        style_run(r, 12, bold, colour, italic)
    return box


prs = Presentation(args.input)
slides = list(prs.slides)
assert len(slides) == 14, len(slides)
arch, priv = slides[9], slides[10]
assert title_ph(arch).text_frame.text == "Proposed Architecture and Data Flow"
assert title_ph(priv).text_frame.text == "Privacy and Governance"

# ===================================================================== option A (replaces the old diagram)
for sh in [sh for sh in arch.shapes if sh.shape_type == 13]:
    remove(sh)
remove(shape_with(arch, "A proposed design, not yet implemented"))
remove(shape_with(arch, "The benchmark sent unmasked OCR text"))
set_text(title_ph(arch), "Option A: Internal Platform Masking")
shape_with(arch, "PROPOSED · NOT IMPLEMENTED")  # the tag stays
place_diagram(arch, DIAGRAM_A)
caption(arch, "Masking on the Internal Data Platform; only masked text reaches Azure OpenAI.",
        "Accuracy on masked text is not yet tested.")
arch.notes_slide.notes_text_frame.text = (
    "Option A, a proposed architecture: it is not implemented, approved or selected. It is different from the "
    "benchmark workflow, where Azure Document Intelligence read the receipt images and the unmasked OCR text went "
    "straight to Azure OpenAI. In Option A: (1) approved receipt images from the internal document source are "
    "uploaded to SharePoint; (2) Azure Document Intelligence in Azure Compute converts them to OCR text, and (3) the "
    f"unmasked OCR text returns to SharePoint, where it may contain personal information; (4) the {PLATFORM} takes "
    "the text for PII masking, where customer, claims and policy data are available, and (5) uploads the masked text "
    "to SharePoint; (6) only the masked OCR text is sent to Azure OpenAI, the only step that leaves Hong Kong; (7) the "
    f"structured results return to SharePoint and (8) the {PLATFORM} retrieves them and links them to the receipts "
    "for audit testing. The benchmark used unmasked OCR text, so accuracy on masked text still needs testing. The "
    "next slide shows an alternative, Option B. The open privacy and governance decisions for both options follow.")

# ===================================================================== option B (new slide after option A)
new = prs.slides.add_slide(arch.slide_layout)
for sh in list(new.shapes):
    remove(sh)
for el in arch.shapes._spTree:
    if el.tag in (qn("p:sp"),) and el is not None:  # title, page number, tag and caption: text shapes only
        new.shapes._spTree.append(copy.deepcopy(el))
set_text(title_ph(new), "Option B: Local LLM Masking in Azure")
remove(shape_with(new, "Masking on the Internal Data Platform"))
place_diagram(new, DIAGRAM_B)
caption(new, "Key benefit: masking within Azure Compute, one fewer SharePoint round trip.",
        "Accuracy, feasibility and privacy controls still require validation.")
new.notes_slide.notes_text_frame.text = (
    "Option B, a proposed alternative: it is not implemented, approved or selected. The key benefit is that masking "
    "takes place within Azure Compute, which removes one SharePoint round trip and reduces data transfers between "
    "systems: the unmasked OCR text no longer returns to SharePoint or goes to the "
    f"{PLATFORM} for masking. In Option B: (1) approved receipt images are uploaded to SharePoint; (2) Azure Document "
    "Intelligence converts them to OCR text; (3) a local LLM in Azure Compute masks the personal data in the OCR "
    "text; (4) only the masked OCR text is sent to Azure OpenAI, the only step that leaves Hong Kong; (5) the "
    f"structured results return to SharePoint and (6) the {PLATFORM} retrieves them and links them to the receipts "
    "for audit testing, where customer, claims and policy data stay. The local LLM masking has not been built or "
    "tested: its masking accuracy, its feasibility in Azure Compute and its privacy controls still require "
    "validation, and extraction accuracy on masked text is not yet tested for either option.")
lst = prs.slides._sldIdLst
ids = list(lst)
lst.remove(ids[-1])
lst.insert(10, ids[-1])

# ===================================================================== privacy and governance: both options
set_text(shape_with(priv, "Masking and data handling must be agreed"),
         "Neither masking option is selected; data handling must be approved before real receipts are processed.")
set_text(shape_with(priv, "SharePoint may hold unmasked text"), "Where masking happens is open")
body = shape_with(priv, "OCR text returned by Azure DI may sit unmasked")
set_text(body, "Option A: Internal Data Platform; SharePoint may first hold unmasked OCR text. Option B: local "
               "LLM in Azure Compute; still needs validation.")
note_runs = shape_with(priv, "the benchmark used unmasked OCR text").text_frame.paragraphs[0].runs
assert [r.text for r in note_runs][0] == "Benchmark note: ", [r.text for r in note_runs]
note_runs[1].text = "the benchmark used unmasked OCR text. Accuracy on masked text must be re-tested for either option."
pii = shape_with(priv, "PII masking method")
pii.text_frame.paragraphs[1].runs[0].text = "Option A or B; not yet chosen or approved"
for r in pii.text_frame.paragraphs[1].runs[1:]:
    r._r.getparent().remove(r._r)
priv.notes_slide.notes_text_frame.text = (
    "These are the privacy and governance decisions still open for both proposed options. Neither option is "
    "selected, nothing here is implemented or approved, and no masking method has been chosen. First, masking must "
    "keep what the extraction needs: patient and practitioner names are required fields, and the practitioner name "
    "is where the AI used context in our examples. The design must protect personal data without losing those "
    f"fields, or they must be linked back on the {PLATFORM} after extraction. Second, in both options Azure Document "
    "Intelligence receives the original receipt images, which can show diagnosis, the patient's name and contact "
    "details; this needs approved data handling controls. Third, where masking happens is open. In Option A, masking "
    f"runs on the {PLATFORM}, so the OCR text returned to SharePoint is unmasked until masking and SharePoint may "
    "temporarily hold personal information. In Option B, a local LLM masks the text within Azure Compute, which "
    "removes that SharePoint round trip, but its masking accuracy, feasibility and privacy controls still require "
    "validation. The benchmark used unmasked OCR text, so extraction accuracy on masked text must be re-tested for "
    "either option. Still to be agreed and approved: the PII masking option and method; where data is stored, "
    "including SharePoint, and for how long; who can access receipts, OCR text and results; and how results are "
    f"transferred and linked back to audit records on the {PLATFORM}, where claims, policy and historical records "
    "stay.")

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
