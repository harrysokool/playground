"""Improved rules (Phase 10) on synthetic layouts - not copies of the benchmark receipts.
Run on Azure ML: python -m pytest -q tests/test_extraction_improved.py"""

import json

from receipt_bench.extraction_general import extract_receipt_general
from receipt_bench.extraction_improved import amount, classify, extract_receipt_improved, person, to_date
from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult
from receipt_bench.score import read_result


def _block(text, x0, y0, x1, y1, conf=0.99):
    return OCRBlock(text=text, confidence=conf, polygon=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]])


def _raw(blocks):
    return RawOCRResult(document_id="t", engine_config={},
                        pages=[PageResult(page_number=1, width=1000, height=1400, blocks=blocks, plain_text="")],
                        timings={"total_ms": 5.0})


def _row(y, *cells):
    """Blocks on one line: (text, x0, x1) cells."""
    return [_block(t, x0, y, x1, y + 30) for t, x0, x1 in cells]


# --- label classification ------------------------------------------------------------------------

def test_bilingual_label_translation_is_stripped():
    lab = classify("Patient 病人:")
    assert (lab.kind, lab.rest) == ("patient", "")
    assert classify("Receipt No. 收據編號:AB-12345").rest == "AB-12345"


def test_ocr_glued_and_simplified_labels_are_recognised():
    assert classify("Patient病人：").kind == "patient"
    assert classify("TreatmentDate治療日期：").kind == "service_date"
    assert classify("Receipt No.收據编號:XY-777").rest == "XY-777"  # simplified 编 in the label
    assert classify("Receipt No.收據編：XY-777").rest == "XY-777"  # OCR dropped a character


def test_longest_label_wins_so_distractors_are_not_fields():
    assert classify("Patient No. 病人編號").kind == "x_id"
    assert classify("Client No.").kind == "x_id"
    assert classify("Date Issued 1 Aug 2026").kind == "x_date"
    assert classify("Next Appointment 8 Aug 2026").kind == "x_date"
    assert classify("Total Due: HKD 0.00").kind == "x_balance"
    assert classify("Less: Paid by insurer (direct billing)").kind == "x_part_paid"
    assert classify("Referred by").kind == "x_person"


def test_chinese_labels():
    assert classify("病人姓名").kind == "patient"
    assert classify("主診中醫師").kind == "doctor"
    assert classify("收據編號：Q123456").rest == "Q123456"
    assert classify("覆診日期:2026年5月2日").kind == "x_date"
    assert classify("合計").kind == "total"


# --- value shapes ----------------------------------------------------------------------------------

def test_values():
    assert to_date("2025年11月3日") == "2025-11-03"
    assert to_date("2025年2月30日") is None
    assert to_date("3 Nov 2025") == "2025-11-03"
    assert amount("港幣 $790.00") == (790.0, "decimal")
    assert amount("HKS1,880.00")[0] == 1880.0  # OCR read "$" as "S"
    assert amount("Visa ending 4421") is None
    assert person("Dr. Wong Mei Ling, MBBS (HK), FHKAM") == "Dr. Wong Mei Ling"
    assert person("Lee Tin Tin, Becky") == "Lee Tin Tin, Becky"  # not a degree: kept
    assert person("病人") is None  # a label is never a name


# --- whole receipts ----------------------------------------------------------------------------------

BILINGUAL = (
    _row(100, ("Invoice No. 發票編號", 50, 300), ("ZX-2025-001", 350, 550), ("Invoice Date 發票日期", 600, 800),
         ("9 Jan 2025", 850, 980))
    + _row(150, ("Patient 病人", 50, 300), ("CHAN SIU KEI", 350, 550), ("Patient No. 病人編號", 600, 800),
           ("PN-4410", 850, 980))
    + _row(200, ("Attendance Date 就診日期", 50, 300), ("2 Jan 2025", 350, 550))
    + _row(250, ("Attending Doctor 主診醫生", 50, 300), ("Dr. Lau Ka Ming", 350, 550))
    + _row(300, ("MBBS (HK) · Reg. No. M54321", 50, 500))
    + _row(400, ("Subtotal 小計", 600, 800), ("1,000.00", 850, 980))
    + _row(450, ("Discount 折扣", 600, 800), ("-100.00", 850, 980))
    + _row(500, ("Total Charges 總收費", 600, 800), ("900.00", 850, 980))
    + _row(550, ("Less: Paid by insurer 保險公司直接付款", 500, 800), ("(700.00)", 850, 980))
    + _row(600, ("Balance Due 尚欠餘額", 600, 800), ("200.00", 850, 980))
)


