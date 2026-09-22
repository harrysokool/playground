"""Normalized raw OCR result format shared by every OCR engine in this benchmark.

Phase 1 only produces this raw format - no receipt field extraction yet.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class OCRBlock:
    text: str
    confidence: float | None
    polygon: list[list[float]]  # [[x, y], ...] corner points, image pixel coordinates
    reading_order: int | None = None


@dataclass
class PageResult:
    page_number: int
    width: int
    height: int
    blocks: list[OCRBlock]
    plain_text: str


@dataclass
class RawOCRResult:
    document_id: str
    engine_config: dict
    pages: list[PageResult]
    timings: dict[str, float]

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))

    @staticmethod
    def load(path: Path) -> RawOCRResult:
        data = json.loads(path.read_text())
        pages = [
            PageResult(
                page_number=p["page_number"],
                width=p["width"],
                height=p["height"],
                blocks=[OCRBlock(**b) for b in p["blocks"]],
                plain_text=p["plain_text"],
            )
            for p in data["pages"]
        ]
        return RawOCRResult(
            document_id=data["document_id"],
            engine_config=data["engine_config"],
            pages=pages,
            timings=data["timings"],
        )
