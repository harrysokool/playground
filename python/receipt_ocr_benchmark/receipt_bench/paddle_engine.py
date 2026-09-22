"""PaddleOCR provider shared by both the light and heavy benchmark configurations.

Light vs. heavy is just a difference in which model names a config YAML supplies
(configs/paddle_light.yaml vs configs/paddle_heavy.yaml) - the code path is identical.
"""

from __future__ import annotations

import time
from pathlib import Path

from paddleocr import PaddleOCR

from receipt_bench.raw_ocr import OCRBlock, PageResult, RawOCRResult


class PaddleEngine:
    def __init__(self, config: dict):
        self.config = config
        self._ocr = PaddleOCR(
            text_detection_model_name=config["text_detection_model_name"],
            text_detection_model_dir=config.get("text_detection_model_dir"),
            text_recognition_model_name=config["text_recognition_model_name"],
            text_recognition_model_dir=config.get("text_recognition_model_dir"),
            device=config.get("device", "cpu"),
            # These are separate models layered on top of detection/recognition.
            # Disabled so light vs. heavy only differs in the det/rec models being compared.
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

    def process(self, document_path: Path) -> RawOCRResult:
        start = time.perf_counter()
        page_predictions = self._ocr.predict(str(document_path))
        total_ms = (time.perf_counter() - start) * 1000

        pages = [
            self._to_page_result(page_number=i + 1, prediction=prediction)
            for i, prediction in enumerate(page_predictions)
        ]

        return RawOCRResult(
            document_id=document_path.stem,
            engine_config=self.config,
            pages=pages,
            timings={"total_ms": total_ms},
        )

    @staticmethod
    def _to_page_result(page_number: int, prediction: dict) -> PageResult:
        height, width = prediction["doc_preprocessor_res"]["output_img"].shape[:2]
        texts = prediction["rec_texts"]
        scores = prediction["rec_scores"]
        polygons = prediction["rec_polys"]

        blocks = [
            OCRBlock(
                text=text,
                confidence=float(score),
                # PaddleOCR returns blocks pre-sorted in reading order (top-to-bottom,
                # left-to-right), so the list index is a reliable reading order.
                polygon=polygon.tolist(),
                reading_order=i,
            )
            for i, (text, score, polygon) in enumerate(zip(texts, scores, polygons))
        ]

        return PageResult(
            page_number=page_number,
            width=int(width),
            height=int(height),
            blocks=blocks,
            plain_text="\n".join(texts),
        )
