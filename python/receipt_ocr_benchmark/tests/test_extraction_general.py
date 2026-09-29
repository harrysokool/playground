"""General rules must work on synthetic layouts unrelated to the 6 sample receipts."""

from receipt_bench.extraction_general import extract_receipt_general
from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult


def _block(text: str, x0: float, y0: float, x1: float, y1: float, conf: float = 0.99) -> OCRBlock:
    return OCRBlock(text=text, confidence=conf, polygon=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]])


def _raw(blocks: list[OCRBlock]) -> RawOCRResult:
    return RawOCRResult(
        document_id="t",
        engine_config={},
        pages=[PageResult(page_number=1, width=1000, height=1400, blocks=blocks, plain_text="")],
        timings={"total_ms": 5.0},
    )


def test_labelled_fields_on_a_generic_printed_receipt():
    raw = _raw([
        _block("Receipt No: RC-20931", 50, 50, 400, 80),
        _block("Physician: Dr. Maria Gomez", 50, 100, 450, 130),
        _block("Patient Name", 50, 150, 200, 180),
        _block("John Smith", 260, 150, 420, 180),
        _block("Date of Service: 15 Aug 2025", 50, 200, 450, 230),
        _block("Subtotal", 600, 600, 720, 630),
        _block("$90.00", 800, 600, 900, 630),
        _block("GST", 600, 650, 680, 680),
        _block("$9.00", 800, 650, 900, 680),
        _block("Total", 600, 700, 680, 730),
        _block("$99.00", 800, 700, 900, 730),
        _block("Amount Due", 600, 750, 740, 780),
        _block("$0.00", 800, 750, 900, 780),
    ])

    r = extract_receipt_general(raw)

    assert r.receipt_number == "RC-20931"
    assert r.doctor_name == "Dr. Maria Gomez"
    assert r.patient_name == "John Smith"
    assert r.service_date == "2025-08-15"
    assert r.total_amount == 99.0  # the balance "Amount Due 0.00" is not the total
    assert r.timings["ocr_predict_ms"] == 5.0


def test_fail_closed_when_nearest_value_has_wrong_shape():
    raw = _raw([
        _block("Patient", 50, 50, 150, 80),
        _block("ID 0042 7781", 50, 90, 250, 120),  # nearest block below is not a name
        _block("Some Person", 50, 300, 250, 330),  # further away - must NOT be taken
    ])

    r = extract_receipt_general(raw)

    assert r.patient_name is None
    assert any("patient_name" in w for w in r.warnings)


def test_column_header_is_not_a_label_value_pair():
    raw = _raw([_block("Patient Price", 700, 50, 950, 80)])

    assert extract_receipt_general(raw).patient_name is None


def test_unlabelled_total_from_column_sum_and_merged_labels_split():
    raw = _raw([
        _block("Invoice No: 5521 Doctor: Dr. Ann Lee", 50, 50, 600, 80),
        _block("$12.50", 800, 200, 900, 230),
        _block("$7.50", 800, 240, 900, 270),
        _block("$20.00", 800, 280, 900, 310),
    ])

    r = extract_receipt_general(raw)

    assert r.receipt_number == "5521"
    assert r.doctor_name == "Dr. Ann Lee"
    assert r.total_amount == 20.0


def test_two_different_unlabelled_doctors_is_ambiguous_not_guessed():
    raw = _raw([_block("Dr. Ann Lee", 50, 50, 300, 80), _block("Dr. Bob Wu", 50, 500, 300, 530)])

    r = extract_receipt_general(raw)

    assert r.doctor_name is None
    assert any("different doctor candidates" in w for w in r.warnings)
