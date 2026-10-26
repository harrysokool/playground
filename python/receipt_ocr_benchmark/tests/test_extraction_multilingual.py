"""Multilingual baseline: English behaviour unchanged, Chinese labels and basic bilingual handling added.
Synthetic, made-up layouts only; the parity test compares two rule sets, it does not score anything."""

import re
from dataclasses import asdict
from pathlib import Path

import pytest

from receipt_bench import extraction_multilingual as M
from receipt_bench.extraction_general import extract_receipt_general
from receipt_bench.extraction_multilingual import extract_receipt_multilingual, parse_date
from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[㐀-鿿]")


def _raw(rows, doc="synthetic"):
    """Rows of side-by-side blocks -> raw OCR (30 px lines, 40 px between blocks)."""
    blocks = []
    for i, row in enumerate(rows):
        x, y = 50, 40 + i * 50
        for t in row:
            w = len(t) * 14
            blocks.append(OCRBlock(t, 0.95, [[x, y], [x + w, y], [x + w, y + 30], [x, y + 30]], len(blocks)))
            x += w + 40
    return RawOCRResult(doc, {}, [PageResult(1, 1000, 1400, blocks, "\n".join(b.text for b in blocks))], {})


def _fields(r):
    d = asdict(r)
    return {k: d[k] for k in ("doctor_name", "registration_number", "patient_name", "receipt_number",
                              "service_date", "total_amount", "sources")}


SAVED = sorted(p for e in ("paddle_light", "azure_di") for p in (ROOT / "results" / "v2" / e).glob("receipt*.json"))


@pytest.mark.parametrize("path", SAVED, ids=[f"{p.parent.name}/{p.stem}" for p in SAVED])
def test_english_only_text_gives_the_original_result(path):
    raw = RawOCRResult.load(path)
    for page in raw.pages:
        page.blocks = [b for b in page.blocks if not CJK.search(b.text)]
    assert _fields(extract_receipt_multilingual(raw)) == _fields(extract_receipt_general(raw))


def test_chinese_labels_same_block_and_beside():
    r = extract_receipt_multilingual(_raw([
        ["康寧診所"],
        ["收據編號：R-20391"],
        ["病人姓名", "陳大文"],
        ["主診醫生：黃志明"],
        ["註冊編號：M12345"],
        ["診症日期 2026年1月5日"],
        ["診金", "300.00"],
        ["合計", "HK$300.00"]]))
    assert (r.receipt_number, r.patient_name, r.doctor_name, r.registration_number, r.service_date,
            r.total_amount) == ("R-20391", "陳大文", "黃志明", "M12345", "2026-01-05", 300.0)


def test_simplified_chinese_labels():
    r = extract_receipt_multilingual(_raw([["收据编号：A-7781"], ["患者姓名：李小明"], ["合计", "¥120.00"]]))
    assert (r.receipt_number, r.patient_name, r.total_amount) == ("A-7781", "李小明", 120.0)


def test_bilingual_label_translation_is_not_the_value():
    r = extract_receipt_multilingual(_raw([["Patient 病人"], ["何美玲"], ["Receipt No. 收據編號:", "B-5502"]]))
    assert r.patient_name == "何美玲" and r.receipt_number == "B-5502"
    original = extract_receipt_general(_raw([["Patient 病人"], ["何美玲"]]))
    assert original.patient_name == "病人"  # the original rules read the translation as the name


def test_labels_are_not_values_and_need_a_boundary():
    r = extract_receipt_multilingual(_raw([["病人編號", "P-0091"], ["醫生簽名"], ["姓名", "地址"]]))
    assert r.patient_name is None and r.doctor_name is None  # 病人 ≠ 病人編號; 地址 is a form word
    assert M._person("病人") is None and M._person("陳大文") == "陳大文"


def test_chinese_date_format():
    assert parse_date("2026年6月9日") == ("2026-06-09", "chinese")
    assert parse_date("2026 年 12 月 1 日") == ("2026-12-01", "chinese")
    assert parse_date("2026年2月30日") is None
    assert parse_date("14/03/2026") == ("2026-03-14", "numeric")


def test_nothing_from_the_improved_rules():
    source = Path(M.__file__).read_text()
    assert "extraction_improved" not in source.split('"""', 2)[2]  # docstring may mention it; code may not
    for zh in M.ZH.values():  # every Chinese label belongs to one of the original English label groups
        assert zh and all(CJK.search(l) for l in zh)
