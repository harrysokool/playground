"""Run deterministic field extraction over existing raw OCR JSON results.

Usage:
    python -m receipt_bench.extract_cli --input results/paddle_light --output results/paddle_light_extracted
    python -m receipt_bench.extract_cli --rules tuned --input results/paddle_light --output results/extracted_tuned_light
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from receipt_bench.extraction import extract_receipt
from receipt_bench.extraction_tuned import extract_receipt_tuned
from receipt_bench.raw_ocr import RawOCRResult


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Directory of raw OCR JSON results.")
    parser.add_argument("--output", required=True, type=Path, help="Directory to write extracted JSON to.")
    parser.add_argument(
        "--rules",
        choices=["baseline", "tuned"],
        default="baseline",
        help="baseline = Phase 3 general rules; tuned = Phase 3b rules deliberately overfit to the sample layouts.",
    )
    args = parser.parse_args()
    extract = extract_receipt_tuned if args.rules == "tuned" else extract_receipt

    files = sorted(args.input.glob("*.json"))
    if not files:
        print(f"No OCR JSON files found in {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)
    for file_path in files:
        raw = RawOCRResult.load(file_path)
        extracted = extract(raw)
        out_path = args.output / file_path.name
        extracted.save(out_path)
        print(f"{file_path.name} -> {out_path} (warnings: {len(extracted.warnings)})")


if __name__ == "__main__":
    main()
