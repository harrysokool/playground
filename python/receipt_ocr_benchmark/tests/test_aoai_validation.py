"""Checks on Azure OpenAI field values (improved DI + AOAI pipeline). Made-up names and numbers only."""

from receipt_bench.aoai_validation import check_total, clean_registration, strip_qualifications, validate


def test_trailing_qualifications_are_removed_from_doctor_names():
    assert strip_qualifications("Dr. Wong Mei Ling, BDS (HK)") == "Dr. Wong Mei Ling"
    assert strip_qualifications("Dr Chan Tai Man MBBS (HK), FHKAM (Medicine)") == "Dr Chan Tai Man"
    assert strip_qualifications("Dr. Ada Brown, BVSc (Hons) CVA") == "Dr. Ada Brown"
    assert strip_qualifications("Dr. Kwok Siu Fan, MChinMed") == "Dr. Kwok Siu Fan"


def test_names_that_only_look_unusual_are_kept():
    assert strip_qualifications("Lee Ka Yan, Becky") == "Lee Ka Yan, Becky"  # English name after a comma
    assert strip_qualifications("CHAN Siu Ming") == "CHAN Siu Ming"  # surname in capitals
    assert strip_qualifications("Dr. Ma Hoi") == "Dr. Ma Hoi"  # "Ma" is a surname, not "MA"
    assert strip_qualifications("陳大文") == "陳大文"
    for surname in ("Hong", "Mak", "MAK", "BAKER", "Dipak", "MA"):  # never mistaken for a qualification
        assert strip_qualifications(f"Dr. Lee {surname}") == f"Dr. Lee {surname}"


def test_registration_number_keeps_only_the_identifier():
    assert clean_registration("MBBS (HK) · Reg. No. A12345") == ("A12345", "registration_number: kept identifier "
                                                                "'A12345' from 'MBBS (HK) · Reg. No. A12345'")
    assert clean_registration("註冊編號: 004567")[0] == "004567"
    assert clean_registration("PT001234") == ("PT001234", None)  # already an identifier: untouched
    value, warning = clean_registration("A123 / B456")
    assert value == "A123 / B456" and "not a single identifier" in warning


def test_total_that_matches_a_subtotal_is_flagged():
    text = "Sub Total | HKD 820.50\nRound Down | (+) -0.50\nTotal Amount | HKD 820.00\nPayment received | 820.00"
    assert "subtotal" in check_total(820.5, text)
    assert check_total(820.0, text) is None


def test_payments_that_differ_from_the_total_are_not_flagged():
    copay = "Total | 900.00\nCovered by plan | 800.00\nCo-payment paid (cash) | 100.00"
    assert check_total(900.0, copay) is None  # co-payments and insurer settlements are normal
    assert check_total(None, copay) is None


def test_validate_cleans_values_and_lists_fields_to_review():
    text = "Dr. Wong Mei Ling, BDS (HK) | Reg. No. D01234\nPatient | Lee Ka Yan\nTotal | 500.00"
    fields = {"doctor_name": "Dr. Wong Mei Ling, BDS (HK)", "registration_number": "Reg. No. D01234",
              "patient_name": "Lee Ka Yan", "receipt_number": "R-999", "service_date": "2026-01-02",
              "total_amount": 500.0}
    out, warnings, review = validate(fields, text, ["service_date"])
    assert out["doctor_name"] == "Dr. Wong Mei Ling" and out["registration_number"] == "D01234"
    assert out["patient_name"] == "Lee Ka Yan" and out["total_amount"] == 500.0
    assert review == ["receipt_number", "service_date"]  # R-999 is not in the text; the model was unsure
    assert any("not found in the OCR text" in w for w in warnings)


def test_validate_handles_several_practitioners_and_flags_clinic_names():
    text = "Clinician: Amy Lo | Signed: Dr. Ben Ho, MBBS\nDr Carl Yu Harbour Medical Centre"
    out, _, review = validate({"doctor_name": "Amy Lo; Dr. Ben Ho, MBBS"}, text)
    assert out["doctor_name"] == "Amy Lo; Dr. Ben Ho" and review == []
    out, warnings, review = validate({"doctor_name": "Dr Carl Yu Harbour Medical Centre"}, text)
    assert out["doctor_name"] == "Dr Carl Yu Harbour Medical Centre"  # flagged, not rewritten
    assert review == ["doctor_name"] and any("clinic or hospital" in w for w in warnings)
