"""Deterministic, label-based extraction of a handful of receipt fields from raw OCR output.

Phase 3 of the benchmark: tests how far simple rules (label matching, regex, nearby-block
lookup) get before they become fragile. Only 6 fields, no line items, no ML. If a field has
no reliable simple rule, it stays null and a warning is recorded instead of guessing.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from receipt_bench.raw_ocr import OCRBlock, RawOCRResult

# Explicit labels only (per the benchmark's Phase 3 scope) - no synonym expansion beyond
# what real receipts are expected to use. Longer/more specific phrases are tried first so
# e.g. "grand total" wins over "total", and anchoring the match to the start of the block
# text keeps "total" from matching inside "subtotal".
LABEL_PATTERNS: dict[str, list[str]] = {
    "doctor_name": ["doctor name", "provider name", "doctor", "provider"],
    "registration_number": ["registration no", "registration number", "reg no"],
    "patient_name": ["patient name", "patient"],
    "receipt_number": ["receipt no", "receipt number", "invoice no", "invoice number"],
    "service_date": ["service date"],
    "total_amount": ["grand total", "total"],
}

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%b %d, %Y", "%b %d %Y"]


@dataclass
class ExtractedReceipt:
    document_id: str
    doctor_name: str | None = None
    registration_number: str | None = None
    patient_name: str | None = None
    receipt_number: str | None = None
    service_date: str | None = None
    total_amount: float | None = None
    sources: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))


def extract_receipt(raw: RawOCRResult) -> ExtractedReceipt:
    result = ExtractedReceipt(document_id=raw.document_id)
    all_blocks = [block for page in raw.pages for block in page.blocks]

    for field_name, patterns in LABEL_PATTERNS.items():
        found = _find_field_value(patterns, all_blocks)
        if found is None:
            result.warnings.append(f"{field_name}: no matching label found")
            continue

        raw_value, source_text = found
        value, warning = _normalize(field_name, raw_value)
        if value is None:
            result.warnings.append(f"{field_name}: {warning}")
            continue

        setattr(result, field_name, value)
        result.sources[field_name] = source_text
        if warning:
            result.warnings.append(f"{field_name}: {warning}")

    return result


def _find_field_value(patterns: list[str], all_blocks: list[OCRBlock]) -> tuple[str, str] | None:
    """Find a label match and its value: same block first, else the nearest block by position."""
    for block in all_blocks:
        label_match = _match_label(block.text, patterns)
        if label_match is None:
            continue
        _label, remainder = label_match

        if remainder:
            return remainder, block.text

        nearby = _find_nearby_value_block(block, all_blocks)
        if nearby is not None and nearby.text.strip():
            return nearby.text.strip(), f"{block.text} | {nearby.text}"

    return None


def _match_label(text: str, patterns: list[str]) -> tuple[str, str] | None:
    """If `text` starts with one of `patterns`, return (label, remainder-after-label)."""
    stripped = text.strip()
    for pattern in sorted(patterns, key=len, reverse=True):
        match = re.match(rf"(?i)^{re.escape(pattern)}\b\s*[:\-]?\s*(.*)$", stripped)
        if match:
            return pattern, match.group(1).strip()
    return None


def _find_nearby_value_block(label_block: OCRBlock, all_blocks: list[OCRBlock]) -> OCRBlock | None:
    """Best-effort spatial lookup: the closest block to the right on the same line, else the
    next block in reading order (e.g. the label sits above the value in a form layout)."""
    lx0, ly0, lx1, ly1 = _bbox(label_block)
    label_height = ly1 - ly0

    same_line = []
    for block in all_blocks:
        if block is label_block:
            continue
        bx0, by0, bx1, by1 = _bbox(block)
        block_center_y = (by0 + by1) / 2
        if bx0 >= lx1 and abs(block_center_y - (ly0 + ly1) / 2) < label_height:
            same_line.append(block)

    if same_line:
        return min(same_line, key=lambda b: _bbox(b)[0])

    if label_block.reading_order is not None:
        for block in all_blocks:
            if block.reading_order == label_block.reading_order + 1:
                return block

    return None


def _bbox(block: OCRBlock) -> tuple[float, float, float, float]:
    xs = [p[0] for p in block.polygon]
    ys = [p[1] for p in block.polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _normalize(field_name: str, value: str) -> tuple[str | float | None, str | None]:
    value = value.strip()

    if field_name == "total_amount":
        match = re.search(r"\d[\d,]*\.\d{2}|\d+", value)
        if not match:
            return None, f"could not parse a number from '{value}'"
        return float(match.group(0).replace(",", "")), None

    if field_name == "service_date":
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date().isoformat(), None
            except ValueError:
                continue
        return value, f"date '{value}' did not match a known format, kept as-is"

    if not value:
        return None, "label matched but the value was empty"

    return value, None
