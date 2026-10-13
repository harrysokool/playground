"""Phase 10: improved rule-based extraction (no language model). TUNED ON THE VERSION 2 RECEIPTS.

The original general rules (extraction_general.py) are left unchanged so both can be compared.
This module keeps their approach (labels, nearby values, fail closed, shape checks) and adds
reusable rules for what made them fail on the Version 2 receipts. The receipts were used to
develop these rules, so Version 2 scores with them are NOT an independent test.

What changed compared with the general rules:
  1. Every block is classified by its LONGEST matching label across all kinds, including
     "distractor" labels that must never supply an answer (Patient No., Client No., Referred by,
     Nurse, Date Issued, Next Appointment, Printed, Paid by insurer, Balance ...). So
     "Patient No." can no longer be read as the patient label, nor "Date Issued" as a date label.
  2. Traditional Chinese labels (病人姓名, 主診醫生, 註冊編號, 收據編號, 診症日期, 合計 ...), and
     bilingual labels where the Chinese translation follows the English one ("Patient 病人:").
     The translation is stripped instead of being read as the value.
  3. Label matching tolerates what OCR does to labels: no space between words or scripts
     ("TreatmentDate治療日期"), full-width punctuation ("："), and simplified characters in
     labels ("收據编號"). The mapping is applied to labels only, never to values.
  4. A label block is never a value. When the nearest candidate is another label, the next
     direction is tried. A role header with a "Name" row under it (a card layout: "CLIENT" /
     "Name | ...") is resolved through that row.
  5. Registration numbers are also found inside a line ("MBBS (HK) · Reg. No. M17642").
  6. Dates: service-date labels first, then a bare "Date"/"日期"; dates under distractor labels
     are excluded everywhere. Traditional Chinese dates (2026年6月9日) are read.
  7. Totals: total labels first (incl. "Total Charges", 合計, 總額). Amounts are also looked for
     below a label in a row of label cards, but only when the amount is the last one in its column.
     Insurer/plan payments, partial payments and balances are never the total. If no total
     label is found: subtotal minus discounts, then the amount paid (only if nothing else paid
     part of it), then the original column-sum check. OCR "HKS" before digits is read as "HK$".
  8. Doctor names lose trailing qualifications from a short list of degree abbreviations
     ("Dr. Ho Ching Yee, BDS (HK)" -> "Dr. Ho Ching Yee"). The unlabelled "Dr <Name>" fallback
     ignores names under distractor labels (Referred by, Nurse ...).

Not done on purpose: no per-layout or per-receipt handling, no clinic/doctor/value lists, no
receipt coordinates, no language model.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date

from receipt_bench.extraction_general import (FIELDS, GeneralReceipt, _above_right, _below, _CJK_NAME, _clean_name,
                                              _is_header_cell, _LATIN_NAME, _looks_like_label, _prepare, _right)
from receipt_bench.extraction_tuned import parse_amount, parse_date, repair_lost_decimal
from receipt_bench.raw_ocr import RawOCRResult

# --- label vocabulary: kind -> (English labels, Chinese labels), most specific first -----------------
LABELS: dict[str, tuple[list[str], list[str]]] = {
    "doctor": (["attending doctor", "attending physician", "treating doctor", "consulting doctor", "doctor name",
                "doctor", "physician", "dentist", "physiotherapist", "chiropractor", "therapist",
                "medical practitioner", "practitioner", "clinician", "prescriber", "veterinarian", "provider name",
                "provider"],
               ["主診中醫師", "主診醫生", "主診醫師", "主診中醫", "中醫師", "牙科醫生", "物理治療師", "醫生", "醫師", "牙醫",
                "脊醫"]),
    "patient": (["patient name", "name of patient", "patient", "client name", "client", "customer name",
                 "customer", "member name", "pet name"],
                ["病人姓名", "患者姓名", "病人", "患者", "求診者"]),
    "name": (["name"], ["姓名"]),  # generic: patient as a last resort, or the row under a role header
    "reg": (["registration number", "registration no", "reg no", "reg number", "licence no", "license no"],
            ["註冊中醫編號", "醫生註冊編號", "註冊編號", "註冊號碼"]),
    "receipt": (["official receipt no", "receipt number", "receipt no", "receipt #", "invoice number", "invoice no",
                 "invoice #", "bill number", "bill no", "reference no", "ref no", "transaction no"],
                ["收據編號", "收據號碼", "發票編號", "發票號碼", "單據編號", "單號"]),
    "service_date": (["date of service", "service date", "date of consultation", "consultation date", "date of visit",
                      "visit date", "treatment date", "session date", "attendance date", "admission date"],
                     ["診症日期", "就診日期", "治療日期", "求診日期", "診治日期", "服務日期", "應診日期"]),
    "date": (["date"], ["日期"]),
    "total": (["grand total", "total amount due", "total amount", "total charges", "total charge", "total fees",
               "total payable", "amount payable", "net total", "net amount", "total"],
              ["應付總額", "應付金額", "總收費", "總金額", "總額", "總計", "合計"]),
    "subtotal": (["subtotal", "sub total", "sub-total"], ["小計"]),
    "discount": (["member discount", "discount"], ["會員折扣", "會員優惠", "折扣", "優惠"]),
    "charge": (["tax", "gst", "vat", "service charge", "surcharge"], ["服務費", "稅"]),
    "paid": (["total payment received", "payment received", "amount paid", "total paid", "paid by", "paid"],
             ["已付", "實收", "已收"]),
    # never the answer to any field:
    "x_part_paid": (["paid by insurer", "paid by patient", "paid by plan", "covered by plan", "covered by insurance",
                     "insurance paid", "insurer paid", "co-payment", "copayment", "deposit"],
                    ["保險公司直接付款", "病人已付", "病人自付", "計劃承保", "按金"]),
    "x_balance": (["outstanding balance", "balance due", "amount due", "total due", "balance"],
                  ["尚欠餘額", "結欠", "尚欠", "餘額"]),
    "x_date": (["date issued", "issue date", "issued on", "invoice date", "receipt date", "bill date", "print date",
                "printed on", "printed", "payment date", "due date", "next appointment", "next recall", "next visit",
                "follow up", "follow-up", "expiry date", "expiry"],
               ["發票日期", "收據日期", "列印日期", "付款日期", "覆診日期", "下次覆診", "到期日"]),
    "x_id": (["plan member no", "member no", "membership no", "patient no", "patient id", "patient number",
              "hospital no", "file no", "client no", "policy no", "episode no", "case no", "record no",
              "medical record no", "item code", "card no", "account no"],
             ["計劃會員編號", "會員號碼", "會員編號", "病人編號", "病歷編號", "保單編號", "診症編號", "檔案編號", "項目編號",
              "收銀機", "收銀員"]),
    "x_person": (["referred by", "referring doctor", "referral", "performed by", "nurse", "cashier", "insurer"],
                 ["轉介醫生", "轉介", "負責人員", "護士", "收銀員", "保險公司"]),
}

# Simplified -> Traditional for characters seen in OCR'd labels; applied to label matching only.
_S2T = str.maketrans("编号额诊医疗项现计总单价册历实费应发据银员码会剂药处负责划余结时间师记录检务险证书欠", "編號額診醫療項現計總單價冊歷實費應發據銀員碼會劑藥處負責劃餘結時間師記錄檢務險證書欠")
_FULLWIDTH = str.maketrans("：（）．＃，", ":().#,")
_CJK = r"㐀-鿿"
_CN_LABELS = sorted({l for _, (_, zh) in LABELS.items() for l in zh}, key=len, reverse=True)


def _label_key(text: str) -> str:
    """Text as compared with labels: full-width punctuation and simplified label characters mapped.
    1:1 character mapping, so positions in it match positions in the original text."""
    return text.translate(_FULLWIDTH).translate(_S2T)


def _en_pattern(label: str) -> str:
    """'reg no' -> tolerant regex: words may be glued or separated by spaces / dots."""
    words = re.findall(r"[a-z0-9#]+|-", label)
    return r"[\s.]*".join(re.escape(w) for w in words) + r"\.?"


_EN = {kind: [(l, re.compile(r"(?i)(?:less\s*:\s*)?" + _en_pattern(l) + r"(?![A-Za-z])")) for l in en]
       for kind, (en, _) in LABELS.items()}
_ZH = {kind: zh for kind, (_, zh) in LABELS.items()}


def _strip_translation(key: str, pos: int) -> int:
    """After an English label: skip a Chinese translation (a known Chinese label, an OCR-damaged
    start of one, or any Chinese run directly followed by a colon), then separators."""
    m = re.match(rf"\s*([{_CJK}()（）]+)", key[pos:])
    if m:
        run = m.group(1).strip("()（）")
        follows_colon = re.match(r"\s*[:：]", key[pos + m.end():]) is not None
        if any(run.startswith(l) or (len(run) >= 2 and l.startswith(run)) for l in _CN_LABELS) or follows_colon:
            pos += m.end()
    m = re.match(r"[\s:：.#\-]*", key[pos:])
    return pos + m.end()


@dataclass
class Label:
    kind: str
    label: str
    rank: int  # position in that kind's vocabulary (lower = more specific)
    rest: str  # text after the label (and translation / separators)


def classify(text: str) -> Label | None:
    """The longest label that starts this block, across all kinds; None if the block is not a label."""
    if not text or text[:1].islower():
        return None
    key = _label_key(text)
    best = None  # (matched length, Label)
    for kind, pats in _EN.items():
        for rank, (label, rx) in enumerate(pats):
            m = rx.match(key)
            if m and (best is None or m.end() > best[0]):
                best = (m.end(), Label(kind, label, rank, text[_strip_translation(key, m.end()):].strip()))
    for kind, zh in _ZH.items():
        for rank, label in enumerate(zh):
            if key.startswith(label) and (best is None or len(label) > best[0]):
                end = len(label) + len(re.match(r"[\s:：]*", key[len(label):]).group(0))
                best = (len(label), Label(kind, label, rank, text[end:].strip()))
    return best[1] if best else None


# --- values ------------------------------------------------------------------------------------------

DEGREES = {"MBBS", "MBCHB", "MD", "BDS", "DDS", "DMD", "BCHD", "FRCP", "MRCP", "FRCS", "MRCS", "FHKAM", "FHKCP",
           "FHKCFP", "FRACGP", "FHKCOG", "DCH", "BSC", "MSC", "MPHIL", "PHD", "BPHARM", "RN", "BCM", "BCHINMED"}


def _strip_qualifications(t: str) -> str:
    """Drop trailing degree abbreviations: 'Dr. Ho Ching Yee, BDS (HK)' -> 'Dr. Ho Ching Yee'."""
    parts = [p.strip() for p in t.split(",")]
    while len(parts) > 1 and all(re.sub(r"\(.*?\)|[.\s]", "", w).upper() in DEGREES or w.startswith("(")
                                 for w in parts[-1].split()):
        parts.pop()
    return ", ".join(parts)


def person(t: str) -> str | None:
    if classify(t) is not None:
        return None
    t = _clean_name(_strip_qualifications(t))
    core = re.sub(r"^Dr\.\s*", "", t)
    if not core or any(c.isdigit() for c in core) or _looks_like_label(core):
        return None
    return t if (_LATIN_NAME.match(core) or _CJK_NAME.match(core)) else None


def id_token(t: str) -> str | None:
    if classify(t) is not None:
        return None
    tok = t.split()[0].strip(".,;:") if t.split() else ""
    return tok if len(tok) >= 3 and any(c.isdigit() for c in tok) and re.fullmatch(r"[A-Za-z0-9\-/]+", tok) else None


_ZH_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def to_date(t: str) -> str | None:
    if m := _ZH_DATE.search(t):
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return None
    p = parse_date(t)
    return p[0] if p else None


def amount(t: str):
    """Amount-only text, allowing a currency in front: '港幣 $790.00', 'HK$1,575.00', OCR 'HKS1,880.00'."""
    s = re.sub(r"HKS(?=\s*\d)", "HK$", t.strip())
    s = re.sub(r"^(?:港幣|HKD|HK\$|\$)\s*", "", s).replace("$", "").strip()
    if re.fullmatch(r"-?[\dZO][\d,.ZO]*", s) and any(c.isdigit() for c in s):
        return parse_amount(s)
    return None


# --- lookup ------------------------------------------------------------------------------------------

def _value(b, blocks, labels: dict, parse, directions):
    """Value for label block `b`: its own remainder, else the nearest block in each direction.
    A label block is never a value; a 'Name' row under a role header is followed through."""
    lab = labels[id(b)]
    if lab.rest:
        v = parse(lab.rest)
        if v is not None:
            return v, b.src, "same block"
        # the remainder is not a value (e.g. "Member discount 10% 會員折扣", "已付(現金)"): look nearby
    for d in directions:
        n = {"right": _right, "below": _below, "above_right": _above_right}[d](b, blocks)
        if n is None:
            continue
        nl = labels.get(id(n))
        if nl is not None:
            if nl.kind == "name" and d == "below":  # role header card: "CLIENT" / "Name | Yeung Tsz Kit"
                inner = _value(n, blocks, labels, parse, ("right",))
                if inner:
                    return inner[0], f"{n.src} | {inner[1]}", "header + Name row"
            continue  # a label is not a value: try the next direction
        v = parse(n.text)
        return (v, f"{b.src} | {n.src}", d) if v is not None else None  # nearest candidate only (fail closed)
    return None


def _find(blocks, labels, kinds, parse, directions=("right", "below"), skip_headers=False):
    cands = sorted(((labels[id(b)].rank, i, b) for i, b in enumerate(blocks)
                    if id(b) in labels and labels[id(b)].kind in kinds),
                   key=lambda c: (kinds.index(labels[id(c[2])].kind), c[0], c[1]))
    for _, _, b in cands:
        dirs = directions
        if skip_headers and not labels[id(b)].rest and _is_header_cell(b, blocks):
            dirs = ("below_last",)
        if dirs == ("below_last",):
            n = _below(b, blocks)
            if n is not None and id(n) not in labels and _last_in_column(n, blocks):
                v = parse(n.text)
                if v is not None:
                    return v, f"{b.src} | {n.src}", f"label '{labels[id(b)].label}' (card, below)"
            continue
        hit = _value(b, blocks, labels, parse, dirs)
        if hit:
            return hit[0], hit[1], f"label '{labels[id(b)].label}' ({hit[2]})"
    return None


def _last_in_column(n, blocks) -> bool:
    """No other amount further down in the same column (so a column header's first row is not used)."""
    return not any(o is not n and o.y0 > n.y1 and abs(o.x1 - n.x1) < n.h * 1.5 and amount(o.text) for o in blocks)


def _distractor_values(blocks, labels) -> set[int]:
    """Blocks that are the value of a distractor label (referred-by doctor, next-appointment date ...)."""
    out = set()
    for b in blocks:
        lab = labels.get(id(b))
        if lab and lab.kind.startswith("x_"):
            out.add(id(b))
            if not lab.rest or (lab.kind == "x_person" and person(lab.rest) is None):
                for f in (_right, _below):
                    if (n := f(b, blocks)) is not None and id(n) not in labels:
                        out.add(id(n))
                        break
    return out


# --- fields ------------------------------------------------------------------------------------------

def _doctor(blocks, labels, excluded):
    hit = _find(blocks, labels, ["doctor"], person)
    if hit:
        return hit
    cands = []
    for b in blocks:
        if id(b) in excluded:
            continue
        if m := re.search(r"(?:^|[\s,|·])(Dr\.?\s*[A-Z][^\d|·]*)$", b.text):
            if v := person(m.group(1)):
                cands.append((v, b.src, "unlabelled 'Dr <name>' pattern"))
        elif m := re.search(rf"([{_CJK}]{{2,4}})(?:醫生|医生)", b.text):
            cands.append((m.group(0), b.src, "unlabelled CJK name + 醫生 title"))
    distinct = {c[0] for c in cands}
    return cands[0] if len(distinct) == 1 else None


_EMBEDDED_REG = re.compile(r"(?i)(?:reg(?:istration)?[\s.]*(?:no|number|#)\.?|licen[cs]e[\s.]*no\.?|註冊(?:中醫)?編號|"
                           r"註冊號碼)\s*[:：]?\s*([A-Z]{0,3}\d{3,8})(?![\w])")


def _registration(blocks, labels):
    hit = _find(blocks, labels, ["reg"], id_token)
    if hit:
        return hit
    found = {(m.group(1), b.src) for b in blocks if (m := _EMBEDDED_REG.search(_label_key(b.text)))}
    values = {v for v, _ in found}
    if len(values) == 1:
        v, src = next(iter(found))
        return v, src, "registration label inside a line"
    return None


def _date(blocks, labels, excluded):
    for kinds, note in ((["service_date"], ""), (["date"], "generic date label")):
        hit = _find(blocks, labels, kinds, to_date)
        if hit:
            return hit[0], hit[1], hit[2] + (f", {note}" if note else "")
    found = [(d, b.src) for b in blocks if id(b) not in excluded and (d := to_date(b.text))]
    if found:
        (iso, n), = Counter(d for d, _ in found).most_common(1)
        if n * 2 > len(found) and n >= 2:
            return iso, next(s for d, s in found if d == iso), f"unlabelled: {n}/{len(found)} dates agree"
    return None


def _total(blocks, labels, r: GeneralReceipt):
    dirs = ("right", "above_right", "below")
    got = {k: _find(blocks, labels, [k], amount, dirs, skip_headers=True)
           for k in ("total", "subtotal", "discount", "charge", "paid", "x_part_paid", "x_balance")}
    got = {k: v for k, v in got.items() if v}
    vals = {k: v[0][0] for k, v in got.items()}
    if vals:
        r.validations.append(f"total_amount: labelled amounts {vals}")
    peers = [vals[k] for k in ("subtotal", "paid") if k in vals]
    if "total" in got:
        (v, kind), src, rule = got["total"]
        v, repaired = repair_lost_decimal(v, kind, [p for p in peers if p != v])
        return v, src, f"total: {rule}" + (" + lost-decimal repair" if repaired else "")
    if "subtotal" in vals and "discount" in vals:
        v = round(vals["subtotal"] - abs(vals["discount"]), 2)
        return v, got["subtotal"][1], "subtotal minus discount (no total label)"
    if "paid" in got and "x_part_paid" not in got and vals.get("x_balance", 0) == 0:
        (v, _), src, rule = got["paid"]
        return v, src, f"paid in full (no total label): {rule}"
    if "subtotal" in got and "charge" not in got:
        (v, _), src, rule = got["subtotal"]
        return v, src, f"subtotal (no total/paid, no tax/charge): {rule}"
    col = [(b, a[0]) for b in blocks if (a := amount(b.text)) and "." in b.text]
    for b, v in sorted(col, key=lambda x: -x[0].y0):
        above = [ov for o, ov in col if o.y1 <= b.y0 + b.h * 0.3 and abs(o.x1 - b.x1) < b.h * 1.5]
        if len(above) >= 2 and abs(sum(above) - v) < 0.005 and v > 0:
            return v, b.src, f"unlabelled column sum of {len(above)} amounts above"
    return None


def extract_receipt_improved(raw: RawOCRResult) -> GeneralReceipt:
    blocks = _prepare(raw)
    labels = {id(b): lab for b in blocks if (lab := classify(b.text))}
    excluded = _distractor_values(blocks, labels)
    r = GeneralReceipt(document_id=raw.document_id)
    r.timings["ocr_predict_ms"] = raw.timings.get("total_ms", 0.0)
    hits = {
        "doctor_name": _doctor(blocks, labels, excluded),
        "registration_number": _registration(blocks, labels),
        "patient_name": _find(blocks, labels, ["patient", "name"], person),
        "receipt_number": _find(blocks, labels, ["receipt"], id_token),
        "service_date": _date(blocks, labels, excluded),
        "total_amount": _total(blocks, labels, r),
    }
    for f in FIELDS:
        if hits[f] is None:
            r.null(f, "no label or reusable pattern produced a confident value")
        else:
            r.set(f, *hits[f])
    if r.doctor_name and r.patient_name and re.sub(r"^Dr\.\s*", "", r.doctor_name) == r.patient_name:
        r.warnings.append("patient_name: same as doctor_name, dropped")
        r.patient_name = None
    return r
