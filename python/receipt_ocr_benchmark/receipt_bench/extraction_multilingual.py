"""Multilingual baseline: the original general rules plus common Chinese labels. RETROSPECTIVE.

The original general rules (extraction_general.py) knew English labels only, so they could not read
Chinese or bilingual receipts. This module adds exactly what docs/MULTILINGUAL_BASELINE.md lists, and
nothing else:
  1. Traditional and Simplified Chinese translations of the EXISTING English labels (no new label
     concepts; labels without one common receipt translation are skipped).
  2. Basic bilingual support: full-width "：" is a separator; a label right after a label (its
     translation) is skipped, not read as the value; a candidate value that starts with a known label
     or a Chinese form word is rejected.
  3. Chinese dates written YYYY年M月D日.

Everything else (geometry, value shapes, fail-closed lookups, unlabelled fallbacks, totals semantics)
is the original code, imported from extraction_general.py. Nothing comes from extraction_improved.py.
The nine Version 2 receipts were already examined before this baseline was written, so its scores
there are retrospective, not an independent test.
"""

from __future__ import annotations

import re
from collections import Counter

from receipt_bench import extraction_general as G
from receipt_bench.extraction_general import (FIELDS, Blk, GeneralReceipt, _above_right, _amount_only, _below,
                                              _clean_name, _CJK_NAME, _id_token, _is_header_cell, _LATIN_NAME,
                                              _right)
from receipt_bench.extraction_tuned import parse_amount, parse_date as parse_date_original
from receipt_bench.extraction_tuned import repair_lost_decimal
from receipt_bench.raw_ocr import RawOCRResult

# --- 1. label translations (docs/MULTILINGUAL_BASELINE.md, section 1) ------------------------
ZH = {
    "doctor": ["主診醫生", "主诊医生", "醫生姓名", "医生姓名", "醫生", "医生", "醫師", "医师", "獸醫", "兽医"],
    "patient": ["病人姓名", "患者姓名", "客戶姓名", "客户姓名", "寵物名稱", "宠物名称", "病人", "患者", "姓名"],
    "reg": ["註冊編號", "註冊號碼", "注册编号", "注册号码", "牌照號碼", "牌照号码"],
    "receipt": ["收據編號", "收據號碼", "收据编号", "收据号码", "發票編號", "發票號碼", "发票编号", "发票号码",
                "單據編號", "单据编号", "參考編號", "参考编号", "交易編號", "交易编号"],
    "service_date": ["服務日期", "服务日期", "診症日期", "诊症日期", "就診日期", "就诊日期", "治療日期", "治疗日期",
                     "入院日期"],
    "document_date": ["發票日期", "发票日期", "收據日期", "收据日期", "單據日期", "单据日期", "日期"],
    "total": ["應付總額", "应付总额", "總金額", "总金额", "總計", "总计", "總額", "总额", "合計", "合计", "總數", "总数"],
    "paid": ["已收款項", "已收款项", "已付金額", "已付金额", "已付"],
    "subtotal": ["小計", "小计"],
    "charge": ["稅項", "税项", "服務費", "服务费", "稅", "税"],
    "balance": ["尚欠餘額", "尚欠余额", "應付金額", "应付金额", "餘額", "余额", "結餘", "结余"],
}
ZH_FORM_WORDS = ["地址", "電話", "电话", "年齡", "年龄", "性別", "性别", "金額", "金额", "數量", "数量", "單價", "单价",
                 "項目", "项目", "備註", "备注", "診所", "诊所", "醫院", "医院"]


def _with_zh(english: list[str], key: str) -> list[str]:
    """English labels in their original order, then the Chinese ones, longest first."""
    return english + sorted(ZH[key], key=len, reverse=True)


DOCTOR_LABELS = _with_zh(G.DOCTOR_LABELS, "doctor")
PATIENT_LABELS = _with_zh(G.PATIENT_LABELS, "patient")
REG_LABELS = _with_zh(G.REG_LABELS, "reg")
RECEIPT_LABELS = _with_zh(G.RECEIPT_LABELS, "receipt")
DATE_LABELS = [_with_zh(G.DATE_LABELS[0], "service_date"), _with_zh(G.DATE_LABELS[1], "document_date")]
TOTAL_LABELS = _with_zh(G.TOTAL_LABELS, "total")
PAID_LABELS = _with_zh(G.PAID_LABELS, "paid")
SUBTOTAL_LABELS = _with_zh(G.SUBTOTAL_LABELS, "subtotal")
CHARGE_LABELS = _with_zh(G.CHARGE_LABELS, "charge")
BALANCE_LABELS = _with_zh(G.BALANCE_LABELS, "balance")
ALL_LABELS = sorted({l for group in (DOCTOR_LABELS, PATIENT_LABELS, REG_LABELS, RECEIPT_LABELS, TOTAL_LABELS,
                                     PAID_LABELS, SUBTOTAL_LABELS, CHARGE_LABELS, BALANCE_LABELS) for l in group}
                    | {l for g in DATE_LABELS for l in g}, key=len, reverse=True)
