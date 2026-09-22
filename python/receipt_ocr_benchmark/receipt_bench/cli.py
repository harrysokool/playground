"""Run a PaddleOCR benchmark config over one receipt file or a directory of them.

Usage:
    python -m receipt_bench.cli --config configs/paddle_light.yaml --input data/raw --output results/paddle_light
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from receipt_bench.paddle_engine import PaddleEngine

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pdf"}


def iter_input_files(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(p for p in input_path.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
    return [input_path]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="Engine config YAML.")
    parser.add_argument("--input", required=True, type=Path, help="A receipt file or a directory of receipts.")
    parser.add_argument("--output", required=True, type=Path, help="Directory to write JSON results to.")
    args = parser.parse_args()

    files = iter_input_files(args.input)
    if not files:
        print(f"No receipt files found in {args.input}", file=sys.stderr)
        sys.exit(1)

    config = yaml.safe_load(args.config.read_text())
    engine = PaddleEngine(config)
    args.output.mkdir(parents=True, exist_ok=True)

    for file_path in files:
        print(f"Processing {file_path} ...")
        result = engine.process(file_path)
        out_path = args.output / f"{file_path.stem}.json"
        result.save(out_path)
        print(f"  -> {out_path} ({result.timings['total_ms']:.0f} ms)")


if __name__ == "__main__":
    main()
