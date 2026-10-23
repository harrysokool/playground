"""Diagnosis comment detection: run the rules over raw OCR, and score any approach against the
diagnosis ground truth. Kept apart from the six-field benchmark (`score.py`).

Usage:
    python -m receipt_bench.diagnosis_cli detect --input results/v2/paddle_light --output results/diagnosis/v2/rules_light
    python -m receipt_bench.diagnosis_cli score --ground-truth data/diagnosis/ground_truth.csv \
        --approach rules_light=v2:results/diagnosis/v2/rules_light \
        --approach rules_light=v1:results/diagnosis/v1/rules_light \
        --approach aoai_v2=v2:results/diagnosis/v2/aoai_v2_rows --output-dir results/diagnosis/scores

`--approach NAME=SET:DIR` reads one JSON per receipt from DIR (rules output, or DI + AOAI output run
with --diagnosis) for the ground-truth rows of SET (v2 / v1). Repeat it with the same NAME to cover
several sets. Receipts in DIR with no ground-truth row are ignored.

Per receipt: correct when the status equals the ground truth (present / missing). Otherwise:
- needs_review: the approach could not decide (a person looks at it);
- false missing: a comment is there but the receipt would be flagged;
- false present: no comment, but the receipt would NOT be flagged (the costly error);
- no result: missing file, failed run, or no diagnosis in the output.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from receipt_bench.diagnosis import detect_diagnosis, status_of
from receipt_bench.raw_ocr import RawOCRResult

OUTCOMES = ["correct", "needs_review", "false_missing", "false_present", "no_result"]


def detect(input_dir: Path, output_dir: Path) -> None:
    files = sorted(input_dir.glob("*.json"))
    if not files:
        sys.exit(f"No OCR JSON files found in {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        start = time.perf_counter()
        result = detect_diagnosis(RawOCRResult.load(path))
        result.timings["detect_ms"] = (time.perf_counter() - start) * 1000
        result.save(output_dir / path.name)
        print(f"{path.name}: {result.status} ({result.reason})")


def load_ground_truth(path: Path) -> dict[tuple[str, str], dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = {(r["set"], r["receipt"]): r for r in csv.DictReader(f)}
    bad = [k for k, r in rows.items() if r["diagnosis_comment"] not in ("present", "missing")]
    if bad:
        sys.exit(f"Ground truth must be 'present' or 'missing': {bad}")
    return rows


def outcome(truth: str, predicted: str | None) -> str:
    if predicted is None:
        return "no_result"
    if predicted == truth:
        return "correct"
    if predicted == "needs_review":
        return "needs_review"
    return "false_missing" if truth == "present" else "false_present"


def evidence_text(record: dict) -> str:
    d = record.get("diagnosis") or {}
    ev = d.get("evidence")
    if isinstance(ev, list):
        ev = "; ".join(f"{e['source']} -> {e['value']!r} ({e['status']})" for e in ev)
    return (ev or "").replace("\n", " ")


def score(gt: dict, approaches: list[tuple[str, str, Path]]) -> tuple[list[dict], list[dict]]:
    detail = []
    for name, set_name, directory in approaches:
        rows = [(k, r) for k, r in gt.items() if k[0] == set_name]
        if not rows:
            sys.exit(f"No ground-truth rows for set {set_name!r}")
        for (s, receipt), r in rows:
            path = directory / f"{receipt}.json"
            record = json.loads(path.read_text()) if path.exists() else {}
            predicted = status_of(record)
            detail.append({"approach": name, "set": s, "receipt": receipt, "truth": r["diagnosis_comment"],
                           "predicted": predicted or "", "outcome": outcome(r["diagnosis_comment"], predicted),
                           "evidence": evidence_text(record)})
    summary = []
    for name in dict.fromkeys(a[0] for a in approaches):
        mine = [d for d in detail if d["approach"] == name]
        counts = {o: sum(d["outcome"] == o for d in mine) for o in OUTCOMES}
        summary.append({"approach": name, "sets": "+".join(dict.fromkeys(d["set"] for d in mine)),
                        "receipts": len(mine), **counts,
                        "accuracy_pct": round(100 * counts["correct"] / len(mine), 1)})
    return summary, detail


def write_outputs(summary: list[dict], detail: list[dict], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("summary.csv", summary), ("detail.csv", detail)):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    names = [s["approach"] for s in summary]
    lines = ["# Diagnosis comment detection (separate from the six-field scores)", "",
             "| | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    labels = {"receipts": "Receipts", "correct": "**Correct**", "accuracy_pct": "**Accuracy %**",
              "needs_review": "Needs review", "false_missing": "False missing (comment there, flagged)",
              "false_present": "False present (no comment, not flagged)", "no_result": "No result"}
    for key, label in labels.items():
        lines.append(f"| {label} | " + " | ".join(str(s[key]) for s in summary) + " |")
    lines += ["", "## Detail", "", "| set | receipt | truth | " + " | ".join(names) + " |",
              "|---" * (len(names) + 3) + "|"]
    keys = list(dict.fromkeys((d["set"], d["receipt"], d["truth"]) for d in detail))
    for s, receipt, truth in keys:
        cells = []
        for n in names:
            d = next((d for d in detail if d["approach"] == n and d["set"] == s and d["receipt"] == receipt), None)
            cells.append("" if d is None else (d["predicted"] or "-") + ("" if d["outcome"] == "correct"
                                                                        else f" ({d['outcome']})"))
        lines.append(f"| {s} | {receipt} | {truth} | " + " | ".join(cells) + " |")
    (out / "report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("detect", help="Run the diagnosis rules over a directory of raw OCR JSON.")
    d.add_argument("--input", required=True, type=Path)
    d.add_argument("--output", required=True, type=Path)
    s = sub.add_parser("score", help="Score approaches against the diagnosis ground truth.")
    s.add_argument("--ground-truth", required=True, type=Path)
    s.add_argument("--approach", action="append", required=True, metavar="NAME=SET:DIR")
    s.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "detect":
        detect(args.input, args.output)
        return
    approaches = []
    for spec in args.approach:
        name, _, rest = spec.partition("=")
        set_name, _, directory = rest.partition(":")
        if not (name and set_name and directory):
            sys.exit(f"--approach must be NAME=SET:DIR, got {spec!r}")
        approaches.append((name, set_name, Path(directory)))
    summary, detail = score(load_ground_truth(args.ground_truth), approaches)
    write_outputs(summary, detail, args.output_dir)
    for row in summary:
        print(f"{row['approach']}: {row['correct']}/{row['receipts']} correct, {row['needs_review']} needs review, "
              f"{row['false_present']} false present, {row['false_missing']} false missing, "
              f"{row['no_result']} no result")


if __name__ == "__main__":
    main()
