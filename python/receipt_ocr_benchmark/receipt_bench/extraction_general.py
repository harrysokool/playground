"""Phase 3c: general-rules extraction - reusable deterministic rules, NO layout knowledge.

Question this module answers: how well does PaddleOCR + reusable deterministic rules do on
varied receipts WITHOUT a custom handler per layout? Compare with:
  - extraction.py        Phase 3 first-pass rules
  - extraction_tuned.py  Phase 3b rules deliberately overfit to the 6 sample receipts

Constraints this module keeps (and must keep):
  - no layout detection, no per-layout handlers, no receipt-specific coordinates;
  - no header-text recognition, no knowledge like "top-left barcode = receipt number";
  - no name/surname dictionaries; no rule that encodes an expected ground-truth value;
  - every rule must plausibly apply to an unrelated receipt layout;
  - fail closed: if the nearest candidate for a label fails its shape check, that label
    yields nothing (we do not keep searching further away for something that fits).

Rules, all layout-independent:
  1. Preprocess: drop low-confidence / empty blocks; split a block that contains 2+ known
     "Label:" prefixes (OCR merging several label/value pairs from one visual line).
  2. Label match: a block that starts (capitalised) with a known label for the field; value =
     rest of the block, else the nearest block to the right on the same line, else the nearest
     block below in the same column. Amount fields also look slightly above-right (values
     handwritten on an underline sit above the printed label baseline).
  3. Unlabelled fallbacks recognisable by shape alone: a "Dr <Name>" / "<CJK name>醫生"
     person anywhere; a single date that makes up the clear majority of all dates on the page;
     a column amount that equals the sum of the amounts above it.
  4. Totals semantics: explicit total > amount paid > subtotal (only if no tax/charge amount
     was found). "Amount due / total due / balance" is treated as an outstanding balance, not
     the invoice total. Cross-checks: lost-decimal repair against peer amounts.
  5. Low-risk OCR cleanup: letter->digit fix inside amount-shaped tokens only; "/" read as "1"
     in a date only when the repaired string is a valid calendar date; whitespace/punctuation.

Post-first-run changes (each reusable, each can only turn a wrong value into null):
  - "price", "cost", "fee", "unit" added to FORM_WORDS: a column header "Patient Price" was
    read as label "Patient" + value "Price".
  - every word of a Latin name must be capitalised: a lowercase OCR token ("ehoi") means the
    name was not read confidently.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from receipt_bench.raw_ocr import RawOCRResult

# Low-level parsers are shared with the tuned module; these three are the generic ones there
# (amount parsing with in-token OCR fixes, date parsing, lost-decimal cross-check).
from receipt_bench.extraction_tuned import parse_amount, parse_date, repair_lost_decimal

FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]
MIN_CONF = 0.5

# Label vocabularies: common receipt/invoice wording across providers, most specific first.
DOCTOR_LABELS = ["attending doctor", "doctor name", "doctor", "physician", "medical practitioner", "practitioner",
                 "clinician", "prescriber", "veterinarian", "provider name", "provider"]
PATIENT_LABELS = ["patient name", "name of patient", "patient", "client name", "customer name", "pet name", "name"]
REG_LABELS = ["registration number", "registration no", "reg. no", "reg no", "licence no", "license no"]
RECEIPT_LABELS = ["receipt number", "receipt no", "receipt #", "receipt#", "invoice number", "invoice no",
                  "invoice #", "bill number", "bill no", "reference no", "ref no", "transaction no"]
DATE_LABELS = [
    # service-specific first, then document dates, then a bare "Date"
    ["service date", "date of service", "consultation date", "visit date", "treatment date", "admission date"],
    ["invoice date", "receipt date", "bill date", "date"],
]
TOTAL_LABELS = ["grand total", "total amount due", "total amount", "total payable", "net total", "total"]
PAID_LABELS = ["total payment received", "payment received", "amount paid", "total paid", "paid"]
SUBTOTAL_LABELS = ["subtotal", "sub total", "sub-total"]
CHARGE_LABELS = ["tax", "gst", "vat", "service charge", "surcharge"]
BALANCE_LABELS = ["balance due", "amount due", "total due", "balance"]

ALL_LABELS = sorted({l for group in (DOCTOR_LABELS, PATIENT_LABELS, REG_LABELS, RECEIPT_LABELS, TOTAL_LABELS, PAID_LABELS,
                                     SUBTOTAL_LABELS, CHARGE_LABELS, BALANCE_LABELS) for l in group}
                    | {l for g in DATE_LABELS for l in g}, key=len, reverse=True)
# Other common form words: a "value" starting with one of these is really the next label.
FORM_WORDS = {"address", "phone", "tel", "email", "fax", "age", "sex", "gender", "date", "payment", "mode", "bed", "ward",
              "hospital", "clinic", "total", "subtotal", "tax", "paid", "amount", "qty", "rate", "description",
              "particulars", "notes", "discharge", "price", "cost", "fee", "unit", "admission", "consultant", "name", "patient", "doctor", "invoice", "receipt"}
ORG_WORDS = r"(?:Medical|Health|Dental)\s+(?:Centre|Center|Clinic|Group)|Clinic|Hospital|Pharmacy|Surgery|Centre|Center"


@dataclass
class Blk:
    text: str
    conf: float
    x0: float
    y0: float
    x1: float
    y1: float
    src: str

    @property
    def h(self) -> float:
        return max(self.y1 - self.y0, 1.0)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class GeneralReceipt:
    document_id: str
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
    timings: dict[str, float] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))

    def set(self, f: str, value, source: str, rule: str) -> None:
        setattr(self, f, value)
        self.sources[f] = source
        self.rules[f] = rule

    def null(self, f: str, reason: str) -> None:
        self.warnings.append(f"{f}: {reason}")


# --- preprocessing ---------------------------------------------------------------------------

_SPLIT = re.compile(r"(?:(?<=\s)|^)(?:" + "|".join(re.escape(l) for l in ALL_LABELS) + r")\s*:", re.I)


def _prepare(raw: RawOCRResult) -> list[Blk]:
    out: list[Blk] = []
    for page in raw.pages[:1]:  # coordinates are per page; all benchmark receipts are 1 page
        for b in page.blocks:
            text = re.sub(r"\s+", " ", b.text).strip()
            if not text or (b.confidence or 0.0) < MIN_CONF:
                continue
            xs = [p[0] for p in b.polygon]
            ys = [p[1] for p in b.polygon]
            out.extend(_split_merged(Blk(text, b.confidence or 0.0, min(xs), min(ys), max(xs), max(ys), b.text)))
    return out


def _split_merged(b: Blk) -> list[Blk]:
    starts = [m.start() for m in _SPLIT.finditer(b.text)]
    if len(starts) < 2:
        return [b]
    if starts[0] != 0:
        starts = [0] + starts
    n = len(b.text)
    parts = []
    for a, e in zip(starts, starts[1:] + [n]):
        piece = b.text[a:e].strip()
        if piece:
            parts.append(Blk(piece, b.conf, b.x0 + (b.x1 - b.x0) * a / n, b.y0, b.x0 + (b.x1 - b.x0) * e / n, b.y1, b.src))
    return parts


# --- geometry -------------------------------------------------------------------------------


def _right(label: Blk, blocks: list[Blk]) -> Blk | None:
    c = [b for b in blocks if b is not label and b.x0 >= label.x1 - label.h * 0.5
         and b.x0 - label.x1 <= label.h * 10 and abs(b.cy - label.cy) < label.h * 0.7]
    return min(c, key=lambda b: b.x0) if c else None


def _below(label: Blk, blocks: list[Blk]) -> Blk | None:
    c = [b for b in blocks if b is not label and b.y0 >= label.y1 - label.h * 0.3 and b.y0 - label.y1 <= label.h * 2.5
         and b.x0 < label.x1 + label.h and b.x1 > label.x0 - label.h]
    return min(c, key=lambda b: b.y0) if c else None


def _above_right(label: Blk, blocks: list[Blk]) -> Blk | None:
    c = [b for b in blocks if b is not label and b.x0 >= label.x1 - label.h * 0.5 and b.x0 - label.x1 <= label.h * 10
         and 0 <= label.cy - b.cy <= label.h * 1.6]
    return min(c, key=lambda b: label.cy - b.cy) if c else None


def _match_label(text: str, label: str, allow_glued_amount: bool = False) -> str | None:
    """Remainder after `label` if the block starts with it (capitalised = printed label)."""
    if text[:1].islower():
        return None
    m = re.match(rf"(?i){re.escape(label)}\b[\s:.#\-]*(.*)$", text)
    if m:
        return m.group(1).strip()
    if allow_glued_amount:  # "TOTAL20.00": value glued to the label by OCR
        m = re.match(rf"(?i){re.escape(label)}([$\dZO][\d.,ZO]*\d)$", text)
        if m and parse_amount(m.group(1)):
            return m.group(1)
    return None


def _is_header_cell(b: Blk, blocks: list[Blk]) -> bool:
    """A bare column header shares its row with 2+ other short, purely textual cells."""
    same = [o for o in blocks if o is not b and abs(o.cy - b.cy) < b.h * 0.7 and len(o.text.split()) <= 3
            and not any(ch.isdigit() for ch in o.text)]
    return len(same) >= 2


# --- value shapes ---------------------------------------------------------------------------

_LATIN_NAME = re.compile(r"^[A-Z][A-Za-z.'\-]*(?:,? [A-Z][A-Za-z.'\-]*){0,4}$")
_CJK_NAME = re.compile(r"^[一-鿿]{2,4}$")


def _clean_name(t: str) -> str:
    t = re.sub(r"\bDr\.?\s*(?=[A-Z])", "Dr. ", t)
    t = re.sub(r"\s+,", ",", t)
    t = re.split(rf"\s+(?:\S+\s+)?(?:{ORG_WORDS})\b", t)[0]  # a name never contains an organisation word
    return re.sub(r"\s+", " ", t).strip(" ,.:;")


def _looks_like_label(t: str) -> bool:
    first = re.split(r"[\s:,.]", t.lower(), maxsplit=1)[0]
    return any(first.startswith(w) for w in FORM_WORDS)


def _person(t: str) -> str | None:
    t = _clean_name(t)
    core = re.sub(r"^Dr\.\s*", "", t)
    if not core or any(c.isdigit() for c in core) or _looks_like_label(core):
        return None
    return t if (_LATIN_NAME.match(core) or _CJK_NAME.match(core)) else None


def _id_token(t: str) -> str | None:
    tok = t.split()[0] if t.split() else ""
    tok = tok.strip(".,;:")
    return tok if len(tok) >= 3 and any(c.isdigit() for c in tok) and re.fullmatch(r"[A-Za-z0-9\-/]+", tok) else None


def _amount_only(t: str):
    """Block that is just an amount (optional currency), e.g. 'HKD 1,361.00', '$51.20', 'ZO.00'."""
    if re.fullmatch(r"(?:[A-Z]{3}|HK\$|\$|S\$)?\s*-?[\dZO$][\d,.ZO]*", t.strip()) and any(c.isdigit() for c in t):
        return parse_amount(t)
    return None


# --- labelled lookup --------------------------------------------------------------------------


def _labelled(blocks, labels, parse, directions=("right", "below"), glued=False, skip_headers=False):
    """First label (vocabulary order, then reading order) whose value parses. For each label
    occurrence only the NEAREST candidate is tried (fail closed)."""
    for label in labels:
        for b in blocks:
            rem = _match_label(b.text, label, allow_glued_amount=glued)
            if rem is None:
                continue
            if skip_headers and not rem and _is_header_cell(b, blocks):
                continue
            if rem:
                v = parse(rem)
                if v is not None:
                    return v, b.src, f"label '{label}' (same block)"
                continue
            for d in directions:
                n = {"right": _right, "below": _below, "above_right": _above_right}[d](b, blocks)
                if n is None:
                    continue
                v = parse(n.text)
                if v is not None:
                    return v, f"{b.src} | {n.src}", f"label '{label}' ({d})"
                break  # nearest candidate failed its shape check: fail closed for this label
    return None


# --- field extractors -----------------------------------------------------------------------


def _doctor(blocks):
    hit = _labelled(blocks, DOCTOR_LABELS, _person)
    if hit:
        return hit
    # Unlabelled: "Dr <Name>" or "<CJK name>醫生" anywhere in a block. Single candidate only.
    cands = []
    for b in blocks:
        if m := re.search(r"(?:^|[\s,])(Dr\.?\s*[A-Z][^\d]*)$", b.text):
            if v := _person(m.group(1)):
                cands.append((v, b.src, "unlabelled 'Dr <name>' pattern"))
        elif m := re.search(r"([一-鿿]{2,4})(?:醫生|医生)", b.text):
            cands.append((m.group(0), b.src, "unlabelled CJK name + 醫生 title"))
    distinct = {c[0] for c in cands}
    if len(distinct) == 1:
        return cands[0]
    if len(distinct) > 1:
        return ("__AMBIGUOUS__", "", f"{len(distinct)} different doctor candidates: {sorted(distinct)}")
    return None


def _date(blocks):
    for tier in DATE_LABELS:
        hit = _labelled(blocks, tier, lambda t: parse_date(t))
        if hit:
            (iso, kind), src, rule = hit
            return iso, src, f"{rule}, {kind}"
    # Unlabelled: one date clearly dominates (> half of all date occurrences on the page).
    found = [(p[0], b.src) for b in blocks if (p := parse_date(b.text))]
    if found:
        (iso, n), = Counter(d for d, _ in found).most_common(1)
        if n * 2 > len(found) and n >= 2:
            return iso, next(s for d, s in found if d == iso), f"unlabelled: {n}/{len(found)} dates on the page agree"
    return None


def _total(blocks, result: GeneralReceipt):
    amt = lambda t: _amount_only(t) or (parse_amount(t) if re.search(r"\d", t) and not re.search(r"[A-Za-z]{3,}", t) else None)
    dirs = ("right", "above_right")
    got = {}
    for key, labels in (("total", TOTAL_LABELS), ("paid", PAID_LABELS), ("subtotal", SUBTOTAL_LABELS),
                        ("charge", CHARGE_LABELS), ("balance", BALANCE_LABELS)):
        # balance labels must be checked so "Total Due" is not read as "Total"
        hit = _labelled([b for b in blocks if not any(_match_label(b.text, bl) is not None for bl in BALANCE_LABELS)]
                        if key != "balance" else blocks, labels, amt, dirs, glued=True, skip_headers=True)
        if hit:
            got[key] = hit
    vals = {k: v[0][0] for k, v in got.items()}
    if vals:
        result.validations.append(f"total_amount: labelled amounts {vals}")

    peers = [vals[k] for k in ("subtotal", "paid") if k in vals]
    for key in ("total", "paid"):
        if key in got:
            (v, kind), src, rule = got[key]
            v, repaired = repair_lost_decimal(v, kind, [p for p in peers if p != v])
            note = " + lost-decimal repair (100x a peer amount)" if repaired else ""
            if key == "total" and "subtotal" in vals and "charge" not in vals and abs(v - vals["subtotal"]) >= 0.005:
                result.validations.append(f"total_amount: total {v} != subtotal {vals['subtotal']} with no tax/charge found")
            return v, src, f"{key}: {rule}{note}"
    if "subtotal" in got and "charge" not in got:
        (v, _), src, rule = got["subtotal"]
        return v, src, f"subtotal (no total/paid value, no tax/charge amount): {rule}"

    # Unlabelled: an amount equal to the sum of 2+ amounts directly above it in the same column.
    col_amounts = [(b, a[0]) for b in blocks if (a := _amount_only(b.text)) and "." in b.text]
    for b, v in sorted(col_amounts, key=lambda x: -x[0].y0):
        above = sorted([(o, ov) for o, ov in col_amounts if o.y1 <= b.y0 + b.h * 0.3 and abs(o.x1 - b.x1) < b.h * 1.5],
                       key=lambda x: x[0].y0)
        if len(above) >= 2 and abs(sum(ov for _, ov in above) - v) < 0.005 and v > 0:
            result.validations.append(f"total_amount: {' + '.join(o.text for o, _ in above)} == {b.text}")
            return v, b.src, f"unlabelled column sum of {len(above)} amounts above"
    return None


def extract_receipt_general(raw: RawOCRResult) -> GeneralReceipt:
    blocks = _prepare(raw)
    r = GeneralReceipt(document_id=raw.document_id)
    r.timings["ocr_predict_ms"] = raw.timings.get("total_ms", 0.0)

    hits = {
        "doctor_name": _doctor(blocks),
        "registration_number": _labelled(blocks, REG_LABELS, _id_token),
        "patient_name": _labelled(blocks, PATIENT_LABELS, _person),
        "receipt_number": _labelled(blocks, RECEIPT_LABELS, _id_token),
        "service_date": _date(blocks),
        "total_amount": _total(blocks, r),
    }
    for f in FIELDS:
        hit = hits[f]
        if hit is None:
            r.null(f, "no label or reusable pattern produced a confident value")
        elif hit[0] == "__AMBIGUOUS__":
            r.null(f, hit[2])
        else:
            r.set(f, hit[0], hit[1], hit[2])

    # Doctor and patient must not be the same person (would mean a bare 'Name' grabbed the doctor).
    if r.doctor_name and r.patient_name and re.sub(r"^Dr\.\s*", "", r.doctor_name) == r.patient_name:
        r.warnings.append("patient_name: same as doctor_name, dropped")
        r.patient_name = None
    return r
