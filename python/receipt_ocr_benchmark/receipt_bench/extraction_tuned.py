"""Phase 3b: aggressively OVERFIT deterministic extraction - an intentional experiment.

Question this module answers: if we keep writing OCR + regex + coordinate rules around the
exact receipt layouts we already have, how far can a no-AI approach get? It is deliberately
tuned to the 6 receipts in data/raw (4 layouts) and is NOT expected to generalize. Compare
with `extraction.py` (Phase 3 baseline, general rules only) to see what the tuning bought.

Every rule is tagged in a comment:
  [GENERAL]  a technique that would plausibly help on unseen receipts too.
  [OVERFIT]  exists only because of a specific layout / OCR quirk in the current sample set.
The same tag is recorded per field in the output `rules` map, so every value is traceable to
both its source OCR text (`sources`) and the rule that produced it (`rules`).

Still pure OCR + deterministic logic: no Azure DI, no AOAI, no local LLM, no new dependencies.

Layouts handled (detected by fixed header text - itself [OVERFIT]):
  medical_template       r1, r2, r5  "MEDICAL RECEIPT TEMPLATE" hand-filled paper form
  flexcare               r3          "FLEXCARE HEALTH" hand-filled invoice
  vet_tung_chung         r4          Tung Chung Animal Clinic printed invoice
  pharmacy_prescription  r6          "Prescription Receipt/Information" pharmacy slip
  unknown                -           falls back to the Phase 3 baseline rules
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from receipt_bench import extraction as baseline
from receipt_bench.raw_ocr import RawOCRResult

FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]


@dataclass
class Blk:
    """An OCR block after preprocessing (may be a slice of a merged OCR block)."""

    text: str
    conf: float
    x0: float
    y0: float
    x1: float
    y1: float
    src: str  # the original, unmodified OCR block text - for traceability

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class TunedReceipt:
    document_id: str
    layout: str
    doctor_name: str | None = None
    registration_number: str | None = None
    patient_name: str | None = None
    receipt_number: str | None = None
    service_date: str | None = None
    total_amount: float | None = None
    sources: dict[str, str] = field(default_factory=dict)
    rules: dict[str, str] = field(default_factory=dict)
    validations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))

    def set(self, field_name: str, value, source: str, rule: str) -> None:
        setattr(self, field_name, value)
        self.sources[field_name] = source
        self.rules[field_name] = rule

    def null(self, field_name: str, reason: str) -> None:
        self.rules[field_name] = reason
        self.warnings.append(f"{field_name}: {reason}")


# --- preprocessing ------------------------------------------------------------------------

# [GENERAL] near-zero-confidence blocks are detector noise (empty strings, scribbles, glare).
MIN_CONF = 0.30
# [OVERFIT] the template photos show the *back* of the page through the paper, so PaddleOCR
# reads mirrored copies of the totals labels ("JATOTSUZ" = SUBTOTAL, "GIA9" = PAID). Some carry
# digits ("0002JATOT"), so they must be dropped before any amount lookup.
MIRRORED = re.compile(r"JATOT|XAT|MIA[DL]|GIA9|DIAP|BUOJ")
# [OVERFIT] r4 prints a checkbox glyph before "Clinician:" / "Patient:" which OCR reads as "F".
CHECKBOX_PREFIX = re.compile(r"(^|\s)F(?=(?:Clinician|Patient|Doctor)\s*:)")
# [GENERAL] OCR merges several "Label: value" pairs printed on one visual line into one block;
# split at every known "Label:" so each value can be read on its own.
SPLIT_LABELS = re.compile(r"(?:(?<=\s)|^)(?:Invoice No|Invoice Number|Receipt No|Clinician|Patient|Doctor)\s*:")


def _prepare(raw: RawOCRResult) -> tuple[list[Blk], float, float, str]:
    blocks: list[Blk] = []
    page = raw.pages[0]  # all current receipts are single-page
    for b in page.blocks:
        text = b.text.strip()
        if not text or (b.confidence or 0.0) < MIN_CONF:
            continue
        if MIRRORED.search(text):
            continue
        xs = [p[0] for p in b.polygon]
        ys = [p[1] for p in b.polygon]
        text = CHECKBOX_PREFIX.sub(r"\1", text)
        blocks.extend(_split_merged(Blk(text, b.confidence or 0.0, min(xs), min(ys), max(xs), max(ys), b.text)))
    plain = " ".join(b.text for b in page.blocks)
    return blocks, float(page.width), float(page.height), plain


def _split_merged(blk: Blk) -> list[Blk]:
    starts = [m.start() for m in SPLIT_LABELS.finditer(blk.text)]
    if not starts or starts == [0]:
        return [blk]
    if starts[0] != 0:
        starts = [0] + starts
    bounds = starts + [len(blk.text)]
    n = len(blk.text)
    parts = []
    for a, b in zip(bounds, bounds[1:]):
        piece = blk.text[a:b].strip()
        if not piece:
            continue
        # x coordinates interpolated by character offset - good enough for same-line lookups.
        x0 = blk.x0 + (blk.x1 - blk.x0) * a / n
        x1 = blk.x0 + (blk.x1 - blk.x0) * b / n
        parts.append(Blk(piece, blk.conf, x0, blk.y0, x1, blk.y1, blk.src))
    return parts


def detect_layout(plain_text: str) -> str:
    # [OVERFIT] fixed header strings of the 4 layouts in the sample set.
    t = re.sub(r"\s+", "", plain_text).upper()
    if "MEDICALRECEIPTTEMPLATE" in t or ("MEDICALINVOICE" in t and "HOSPITALNO" in t):
        return "medical_template"
    if "FLEXCARE" in t:
        return "flexcare"
    if "ANIMALCLINIC" in t:
        return "vet_tung_chung"
    if "PRESCRIPTIONRECEIPT" in t:
        return "pharmacy_prescription"
    return "unknown"


# --- generic helpers ------------------------------------------------------------------------


def _labels(blocks: list[Blk], pattern: str) -> list[tuple[Blk, str]]:
    """Blocks that *start* with `pattern`, with the remainder after the label. [GENERAL] a
    block starting lowercase is prose, not a printed label (r1 notes: "patient B cverely injurel")."""
    rx = re.compile(pattern, re.I)
    out = []
    for b in blocks:
        if b.text[:1].islower():
            continue
        m = rx.match(b.text)
        if m:
            out.append((b, b.text[m.end():].lstrip(" :;-,").strip()))
    return out


def _right_of(label: Blk, blocks: list[Blk], max_dx_h: float = 12, dy: float = 0.8, max_x: float | None = None) -> list[Blk]:
    """[GENERAL] same-line lookup: blocks to the right whose vertical centre is within `dy`
    label-heights, sorted left to right."""
    cands = [
        b
        for b in blocks
        if b is not label
        and b.x0 >= label.x1 - label.h * 0.5
        and b.x0 - label.x1 <= label.h * max_dx_h
        and abs(b.cy - label.cy) < label.h * dy
        and (max_x is None or b.x0 < max_x)
    ]
    return sorted(cands, key=lambda b: b.x0)


def _below(anchor: Blk, blocks: list[Blk], max_dy_h: float = 2.0, max_dx_h: float = 3.0) -> list[Blk]:
    """[GENERAL] blocks directly below `anchor` in roughly the same column, nearest first."""
    cands = [
        b
        for b in blocks
        if b is not anchor
        and b.y0 >= anchor.y1 - anchor.h * 0.3
        and b.y0 - anchor.y1 <= anchor.h * max_dy_h
        and abs(b.x0 - anchor.x0) <= anchor.h * max_dx_h
    ]
    return sorted(cands, key=lambda b: b.y0)


# [GENERAL] common OCR letter-for-digit confusions, applied ONLY inside an amount-shaped token
# (must already contain a real digit and a 2-digit decimal part). Seen: "ZO.00" for 20.00.
OCR_DIGIT_FIX = str.maketrans({"Z": "2", "z": "2", "O": "0", "o": "0", "S": "5", "l": "1", "I": "1"})
_DEC_AMOUNT = re.compile(r"-?[0-9ZzOoSlI][0-9ZzOoSlI,]*\.[0-9ZzOo]{2}(?![0-9])")
_INT_AMOUNT = re.compile(r"(?<![\w.])\d[\d,]*(?![\w.])")


def parse_amount(text: str) -> tuple[float, str] | None:
    """Returns (value, kind); kind is 'decimal', 'ocr_fixed' or 'integer'."""
    for m in _DEC_AMOUNT.finditer(text):
        tok = m.group(0)
        if not any(c.isdigit() for c in tok):
            continue
        raw = tok.replace(",", "")
        fixed = raw.translate(OCR_DIGIT_FIX)
        try:
            return float(fixed), ("ocr_fixed" if fixed != raw else "decimal")
        except ValueError:
            continue
    m = _INT_AMOUNT.search(text)
    if m:
        return float(m.group(0).replace(",", "")), "integer"
    return None


def repair_lost_decimal(value: float, kind: str, peers: list[float]) -> tuple[float, bool]:
    """[GENERAL] cross-field check: a handwritten decimal point is often lost by OCR ("1540.00"
    -> "154000"). If an integer-looking amount is exactly 100x another amount on the same
    receipt (subtotal / paid), trust the peer and restore the decimal point."""
    if kind == "integer" and any(abs(value / 100 - p) < 0.005 for p in peers):
        return value / 100, True
    return value, False


MONTHS = {m[:3].lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
_NUM_DATE = re.compile(r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4}|\d{2})(?!\d)")
# [GENERAL-ish] handwritten "/" is regularly read as "1": "07/0212026", "07101/2026". Only used
# when the strict pattern fails, requires a 2-digit middle part, a 19xx/20xx year, and at least
# one real separator; the result must still be a valid calendar date.
_NUM_DATE_OCR = re.compile(r"(?<!\d)(\d{1,2})([/.\-]|1)(\d{2})([/.\-]|1)((?:19|20)\d{2})(?!\d)")
_TXT_MDY = re.compile(r"([A-Za-z]{3,9})\.?\s*(\d{1,2})[\s,/.\-]*(\d{4})(?!\d)")
_TXT_DMY = re.compile(r"(\d{1,2})\s*([A-Za-z]{3,9})\.?,?\s*(\d{4}|\d{2})(?!\d)")


def parse_date(text: str, dayfirst: bool = True) -> tuple[str, str] | None:
    """Returns (iso_date, kind). kind 'numeric_ambiguous' means both day and month are <= 12
    and the day/month order was decided by `dayfirst`, not by the receipt."""

    def mk(y: int, mth: int, d: int) -> date | None:
        if y < 100:
            y += 2000
        try:
            return date(y, mth, d)
        except ValueError:
            return None

    for rx, kind in ((_NUM_DATE, "numeric"), (_NUM_DATE_OCR, "numeric_ocr_fixed")):
        for m in rx.finditer(text):
            if kind == "numeric_ocr_fixed":
                if m.group(2) != "1" or m.group(4) != "1":
                    a, b, y = int(m.group(1)), int(m.group(3)), int(m.group(5))
                else:
                    continue
            else:
                a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            d = mk(y, b, a) if dayfirst else mk(y, a, b)
            if d is None:
                d = mk(y, a, b) if dayfirst else mk(y, b, a)
            if d:
                return d.isoformat(), (kind + "_ambiguous" if a <= 12 and b <= 12 and a != b else kind)
    for m in _TXT_MDY.finditer(text):
        mon = MONTHS.get(m.group(1)[:3].lower())
        if mon and (d := mk(int(m.group(3)), mon, int(m.group(2)))):
            return d.isoformat(), "textual"
    for m in _TXT_DMY.finditer(text):
        mon = MONTHS.get(m.group(2)[:3].lower())
        if mon and (d := mk(int(m.group(3)), mon, int(m.group(1)))):
            return d.isoformat(), "textual"
    return None


# [OVERFIT] tiny lexicon of HK romanized surnames, only used to repair a lowercase-initial OCR
# token in a signature line (r4: "ehoi" -> "Choi").
HK_SURNAMES = ["Chan", "Cheung", "Choi", "Chow", "Chu", "Fung", "Ho", "Kwok", "Lam", "Lau", "Lee", "Leung",
               "Li", "Lo", "Lok", "Ma", "Mak", "Ng", "Poon", "Tam", "Tang", "Tse", "Tseng", "Wong", "Yeung", "Yip"]


def clean_person_name(text: str, snap_surnames: bool = False) -> str:
    t = re.sub(r"\b([BD])r\.?\s*(?=[A-Z])", "Dr. ", text)  # [GENERAL] "Dr.Fung" -> "Dr. Fung"
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)  # [GENERAL] "LokYi" -> "Lok Yi"
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r"\s+", " ", t).strip(" ,.")
    if snap_surnames:
        words = []
        for w in t.split(" "):
            if w[:1].islower():
                hit = difflib.get_close_matches(w.capitalize(), HK_SURNAMES, n=1, cutoff=0.7)
                w = hit[0] if hit else w
            words.append(w)
        t = " ".join(words)
    return t


_NAME_OK = re.compile(r"^(?:[A-Za-z][A-Za-z.'\-]*(?:[ ,]+[A-Za-z][A-Za-z.'\-]*){0,5}|[一-鿿]{2,6})$")
_NOT_NAMES = {"address", "phone", "email", "age", "name", "patient", "consultant", "hospital no"}


def looks_like_name(text: str) -> bool:
    # [GENERAL] fail closed: no digits, letters only, and not a form label.
    return bool(_NAME_OK.match(text)) and text.lower() not in _NOT_NAMES


def _first_name_value(label: Blk, remainder: str, blocks: list[Blk], max_x: float) -> tuple[str, str] | None:
    """Value for a name label: remainder in the same block, else the same-line block(s) to
    the right (left column only)."""
    if remainder:
        v = clean_person_name(remainder)
        return (v, label.src) if looks_like_name(v) else None
    right = _right_of(label, blocks, max_dx_h=8, max_x=max_x)
    if right:
        v = clean_person_name(right[0].text)
        if looks_like_name(v):
            return v, f"{label.src} | {right[0].src}"
    return None


def _totals_ladder(result: TunedReceipt, blocks: list[Blk], label_specs: list[tuple[str, str]], total_keys: list[str],
                   min_x: float, rule_prefix: str) -> None:
    """[GENERAL technique, OVERFIT label sets] Hand-written totals boxes: each label ("SUBTOTAL",
    "TOTAL", "PAID"...) has its value written on the underline to its RIGHT and usually a bit
    ABOVE the printed label (up to ~2 label-heights). Glued values ("TOTALZO.00", "PAID20.00")
    are read from the label block itself. Then pick by meaning: an explicit total first, then
    paid, then subtotal (+tax) when the total line was left blank."""
    labels: dict[str, Blk] = {}
    values: dict[str, tuple[float, str, str]] = {}
    for b in blocks:
        if b.x0 < min_x:
            continue
        for key, pat in label_specs:
            m = re.match(pat, b.text, re.I)
            if m and key not in labels:
                labels[key] = b
                rem = b.text[m.end():].strip(" :_")
                parsed = parse_amount(rem) if rem and any(c.isdigit() for c in rem) else None
                if parsed:
                    values[key] = (parsed[0], parsed[1], b.src)
                break
    label_blocks = set(id(b) for b in labels.values())
    for b in blocks:
        if id(b) in label_blocks or not any(c.isdigit() for c in b.text) or re.search(r"[A-Za-z]{3,}", b.text):
            continue
        parsed = parse_amount(b.text)
        if not parsed:
            continue
        best, best_d = None, None
        for key, lb in labels.items():
            d = lb.cy - b.cy  # >0: value sits above the label's centre
            if b.x0 >= lb.x0 and -0.6 * lb.h <= d <= 2.2 * lb.h and (best_d is None or abs(d) < best_d):
                best, best_d = key, abs(d)
        if best and best not in values:
            values[best] = (parsed[0], parsed[1], f"{labels[best].src} | {b.src}")

    found = {k: v[0] for k, v in values.items()}
    result.validations.append(f"total_amount: totals box read as {found}")
    peers = [found[k] for k in ("subtotal", "paid") if k in found]
    for key in total_keys:
        if key in values:
            value, kind, src = values[key]
            value, repaired = repair_lost_decimal(value, kind, [p for p in peers if p != value])
            rule = f"{rule_prefix}: '{key}' line"
            if repaired:
                rule += " + lost-decimal repair against subtotal/paid [GENERAL]"
            if kind == "ocr_fixed":
                rule += " + OCR letter->digit fix [GENERAL]"
            others = [p for p in peers if abs(p - value) >= 0.005]
            if others:
                result.validations.append(f"total_amount: {value} disagrees with subtotal/paid {others}")
            result.set("total_amount", value, src, rule)
            return
    if "subtotal" in values:
        value, _, src = values["subtotal"]
        tax = found.get("tax", 0.0)
        result.set("total_amount", value + tax, src,
                   f"{rule_prefix}: total/paid lines blank -> subtotal + tax ({tax}) [OVERFIT assumption: blank tax = 0]")
        return
    result.null("total_amount", f"{rule_prefix}: no total, paid or subtotal value found")


# --- layout handlers ---------------------------------------------------------------------------


def _medical_template(result: TunedReceipt, blocks: list[Blk], w: float, h: float) -> None:
    """[OVERFIT] handwritten "MEDICAL RECEIPT TEMPLATE" (r1, r2, r5). Known structure:
    doctor's name is written into / just above the "Hospital Name, Slogan" line; patient on the
    "Patient" line (repeated on "Name"); the only date is "Admission Date"; totals box on the
    lower right; the form has no receipt-number or registration-number field at all."""
    patient_labels = _labels(blocks, r"^Patient\b")
    header_bottom = min((b.y0 for b, _ in patient_labels), default=h * 0.35)

    # doctor_name: ranked candidates from the header region.
    hosp = re.compile(r"^Hospital\s*Name[\s,]*(?:S[il1]ogan)?[\s,:]*", re.I)
    cands = []  # (priority, -confidence, value, source, rule)
    for b in blocks:
        if b.y1 > header_bottom:
            continue
        t = hosp.sub("", b.text)
        stripped_label = t != b.text
        if m := re.search(r"(?:^|\s)((?:Dr|Br)\.?\s*[A-Z].*)$", t):
            cands.append((1, -b.conf, clean_person_name(m.group(1)), b.src,
                          "medical_template: 'Dr ...' in header / hospital-name slot [OVERFIT slot, GENERAL 'Dr' pattern]"))
        elif m := re.search(r"([一-鿿]{2,4}(?:醫生|医生))", t):
            cands.append((2, -b.conf, m.group(1), b.src,
                          "medical_template: CJK name + 醫生 suffix in header [GENERAL pattern]"))
        elif stripped_label and t.strip() and looks_like_name(t.strip()):
            cands.append((3, -b.conf, t.strip(), b.src, "medical_template: text in hospital-name slot [OVERFIT]"))
    if cands:
        _, _, v, s, r = min(cands)
        result.set("doctor_name", v, s, r)
        if len(cands) > 1:
            result.validations.append(f"doctor_name: {len(cands)} candidates {[c[2] for c in sorted(cands)]}, highest priority kept")
    else:
        result.null("doctor_name", "medical_template: no doctor candidate in header")

    # patient_name: "Patient" line, cross-checked against the "Name" line.
    left_col = w * 0.5
    pat = next((v for b, rem in patient_labels if (v := _first_name_value(b, rem, blocks, left_col))), None)
    nam = next((v for b, rem in _labels(blocks, r"^Name\b") if (v := _first_name_value(b, rem, blocks, left_col))), None)
    if pat:
        result.set("patient_name", pat[0], pat[1], "medical_template: 'Patient' line [OVERFIT layout]")
        if nam:
            result.validations.append(f"patient_name: 'Name' line {'agrees' if nam[0] == pat[0] else 'DISAGREES'} ({nam[0]})")
    elif nam:
        result.set("patient_name", nam[0], nam[1], "medical_template: 'Name' line (Patient line blank) [OVERFIT layout]")
    else:
        result.null("patient_name", "medical_template: Patient and Name lines blank/unreadable")

    result.null("receipt_number", "medical_template: form has no receipt/invoice number field [OVERFIT]")
    result.null("registration_number", "medical_template: form has no registration number field [OVERFIT]")

    # service_date: the only date on the form is "Admission Date".
    for b, rem in _labels(blocks, r"^Admission\s*Date"):
        texts = [(rem, b.src)] if rem else [(r.text, f"{b.src} | {r.src}") for r in _right_of(b, blocks)]
        for t, s in texts:
            if parsed := parse_date(t):
                result.set("service_date", parsed[0], s,
                           f"medical_template: Admission Date used as service date ({parsed[1]}) [OVERFIT semantic choice]")
                break
        if result.service_date:
            break
    if not result.service_date:
        result.null("service_date", "medical_template: Admission Date blank/unparseable")

    _totals_ladder(
        result, blocks,
        [("subtotal", r"^SUB\s*TOTAL"), ("tax", r"^TAX\s*[\d.]*\s*%?"), ("med_claim", r"^MED\s*CLAIM"),
         ("total_due", r"^TOTAL\s*DUE"), ("total", r"^TOTAL"), ("paid", r"^PAID")],
        ["total", "paid"], min_x=w * 0.5, rule_prefix="medical_template totals box [OVERFIT layout]",
    )


def _flexcare(result: TunedReceipt, blocks: list[Blk], w: float, h: float) -> None:
    """[OVERFIT] FLEXCARE HEALTH invoice (r3): "Clinic Name:" holds the practitioner's name
    (GT treats it as the doctor), "Invoice Number:", "Date:", totals box lower right, no
    patient or registration field."""
    for b, rem in _labels(blocks, r"^Clinic\s*Name\s*:?"):
        # handwriting continues in separate blocks on the same line ("Lee" + "Tin Tin , Becky")
        parts = [rem] if rem else []
        srcs = [b.src]
        for r in _right_of(b, blocks, max_x=w * 0.5):
            parts.append(r.text)
            srcs.append(r.src)
        v = clean_person_name(" ".join(parts))
        if looks_like_name(v):
            result.set("doctor_name", v, " | ".join(srcs),
                       "flexcare: 'Clinic Name:' + same-line continuation blocks [OVERFIT semantic: clinic name = practitioner]")
            break
    if not result.doctor_name:
        result.null("doctor_name", "flexcare: Clinic Name blank")

    result.null("patient_name", "flexcare: form has no patient field [OVERFIT]")
    result.null("registration_number", "flexcare: form has no registration number field [OVERFIT]")

    for b, rem in _labels(blocks, r"^Invoice\s*Number\s*:?"):
        v = rem.split()[0] if rem else next((r.text for r in _right_of(b, blocks)), "")
        if re.fullmatch(r"[A-Z0-9\-]{4,}", v or ""):
            result.set("receipt_number", v, b.src, "flexcare: 'Invoice Number:' [GENERAL label]")
            break
    if not result.receipt_number:
        result.null("receipt_number", "flexcare: Invoice Number blank")

    for b, rem in _labels(blocks, r"^Date\s*:"):
        texts = [(rem, b.src)] if rem else [(r.text, f"{b.src} | {r.src}") for r in _right_of(b, blocks)]
        for t, s in texts:
            if parsed := parse_date(t):
                result.set("service_date", parsed[0], s, f"flexcare: 'Date:' ({parsed[1]}) [GENERAL label]")
                break
    if not result.service_date:
        result.null("service_date", "flexcare: Date blank/unparseable")

    _totals_ladder(
        result, blocks,
        [("subtotal", r"^Sub\s*total\s*:?"), ("tax", r"^Tax\s*:?"), ("total_amount_due", r"^Total\s*Amount\s*Due\s*:?")],
        ["total_amount_due"], min_x=w * 0.5, rule_prefix="flexcare totals box [OVERFIT layout]",
    )


def _vet_tung_chung(result: TunedReceipt, blocks: list[Blk], w: float, h: float) -> None:
    """[OVERFIT] Tung Chung Animal Clinic invoice (r4). Header line "Invoice No: .. Clinician:
    .. Patient: .." (merged by OCR, checkbox glyphs read as "F") with the invoice date at the
    far right; signing vet under "Vet's Signature & Stamp:"; "Total Amount" is the invoice total
    while "Total Due" is the outstanding balance (0.00)."""
    inv = _labels(blocks, r"^Invoice\s*No\s*:?")
    for b, rem in inv:
        tok = rem.split()[0] if rem else ""
        if tok.isdigit():
            result.set("receipt_number", tok, b.src, "vet: 'Invoice No:' (merged block split) [GENERAL]")
            break
    if not result.receipt_number:
        result.null("receipt_number", "vet: Invoice No not found")

    for b, rem in _labels(blocks, r"^Patient\s*:"):
        v = clean_person_name(rem)
        if looks_like_name(v):
            result.set("patient_name", v, b.src, "vet: 'Patient:' after checkbox-'F' strip + merged block split [GENERAL+OVERFIT]")
            if any(x.text == v and x is not b for x in blocks):
                result.validations.append(f"patient_name: '{v}' also appears in the animal info box")
            break
    if not result.patient_name:
        result.null("patient_name", "vet: Patient not found")

    # doctor_name: BOTH the attending clinician and the signing vet (GT lists both).
    names, srcs = [], []
    for b, rem in _labels(blocks, r"^Clinician\s*:"):
        if looks_like_name(v := clean_person_name(rem)):
            names.append(v)
            srcs.append(b.src)
            break
    for b, _ in _labels(blocks, r"^Vet'?s\s*Signature"):
        for r in _right_of(b, blocks, max_dx_h=20, dy=1.2):
            # [OVERFIT] OCR reads the stamped "Dr." as "Br." - only corrected here, in the
            # signature slot, where a doctor's title is the only plausible reading.
            if re.match(r"^[BD]r\.?", r.text):
                names.append(clean_person_name(r.text, snap_surnames=True))
                srcs.append(r.src)
                break
    if names:
        result.set("doctor_name", ", ".join(names), " | ".join(srcs),
                   "vet: Clinician + signing vet (Br->Dr in signature slot, surname lexicon snap) [OVERFIT]")
        if len(names) > 1:
            result.validations.append(f"doctor_name: multiple doctors {names} - both reported")
    else:
        result.null("doctor_name", "vet: no clinician or signature")

    result.null("registration_number", "vet: invoice has no registration number [OVERFIT]")

    # service_date: date printed at the far right of the Invoice No line.
    for b, _ in inv:
        for r in blocks:
            if r.x0 > w * 0.6 and abs(r.cy - b.cy) < b.h * 1.5 and (parsed := parse_date(r.text)):
                result.set("service_date", parsed[0], r.src, "vet: date at right end of the Invoice No line [OVERFIT layout]")
                break
        if result.service_date:
            break
    if not result.service_date:
        result.null("service_date", "vet: invoice date not found")

    for b, rem in _labels(blocks, r"^Total\s*Amount\b"):
        cands = [(rem, b.src)] if rem else [(r.text, f"{b.src} | {r.src}") for r in _right_of(b, blocks, max_dx_h=15)]
        for t, s in cands:
            if parsed := parse_amount(t):
                result.set("total_amount", parsed[0], s, "vet: 'Total Amount' (not 'Total Due' = balance) [GENERAL semantics]")
                break
        if result.total_amount is not None:
            break
    if result.total_amount is None:
        result.null("total_amount", "vet: Total Amount not found")
    else:
        # [GENERAL] cross-field validation: Sub Total + Round Down == Total Amount == payments.
        sub = next((parse_amount(r.text) for b, _ in _labels(blocks, r"^Sub\s*Total") for r in _right_of(b, blocks, max_dx_h=15)), None)
        rnd = next((parse_amount(r.text) for b, _ in _labels(blocks, r"^Round\s*Down") for r in _right_of(b, blocks, max_dx_h=15)), None)
        paid = next((parse_amount(rem) for b, rem in _labels(blocks, r"^Total\s*payment\s*received")), None)
        if sub and rnd:
            ok = abs(sub[0] + rnd[0] - result.total_amount) < 0.005
            result.validations.append(f"total_amount: sub total {sub[0]} + round {rnd[0]} {'==' if ok else '!='} {result.total_amount}")
        if paid:
            ok = abs(paid[0] - result.total_amount) < 0.005
            result.validations.append(f"total_amount: payments received {paid[0]} {'==' if ok else '!='} total")


def _pharmacy_prescription(result: TunedReceipt, blocks: list[Blk], w: float, h: float) -> None:
    """[OVERFIT] NZ "Prescription Receipt/Information" pharmacy slip (r6): unlabeled barcode
    number top-left = receipt number, patient name directly under it and repeated under "Check
    recipient is patient named above"; prescriber line "Dr <name> <practice> Medical Centre";
    unlabeled total = the underlined sum at the bottom of the price column."""
    num = next((b for b in blocks if re.fullmatch(r"\d{10,14}", b.text) and b.y0 < h * 0.3 and b.x0 < w * 0.4), None)
    if num:
        result.set("receipt_number", num.text, num.src, "pharmacy: unlabeled 10-14 digit barcode number, top-left [OVERFIT layout]")
    else:
        result.null("receipt_number", "pharmacy: barcode number not found")

    top = next((b for b in (_below(num, blocks) if num else []) if looks_like_name(b.text)), None)
    chk = next((b for c, _ in _labels(blocks, r"^Check\s*recipient") for b in _below(c, blocks, max_dx_h=12)
                if b.x0 < w * 0.4 and looks_like_name(b.text)), None)
    if top or chk:
        v = (top or chk).text
        result.set("patient_name", v, (top or chk).src,
                   "pharmacy: name under barcode number / under 'Check recipient is patient named above' [OVERFIT layout]")
        if top and chk:
            result.validations.append(f"patient_name: both positions {'agree' if top.text == chk.text else 'DISAGREE'}")
    else:
        result.null("patient_name", "pharmacy: patient name not found")

    for b, _ in _labels(blocks, r"^Dr\.?\s+[A-Z]"):
        # [GENERAL-ish] strip a trailing practice name "<Place> Medical Centre".
        v = re.sub(r"\s+\S+\s+(?:Medical\s+Cent(?:re|er)|Health\s+Cent(?:re|er)|Clinic|Surgery|Hospital)\s*$", "", b.text)
        result.set("doctor_name", clean_person_name(v), b.src, "pharmacy: prescriber 'Dr ...' line minus practice name [OVERFIT]")
        break
    if not result.doctor_name:
        result.null("doctor_name", "pharmacy: prescriber line not found")

    result.null("registration_number", "pharmacy: GST no. is the pharmacy's tax id, NHI is the patient's - no prescriber registration [OVERFIT]")

    for b in blocks:
        if m := re.search(r"Printed\s*on\s*(.+)$", b.text, re.I):
            if parsed := parse_date(m.group(1)):
                result.set("service_date", parsed[0], b.src, "pharmacy: 'Printed on' date [OVERFIT semantic choice: not the 1Mar17 dispense dates]")
                break
    if not result.service_date:
        result.null("service_date", "pharmacy: printed date not found")

    # [GENERAL] unlabeled total: the amount in the price column equal to the sum of the amounts above it.
    col = sorted((b for b in blocks if b.x0 > w * 0.75 and re.fullmatch(r"\$?\s*\d[\d,]*\.\d{2}", b.text)), key=lambda b: b.y0)
    running = 0.0
    for i, b in enumerate(col):
        v = parse_amount(b.text)[0]
        if i >= 2 and abs(v - running) < 0.005:
            result.set("total_amount", v, b.src, f"pharmacy: price-column amount equal to sum of the {i} amounts above [GENERAL]")
            result.validations.append(f"total_amount: {' + '.join(c.text for c in col[:i])} == {b.text}")
            break
        running += v
    if result.total_amount is None:
        result.null("total_amount", "pharmacy: no column total found")


HANDLERS = {
    "medical_template": _medical_template,
    "flexcare": _flexcare,
    "vet_tung_chung": _vet_tung_chung,
    "pharmacy_prescription": _pharmacy_prescription,
}


def extract_receipt_tuned(raw: RawOCRResult) -> TunedReceipt:
    blocks, w, h, plain = _prepare(raw)
    layout = detect_layout(plain)
    result = TunedReceipt(document_id=raw.document_id, layout=layout)
    handler = HANDLERS.get(layout)
    if handler:
        handler(result, blocks, w, h)
        return result

    # Unknown layout: nothing tuned applies - fall back to the Phase 3 baseline rules.
    base = baseline.extract_receipt(raw)
    for f in FIELDS:
        if getattr(base, f) is not None:
            result.set(f, getattr(base, f), base.sources.get(f, ""), "baseline Phase 3 rules (unknown layout)")
        else:
            result.null(f, "baseline Phase 3 rules found nothing (unknown layout)")
    return result
