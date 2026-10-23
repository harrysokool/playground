"""Diagnosis comment detection: is there a written comment about the patient's condition,
symptoms or diagnosis? Rules only, no language model. Separate from the six-field benchmark.

Reads the same raw OCR JSON as the extraction rules, so PaddleOCR Light and Azure DI go through
exactly the same logic. What the comment says, and whether it is medically right, is not checked.

Result per receipt: `present`, `missing` or `needs_review`, plus the evidence it is based on.
  1. Too little OCR text (fewer than MIN_BLOCKS blocks) -> needs_review: an unreadable page is never
     reported as missing.
  2. Find labels. Strong labels name the diagnosis itself (Diagnosis, Symptoms, Chief complaint,
     診斷, 症狀 ...). Weak labels can hold anything (Notes, Remarks, 備註 ...). A label must start
     a block and be followed by ":" , the end of the block or (Chinese) a space; a strong label
     followed by ":" may also start mid-line. So "Please Note. We are open..." is not a label.
     Treatment / service / visit-date labels (Treatment, 診症日期, 覆診) are not in the vocabulary.
  3. Its value: the rest of the block, else the blocks to the right on the same row, else the line
     below. Another label (or a far-away column) is never a value.
  4. Judge the value:
     - blank or a placeholder (-, N/A, nil, 無 ...) -> missing (the label is empty);
     - fewer than 2 letters -> needs_review (unreadable);
     - strong label -> present;
     - weak label: words about symptoms or illness -> present; only administrative words (payment,
       receipt, insurance, appointment ...) -> missing; anything else -> needs_review.
  5. Any label present -> present; else any needs_review -> needs_review; else missing.

Not done on purpose: no per-receipt or per-layout handling, and comments with no label (a
condition written as a line item, free handwriting) are not looked for - that is where AOAI may
add value.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from receipt_bench.extraction_general import ALL_LABELS, Blk, _prepare
from receipt_bench.raw_ocr import RawOCRResult

STATUSES = ("present", "missing", "needs_review")
MIN_BLOCKS = 10  # fewer OCR text blocks than this: the page was not read, so "missing" can't be told

STRONG_EN = ["provisional diagnosis", "clinical diagnosis", "diagnosis", "diagnoses", "dx", "ddx", "impression",
             "clinical findings", "clinical notes", "medical notes", "doctor's notes", "medical condition",
             "condition", "signs and symptoms", "symptoms", "symptom", "chief complaint", "presenting complaint",
             "reason for visit", "reason for consultation", "nature of illness", "illness", "injury"]
STRONG_ZH = ["臨床診斷", "临床诊断", "初步診斷", "初步诊断", "診斷", "诊断", "病症", "病況", "病况", "病情", "症狀", "症状",
             "病徵", "病征", "主訴", "主诉", "求診原因", "求诊原因", "就診原因", "就诊原因"]
WEAK_EN = ["doctor's remarks", "remarks", "remark", "comments", "comment", "notes", "note"]
WEAK_ZH = ["醫生意見", "医生意见", "備註", "備注", "备注", "附註", "附注"]

_LABELS = sorted([(l, "strong", False) for l in STRONG_EN] + [(l, "strong", True) for l in STRONG_ZH]
                 + [(l, "weak", False) for l in WEAK_EN] + [(l, "weak", True) for l in WEAK_ZH],
                 key=lambda x: len(x[0]), reverse=True)

PLACEHOLDER = re.compile(r"(?i)^(?:n/?a|nil|none|not applicable|na|無|无|沒有|没有)?$")
# General words about symptoms or illness (English stems, Chinese characters), for weak labels only.
MEDICAL_CUES = re.compile(
    r"(?i)\b(?:pains?\b|painful|aches?\b|fever|cough|colds?\b|flu\b|influenza|infect|injur|fractur|sprain|strain|rash|allerg"
    r"|diarrh|vomit|nausea|dizz|sore|swell|bleed|wound|burn|asthma|hypertension|diabet|inflam|symptom|diagnos"
    r"|disease|illness|condition)|\w(?:itis|ache)\b|[痛燒烧咳炎傷伤瀉泻嘔呕暈晕腫肿症病敏]|感冒|骨折|扭")
ADMIN_CUES = re.compile(
    r"(?i)pay|settle|balance|receipt|invoice|insur|claim|refund|appointment|thank|open\b|closed|office hours|copy"
    r"|valid|cheque|cash|deposit|keep this|收據|收据|發票|保險|保险|索償|索偿|付款|繳|缴|預約|预约|謝謝|谢谢|多謝|營業|营业")
_CJK = re.compile(r"[㐀-鿿]")


@dataclass
class DiagnosisResult:
    document_id: str
    status: str
    reason: str
    evidence: list[dict] = field(default_factory=list)  # one entry per label found
    timings: dict[str, float] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"document_id": self.document_id,
                                    "diagnosis": {"status": self.status, "reason": self.reason,
                                                  "evidence": self.evidence},
                                    "timings": self.timings}, indent=2, ensure_ascii=False))


# --- labels ---------------------------------------------------------------------------------


def _label_at(text: str, pos: int) -> tuple[str, str, bool, int] | None:
    """(label, kind, is_chinese, end) for the longest label starting at text[pos]."""
    for label, kind, zh in _LABELS:
        end = pos + len(label)
        if zh and text.startswith(label, pos):
            return label, kind, zh, end
        if not zh and text[pos:end].lower() == label and not text[end:end + 1].isalpha():
            return label, kind, zh, end
    return None


def parse_label(text: str) -> tuple[str, str, str] | None:
    """(kind, label, rest) if the block is a diagnosis/notes label, else None.
    A translation of the label ("Diagnosis 診斷:") is skipped."""
    text = text.replace("：", ":")
    for start in [0] + [m.end() for m in re.finditer(r"\s+", text)]:
        hit = _label_at(text, start)
        if not hit:
            continue
        label, kind, zh, end = hit
        gap = re.match(r"\s*", text[end:]).end()
        translation = _label_at(text, end + gap)
        if translation:
            end = translation[3]
        after = text[end:]
        colon = re.match(r"\s*:\s*", after)
        if colon:
            rest = after[colon.end():]
        elif start == 0 and not after.strip():
            rest = ""
        elif start == 0 and (zh or (translation and translation[2])) and after[:1].isspace():
            rest = after.strip()
        else:
            continue
        if start > 0 and (kind != "strong" or not colon):
            continue  # mid-line: only "Diagnosis:"-style labels
        return kind, label, rest.strip()
    return None


def _is_label(text: str) -> bool:
    """Another label: a diagnosis/notes label, text ending in ":", or a common receipt label."""
    t = text.strip()
    if parse_label(t) or t.endswith(":"):
        return True
    return any(re.fullmatch(rf"(?i){re.escape(l)}\s*[.#]?", t) for l in ALL_LABELS)


# --- values ---------------------------------------------------------------------------------

MAX_GAP = 6  # line heights between a label and its value on the same row (columns are further apart)


def _value(label: Blk, blocks: list[Blk]) -> str:
    """Blocks to the right on the label's row (chained while close), else the first line below."""
    row = sorted((b for b in blocks if b is not label and abs(b.cy - label.cy) < label.h * 0.7
                  and b.x0 >= label.x1 - label.h * 0.5), key=lambda b: b.x0)
    parts, x = [], label.x1
    for b in row:
        if b.x0 - x > label.h * MAX_GAP or _is_label(b.text):
            break
        parts.append(b.text)
        x = b.x1
    if parts:
        return " ".join(parts)
    below = [b for b in blocks if b is not label and label.y1 - label.h * 0.5 <= b.y0 <= label.y1 + label.h * 2.5
             and b.x0 < label.x1 + label.h and b.x1 > label.x0 - label.h and abs(b.cy - label.cy) >= label.h * 0.5]
    first = min(below, key=lambda b: b.y0, default=None)
    return "" if first is None or _is_label(first.text) or _is_item_line(first, blocks) else first.text


