"""Prepare the Version 2 benchmark inputs: one upright copy of each of the nine receipt images.

    python data/receipts_v2/prepare_inputs.py     (run on Azure ML, from python/receipt_ocr_benchmark/)

Reads data/receipts_v2/benchmark_inputs/receiptN.* (symlinks to printable_images/; the originals
are never modified) and writes results/v2/inputs/, which all four approaches then read, so they
all get identical pixels whatever their own EXIF handling.

- No EXIF orientation, or orientation 1: the file is copied byte for byte.
- Any other orientation (the phone photos store their pixels sideways with orientation 6): the
  pixels are turned upright with Pillow's exif_transpose (an exact 90/180/270 degree rotation or
  flip) and saved as lossless PNG without the orientation tag, keeping the colour profile. No crop,
  no resize, no enhancement.

Stops unless there are exactly the nine images named in benchmark_ground_truth.xlsx and every one
can be decoded. Writes results/v2/inputs/manifest.csv recording what was done to each image.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))  # the project root, so receipt_bench imports when run as a script
from receipt_bench.score import load_ground_truth  # noqa: E402

SRC = HERE / "benchmark_inputs"
GT = HERE / "benchmark_ground_truth.xlsx"
OUT = HERE.parent.parent / "results" / "v2" / "inputs"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
ORIENTATION_TAG = 0x0112


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> None:
    images = sorted(p for p in SRC.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    expected = set(load_ground_truth(GT))
    found = {p.stem for p in images}
    if found != expected:
        sys.exit(f"Inputs do not match the ground truth. Missing: {sorted(expected - found)}; "
                 f"unexpected: {sorted(found - expected)}")

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for src in images:
        with Image.open(src) as im:
            im.load()  # fails here if the image cannot be decoded
            orientation = im.getexif().get(ORIENTATION_TAG, 1)
            before = im.size
            if orientation in (None, 1):
                dst = OUT / src.name
                shutil.copyfile(src, dst)  # follows the symlink; byte-identical copy
                action, after = "copied unchanged", before
            else:
                upright = ImageOps.exif_transpose(im)
                dst = OUT / f"{src.stem}.png"
                upright.save(dst, format="PNG", icc_profile=im.info.get("icc_profile"))
                action, after = f"rotated upright (EXIF orientation {orientation}), saved as PNG", upright.size
        with Image.open(dst) as check:
            check.load()
            if check.getexif().get(ORIENTATION_TAG, 1) not in (None, 1):
                sys.exit(f"{dst.name} still carries an orientation tag")
        rows.append({"input": dst.name, "source": src.resolve().name, "orientation": orientation, "action": action,
                     "size_before": f"{before[0]}x{before[1]}", "size_after": f"{after[0]}x{after[1]}",
                     "sha256_16": sha256(dst)})
        print(f"{dst.name:15} <- {src.resolve().name:8} {action}  {before[0]}x{before[1]} -> {after[0]}x{after[1]}")

    with open(OUT / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} benchmark inputs ready in {OUT}")


if __name__ == "__main__":
    main()
