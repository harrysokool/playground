"""Azure Document Intelligence (prebuilt-read) as an OCR engine for the benchmark.

DI only does the OCR. Its result is converted into the same raw OCR format PaddleOCR produces
(`raw_ocr.RawOCRResult`), so the general rules (`extract_cli --rules general`) and `score.py`
work on it unchanged. There are no DI-specific extraction rules.

Usage (on Azure ML compute - every receipt is a paid DI call):
    export AZURE_DI_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
    export AZURE_DI_KEY=<key>        # optional: without it, Entra ID (DefaultAzureCredential) is used
    python -m receipt_bench.azure_di --input data/raw --output results/azure_di

Offline (no Azure calls): re-convert DI responses saved by an earlier run.
    python -m receipt_bench.azure_di --from-responses results/azure_di/di_response --output results/azure_di

For each receipt the output directory gets:
- receiptN.json               raw OCR in the common format; timings.total_ms = DI call time
- di_response/receiptN.json   the full DI response as returned (or {"error": ...} if it failed)
A failed receipt gets no receiptN.json, so the scorer counts all its fields as Wrong.

Conversion: one OCR block per DI line - text, 4-point polygon (DI's flat [x1, y1, ..., x4, y4]),
reading order (DI's line order), and confidence = mean confidence of the line's words (DI has
no line-level confidence; the general rules drop blocks without one).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult

MODEL_ID = "prebuilt-read"
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pdf"}  # same as cli.py


def _line_confidence(line: dict, words: list[dict]) -> float | None:
    """Mean confidence of the words whose span falls inside the line's spans."""
    ranges = [(s["offset"], s["offset"] + s["length"]) for s in line.get("spans", [])]
    confs = [w["confidence"] for w in words
             if "confidence" in w and any(a <= w["span"]["offset"] < b for a, b in ranges)]
    return sum(confs) / len(confs) if confs else None


def di_to_raw_ocr(document_id: str, di_result: dict, di_ms: float) -> RawOCRResult:
    """Converts a DI analyze result (REST/`as_dict()` shape, camelCase keys) into RawOCRResult."""
    pages = []
    for page in di_result.get("pages", []):
        words = page.get("words", [])
        blocks = []
        for i, line in enumerate(page.get("lines", [])):
            flat = line.get("polygon") or []
            blocks.append(OCRBlock(
                text=line["content"],
                confidence=_line_confidence(line, words),
                polygon=[[float(flat[j]), float(flat[j + 1])] for j in range(0, len(flat) - 1, 2)],
                reading_order=i,
            ))
        pages.append(PageResult(
            page_number=page["pageNumber"],
            width=page["width"],
            height=page["height"],
            blocks=blocks,
            plain_text="\n".join(b.text for b in blocks),
        ))
    return RawOCRResult(
        document_id=document_id,
        engine_config={"engine_config_name": "azure_di", "model_id": di_result.get("modelId", MODEL_ID),
                       "api_version": di_result.get("apiVersion"), "unit": (di_result.get("pages") or [{}])[0].get("unit")},
        pages=pages,
        timings={"total_ms": di_ms},
    )


def _client():
    """Built only when actually calling Azure, so tests and offline runs need no Azure SDK."""
    from azure.ai.documentintelligence import DocumentIntelligenceClient

    endpoint = os.environ.get("AZURE_DI_ENDPOINT")
    if not endpoint:
        sys.exit("Set AZURE_DI_ENDPOINT (and AZURE_DI_KEY, or sign in for Entra ID auth).")
    if os.environ.get("AZURE_DI_KEY"):
        from azure.core.credentials import AzureKeyCredential
        credential = AzureKeyCredential(os.environ["AZURE_DI_KEY"])
    else:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
    return DocumentIntelligenceClient(endpoint=endpoint, credential=credential)


def analyze(client, path: Path) -> tuple[dict, float]:
    """One prebuilt-read call. Time covers upload, service processing and result polling."""
    start = time.perf_counter()
    with open(path, "rb") as fh:
        poller = client.begin_analyze_document(MODEL_ID, body=fh, content_type="application/octet-stream")
        result = poller.result()
    return result.as_dict(), (time.perf_counter() - start) * 1000


def _load_saved_response(path: Path) -> tuple[dict | None, float | None, str | None]:
    """Reads a saved response: this module's di_response/ files, or the older DI runner format
    (`raw_di_result` + `timings_seconds.di`). Returns (di_result, di_ms, error)."""
    data = json.loads(path.read_text())
    if "raw_di_result" in data:
        secs = (data.get("timings_seconds") or {}).get("di")
        return data["raw_di_result"], (secs * 1000 if secs is not None else None), data.get("error")
    return data.get("result"), data.get("di_ms"), data.get("error")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="A receipt file or directory of receipts (calls Azure DI).")
    src.add_argument("--from-responses", type=Path, help="Directory of saved DI responses (no Azure calls).")
    parser.add_argument("--output", required=True, type=Path, help="Directory to write raw OCR JSON to.")
    args = parser.parse_args()

    response_dir = args.output / "di_response"
    response_dir.mkdir(parents=True, exist_ok=True)
    failed = 0

    if args.input:
        files = (sorted(p for p in args.input.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
                 if args.input.is_dir() else [args.input])
        client = _client()
        for path in files:
            print(f"Processing {path} ...")
            try:
                di_result, di_ms = analyze(client, path)
            except Exception as exc:  # record and continue; the scorer counts it as no result
                failed += 1
                (response_dir / f"{path.stem}.json").write_text(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2))
                print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
                continue
            (response_dir / f"{path.stem}.json").write_text(
                json.dumps({"di_ms": di_ms, "result": di_result}, indent=2, ensure_ascii=False))
            di_to_raw_ocr(path.stem, di_result, di_ms).save(args.output / f"{path.stem}.json")
            print(f"  -> {args.output / (path.stem + '.json')} ({di_ms:.0f} ms)")
    else:
        for path in sorted(args.from_responses.glob("*.json")):
            if path.stem == "summary":
                continue
            di_result, di_ms, error = _load_saved_response(path)
            if error or di_result is None:
                failed += 1
                print(f"{path.name}: skipped, saved run failed: {error}", file=sys.stderr)
                continue
            if path.parent.resolve() != response_dir.resolve():
                (response_dir / path.name).write_text(
                    json.dumps({"di_ms": di_ms, "result": di_result, "reused_from": str(path)}, indent=2, ensure_ascii=False))
            di_to_raw_ocr(path.stem, di_result, di_ms or 0.0).save(args.output / path.name)
            print(f"{path.name} -> {args.output / path.name} (reused DI response, {di_ms or 0:.0f} ms)")

    if failed:
        print(f"{failed} receipt(s) failed - see {response_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