def test_bilingual_invoice_with_distractors():
    r = extract_receipt_improved(_raw(BILINGUAL))
    assert r.receipt_number == "ZX-2025-001"
    assert r.patient_name == "CHAN SIU KEI"
    assert r.service_date == "2025-01-02"  # not the invoice date
    assert r.doctor_name == "Dr. Lau Ka Ming"
    assert r.registration_number == "M54321"  # inside a line
    assert r.total_amount == 900.0  # not subtotal, insurer payment or balance


def test_original_rules_are_unchanged_on_the_same_layout():
    r = extract_receipt_general(_raw(BILINGUAL))
    assert r.patient_name == "病人"  # the known original failure, kept for comparison


CHINESE = (
    _row(100, ("收據編號：Q123456", 600, 950))
    + _row(150, ("病人姓名", 50, 250), ("陳美玲", 300, 500))
    + _row(200, ("診症日期", 50, 250), ("2025年3月14日", 300, 500))
    + _row(250, ("主診中醫師", 50, 250), ("何志強", 300, 500))
    + _row(300, ("註冊中醫編號", 50, 250), ("004512", 300, 500))
    + _row(400, ("合計", 50, 250), ("港幣 $560.00", 300, 500))
    + _row(450, ("覆診日期:2025年3月21日", 50, 500))
)


def test_chinese_only_receipt():
    r = extract_receipt_improved(_raw(CHINESE))
    assert (r.patient_name, r.doctor_name, r.registration_number) == ("陳美玲", "何志強", "004512")
    assert (r.receipt_number, r.service_date, r.total_amount) == ("Q123456", "2025-03-14", 560.0)


CARDS = (
    _row(100, ("CLIENT", 50, 200), ("THERAPIST", 500, 700))
    + _row(150, ("Name", 50, 150), ("Ng Wing Sze", 200, 400), ("Name", 500, 600), ("FONG Ka Chun", 650, 850))
    + _row(200, ("Referred by", 50, 180), ("Dr. Yip Tak Ming", 200, 400))
    + _row(300, ("Date Issued 5 Mar 2025", 50, 400), ("Session Date 4 Mar 2025", 500, 900))
    + _row(400, ("Total", 50, 150), ("Amount Paid", 350, 500), ("Outstanding Balance", 650, 900))
    + _row(450, ("HK$800.00", 50, 200), ("HK$300.00", 350, 500), ("HK$500.00", 650, 800))
)


def test_card_layout_header_name_rows_dates_and_total():
    r = extract_receipt_improved(_raw(CARDS))
    assert r.patient_name == "Ng Wing Sze"
    assert r.doctor_name == "FONG Ka Chun"  # not the referring doctor
    assert r.service_date == "2025-03-04"  # session date, not the issue date
    assert r.total_amount == 800.0  # not the paid amount or the balance


def test_total_from_subtotal_minus_discount_when_no_total_label():
    blocks = (_row(100, ("Subtotal", 600, 800), ("500.00", 850, 980))
              + _row(150, ("Member discount 10%", 600, 800), ("-50.00", 850, 980)))
    assert extract_receipt_improved(_raw(blocks)).total_amount == 450.0


def test_output_is_scoring_compatible(tmp_path):
    r = extract_receipt_improved(_raw(CHINESE))
    r.timings["extract_ms"] = 2.0
    r.save(tmp_path / "receipt1.json")
    fields, ms = read_result(json.loads((tmp_path / "receipt1.json").read_text()))
    assert fields["patient_name"] == "陳美玲" and ms == 7.0
