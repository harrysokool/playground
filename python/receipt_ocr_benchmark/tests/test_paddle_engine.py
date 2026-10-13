"""Real smoke test: confirms the light and heavy configs share one implementation
and both produce the same normalized raw OCR shape. Downloads PaddleOCR models on
first run (cached under ~/.paddlex afterwards).
"""

from pathlib import Path

import pytest
import yaml

from receipt_bench.paddle_engine import PaddleEngine

FIXTURE = Path(__file__).parent / "fixtures" / "receipt.png"
CONFIG_DIR = Path(__file__).parent.parent / "configs"
CONFIGS = [CONFIG_DIR / "paddle_light.yaml", CONFIG_DIR / "paddle_heavy.yaml"]


@pytest.mark.parametrize("config_path", CONFIGS, ids=lambda p: p.stem)
def test_paddle_engine_processes_receipt(config_path):
    config = yaml.safe_load(config_path.read_text())
    engine = PaddleEngine(config)

    result = engine.process(FIXTURE)

    assert result.document_id == "receipt"
    assert result.engine_config == config
    assert len(result.pages) == 1

    page = result.pages[0]
    assert page.width > 0
    assert page.height > 0
    assert page.blocks, "expected at least one detected text block"
    assert "clinic" in page.plain_text.lower()

    block = page.blocks[0]
    assert isinstance(block.text, str) and block.text
    assert 0.0 <= block.confidence <= 1.0
    assert len(block.polygon) == 4

    assert result.timings["total_ms"] > 0


def test_enable_mkldnn_is_passed_only_when_configured(monkeypatch):
    calls = []
    monkeypatch.setattr("receipt_bench.paddle_engine.PaddleOCR", lambda **kw: calls.append(kw))
    base = yaml.safe_load(CONFIGS[0].read_text())

    PaddleEngine(base)
    PaddleEngine({**base, "enable_mkldnn": False})

    assert "enable_mkldnn" not in calls[0]
    assert calls[1]["enable_mkldnn"] is False


@pytest.mark.parametrize("name", ["paddle_light", "paddle_heavy"])
def test_azure_config_differs_only_by_onednn_flag(name):
    base = yaml.safe_load((CONFIG_DIR / f"{name}.yaml").read_text())
    azure = yaml.safe_load((CONFIG_DIR / f"{name}_azure.yaml").read_text())
    assert azure == {**base, "enable_mkldnn": False}
    assert base["device"] == "cpu" and base["text_detection_model_dir"].startswith("models/")
