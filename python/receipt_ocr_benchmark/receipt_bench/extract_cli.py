"""Run deterministic field extraction over existing raw OCR JSON results.

Usage:
    python -m receipt_bench.extract_cli --input results/paddle_light --output results/paddle_light_extracted
    python -m receipt_bench.extract_cli --rules tuned --input results/paddle_light --output results/extracted_tuned_light
    python -m receipt_bench.extract_cli --rules general --input results/paddle_light --output results/extracted_general_light
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from receipt_bench.extraction import extract_receipt
from receipt_bench.extraction_general import extract_receipt_general
from receipt_bench.extraction_tuned import extract_receipt_tuned
from receipt_bench.raw_ocr import RawOCRResult


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Directory of raw OCR JSON results.")
    parser.add_argument("--output", required=True, type=Path, help="Directory to write extracted JSON to.")
    parser.add_argument(
        "--rules",
        choices=["baseline", "tuned", "general"],
        default="baseline",
        help="baseline = Phase 3 first-pass rules; tuned = Phase 3b rules deliberately overfit to the sample layouts; "
        "general = Phase 3c reusable rules with no layout knowledge.",
    )
    args = parser.parse_args()
    extract = {"baseline": extract_receipt, "tuned": extract_receipt_tuned, "general": extract_receipt_general}[args.rules]

    files = sorted(args.input.glob("*.json"))
    if not files:
        print(f"No OCR JSON files found in {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)
    for file_path in files:
        raw = RawOCRResult.load(file_path)
        start = time.perf_counter()
        extracted = extract(raw)
        extract_ms = (time.perf_counter() - start) * 1000
        if hasattr(extracted, "timings"):
            extracted.timings["extract_ms"] = extract_ms
        out_path = args.output / file_path.name
        extracted.save(out_path)
        print(f"{file_path.name} -> {out_path} (warnings: {len(extracted.warnings)}, extract {extract_ms:.1f} ms)")


if __name__ == "__main__":
    main()
