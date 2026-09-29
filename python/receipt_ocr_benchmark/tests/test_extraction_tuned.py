from receipt_bench.extraction_tuned import (
    clean_person_name,
    detect_layout,
    extract_receipt_tuned,
    parse_amount,
    parse_date,
    repair_lost_decimal,
)
from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult


def _block(text: str, x0: float, y0: float, x1: float, y1: float, conf: float = 0.99) -> OCRBlock:
    return OCRBlock(text=text, confidence=conf, polygon=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]])


def _raw(blocks: list[OCRBlock], width: int = 3000, height: int = 4000) -> RawOCRResult:
    return RawOCRResult(
        document_id="t",
        engine_config={},
        pages=[PageResult(page_number=1, width=width, height=height, blocks=blocks, plain_text="\n".join(b.text for b in blocks))],
        timings={"total_ms": 1.0},
    )


# --- OCR-repair helpers (observed in the real receipts) --------------------------------------


def test_amount_letter_digit_confusion_is_fixed_only_inside_amount_shapes():
    assert parse_amount("ZO.00") == (20.0, "ocr_fixed")
    assert parse_amount("HKD 1361.00") == (1361.0, "decimal")
    assert parse_amount("154000") == (154000.0, "integer")
    assert parse_amount("Paid by Visa") is None


def test_lost_decimal_is_repaired_only_when_a_peer_amount_confirms_it():
    assert repair_lost_decimal(154000.0, "integer", [1540.0]) == (1540.0, True)
    assert repair_lost_decimal(154000.0, "integer", [999.0]) == (154000.0, False)
    assert repair_lost_decimal(1540.0, "decimal", [15.4]) == (1540.0, False)


def test_handwritten_slash_read_as_one_is_repaired_in_dates():
    assert parse_date("07/0212026") == ("2026-02-07", "numeric_ocr_fixed_ambiguous")
    assert parse_date("07101/2026") == ("2026-01-07", "numeric_ocr_fixed_ambiguous")


def test_textual_date_variants():
    assert parse_date("Feb09,2023")[0] == "2023-02-09"
    assert parse_date("Printedon24March17")[0] == "2017-03-24"
    assert parse_date("24/03/17")[0] == "2017-03-24"


def test_person_name_cleanup():
    assert clean_person_name("Dr.Fung Ka Kit Paul") == "Dr. Fung Ka Kit Paul"
    assert clean_person_name("Tin Tin , Becky") == "Tin Tin, Becky"
    assert clean_person_name("Br.LokYi ehoi", snap_surnames=True) == "Dr. Lok Yi Choi"


# --- layout-specific (intentionally overfit) behaviour ---------------------------------------


def test_layout_detection():
    assert detect_layout("MEDICAL RECEIPT TEMPLATE ...") == "medical_template"
    assert detect_layout("Tung Chung Animal Clinic") == "vet_tung_chung"
    assert detect_layout("Some other clinic") == "unknown"


def test_medical_template_totals_box_values_above_labels_and_blank_total_falls_back_to_subtotal():
    raw = _raw([
        _block("MEDICAL RECEIPT TEMPLATE", 800, 600, 1600, 650),
        _block("Patient Carol Tse", 360, 1360, 700, 1410),
        _block("998.00", 1980, 2798, 2150, 2850),  # handwritten on the underline, above its label
        _block("SUBTOTAL", 1650, 2825, 1900, 2870),
        _block("TOTAL", 1660, 3150, 1800, 3195),  # left blank on the paper
        _block("0002JATOT", 840, 3130, 1100, 3180),  # mirrored show-through from the back page
    ])

    result = extract_receipt_tuned(raw)

    assert result.layout == "medical_template"
    assert result.patient_name == "Carol Tse"
    assert result.total_amount == 998.0
    assert "subtotal" in result.rules["total_amount"]
    assert result.receipt_number is None


def test_vet_merged_header_block_with_checkbox_glyphs_is_split():
    raw = _raw([
        _block("Tung Chung Animal Clinic", 460, 20, 900, 50),
        _block("Invoice No: 369303 FClinician: Angel Tseng FPatient: Fuk Jai", 38, 495, 800, 530),
        _block("Feb 09, 2023", 1020, 489, 1160, 525),
    ], width=1200, height=1600)

    result = extract_receipt_tuned(raw)

    assert result.receipt_number == "369303"
    assert result.patient_name == "Fuk Jai"
    assert result.doctor_name == "Angel Tseng"
    assert result.service_date == "2023-02-09"


def test_unknown_layout_falls_back_to_baseline_rules():
    raw = _raw([_block("Receipt No: R-00123", 10, 10, 300, 30)])

    result = extract_receipt_tuned(raw)

    assert result.layout == "unknown"
    assert result.receipt_number == "R-00123"
    assert "baseline" in result.rules["receipt_number"]
