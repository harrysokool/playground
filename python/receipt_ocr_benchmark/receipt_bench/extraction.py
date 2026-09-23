"""Deterministic, rule-based extraction of a handful of receipt fields from raw OCR output.

Phase 3 of the benchmark: tests how far simple rules (label matching, regex, nearby-block
lookup by coordinates) get before they become fragile. Only 6 fields, no line items, no ML.
If a field has no reliable simple rule, it stays null and a warning is recorded instead of
guessing.

Rules below were shaped by inspecting the 5 real receipts' actual OCR JSON (results/paddle_light,
results/paddle_heavy), not just the synthetic test fixture - see the phase report for what was
found and why each rule exists.

Two matching strategies per field, tried in order:
1. Label match: a block starts with one of `label_patterns` (most specific/authoritative
   first), and the value is either the rest of that block, or - if the label is alone in its
   block - the nearest block by OCR coordinates (same line to the right, else directly below).
2. Standalone pattern (fallback, only if no label matched anywhere): a regex that recognizes
   the value on its own, e.g. "Dr Chan" or "M12345", for receipts that don't label the field
   at all.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from receipt_bench.raw_ocr import OCRBlock, RawOCRResult


@dataclass
class FieldRule:
    # Ordered most specific/authoritative first: the first pattern with any match anywhere
    # in the document wins, so e.g. "grand total" beats a "total" found earlier in reading order.
    label_patterns: list[str]
    # A regex `fullmatch`ed against a whole block's text, used only when no label matched at all.
    standalone_pattern: re.Pattern | None = None
    # Fields expected to be a single short code/token (IDs, numbers) - if a label's remainder
    # runs on into unrelated text (a real failure mode: OCR merges several "label: value" pairs
    # from one visual line into a single block), only the first token is kept.
    single_token: bool = False


DOCTOR_TITLES = r"Dr\.?|Doctor|Physician|Medical Practitioner|Provider|Clinician"
# Chinese medical titles are a suffix on the name ("李俊年醫生"), not a prefix like English.
CJK_DOCTOR_SUFFIX = re.compile(r"^([一-鿿]{2,8})(医生|醫生)$")

FIELD_RULES: dict[str, FieldRule] = {
    "doctor_name": FieldRule(
        # NOTE: "consultant" is a real label seen in 3/5 receipts but its value was
        # unreliable/blank in every case observed - see the phase report. Left out
        # deliberately rather than added just to match label vocabulary.
        label_patterns=["doctor name", "provider name", "medical practitioner", "physician", "clinician", "doctor", "provider"],
        standalone_pattern=re.compile(
            rf"(?i)^({DOCTOR_TITLES})\s+([A-Za-z][A-Za-z.,'\-]*(?:\s+[A-Za-z][A-Za-z.,'\-]*){{0,3}})$"
        ),
    ),
    "registration_number": FieldRule(
        label_patterns=["registration number", "registration no", "reg no"],
        standalone_pattern=re.compile(r"^M[\-\s]?\d{4,}$"),
        single_token=True,
    ),
    "patient_name": FieldRule(
        label_patterns=["patient name", "patient", "name"],
    ),
    "receipt_number": FieldRule(
        label_patterns=["receipt number", "receipt no", "invoice number", "invoice no", "bill no"],
        single_token=True,
    ),
    "service_date": FieldRule(
        label_patterns=["service date", "date of service", "consultation date", "visit date", "treatment date"],
    ),
    "total_amount": FieldRule(
        # Ranked by what the label actually means, not just specificity: "total amount" is
        # the invoice's real total, while "amount due"/"total due" is the *outstanding
        # balance* and can legitimately read $0.00 on a fully-paid invoice that still has a
        # much larger real total elsewhere (seen in real data) - so those rank lower, not
        # higher, despite sounding equally "final". "subtotal" is never matched because
        # matching requires the block to *start* with the pattern, and "Subtotal" starts
        # with "Sub", not "total".
        label_patterns=["grand total", "net total", "total amount due", "total amount", "total", "amount due", "total due", "paid"],
    ),
}

DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d",
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%m/%d/%Y",
    "%d %b %Y", "%b %d, %Y", "%b %d %Y",
]
DATE_PATTERN = re.compile(
    r"\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}"
    r"|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4}"
)


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

    for field_name, rule in FIELD_RULES.items():
        found = _find_labeled_value(field_name, rule.label_patterns, all_blocks)
        if found is None and rule.standalone_pattern is not None:
            found = _find_standalone_value(rule.standalone_pattern, all_blocks)
        if found is None and field_name == "doctor_name":
            found = _find_cjk_doctor_suffix(all_blocks)
        if found is None:
            result.warnings.append(f"{field_name}: no matching label or pattern found")
            continue

        raw_value, source_text = found
        if rule.single_token:
            raw_value = raw_value.split()[0] if raw_value.split() else raw_value

        if field_name in ("doctor_name", "patient_name") and any(c.isdigit() for c in raw_value):
            result.warnings.append(
                f"{field_name}: matched value '{raw_value}' contains digits, doesn't look like a name, skipped"
            )
            continue
        if field_name == "patient_name" and re.match(rf"(?i)^({DOCTOR_TITLES})\b", raw_value):
            result.warnings.append(
                f"patient_name: matched value '{raw_value}' looks like a doctor's name, skipped"
            )
            continue

        value, warning = _normalize(field_name, raw_value)
        if value is None:
            result.warnings.append(f"{field_name}: {warning}")
            continue

        setattr(result, field_name, value)
        result.sources[field_name] = source_text
        if warning:
            result.warnings.append(f"{field_name}: {warning}")

    return result


def _find_labeled_value(field_name: str, patterns: list[str], all_blocks: list[OCRBlock]) -> tuple[str, str] | None:
    """Try each label pattern in priority order; within a pattern, first match in reading
    order wins. A pattern found anywhere beats a lower-priority pattern found earlier."""
    for pattern in patterns:
        for block in all_blocks:
            remainder = _match_label(block.text, pattern)
            if remainder is None:
                continue
            # Bare "Total" is also a common table-column header (next to QTY/RATE/AMOUNT);
            # if it shares its line with several other short blocks, it's a header, not
            # the grand total label - skip it and keep looking.
            if pattern == "total" and _looks_like_table_header_row(block, all_blocks):
                continue

            if remainder:
                value = remainder
                source = block.text
            else:
                nearby = _find_nearby_value_block(block, all_blocks)
                if nearby is None or not nearby.text.strip():
                    continue
                value = nearby.text.strip()
                source = f"{block.text} | {nearby.text}"

            if field_name == "total_amount" and not any(c.isdigit() for c in value):
                continue
            return value, source
    return None


def _match_label(text: str, pattern: str) -> str | None:
    """If `text` starts with `pattern`, return the remainder after stripping common
    label/value separators (colon, period, hyphen, whitespace, in any mix), else None.
    Requires the block to start with an uppercase letter: real form labels are capitalized,
    so a lowercase match is more likely a coincidental word inside a prose/notes sentence
    (seen in real data: a notes block "patient B cverely injurel" starting with a lowercase
    "patient" was otherwise indistinguishable from a real "Patient" label)."""
    stripped = text.strip()
    if stripped[:1].islower():
        return None
    match = re.match(rf"(?i)^{re.escape(pattern)}\b[\s:.\-]*(.*)$", stripped)
    return match.group(1).strip() if match else None


def _find_standalone_value(pattern: re.Pattern, all_blocks: list[OCRBlock]) -> tuple[str, str] | None:
    """Fallback for unlabeled fields recognizable by shape alone (e.g. 'Dr Chan', 'M12345').
    If several blocks match, the topmost on the page wins."""
    candidates = [block for block in all_blocks if pattern.match(block.text.strip())]
    if not candidates:
        return None
    best = min(candidates, key=lambda b: _bbox(b)[1])
    return best.text.strip(), best.text


def _find_cjk_doctor_suffix(all_blocks: list[OCRBlock]) -> tuple[str, str] | None:
    candidates = [block for block in all_blocks if CJK_DOCTOR_SUFFIX.match(block.text.strip())]
    if not candidates:
        return None
    best = min(candidates, key=lambda b: _bbox(b)[1])
    return best.text.strip(), best.text


def _find_nearby_value_block(label_block: OCRBlock, all_blocks: list[OCRBlock]) -> OCRBlock | None:
    """Coordinate-based lookup for when a label is alone in its block: the closest block to
    the right on the same line, else the closest block roughly below it in the same column.
    Both are capped to a distance scaled off the label's own text height, so a label doesn't
    reach across a wide multi-column layout and grab an unrelated field (real example: a
    "Name" label on the left grabbed "Payment Mode VD" from a column ~18 text-heights away)."""
    lx0, ly0, lx1, ly1 = _bbox(label_block)
    label_height = ly1 - ly0
    label_width = lx1 - lx0
    label_center_y = (ly0 + ly1) / 2
    max_gap = label_height * 8

    same_line = [
        block
        for block in all_blocks
        if block is not label_block
        and lx1 <= _bbox(block)[0] <= lx1 + max_gap
        and abs((_bbox(block)[1] + _bbox(block)[3]) / 2 - label_center_y) < label_height
    ]
    if same_line:
        return min(same_line, key=lambda b: _bbox(b)[0])

    below = [
        block
        for block in all_blocks
        if block is not label_block
        and ly0 < _bbox(block)[1] <= ly1 + max_gap
        and _bbox(block)[0] < lx1 + label_width  # roughly the same column, not a different one
    ]
    if below:
        return min(below, key=lambda b: _bbox(b)[1])

    return None


def _looks_like_table_header_row(block: OCRBlock, all_blocks: list[OCRBlock], min_neighbors: int = 2) -> bool:
    """Column headers are short (1-2 words each). Only count same-line neighbors that are
    also short - a tall, multi-line notes paragraph can vertically overlap a label's height
    band without actually being a neighboring header cell (real example: a 4-word notes block
    overlapped the real "TOTAL" label's height band and was wrongly counted as a second
    header sibling)."""
    bx0, by0, bx1, by1 = _bbox(block)
    center_y = (by0 + by1) / 2
    height = by1 - by0
    same_line = [
        other
        for other in all_blocks
        if other is not block
        and abs((_bbox(other)[1] + _bbox(other)[3]) / 2 - center_y) < height
        and len(other.text.split()) <= 3
    ]
    return len(same_line) >= min_neighbors


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
        date_match = DATE_PATTERN.search(value)
        candidate = date_match.group(0) if date_match else value
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date().isoformat(), None
            except ValueError:
                continue
        return value, f"date '{value}' did not match a known format, kept as-is"

    if not value:
        return None, "label matched but the value was empty"

    return value, None
