"""Export the eight validated receipt PDFs as print-quality PNG images.

    python data/receipts_v2/export_images.py     (from python/receipt_ocr_benchmark/)

The PDFs in printable/ are rasterised at 300 dpi (Poppler pdftoppm), so each image is identical to
the approved design. A4 receipts keep the full A4 page. The smaller receipts are cropped to their
real cut-out size (A5, A5 landscape, 80 mm till slip), without the trim marks. Each PNG stores
300 dpi, so it prints at its physical size at 100% scale.

Writes printable_images/receiptN.png and printable_images/contact_sheet.png, then checks:
- every word in the PDF (all specified values were already checked present) falls inside its
  image and is actually rendered there (ink inside the word's box);
- nothing but trim marks is cut away, and nothing touches the image edge;
- the printed size in mm matches the intended receipt size.
No OCR is used.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PDFS, OUT = HERE / "printable", HERE / "printable_images"
DPI = 300
MM = DPI / 25.4  # pixels per mm

# Receipt rectangle on the A4 page in mm (x, y, w, h); must match generate_receipts.py.
# None = the full page; "auto" = the till slip, whose height follows its content (found from its outline).
BOXES = {"r1": (31, 22, 148, 210), "r2": None, "r3": None, "r4": (31, 22, 148, 210),
         "r5": (0, 30, 210, 148), "r6": None, "r7": "auto", "r8": None}
INTENDED_MM = {"r1": (148, 210), "r2": (210, 297), "r3": (210, 297), "r4": (148, 210),
               "r5": (210, 148), "r6": (210, 297), "r7": (80, None), "r8": (210, 297)}
WHITE_LIMIT = 245  # a pixel darker than this (any channel) counts as ink


def rasterise(pdf: Path, workdir: Path) -> Image.Image:
    stem = workdir / pdf.stem
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), "-singlefile", str(pdf), str(stem)], check=True)
    return Image.open(f"{stem}.png").convert("RGB")


def ink_bbox(im: Image.Image) -> tuple[int, int, int, int] | None:
    gray = im.convert("L").point(lambda v: 255 if v < WHITE_LIMIT else 0)
    return gray.getbbox()


def crop_box(rid: str, page: Image.Image) -> tuple[int, int, int, int]:
    box = BOXES[rid]
    if box is None:
        return (0, 0, page.width, page.height)
    if box == "auto":  # the slip sits in the middle third of the page; its dashed outline bounds it
        x0, x1 = round(60 * MM), round(150 * MM)
        bb = ink_bbox(page.crop((x0, 0, x1, page.height)))
        return (x0 + bb[0], bb[1], x0 + bb[2], bb[3])
    x, y, w, h = box
    return (round(x * MM), round(y * MM), min(round((x + w) * MM), page.width), round((y + h) * MM))


def words(pdf: Path) -> list[tuple[str, float, float, float, float]]:
    """Every word in the PDF with its box in PDF points (pdftotext -bbox)."""
    xml = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    return [(m[5], float(m[1]), float(m[2]), float(m[3]), float(m[4])) for m in re.finditer(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', xml)]


def check(rid: str, pdf: Path, page: Image.Image, box: tuple[int, int, int, int], img: Image.Image) -> list[str]:
    problems = []
    scale = DPI / 72
    for text, x0, y0, x1, y1 in words(pdf):
        px = (x0 * scale, y0 * scale, x1 * scale, y1 * scale)
        if px[0] < box[0] - 1 or px[1] < box[1] - 1 or px[2] > box[2] + 1 or px[3] > box[3] + 1:
            problems.append(f"{rid}: word {text!r} lies outside the image")
            continue
        region = img.crop((int(px[0] - box[0]), int(px[1] - box[1]), int(px[2] - box[0]) + 1, int(px[3] - box[1]) + 1))
        if ink_bbox(region) is None:
            problems.append(f"{rid}: word {text!r} is not rendered (no ink in its box)")
    # nothing but light-grey trim marks may be cut away
    if box != (0, 0, page.width, page.height):
        mask = Image.new("L", page.size, 255)
        ImageDraw.Draw(mask).rectangle(box, fill=0)
        outside = Image.composite(page, Image.new("RGB", page.size, "white"), mask)
        dark = outside.convert("L").point(lambda v: 255 if v < 120 else 0).getbbox()  # trim marks are #9a9a9a
        if dark:
            problems.append(f"{rid}: dark content was cropped away at {dark} (content outside the receipt?)")
    return problems


def contact_sheet(images: dict[str, Image.Image], spec: dict) -> Image.Image:
    """All eight at the same physical scale (1 mm = 2 px), so their relative sizes are true."""
    s, pad, label = 2.0, 40, 60
    cells = [(r, images[r["receipt_id"]]) for r in spec["receipts"]]
    thumbs = [(r, im.resize((round(im.width / MM * s), round(im.height / MM * s)), Image.LANCZOS)) for r, im in cells]
    col_w, row_h = round(210 * s), round(297 * s)
    sheet = Image.new("RGB", (4 * col_w + 5 * pad, 2 * (row_h + label) + 3 * pad), "#e9e9e9")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    for i, (r, th) in enumerate(thumbs):
        x = pad + (i % 4) * (col_w + pad)
        y = pad + (i // 4) * (row_h + label + pad)
        sheet.paste(th, (x + (col_w - th.width) // 2, y))
        draw.rectangle([x + (col_w - th.width) // 2 - 1, y - 1, x + (col_w + th.width) // 2, y + th.height], outline="#888888")
        w_mm, h_mm = images[r["receipt_id"]].width / MM, images[r["receipt_id"]].height / MM
        draw.text((x, y + row_h + 8), f"{r['file_stem']}: {r['type']}", fill="black", font=font)
        draw.text((x, y + row_h + 32), f"{w_mm:.0f} x {h_mm:.0f} mm · {r['language'].split(' (')[0]}", fill="#444444", font=font)
    return sheet


def main() -> None:
    spec = json.loads((HERE / "receipts_spec.json").read_text())
    OUT.mkdir(exist_ok=True)
    problems, images, sizes = [], {}, []
    with tempfile.TemporaryDirectory() as tmp:
        for r in spec["receipts"]:
            rid, pdf = r["receipt_id"], PDFS / f"{r['file_stem']}.pdf"
            page = rasterise(pdf, Path(tmp))
            box = crop_box(rid, page)
            img = page.crop(box)
            problems += check(rid, pdf, page, box, img)
            img.save(OUT / f"{r['file_stem']}.png", dpi=(DPI, DPI), optimize=True)
            images[rid] = img
            w_mm, h_mm = img.width / MM, img.height / MM
            want_w, want_h = INTENDED_MM[rid]
            if abs(w_mm - want_w) > 1 or (want_h and abs(h_mm - want_h) > 1):
                problems.append(f"{rid}: prints at {w_mm:.1f} x {h_mm:.1f} mm, intended {want_w} x {want_h}")
            sizes.append(f"{r['file_stem']}.png  {img.width} x {img.height} px  = {w_mm:.1f} x {h_mm:.1f} mm at {DPI} dpi")
    contact_sheet(images, spec).save(OUT / "contact_sheet.png", optimize=True)
    print("\n".join(sizes))
    if problems:
        sys.exit("Image check failed:\n- " + "\n- ".join(problems))
    print("All 8 images contain every word of their PDF, rendered, at the intended size.")


if __name__ == "__main__":
    main()
