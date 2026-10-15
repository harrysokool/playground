import csv
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import pytest

from receipt_bench import score
from receipt_bench.score import FIELDS, load_ground_truth, matches, read_result, score_approach

REAL_GT = Path(__file__).resolve().parents[1] / "data" / "ground_truth" / "ground_truth_template.xlsx"
HEADER = ["receipt_id"] + FIELDS


def _write_xlsx(path: Path, rows: list[list[str]]) -> Path:
    """Minimal one-sheet workbook ("Ground Truth") with inline-string cells."""
    def cell(ref, v):
        return f'<c r="{ref}" t="inlineStr"><is><t>{v}</t></is></c>'

    xml_rows = "".join(
        f'<row r="{i}">' + "".join(cell(f"{chr(65 + j)}{i}", v) for j, v in enumerate(r)) + "</row>"
        for i, r in enumerate(rows, 1)
    )
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel_ns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {ns} {rel_ns}><sheets><sheet name="Ground Truth" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData>{xml_rows}</sheetData></worksheet>")
    return path


def _gt(**overrides):
    values = {"doctor_name": "Dr. Lau Sai Kit", "registration_number": None, "patient_name": "Carol Tse",
              "receipt_number": None, "service_date": "2026-02-07", "total_amount": "1540"}
    return {"receipt1": {**values, **overrides}}


# --- ground truth ---------------------------------------------------------------------------


def test_real_ground_truth_has_verified_corrections_and_iso_dates():
    gt = load_ground_truth(REAL_GT)
    assert sorted(gt) == [f"receipt{i}" for i in range(1, 7)]
    assert gt["receipt3"]["doctor_name"] == "Lee Tin Tin, Becky"
    assert gt["receipt2"]["patient_name"] == "Carol Tse"
    assert gt["receipt1"]["registration_number"] is None  # "na"
    for rec in gt.values():
        date.fromisoformat(rec["service_date"])


def test_ground_truth_rejects_excel_serial_dates(tmp_path):
    path = _write_xlsx(tmp_path / "gt.xlsx", [HEADER, ["r1", "Dr A", "na", "na", "na", "46205", "10"]])
    with pytest.raises(ValueError, match="ISO"):
        load_ground_truth(path)


# --- normalization --------------------------------------------------------------------------


def test_dates_compare_by_meaning_without_day_month_swap():
    assert matches("service_date", "2026-02-07", "2026-02-07")
    assert matches("service_date", "2026-02-07", "07/02/2026")  # non-ISO prediction read day-first
    assert not matches("service_date", "2026-02-07", "2026-07-02")  # swapped day/month is wrong


def test_traditional_chinese_dates_are_read_by_the_scorer():
    assert matches("service_date", "2026-06-09", "2026年6月9日")
    assert matches("service_date", "2026-06-09", "診症日期：2026年 6月 9日")
    assert not matches("service_date", "2026-06-09", "2026年9月6日")
    assert not matches("service_date", "2026-06-09", "2026年2月30日")  # invalid date is wrong, not a crash


def test_names_and_amounts_use_simple_normalization():
    assert matches("doctor_name", "Dr Jessica Sterenborg", "Dr. Jessica  Sterenborg")
    assert matches("doctor_name", "李俊年", "李俊年醫生")
    assert matches("total_amount", "1540", "1,540.00")
    assert matches("total_amount", "51.2", 51.2)
    assert not matches("total_amount", "10", "-")


def test_several_people_must_all_be_named_in_any_order():
    gt = "Amy Lo, Ben Ho"
    for pred in ("Amy Lo, Ben Ho", "Ben Ho, Amy Lo", "Amy Lo; Dr. Ben Ho", "Dr Ben Ho and Amy Lo", "Amy Lo & Ben Ho",
                 "Amy Lo / Ben Ho"):
        assert matches("doctor_name", gt, pred), pred
    for pred in ("Amy Lo", "Ben Ho", "Amy Lo, Ben Ho, Carl Yu", "Amy Lo, Carl Yu", "Amy Lo, Dr. Ben Hon"):
        assert not matches("doctor_name", gt, pred), pred


def test_single_names_score_as_before():
    assert matches("doctor_name", "Lee Ka Yan, Becky", "Lee Ka Yan, Becky")  # one person with an English name
    assert matches("doctor_name", "Lee Ka Yan, Becky", "Lee Ka Yan Becky")  # whole-string match still counts
    assert not matches("doctor_name", "Lee Ka Yan, Becky", "Lee Ka Yan")
    assert not matches("doctor_name", "Dr. Wong Mei Ling", "Dr. Wong Mei Ling, BDS (HK)")  # extra text is wrong
    assert not matches("doctor_name", "Dr. Wong Mei Ling", "Dr. Wong Mei Ling; Dr. Carl Yu")


# --- marking --------------------------------------------------------------------------------


def _result(**fields):
    return {f: fields.get(f) for f in FIELDS}, None


def test_missing_value_counts_as_wrong():
    s = score_approach(_gt(), {"receipt1": _result(doctor_name="Dr. Lau Sai Kit", total_amount=1540.0, service_date="2026-02-07")})
    marks = {r["field"]: r["result"] for r in s["detail"]}
    assert marks["patient_name"] == "Wrong"
    assert (s["correct"], s["applicable"], s["accuracy_pct"]) == (3, 4, 75.0)


def test_wrong_value_counts_as_wrong():
    s = score_approach(_gt(), {"receipt1": _result(total_amount=1500.0)})
    assert s["fields"]["total_amount"] == {"correct": 0, "applicable": 1, "invented": 0, "accuracy_pct": 0.0}


