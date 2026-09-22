from receipt_bench.extraction import extract_receipt
from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult


def _block(text: str, x0: float, y0: float, x1: float, y1: float, order: int) -> OCRBlock:
    return OCRBlock(
        text=text,
        confidence=0.99,
        polygon=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
        reading_order=order,
    )


def _raw(document_id: str, blocks: list[OCRBlock]) -> RawOCRResult:
    return RawOCRResult(
        document_id=document_id,
        engine_config={"engine_config_name": "paddle_light"},
        pages=[PageResult(page_number=1, width=600, height=400, blocks=blocks, plain_text="")],
        timings={"total_ms": 1.0},
    )


def test_extracts_same_block_label_value_pairs():
    raw = _raw(
        "same_block",
        [
            _block("Doctor Name: Dr. Jane Smith", 10, 10, 300, 30, 0),
            _block("Patient: John Doe", 10, 40, 300, 60, 1),
            _block("Receipt No: R-00123", 10, 70, 300, 90, 2),
            _block("Service Date: 2026-09-20", 10, 100, 300, 120, 3),
            _block("Total: $150.00", 10, 130, 300, 150, 4),
        ],
    )

    result = extract_receipt(raw)

    assert result.doctor_name == "Dr. Jane Smith"
    assert result.patient_name == "John Doe"
    assert result.receipt_number == "R-00123"
    assert result.service_date == "2026-09-20"
    assert result.total_amount == 150.00
    assert result.sources["total_amount"] == "Total: $150.00"


def test_extracts_value_from_nearby_block_to_the_right():
    raw = _raw(
        "nearby_right",
        [
            _block("Patient Name", 10, 10, 150, 30, 0),
            _block("John Doe", 200, 10, 300, 30, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.patient_name == "John Doe"
    assert "Patient Name | John Doe" == result.sources["patient_name"]


def test_extracts_value_from_next_block_below_when_no_same_line_block():
    raw = _raw(
        "nearby_below",
        [
            _block("Registration No", 10, 10, 150, 30, 0),
            _block("REG-9988", 10, 40, 150, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.registration_number == "REG-9988"


def test_first_total_label_in_reading_order_wins_even_if_not_grand_total():
    # Documents a known limitation: when both "Total" and "Grand Total" appear (e.g. a
    # subtotal-style "Total" before the real "Grand Total"), the rule picks whichever is
    # first in reading order, not necessarily the more authoritative figure.
    raw = _raw(
        "grand_total",
        [
            _block("Total: $100.00", 10, 10, 300, 30, 0),
            _block("Grand Total: $120.00", 10, 40, 300, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.total_amount == 100.00


def test_subtotal_is_not_mistaken_for_total():
    raw = _raw(
        "subtotal_trap",
        [
            _block("Subtotal: $90.00", 10, 10, 300, 30, 0),
            _block("Total: $99.00", 10, 40, 300, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.total_amount == 99.00


def test_missing_fields_produce_warnings_not_guesses():
    raw = _raw("blank", [_block("Some Clinic", 10, 10, 300, 30, 0)])

    result = extract_receipt(raw)

    assert result.doctor_name is None
    assert result.total_amount is None
    assert any("total_amount" in w for w in result.warnings)
    assert any("doctor_name" in w for w in result.warnings)


def test_unparseable_date_is_kept_as_is_with_a_warning():
    raw = _raw("odd_date", [_block("Service Date: twenty-sixth of Sept", 10, 10, 300, 30, 0)])

    result = extract_receipt(raw)

    assert result.service_date == "twenty-sixth of Sept"
    assert any("service_date" in w for w in result.warnings)
