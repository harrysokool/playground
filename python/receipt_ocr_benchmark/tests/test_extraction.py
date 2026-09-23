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


# --- explicit "label: value" blocks -----------------------------------------------------


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


def test_registration_number_label_with_trailing_period():
    # "Reg No." (period right after "No") is a real formatting variant, not just "Reg No:".
    raw = _raw("reg_period", [_block("Reg No. M12345", 10, 10, 300, 30, 0)])

    result = extract_receipt(raw)

    assert result.registration_number == "M12345"


def test_receipt_number_bill_no_label():
    raw = _raw("bill_no", [_block("Bill No: B-556", 10, 10, 300, 30, 0)])

    result = extract_receipt(raw)

    assert result.receipt_number == "B-556"


def test_service_date_alternate_labels():
    raw = _raw(
        "alt_date_labels",
        [
            _block("Consultation Date: 2026-09-20", 10, 10, 300, 30, 0),
            _block("Visit Date: 21 Sep 2026", 10, 40, 300, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    # "consultation date" and "visit date" are both listed labels with no priority between
    # them, so whichever appears first in reading order wins - here, the consultation date.
    assert result.service_date == "2026-09-20"


# --- label alone in its block, value found via OCR coordinates --------------------------


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
    assert result.sources["patient_name"] == "Patient Name | John Doe"


def test_extracts_value_from_closest_block_below_when_no_same_line_block():
    raw = _raw(
        "nearby_below",
        [
            _block("Registration No", 10, 10, 150, 30, 0),
            _block("REG-9988", 10, 40, 150, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.registration_number == "REG-9988"


# --- unlabeled values recognized by shape alone (fallback) ------------------------------


def test_doctor_name_recognized_without_any_label():
    raw = _raw("unlabeled_doctor", [_block("Dr Chan", 10, 10, 150, 30, 0)])

    result = extract_receipt(raw)

    assert result.doctor_name == "Dr Chan"


def test_doctor_name_with_comma_in_a_lastname_firstname_format():
    # Real example: "Dr. Lau Sat Kit, Lawrence" (lastname-first, comma-separated).
    raw = _raw("comma_name", [_block("Dr. Lau Sat Kit, Lawrence", 10, 10, 300, 30, 0)])

    result = extract_receipt(raw)

    assert result.doctor_name == "Dr. Lau Sat Kit, Lawrence"


def test_doctor_name_recognized_from_chinese_title_suffix():
    # Chinese medical titles suffix the name ("醫生" = doctor) instead of prefixing it.
    raw = _raw("cjk_doctor", [_block("李俊年醫生", 10, 10, 150, 30, 0)])

    result = extract_receipt(raw)

    assert result.doctor_name == "李俊年醫生"


def test_registration_number_recognized_without_any_label():
    raw = _raw(
        "unlabeled_reg",
        [_block("City Medical Clinic", 10, 10, 300, 30, 0), _block("M12345", 10, 40, 150, 60, 1)],
    )

    result = extract_receipt(raw)

    assert result.registration_number == "M12345"


# --- total vs. subtotal / weaker labels --------------------------------------------------


def test_subtotal_is_never_mistaken_for_total():
    raw = _raw(
        "subtotal_trap",
        [
            _block("Subtotal: $90.00", 10, 10, 300, 30, 0),
            _block("Total: $99.00", 10, 40, 300, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.total_amount == 99.00


def test_grand_total_wins_over_plain_total_regardless_of_order():
    raw = _raw(
        "grand_total_anywhere",
        [
            _block("Total: $100.00", 10, 10, 300, 30, 0),
            _block("Grand Total: $120.00", 10, 40, 300, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.total_amount == 120.00


def test_total_outranks_amount_due():
    # "Amount Due" is the outstanding *balance*, not the invoice total - a real receipt in
    # the phase-3 sample set showed "Total Due: HKD 0.00" (fully paid) alongside a separate,
    # much larger "Total Amount: HKD 1361.00" elsewhere on the same page. "Total"/"Total
    # Amount" is ranked higher for that reason, not lower.
    raw = _raw(
        "amount_due",
        [
            _block("Total: $75.00", 10, 10, 300, 30, 0),
            _block("Amount Due: $0.00", 10, 40, 300, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.total_amount == 75.00


def test_table_header_total_is_not_mistaken_for_the_grand_total():
    # A bare "Total" column header sharing its row with other headers (as in a line-items
    # table) is skipped; the rule keeps looking rather than grabbing whatever sits below it.
    raw = _raw(
        "header_row",
        [
            _block("DESCRIPTION", 10, 10, 100, 30, 0),
            _block("QTY", 120, 10, 160, 30, 1),
            _block("RATE", 180, 10, 220, 30, 2),
            _block("TOTAL", 240, 10, 280, 30, 3),
            _block("water", 10, 40, 100, 60, 4),
            _block("1", 120, 40, 160, 60, 5),
            _block("Grand Total: $42.00", 10, 200, 300, 220, 6),
        ],
    )

    result = extract_receipt(raw)

    assert result.total_amount == 42.00


# --- guardrails: fail closed rather than guess wrong -------------------------------------


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


def test_paid_label_without_a_parseable_amount_does_not_guess():
    # "Paid" is the weakest total indicator and easily attaches to non-amount text
    # (e.g. a payment method note); the OCR text is correct, but there's nothing to extract.
    raw = _raw("paid_no_amount", [_block("Paid by Visa", 10, 10, 300, 30, 0)])

    result = extract_receipt(raw)

    assert result.total_amount is None
    assert any("total_amount" in w for w in result.warnings)


def test_bare_name_label_does_not_leak_a_doctors_name_into_patient_name():
    # "Name" (with no "Patient"/"Doctor" qualifier) is ambiguous. If the nearest value looks
    # like a doctor's name, it's rejected rather than guessed as the patient's.
    raw = _raw(
        "ambiguous_name",
        [
            _block("Name", 10, 10, 150, 30, 0),
            _block("Dr Chan", 200, 10, 300, 30, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.patient_name is None
    assert any("patient_name" in w for w in result.warnings)


def test_nearby_value_containing_digits_is_rejected_for_name_fields():
    # Real example: a blank "Patient" field's nearest block below was "HospitalNo 12JS678910"
    # (an unrelated record number) - a name should never contain digits, so it's rejected
    # rather than reported as the patient's name.
    raw = _raw(
        "blank_patient_field",
        [
            _block("Patient", 10, 10, 150, 30, 0),
            _block("HospitalNo 12JS678910", 10, 40, 300, 60, 1),
        ],
    )

    result = extract_receipt(raw)

    assert result.patient_name is None
    assert any("patient_name" in w for w in result.warnings)


def test_label_word_appearing_lowercase_mid_sentence_is_not_treated_as_a_label():
    # Real example: a notes block "patient B cverely injurel" (OCR noise for "severely
    # injured") was previously mistaken for the "Patient" label because it starts with the
    # word "patient" - but real form labels are capitalized, so a lowercase match is skipped.
    raw = _raw("prose_not_label", [_block("patient B cverely injurel", 10, 10, 300, 30, 0)])

    result = extract_receipt(raw)

    assert result.patient_name is None


def test_receipt_number_keeps_only_the_first_token_when_the_value_runs_on():
    # Real example: OCR merged three "label: value" pairs from one visual line into a single
    # block: "Invoice No: 369303 FClinician: Angel Tseng FPatient: Fuk Jai". Only the first
    # token of the remainder is kept for code-like fields, since a receipt number is a single
    # token and everything after it is unrelated text bleeding in from the merge.
    raw = _raw(
        "merged_block",
        [_block("Invoice No: 369303 FClinician: Angel Tseng FPatient: Fuk Jai", 10, 10, 600, 30, 0)],
    )

    result = extract_receipt(raw)

    assert result.receipt_number == "369303"