_SEP = r"[\s:：.#\-]*"  # original separators plus the full-width colon (section 2.1)


def _is_chinese(label: str) -> bool:
    return re.search(r"[㐀-鿿]", label) is not None

# --- 3. Chinese dates -----------------------------------------------------------------------
_ZH_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def parse_date(text: str):
    hit = parse_date_original(text)
    if hit:
        return hit
    m = _ZH_DATE.search(text)
    if m:
        try:
            from datetime import date
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat(), "chinese"
        except ValueError:
            return None
    return None


# --- preprocessing and label matching (section 2) --------------------------------------------
_SPLIT = re.compile(r"(?:(?<=\s)|^)(?:" + "|".join(re.escape(l) for l in ALL_LABELS) + r")\s*[:：]", re.I)


def _prepare(raw: RawOCRResult) -> list[Blk]:
    out: list[Blk] = []
    for page in raw.pages[:1]:
        for b in page.blocks:
            text = re.sub(r"\s+", " ", b.text).strip()
            if not text or (b.confidence or 0.0) < G.MIN_CONF:
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


def _starts_with_label(t: str) -> str | None:
    """The known label (any field, either language) the text starts with, else None."""
    for l in ALL_LABELS:
        if re.match(rf"(?i){re.escape(l)}\b", t):
            return l
    return None


def _match_label(text: str, label: str, allow_glued_amount: bool = False) -> str | None:
    """Remainder after `label` if the block starts with it; a translation right after it is skipped."""
    if text[:1].islower():
        return None
    m = re.match(rf"(?i){re.escape(label)}\b{_SEP}(.*)$", text)  # \b as in the original (CJK counts as \w)
    if m:
        rem = m.group(1).strip()
        nxt = _starts_with_label(rem)
        # "Patient 病人" / "病人 Patient": a label in the other language is its translation, not the value
        # (section 2.2). Same-language labels are left alone, so English-only text behaves as before.
        if nxt and _is_chinese(nxt) != _is_chinese(label):
            rem = re.sub(rf"^{_SEP}", "", rem[len(nxt):]).strip()
        return rem
    if allow_glued_amount:
        m = re.match(rf"(?i){re.escape(label)}([$\dZO][\d.,ZO]*\d)$", text)
        if m and parse_amount(m.group(1)):
            return m.group(1)
    return None


def _looks_like_label(t: str) -> bool:
    """Original English form-word check, plus Chinese labels and form words (section 2.3)."""
    nxt = _starts_with_label(t)
    return G._looks_like_label(t) or (nxt is not None and _is_chinese(nxt)) or any(t.startswith(w) for w in ZH_FORM_WORDS)


def _person(t: str) -> str | None:
    t = _clean_name(t)
    core = re.sub(r"^Dr\.\s*", "", t)
    if not core or any(c.isdigit() for c in core) or _looks_like_label(core):
        return None
    return t if (_LATIN_NAME.match(core) or _CJK_NAME.match(core)) else None


# --- the original lookups and field logic, with the extended labels ---------------------------


def _labelled(blocks, labels, parse, directions=("right", "below"), glued=False, skip_headers=False):
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
                break
    return None


def _doctor(blocks):
    hit = _labelled(blocks, DOCTOR_LABELS, _person)
    if hit:
        return hit
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
    col_amounts = [(b, a[0]) for b in blocks if (a := _amount_only(b.text)) and "." in b.text]
    for b, v in sorted(col_amounts, key=lambda x: -x[0].y0):
        above = sorted([(o, ov) for o, ov in col_amounts if o.y1 <= b.y0 + b.h * 0.3 and abs(o.x1 - b.x1) < b.h * 1.5],
                       key=lambda x: x[0].y0)
        if len(above) >= 2 and abs(sum(ov for _, ov in above) - v) < 0.005 and v > 0:
            result.validations.append(f"total_amount: {' + '.join(o.text for o, _ in above)} == {b.text}")
            return v, b.src, f"unlabelled column sum of {len(above)} amounts above"
    return None


def extract_receipt_multilingual(raw: RawOCRResult) -> GeneralReceipt:
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
    if r.doctor_name and r.patient_name and re.sub(r"^Dr\.\s*", "", r.doctor_name) == r.patient_name:
        r.warnings.append("patient_name: same as doctor_name, dropped")
        r.patient_name = None
    return r
