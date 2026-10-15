"""Real smoke test: confirms the light config produces the normalized raw OCR shape. Needs the
local models (see models/README.md). The discontinued heavy configs are kept in configs/archive/
for historical reproduction only and are not run here.
"""

from pathlib import Path

import pytest
import yaml

from receipt_bench.paddle_engine import PaddleEngine

FIXTURE = Path(__file__).parent / "fixtures" / "receipt.png"
CONFIG_DIR = Path(__file__).parent.parent / "configs"
CONFIGS = [CONFIG_DIR / "paddle_light.yaml"]  # the only active PaddleOCR configuration


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


@pytest.mark.parametrize("folder, name", [("", "paddle_light"), ("archive", "paddle_heavy")])
def test_azure_config_differs_only_by_onednn_flag(folder, name):
    base = yaml.safe_load((CONFIG_DIR / folder / f"{name}.yaml").read_text())
    azure = yaml.safe_load((CONFIG_DIR / folder / f"{name}_azure.yaml").read_text())
    assert azure == {**base, "enable_mkldnn": False}
    assert base["device"] == "cpu" and base["text_detection_model_dir"].startswith("models/")


def test_heavy_is_archived_not_active():
    active = sorted(p.name for p in CONFIG_DIR.glob("*.yaml"))
    assert active == ["paddle_light.yaml", "paddle_light_azure.yaml"]
    for name in ("paddle_heavy.yaml", "paddle_heavy_azure.yaml"):
        archived = yaml.safe_load((CONFIG_DIR / "archive" / name).read_text())
        assert archived["text_detection_model_name"] == "PP-OCRv5_server_det"  # unchanged for reproduction
        assert archived["text_detection_model_dir"].startswith("models/")  # still relative to the project root
