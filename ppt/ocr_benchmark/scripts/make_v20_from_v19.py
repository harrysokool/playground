"""Build the Version 20 deck from the archived Version 19 deck: the conclusion becomes a project timeline.

    python3 ppt/ocr_benchmark/scripts/make_v20_from_v19.py --force     (from the repository root)

Main 11 (deck slide 12), "Conclusion and Next Steps", is replaced in place by "Project Timeline and Target
Rollout": a horizontal timeline of four completed milestones (June to November 2026) and four planned activities
(December 2026 to early April 2027), with the early April 2027 target rollout as the prominent milestone. Planned
dates are labelled as proposed targets, not confirmed commitments. The slide keeps its position, layout, title and
page-number placeholders; every other slide is unchanged (check_deck_v20.py verifies this).
"""
import argparse
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

PROJECT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--input", type=Path, default=PROJECT / "archive" / "v19_final" / "OCR_Benchmark_V19.pptx")
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V20.pptx")
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
PALE = RGBColor(0xC9, 0xCD, 0xD1)
LIGHT = RGBColor(0xF2, 0xF2, 0xF2)
RED_TINT = RGBColor(0xFB, 0xE7, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT, FONT_ZH = "Arial", "Microsoft JhengHei"
C = PP_ALIGN.CENTER
X0, XW = 0.39, 12.55


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


def plain_shape(slide, kind, x, y, w, h, fill, line=None, line_w=1.5, dash=False):
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
            sh.line.dash_style = MSO_LINE.DASH
    return sh


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.0, fill=None, line=None, dash=False,
         kind=MSO_SHAPE.RECTANGLE, line_w=1.5):
    box = plain_shape(slide, kind, x, y, w, h, fill, line, line_w, dash) if (fill is not None or line is not None) \
        else slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
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


def line(slide, x1, y1, x2, y2, colour, width, dash=False):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    st = ln._element.find(qn("p:style"))
    if st is not None:
        ln._element.remove(st)
    ln.line.color.rgb = colour
    ln.line.width = Pt(width)
    if dash:
        ln.line.dash_style = MSO_LINE.DASH
    return ln


def title_of(slide):
    return [sh for sh in slide.placeholders if sh.placeholder_format.idx == 10][0].text_frame.text


prs = Presentation(args.input)
slides = list(prs.slides)
assert len(slides) == 14 and title_of(slides[11]) == "Conclusion and Next Steps", [title_of(s) for s in slides[1:]]
s = slides[11]
TAG_SRC = [sh for sh in slides[10].shapes if sh.has_text_frame and sh.text_frame.text == "TO BE AGREED"][0]
MSG_SRC = [sh for sh in slides[10].shapes if sh.has_text_frame and sh.text_frame.text.startswith("Masking and data")][0]

# Keep the layout placeholders (title idx 10, page number idx 4); remove the conclusion content.
for sh in list(s.shapes):
    if not (sh.is_placeholder and sh.placeholder_format.idx in (10, 4)):
        sh._element.getparent().remove(sh._element)
title = [sh for sh in s.placeholders if sh.placeholder_format.idx == 10][0]
title.width = Inches(9.6)
title.text_frame.paragraphs[0].runs[0].text = "Project Timeline and Target Rollout"
for r in title.text_frame.paragraphs[0].runs[1:]:
    r._r.getparent().remove(r._r)

# Status tag and red message line, copied from the privacy slide so the style matches exactly.
import copy  # noqa: E402
s.shapes._spTree.append(copy.deepcopy(TAG_SRC._element))
s.shapes._spTree.append(copy.deepcopy(MSG_SRC._element))
tag = [sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text == "TO BE AGREED"][0]
tag.text_frame.paragraphs[0].runs[0].text = "PLANNED DATES ARE TARGETS"
msg = [sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith("Masking and data")][0]
msg.text_frame.paragraphs[0].runs[0].text = ("Built and benchmarked since June 2026; target rollout for audit use in "
                                             "early April 2027.")

# ===================================================================== timeline
DONE = [("Mid June 2026", "Project kickoff"),
        ("Mid July 2026", "MVP completed and presented to the Internal Audit team"),
        ("Aug – Oct 2026", "Application improved, extraction approaches benchmarked and more audit use cases "
                           "explored"),
        ("Nov 2026", "Business auditors consulted on their manual audit tests and requirements")]
