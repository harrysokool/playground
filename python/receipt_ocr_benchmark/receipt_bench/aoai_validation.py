"""Light, general checks on the fields Azure OpenAI returns (improved DI + AOAI pipeline only).

These are deliberately few and receipt-agnostic: they clean up value boundaries the model gets
wrong (a label or a qualification copied along with the value) and flag values a person should
review. They do not look for fields themselves - that stays the model's job.

Changes a value:
- registration_number: if the reply holds more than an identifier (e.g. "MBBS · Reg. No. X123"),
  keep the one token that contains a digit. Several candidates -> kept as returned, flagged.
- doctor_name: drop trailing qualifications / post-nominals (MBBS, BDS (HK), FHKAM, ...) from
  each name. Several practitioners are separated by "; ".

Flags only (value unchanged, field listed in review_fields):
- a doctor name that contains a clinic / hospital / practice word;
- a text value not found in the OCR text (possible invention or reformatting);
- a total that equals a subtotal while a different total line exists. (Payments are not
  compared: co-payments, insurer settlements and deposits make them differ from the total.)
- any field the model itself listed as uncertain.
"""

from __future__ import annotations

import re

from receipt_bench.extraction_tuned import parse_amount

NAME_SEPARATOR = "; "

# Common medical, dental, Chinese-medicine, allied-health and veterinary post-nominals, matched as
# whole tokens (so surnames such as Hong, Mak or Baker are never taken for one). Only the college
# fellowship / membership families take a suffix (FRCSEd, FHKCFP, MRCPCH).
_QUALIFICATION = re.compile(
    r"(?:MBBS|MBChB|MB|BS|BDS|BChD|DDS|DMD|MDS|MD|PhD|MPhil|MSc|BSc|BPharm|MPharm|PharmD|BVSc|BVMS|DVM|CVA|"
    r"BChinMed|MChinMed|BCM|FRACGP|FRNZCGP|MRCGP|FHKAM|FAMS|DCH|DPT|MPT|BPT|BHSc|MHSc|RN|RPh|Hons|Dip|"
    r"(?:FRCS|FRCP|FRAC|MRCP|MRCS|FHKC)[A-Za-z]*)"
)
_ORG_WORDS = re.compile(r"\b(?:clinic|centre|center|hospital|practice|pharmacy|surgery|polyclinic|medical group)\b"
                        r"|診所|醫院|医院|中心|藥房|药房", re.I)
_SUBTOTAL = re.compile(r"sub\s*-?\s*total|小計|小计", re.I)
_TOTAL = re.compile(r"total|總額|总额|合計|合计|總計|总计", re.I)


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def split_names(value: str) -> list[str]:
    return [n.strip() for n in str(value).split(";") if n.strip()]


def strip_qualifications(name: str) -> str:
    """'Dr. Wong Mei Ling, BDS (HK)' -> 'Dr. Wong Mei Ling'. Only trailing tokens are removed, and
    only qualification tokens, bracketed parts such as (HK) and separators."""
    tokens = re.findall(r"\([^)]*\)|[^\s,·|]+|[,·|]", name)
    while len(tokens) > 1 and (tokens[-1] in ",·|" or tokens[-1].startswith("(")
                               or _QUALIFICATION.fullmatch(tokens[-1].strip("."))):
        tokens.pop()
    kept = " ".join(tokens)
    return re.sub(r"\s+([,.])", r"\1", kept).strip()


def clean_registration(value: str) -> tuple[str, str | None]:
    """Returns (value, warning or None)."""
    if not re.search(r"\s", value):
        return value, None
    ids = re.findall(r"[A-Za-z]*\d[\w\-/]*", value)
    if len(ids) == 1:
        return ids[0], f"registration_number: kept identifier {ids[0]!r} from {value!r}"
    return value, f"registration_number: {value!r} is not a single identifier"


def _amounts(line: str) -> list[float]:
    """Money amounts written with two decimals (so dates and ID numbers are ignored), as positive numbers."""
    out = []
    for m in re.findall(r"\d[\d,]*\.\d{2}\b", line):
        parsed = parse_amount(m)
        if parsed:
            out.append(abs(parsed[0]))
    return out


def check_total(total, ocr_text: str) -> str | None:
    """A warning if the total equals a subtotal line while another total line shows a different amount."""
    if not isinstance(total, (int, float)):
        return None
    lines = ocr_text.splitlines()
    same = lambda xs: any(abs(x - total) < 0.005 for x in xs)
    sub_lines = [l for l in lines if _SUBTOTAL.search(l) and same(_amounts(l))]
    other_totals = [a for l in lines if _TOTAL.search(l) and not _SUBTOTAL.search(l) for a in _amounts(l)]
    if sub_lines and other_totals and not same(other_totals):
        return f"total_amount: {total} matches a subtotal line ({sub_lines[0].strip()!r})"
    return None


def validate(fields: dict, ocr_text: str, uncertain: list[str] | None = None) -> tuple[dict, list[str], list[str]]:
    """Returns (fields, warnings, review_fields). `fields` are already normalized (ISO dates,
    numeric amounts)."""
    fields, warnings, review = dict(fields), [], set(uncertain or [])
    for f in sorted(set(uncertain or [])):
        warnings.append(f"{f}: model marked the value as uncertain")

    reg = fields.get("registration_number")
    if isinstance(reg, str):
        fields["registration_number"], w = clean_registration(reg)
        if w:
            warnings.append(w)
            if "not a single" in w:
                review.add("registration_number")

    doc = fields.get("doctor_name")
    if isinstance(doc, str):
        names = [strip_qualifications(n) for n in split_names(doc)]
        cleaned = NAME_SEPARATOR.join(n for n in names if n)
        if cleaned != doc:
            warnings.append(f"doctor_name: removed qualifications from {doc!r}")
            fields["doctor_name"] = cleaned
        if any(_ORG_WORDS.search(n) for n in names):
            warnings.append(f"doctor_name: {cleaned!r} may include a clinic or hospital name")
            review.add("doctor_name")

    text = _squash(ocr_text)
    for f in ("doctor_name", "registration_number", "patient_name", "receipt_number"):
        v = fields.get(f)
        parts = split_names(v) if f == "doctor_name" and isinstance(v, str) else [v]
        for p in parts:
            if isinstance(p, str) and _squash(p) not in text:
                warnings.append(f"{f}: {p!r} not found in the OCR text")
                review.add(f)

    w = check_total(fields.get("total_amount"), ocr_text)
    if w:
        warnings.append(w)
        review.add("total_amount")
    return fields, warnings, sorted(review)


DIAGNOSIS_STATUSES = ("present", "missing", "needs_review")


def check_diagnosis(status, evidence, ocr_text: str, image: bool = False) -> tuple[str, list[str]]:
    """Diagnosis comment (separate from the six fields): "present" needs evidence whose words are all
    in the OCR text (the comment may run over several rows), else it becomes needs_review. With the
    photo attached the evidence may come from the photo, so it is only flagged."""
    if status not in DIAGNOSIS_STATUSES:
        return "needs_review", [f"diagnosis: unexpected status {status!r}"]
    if status != "present":
        return status, []
    words = re.findall(r"[a-z0-9]+|[㐀-鿿]", str(evidence or "").lower())
    if not words:
        return "needs_review", ["diagnosis: present but no evidence quoted"]
    text = _squash(ocr_text)
    missing = [w for w in words if w not in text]
    if not missing:
        return status, []
    warning = f"diagnosis: evidence words not in the OCR text: {missing[:5]}"
    return (status, [warning]) if image else ("needs_review", [warning])
