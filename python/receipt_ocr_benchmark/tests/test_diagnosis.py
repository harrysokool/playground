"""Diagnosis comment detection: rules on synthetic layouts and on the saved OCR (offline), and its
separate scorer. No OCR engine, no Azure calls."""

import json
from pathlib import Path

import pytest

from receipt_bench import diagnosis, diagnosis_cli
from receipt_bench.diagnosis import detect_diagnosis, judge, parse_label
from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "diagnosis"
CASES = json.loads((DATA / "mock_cases.json").read_text())["cases"]
GT = diagnosis_cli.load_ground_truth(DATA / "ground_truth.csv")

HEADER = [["Sunrise Family Clinic"], ["Receipt No.:", "R-1001"], ["Date:", "01/02/2026"],
          ["Patient:", "Test Patient"], ["Doctor:", "Dr. Test Doctor"]]
ITEMS = [["Consultation", "300.00"], ["Medication", "100.00"], ["Total", "HK$400.00"]]


def _raw(rows, doc="mock"):
    """Rows of side-by-side blocks -> raw OCR: 30 px high lines, 40 px between blocks on a row."""
    blocks = []
    for i, row in enumerate(rows):
        x, y = 50, 40 + i * 50
        for text in row:
            w = len(text) * 12
            blocks.append(OCRBlock(text, 0.95, [[x, y], [x + w, y], [x + w, y + 30], [x, y + 30]], len(blocks)))
            x += w + 40
    page = PageResult(1, 1000, 1400, blocks, "\n".join(b.text for b in blocks))
    return RawOCRResult(doc, {}, [page], {})


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_mock_cases(case):
    rows = case["rows"] if case.get("bare") else HEADER + case["rows"] + ITEMS
    result = detect_diagnosis(_raw(rows))
    assert result.status == case.get("rules_expected", case["expected"]), (result.reason, result.evidence)


def test_mock_cases_cover_the_requested_situations():
    ids = {c["id"] for c in CASES}
    assert {"zh_label_same_block", "en_label_value_beside", "empty_label", "medical_note_en", "admin_remark_en",
            "unreadable_page"} <= ids
    assert {c["expected"] for c in CASES} == {"present", "missing", "needs_review"}


@pytest.mark.parametrize("engine", ["paddle_light", "azure_di"])
def test_saved_version2_ocr_matches_ground_truth(engine):
    # Same logic for both engines, on the OCR saved by the benchmark runs.
    for (s, receipt), row in GT.items():
        if s != "v2":
            continue
        result = detect_diagnosis(RawOCRResult.load(ROOT / "results" / "v2" / engine / f"{receipt}.json"))
        assert result.status == row["diagnosis_comment"], (engine, receipt, result.reason, result.evidence)


def test_blank_ocr_page_is_needs_review_not_missing():
    # PaddleOCR Heavy read nothing on Version 2 receipt5 (discontinued engine; saved output only).
    result = detect_diagnosis(RawOCRResult.load(ROOT / "results" / "v2" / "paddle_heavy" / "receipt5.json"))
    assert result.status == "needs_review" and "too little OCR text" in result.reason


def test_labels():
    assert parse_label("Diagnosis: Colds")[:2] == ("strong", "diagnosis")
    assert parse_label("DIAGNOSIS 診斷：感冒") == ("strong", "diagnosis", "感冒")
    assert parse_label("NOTES:") == ("weak", "notes", "")
    assert parse_label("症狀 咳嗽") == ("strong", "症狀", "咳嗽")
    assert parse_label("Name: A  Dx: B")[2] == "B"
    for not_a_label in ("Please Note. We are open", "Treatment: massage", "診症日期: 2026年6月9日", "Diagnostic imaging",
                        "Conditions apply", "Name: A  Notes: B", "Diagnosis code 123"):
        assert parse_label(not_a_label) is None, not_a_label


def test_judge():
    assert judge("strong", " - ")[0] == "missing"
    assert judge("strong", "無")[0] == "missing"
    assert judge("strong", "x")[0] == "needs_review"
    assert judge("strong", "URTI")[0] == "present"
    assert judge("weak", "sprained wrist")[0] == "present"
    assert judge("weak", "Please keep this receipt")[0] == "missing"
    assert judge("weak", "see attached letter")[0] == "needs_review"


def test_rules_contain_no_benchmark_answers():
    # General rules only: no ground-truth comment of any receipt may appear in the rule code.
    source = Path(diagnosis.__file__).read_text().lower()
    values = {part.split(":", 1)[-1].strip().lower() for r in GT.values() for part in r["evidence"].split(";")}
    values = {v for v in values if len(v) >= 4}
    assert values and not [v for v in values if v in source]


# --- scoring --------------------------------------------------------------------------------


def _write(directory, receipt, record):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{receipt}.json").write_text(json.dumps(record))


def test_scoring_outcomes_and_formats(tmp_path):
    gt = {("v2", "r1"): {"diagnosis_comment": "present"}, ("v2", "r2"): {"diagnosis_comment": "missing"},
          ("v2", "r3"): {"diagnosis_comment": "missing"}, ("v2", "r4"): {"diagnosis_comment": "present"},
          ("v2", "r5"): {"diagnosis_comment": "present"}, ("v1", "r1"): {"diagnosis_comment": "missing"}}
    d = tmp_path / "v2"
    _write(d, "r1", {"document_id": "r1", "diagnosis": {"status": "present", "evidence": []}})  # rules format
    _write(d, "r2", {"status": "ok", "doctor_name": None, "diagnosis": {"status": "present", "evidence": "x"}})  # AOAI
    _write(d, "r3", {"status": "ok", "diagnosis": {"status": "needs_review", "evidence": None}})
    _write(d, "r4", {"status": "error", "error_stage": "aoai"})  # failed run
    _write(d, "r9", {"diagnosis": {"status": "present"}})  # no ground-truth row: ignored
    # r5: no file
    _write(tmp_path / "v1", "r1", {"diagnosis": {"status": "missing", "evidence": []}})
    summary, detail = diagnosis_cli.score(gt, [("a", "v2", d), ("a", "v1", tmp_path / "v1")])
    assert summary == [{"approach": "a", "sets": "v2+v1", "receipts": 6, "correct": 2, "needs_review": 1,
                        "false_missing": 0, "false_present": 1, "no_result": 2, "accuracy_pct": 33.3}]
    diagnosis_cli.write_outputs(summary, detail, tmp_path / "out")
    report = (tmp_path / "out" / "report.md").read_text()
    assert "| v2 | r2 | missing | present (false_present) |" in report


def test_diagnosis_output_does_not_change_six_field_scoring(tmp_path):
    from receipt_bench.score import read_result
    fields, _ = read_result({"document_id": "r1", "diagnosis": {"status": "present"}})
    assert fields is None  # a rules diagnosis file is not a six-field result
