import json
from pathlib import Path

from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult


def test_save_writes_readable_json(tmp_path: Path):
    result = RawOCRResult(
        document_id="sample",
        engine_config={"engine_config_name": "paddle_light"},
        pages=[
            PageResult(
                page_number=1,
                width=600,
                height=300,
                blocks=[
                    OCRBlock(
                        text="Hello",
                        confidence=0.98,
                        polygon=[[0, 0], [10, 0], [10, 10], [0, 10]],
                        reading_order=0,
                    )
                ],
                plain_text="Hello",
            )
        ],
        timings={"total_ms": 123.4},
    )

    out_path = tmp_path / "sample.json"
    result.save(out_path)

    data = json.loads(out_path.read_text())
    assert data["document_id"] == "sample"
    assert data["pages"][0]["width"] == 600
    assert data["pages"][0]["blocks"][0]["text"] == "Hello"
    assert data["timings"]["total_ms"] == 123.4
