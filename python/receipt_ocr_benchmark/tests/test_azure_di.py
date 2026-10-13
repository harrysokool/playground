"""Azure DI conversion tests on synthetic DI responses - no Azure SDK, no network, no cost."""

import json
import sys

from receipt_bench import azure_di
from receipt_bench.azure_di import analyze, di_to_raw_ocr
from receipt_bench.extraction_general import extract_receipt_general
from receipt_bench.raw_ocr import RawOCRResult
from receipt_bench.score import read_result


def _di_result(lines: list[tuple[str, float, float, float, float]], word_conf: float = 0.95) -> dict:
    """A minimal prebuilt-read result (REST / as_dict() shape) with one word entry per token."""
    content, di_lines, words = "", [], []
    for text, x0, y0, x1, y1 in lines:
        offset = len(content)
        content += text + "\n"
        di_lines.append({"content": text, "polygon": [x0, y0, x1, y0, x1, y1, x0, y1],
                         "spans": [{"offset": offset, "length": len(text)}]})
        pos = offset
        for token in text.split(" "):
            words.append({"content": token, "confidence": word_conf, "span": {"offset": pos, "length": len(token)}})
            pos += len(token) + 1
    return {"apiVersion": "2024-11-30", "modelId": "prebuilt-read", "content": content,
            "pages": [{"pageNumber": 1, "angle": 0.0, "width": 1000, "height": 1400, "unit": "pixel",
                       "lines": di_lines, "words": words, "spans": [{"offset": 0, "length": len(content)}]}]}


GENERIC_RECEIPT = [
    ("Receipt No: RC-20931", 50, 50, 400, 80),
    ("Physician: Dr. Maria Gomez", 50, 100, 450, 130),
    ("Patient Name", 50, 150, 200, 180),
    ("John Smith", 260, 150, 420, 180),
    ("Date of Service: 15 Aug 2025", 50, 200, 450, 230),
    ("Total", 600, 700, 680, 730),
    ("$99.00", 800, 700, 900, 730),
]


def test_converts_lines_to_ocr_blocks_with_coordinates_and_reading_order():
    raw = di_to_raw_ocr("receipt1", _di_result(GENERIC_RECEIPT), di_ms=2500.0)

    assert isinstance(raw, RawOCRResult) and raw.document_id == "receipt1"
    page = raw.pages[0]
    assert (page.page_number, page.width, page.height) == (1, 1000, 1400)
    assert [b.text for b in page.blocks] == [t for t, *_ in GENERIC_RECEIPT]
    assert [b.reading_order for b in page.blocks] == list(range(len(GENERIC_RECEIPT)))
    assert page.blocks[0].polygon == [[50.0, 50.0], [400.0, 50.0], [400.0, 80.0], [50.0, 80.0]]
    assert page.plain_text.splitlines()[1] == "Physician: Dr. Maria Gomez"
    assert raw.timings == {"total_ms": 2500.0}
    assert raw.engine_config["model_id"] == "prebuilt-read"


def test_line_confidence_is_the_mean_of_its_words():
    di = _di_result([("Total 99.00", 0, 0, 100, 20), ("Other", 0, 40, 100, 60)])
    di["pages"][0]["words"][1]["confidence"] = 0.5  # "99.00"
    blocks = di_to_raw_ocr("r", di, 1.0).pages[0].blocks
    assert blocks[0].confidence == (0.95 + 0.5) / 2
    assert blocks[1].confidence == 0.95


def test_general_rules_run_unchanged_on_converted_di_output():
    r = extract_receipt_general(di_to_raw_ocr("receipt1", _di_result(GENERIC_RECEIPT), di_ms=2500.0))

    assert r.receipt_number == "RC-20931"
    assert r.doctor_name == "Dr. Maria Gomez"
    assert r.patient_name == "John Smith"
    assert r.service_date == "2025-08-15"
    assert r.total_amount == 99.0
    assert r.timings["ocr_predict_ms"] == 2500.0  # DI time flows into the extraction output


def test_extracted_di_result_is_scoring_compatible(tmp_path):
    r = extract_receipt_general(di_to_raw_ocr("receipt1", _di_result(GENERIC_RECEIPT), di_ms=2500.0))
    r.timings["extract_ms"] = 4.0
    r.save(tmp_path / "receipt1.json")

    fields, ms = read_result(json.loads((tmp_path / "receipt1.json").read_text()))
    assert fields["total_amount"] == 99.0 and fields["registration_number"] is None
    assert ms == 2504.0  # DI + rule extraction


def test_analyze_times_the_call_and_returns_the_rest_shape(tmp_path):
    class FakeResult:
        def as_dict(self):
            return {"modelId": "prebuilt-read", "pages": []}

    class FakeClient:
        def begin_analyze_document(self, model_id, body, content_type):
            assert (model_id, content_type) == ("prebuilt-read", "application/octet-stream")
            assert body.read() == b"img"
            return type("Poller", (), {"result": lambda self: FakeResult()})()

    (tmp_path / "r.png").write_bytes(b"img")
    result, ms = analyze(FakeClient(), tmp_path / "r.png")
    assert result["modelId"] == "prebuilt-read" and ms >= 0


def test_offline_mode_reuses_saved_responses_and_skips_failures(tmp_path, monkeypatch):
    saved = tmp_path / "saved"
    saved.mkdir()
    di = _di_result(GENERIC_RECEIPT)
    (saved / "receipt1.json").write_text(json.dumps({"raw_di_result": di, "timings_seconds": {"di": 2.5}, "error": None}))
    (saved / "receipt2.json").write_text(json.dumps({"di_ms": 3000.0, "result": di}))
    (saved / "receipt3.json").write_text(json.dumps({"error": "HttpResponseError: quota exceeded"}))
    (saved / "summary.json").write_text("{}")
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["azure_di", "--from-responses", str(saved), "--output", str(out)])

    azure_di.main()

    assert sorted(p.name for p in out.glob("*.json")) == ["receipt1.json", "receipt2.json"]
    assert RawOCRResult.load(out / "receipt1.json").timings == {"total_ms": 2500.0}
    assert RawOCRResult.load(out / "receipt2.json").timings == {"total_ms": 3000.0}
    assert "reused_from" in json.loads((out / "di_response" / "receipt1.json").read_text())