_AMOUNT = re.compile(r"(?:HK\$|\$|HKD\s*)?-?[\d,]+\.\d{2}")


def _is_item_line(b: Blk, blocks: list[Blk]) -> bool:
    """A charge line (an amount close by on its right), e.g. the first item under an empty box."""
    return any(o is not b and abs(o.cy - b.cy) < b.h * 0.7 and 0 <= o.x0 - b.x1 <= b.h * MAX_GAP
               and _AMOUNT.fullmatch(o.text.strip()) for o in blocks)


def judge(kind: str, value: str) -> tuple[str, str]:
    """(status, reason) for one label and its value."""
    core = value.strip(" \t-–—_.:;,/|*~")
    if PLACEHOLDER.match(core):
        return "missing", "label with no comment"
    if len(re.findall(r"[A-Za-z]|[㐀-鿿]", core)) < 2:
        return "needs_review", "value unreadable"
    if kind == "strong":
        return "present", "diagnosis label with a value"
    if MEDICAL_CUES.search(core):
        return "present", "note about symptoms or illness"
    if ADMIN_CUES.search(core):
        return "missing", "administrative remark only"
    return "needs_review", "note of unclear content"


# --- receipt --------------------------------------------------------------------------------


def detect_diagnosis(raw: RawOCRResult) -> DiagnosisResult:
    blocks = _prepare(raw)
    if len(blocks) < MIN_BLOCKS:
        return DiagnosisResult(raw.document_id, "needs_review", f"too little OCR text ({len(blocks)} blocks)")
    evidence = []
    for b in blocks:
        parsed = parse_label(b.text)
        if not parsed:
            continue
        kind, label, rest = parsed
        value = rest or _value(b, blocks)
        status, reason = judge(kind, value)
        evidence.append({"label": label, "kind": kind, "value": value, "status": status, "reason": reason,
                         "source": b.text})
    for status in ("present", "needs_review"):
        hits = [e for e in evidence if e["status"] == status]
        if hits:
            return DiagnosisResult(raw.document_id, status, hits[0]["reason"], evidence)
    reason = "only empty or administrative labels" if evidence else "no diagnosis or notes label"
    return DiagnosisResult(raw.document_id, "missing", reason, evidence)


def status_of(record: dict) -> str | None:
    """The diagnosis status in a result file (rules or DI + AOAI), or None if it has none."""
    d = record.get("diagnosis")
    if record.get("status", "ok") != "ok" or not isinstance(d, dict):
        return None
    return d.get("status") if d.get("status") in STATUSES else None