def test_invented_value_is_reported_separately_and_excluded_from_accuracy():
    full = dict(doctor_name="Dr. Lau Sai Kit", patient_name="Carol Tse", service_date="2026-02-07", total_amount=1540)
    s = score_approach(_gt(), {"receipt1": _result(**full, receipt_number="R-1")})
    assert s["invented"] == 1
    assert s["accuracy_pct"] == 100.0
    assert s["fields"]["receipt_number"]["applicable"] == 0


def test_failed_or_missing_result_cannot_score():
    no_file = score_approach(_gt(), {})
    failed = score_approach(_gt(), {"receipt1": (None, 100000.0)})
    for s in (no_file, failed):
        assert (s["correct"], s["applicable"], s["no_result_receipts"]) == (0, 4, 1)
    assert failed["mean_ms_per_receipt"] == 100000


# --- result files and field mapping ---------------------------------------------------------


def test_visit_date_maps_to_service_date():
    fields, ms = read_result({
        "status": "ok",
        "timings_seconds": {"di": 2.0, "aoai": 60.0, "total": 62.0},
        "benchmark_fields": {"doctor_name": "Dr A", "service_date": None, "total_amount": "-"},
        "aoai_output": {"visit_date": "07/02/2026"},
    })
    assert fields["service_date"] == "07/02/2026"
    assert fields["total_amount"] is None  # "-" placeholder
    assert ms == 62000.0
    assert read_result({"visit_date": "2026-02-07", "doctor_name": None})[0]["service_date"] == "2026-02-07"


def test_standard_field_wins_over_alias():
    fields, _ = read_result({"service_date": "2026-01-01", "visit_date": "2026-02-02"})
    assert fields["service_date"] == "2026-01-01"


def test_failed_run_and_raw_ocr_have_no_result():
    assert read_result({"status": "error", "error": "Request timed out.", "benchmark_fields": None,
                        "timings_seconds": {"total": 99.0}}) == (None, 99000.0)
    assert read_result({"ocr_text": "TOTAL 10", "timings_seconds": {"di": 2.5}}) == (None, 2500.0)


def test_paddle_result_reads_top_level_fields_and_timings():
    fields, ms = read_result({"doctor_name": "Dr A", "total_amount": 10.0, "timings": {"ocr_predict_ms": 900.0, "extract_ms": 5.0}})
    assert fields["doctor_name"] == "Dr A" and fields["patient_name"] is None
    assert ms == 905.0


# --- end to end -----------------------------------------------------------------------------


def test_scores_four_named_approaches(tmp_path, monkeypatch):
    gt_path = _write_xlsx(tmp_path / "gt.xlsx", [HEADER, ["r1", "Dr A", "na", "Pat B", "na", "2026-02-07", "10"]])
    runs = {
        "paddle_light": {"doctor_name": "Dr A", "patient_name": "Pat B", "service_date": "2026-02-07", "total_amount": 10.0},
        "azure_di_improved": {"doctor_name": "Dr A", "patient_name": None, "service_date": "2026-07-02", "total_amount": 10.0},
        "azure_di": {"ocr_text": "Dr A", "timings_seconds": {"di": 2.0}},
        "azure_di_aoai": {"status": "ok", "benchmark_fields": {"doctor_name": "Dr A", "receipt_number": "X1"},
                          "aoai_output": {"visit_date": "07/02/2026"}, "timings_seconds": {"total": 30.0}},
    }
    args = ["score", "--ground-truth", str(gt_path), "--output-dir", str(tmp_path / "out")]
    for name, raw in runs.items():
        (tmp_path / name).mkdir()
        (tmp_path / name / "receipt1.json").write_text(json.dumps(raw))
        (tmp_path / name / "summary.json").write_text("{}")  # run summaries are skipped
        args += ["--approach", f"{name}={tmp_path / name}"]
    monkeypatch.setattr(sys, "argv", args)
    score.main()

    rows = {r["approach"]: r for r in csv.DictReader(open(tmp_path / "out" / "summary.csv"))}
    assert list(rows) == list(runs)
    assert {n: (r["correct"], r["applicable"]) for n, r in rows.items()} == {
        "paddle_light": ("4", "4"), "azure_di_improved": ("2", "4"), "azure_di": ("0", "4"), "azure_di_aoai": ("2", "4")}
    assert rows["azure_di_aoai"]["invented"] == "1"
    assert rows["azure_di"]["no_result_receipts"] == "1"
    assert (tmp_path / "out" / "report.md").read_text().startswith("## Overall")
    assert len(list(csv.DictReader(open(tmp_path / "out" / "detail.csv")))) == 4 * len(FIELDS)


def test_aoai_token_usage_is_reported(tmp_path):
    usage = {"prompt_tokens": 500, "completion_tokens": 300, "completion_tokens_details": {"reasoning_tokens": 200}}
    (tmp_path / "receipt1.json").write_text(json.dumps({"status": "ok", "aoai": {"usage": usage}}))
    (tmp_path / "receipt2.json").write_text(json.dumps({"status": "ok", "aoai": {"usage": usage}}))
    (tmp_path / "receipt3.json").write_text(json.dumps({"status": "error", "error": "timeout"}))
    assert score.aoai_token_usage(tmp_path) == {"input": 1000, "output": 600, "reasoning": 400, "receipts": 2}
    (tmp_path / "other").mkdir()
    assert score.aoai_token_usage(tmp_path / "other") is None