PLAN = [("Dec 2026", "Test real masked medical receipts and evaluate extraction accuracy"),
        ("Jan – Feb 2027", "Improve accuracy from test results and complete application development"),
        ("Mar 2027", "Final validation, user acceptance testing and required approvals"),
        ("Early Apr 2027", "Target rollout for actual audit use")]
N = len(DONE) + len(PLAN)
GAP = 0.12
CW = (XW - (N - 1) * GAP) / N
xs = [X0 + k * (CW + GAP) for k in range(N)]
Y_PHASE, Y_DATE, Y_LINE, Y_CARD, H_CARD = 1.9, 2.42, 3.12, 3.55, 1.95

# Phase bands: completed (charcoal) and planned (red dashed outline).
split = xs[len(DONE)] - GAP / 2
text(s, X0, Y_PHASE, split - X0 - GAP / 2, 0.38, [dict(t="COMPLETED", size=12, bold=True, color=WHITE, align=C)],
     anchor=MSO_ANCHOR.MIDDLE, fill=CHAR)
text(s, split + GAP / 2, Y_PHASE, X0 + XW - split - GAP / 2, 0.38,
     [dict(t="PLANNED  ·  PROPOSED TARGETS, NOT CONFIRMED", size=12, bold=True, color=RED, align=C)],
     anchor=MSO_ANCHOR.MIDDLE, fill=WHITE, line=RED, dash=True, line_w=1.25)

# The line: solid through the completed work, dashed through the plan.
mid = [x + CW / 2 for x in xs]
line(s, mid[0], Y_LINE, split, Y_LINE, CHAR, 3)
line(s, split, Y_LINE, mid[-1], Y_LINE, RED, 3, dash=True)

for k, (when, what) in enumerate(DONE + PLAN):
    done, last = k < len(DONE), k == N - 1
    x = xs[k]
    text(s, x, Y_DATE, CW, 0.45, [dict(t=when, size=14 if last else 13, bold=True,
                                       color=RED if last else (CHAR if done else RED), align=C)],
         anchor=MSO_ANCHOR.BOTTOM)
    d = 0.5 if last else 0.3
    marker = plain_shape(s, MSO_SHAPE.OVAL, mid[k] - d / 2, Y_LINE - d / 2, d, d,
                         CHAR if done else (RED if last else WHITE), line=None if (done or last) else RED, line_w=2)
    if done or last:
        tf = marker.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = C
        r = p.add_run(); r.text = "✓" if done else "★"
        style_run(r, 20 if last else 12, True, WHITE)
    if last:
        text(s, x, Y_CARD, CW, H_CARD, [dict(t="TARGET ROLLOUT", size=11, bold=True, color=WHITE, align=C, after=6),
                                        dict(t="For actual audit use", size=14, bold=True, color=WHITE, align=C)],
             anchor=MSO_ANCHOR.MIDDLE, margin=0.12, fill=RED)
    else:
        text(s, x, Y_CARD, CW, H_CARD, [dict(t=what, size=12, color=CHAR)], anchor=MSO_ANCHOR.TOP, margin=0.12,
             fill=LIGHT if done else WHITE, line=None if done else RED, dash=not done, line_w=1.25)

text(s, X0, 5.72, 11.6, 0.32, [dict(t="Planned dates are proposed targets, not confirmed commitments. They depend on "
                                      "test results and the required approvals, including the privacy controls.",
                                    size=11, color=GREY_TXT, italic=True)])

s.notes_slide.notes_text_frame.text = (
    "Where the project stands and where it is going. Completed: we kicked off in mid June 2026; by mid July 2026 we "
    "had completed the MVP and presented it to the Internal Audit team; from August to October 2026 we improved the "
    "application, benchmarked the extraction approaches and explored additional audit use cases; and in November "
    "2026 we consulted business auditors to understand their manual audit tests and business requirements. Planned: "
    "in December 2026, test real masked medical receipts and evaluate extraction accuracy; in January and February "
    "2027, improve accuracy based on the test results and complete application development; in March 2027, "
    "complete final validation, user acceptance testing and the required approvals; and in early April 2027, the "
    "target rollout for actual audit use. The planned dates are proposed targets, not confirmed commitments. They "
    "depend on the test results and on the required approvals, including the privacy and data handling controls "
    "on the previous slide.")

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
