"""Build the Version 19 deck from the archived Version 18 deck: two small wording changes (cover + 11 slides + 2 appendix).

    python3 ppt/ocr_benchmark/scripts/make_v19_from_v18.py --force     (from the repository root)

1. Main 1-2 (deck slides 2-3): no claim that auditors retype or transcribe receipt details by hand; we are not
   certain how business auditors perform their reviews, so the wording is general ("manually reviewing").
2. Main 8 (deck slide 9): the fourth future test "Unusual provider fees" becomes "Line item arithmetic", marked as
   needing fields outside the six benchmark fields.
Text is changed run by run, so fonts, colours and layout are kept. No other slide, the slide order, the benchmark
figures or the architecture diagram change; check_deck_v19.py verifies this.
"""
import argparse
import sys
from pathlib import Path

from pptx import Presentation

PROJECT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--input", type=Path, default=PROJECT / "archive" / "v18_final" / "OCR_Benchmark_V18.pptx")
ap.add_argument("--output", type=Path, default=PROJECT / "current" / "OCR_Benchmark_V19.pptx")
ap.add_argument("--force", action="store_true", help="overwrite the output file if it already exists")
args = ap.parse_args()
OUT = args.output.resolve()
if OUT.is_relative_to((PROJECT / "archive").resolve()) or OUT.is_relative_to((PROJECT.parent / "template").resolve()):
    sys.exit(f"Refusing to write into a protected folder: {OUT}")
if OUT.exists() and not args.force:
    sys.exit(f"{OUT} already exists. Use --force to overwrite, or --output for a new path.")
OUT.parent.mkdir(parents=True, exist_ok=True)


def shape_with(slide, needle):
    hits = [sh for sh in slide.shapes if sh.has_text_frame and needle in sh.text_frame.text]
    if len(hits) != 1:
        sys.exit(f"Expected one shape containing {needle!r}, found {len(hits)}")
    return hits[0]


def run_text(slide, old, new):
    """Replace the whole text of the one run that equals `old` (formatting kept)."""
    runs = [r for sh in slide.shapes if sh.has_text_frame for p in sh.text_frame.paragraphs for r in p.runs
            if r.text == old]
    if len(runs) != 1:
        sys.exit(f"Expected one run equal to {old!r}, found {len(runs)}")
    runs[0].text = new


def notes_text(slide, pairs):
    nf = slide.notes_slide.notes_text_frame
    t = nf.text
    for old, new in pairs:
        if t.count(old) != 1:
            sys.exit(f"Expected {old!r} once in the notes")
        t = t.replace(old, new)
    nf.text = t


prs = Presentation(args.input)
slides = list(prs.slides)
assert len(slides) == 14, len(slides)
s2, s3, s9 = slides[1], slides[2], slides[8]
assert shape_with(s2, "Manual Receipt Review Limits Audit Coverage") and shape_with(s9, "Future Audit Analytics")

# ===================================================================== main 1: general review wording
run_text(s2, "Reading and retyping receipts by hand takes auditor time, so only a small sample can be checked.",
         "Manually reviewing medical receipts takes significant auditor time and effort, limiting how many receipts "
         "can be checked.")
run_text(s2, "read and retyped by hand before testing begins", "reviewed manually by an auditor")
run_text(s2, "auditor time and effort. Reading each receipt by hand keeps coverage to a small sample.",
         "auditor time and effort. Reviewing each receipt manually keeps coverage to a small sample.")
notes_text(s2, [("Each one is read by hand and its details retyped before testing can begin.",
                 "Each one is reviewed manually by an auditor."),
                ("our rough team estimate is 5 to 10 minutes for reading and transcription alone,",
                 "our rough team estimate is 5 to 10 minutes per receipt,"),
                ("separating extraction time from investigation time.",
                 "separating the time spent finding receipt details from investigation time.")])

# ===================================================================== main 2: same, on the value slide
run_text(s3, "Auditors read and retype each receipt.", "Auditors review each receipt manually.")
run_text(s3, "Details are captured again for each test.", "Receipt details are not held as structured data.")
run_text(s3, "Most time goes on reading routine receipts.", "Time goes on manually reviewing routine receipts.")
notes_text(s3, [("receipt details arrive as structured data instead of being read and retyped.",
                 "receipt details arrive as structured data instead of being found manually on each receipt.")])

# ===================================================================== main 8: line item arithmetic
card = shape_with(s9, "Unusual provider fees")
run_text(s9, "Unusual provider fees", "Line item arithmetic")
run_text(s9, "Are charges far from the usual range for the treatment?",
         "Do the individual charges and discounts add up correctly to the final receipt total?")
uses = [r for p in card.text_frame.paragraphs for r in p.runs if r.text == "Itemised charges, provider"]
assert len(uses) == 1
uses[0].text = "Itemised charges, discounts and receipt total (not among the six tested fields)"
run_text(s9, "Some tests need fields beyond the six tested, such as clinic name and itemised charges.",
         "Some tests need fields beyond the six tested, such as itemised charges and discounts.")
notes_text(s9, [("Examples of tests that use extracted receipt information, drawn from the business auditor checklist.",
                 "Examples of tests that use extracted receipt information; the first three are drawn from the "
                 "business auditor checklist."),
                ("Unusual provider fees: charges far from the usual range for a treatment.",
                 "Line item arithmetic: whether the individual charges and discounts add up correctly to the final "
                 "receipt total. Itemised charges and discounts were not among the six benchmark fields, so this "
                 "test needs broader extraction first."),
                ("Some need fields beyond the six we tested, such as clinic name and itemised charges.",
                 "Some need fields beyond the six we tested, such as itemised charges and discounts.")])

prs.save(OUT)
print(f"Saved {OUT} ({len(prs.slides)} slides)")
