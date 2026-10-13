"""Version 2 benchmark: inputs (data/receipts_v2/benchmark_inputs) and scoring ground truth
(data/receipts_v2/benchmark_ground_truth.xlsx) must agree with their sources."""

import json
from pathlib import Path

from receipt_bench.score import FIELDS, load_ground_truth

DATA = Path(__file__).resolve().parents[1] / "data"
V2 = DATA / "receipts_v2"

# benchmark receipt -> where its ground truth comes from
SOURCES = {f"receipt{i}": ("spec", f"r{i}") for i in (1, 2, 3, 4, 5, 6, 8)}
SOURCES.update({"receipt9": ("v1", "receipt4"), "receipt10": ("v1", "receipt6")})


def _expected() -> dict:
    spec = {r["receipt_id"]: r["ground_truth"] for r in json.loads((V2 / "receipts_spec.json").read_text())["receipts"]}
    v1 = load_ground_truth(DATA / "ground_truth" / "ground_truth_template.xlsx")
    out = {}
    for doc, (source, rid) in SOURCES.items():
        if source == "spec":
            out[doc] = {f: None if spec[rid][f] == "N/A" else spec[rid][f] for f in FIELDS}
        else:
            out[doc] = v1[rid]
    return out


def test_benchmark_ground_truth_matches_spec_and_version1():
    gt = load_ground_truth(V2 / "benchmark_ground_truth.xlsx")
    assert set(gt) == set(SOURCES)
    for doc, want in _expected().items():
        for f in FIELDS:
            got, exp = gt[doc][f], want[f]
            if f == "total_amount":
                assert abs(float(got) - float(exp)) < 0.005, (doc, f, got, exp)
            else:
                assert got == (None if exp is None else str(exp)), (doc, f, got, exp)


def test_every_scored_receipt_has_exactly_one_input_image():
    images = [p for p in (V2 / "benchmark_inputs").iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    assert sorted(p.stem for p in images) == sorted(SOURCES)
    for p in images:
        assert p.resolve().is_file() and p.stat().st_size > 0, f"{p.name} does not resolve to an image"
