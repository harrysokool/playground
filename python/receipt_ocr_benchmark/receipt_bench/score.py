"""Score extracted JSON (light + heavy) against the manually entered ground-truth workbook.

Usage:
    python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
        --light results/extracted_tuned_light --heavy results/extracted_tuned_heavy \
        --output results/score_tuned.md

The workbook is read with the standard library (xlsx is zipped XML) to avoid a new dependency.

Comparison rules:
- GT "na" / empty means the field is absent: correct only if the extraction is null.
- Names: case, punctuation, whitespace and titles (Dr / 醫生 / 医生) are ignored.
- Dates: Excel auto-converted the typed numeric dates as MM/DD, while the extractor reads them
  day-first. A numeric date whose day and month are both <= 12 is therefore counted correct
  when it matches with day and month swapped - i.e. it matches the date as printed - and is
  marked "(d/m)" so the ambiguity stays visible.
- Amounts: equal within 0.005. Receipt numbers: exact string match.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree

from receipt_bench.extraction_tuned import FIELDS, parse_date

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def read_sheet(path: Path, sheet_name: str) -> list[list[str | None]]:
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]
        wb = ElementTree.fromstring(z.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid = next(s.get(REL_NS) for s in wb.find("m:sheets", NS) if s.get("name") == sheet_name)
        target = next(r.get("Target") for r in rels if r.get("Id") == rid).lstrip("/")
        sheet = ElementTree.fromstring(z.read(target if target.startswith("xl/") else f"xl/{target}"))

    rows = []
    for row in sheet.iter(f"{{{NS['m']}}}row"):
        cells: dict[int, str | None] = {}
        for c in row.findall("m:c", NS):
            col = _col_index(re.match(r"[A-Z]+", c.get("r")).group(0))
            t = c.get("t")
            if t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
            else:
                v = c.find("m:v", NS)
                val = None if v is None else (shared[int(v.text)] if t == "s" else v.text)
            cells[col] = val
        rows.append([cells.get(i) for i in range(max(cells, default=-1) + 1)])
    return rows


def _col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def load_ground_truth(path: Path) -> dict[str, dict[str, str | None]]:
    rows = read_sheet(path, "Ground Truth")
    header = [h.strip() if h else "" for h in rows[0]]
    gt = {}
    for row in rows[1:]:
        rec = {h: (row[i] if i < len(row) else None) for i, h in enumerate(header)}
        rid = (rec.get("receipt_id") or "").strip()
        if not rid:
            continue
        gt[re.sub(r"^r(\d+)$", r"receipt\1", rid)] = rec
    return gt


def _is_na(v) -> bool:
    return v is None or str(v).strip().lower() in {"", "na", "n/a", "none"}


def _norm_name(v: str) -> str:
    t = str(v).lower().replace("醫生", "").replace("医生", "")
    t = re.sub(r"\bdr\b\.?", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _gt_date(v) -> date | None:
    s = str(v).strip()
    if re.fullmatch(r"\d+(\.0+)?", s):  # Excel serial
        return date(1899, 12, 30) + timedelta(days=int(float(s)))
    parsed = parse_date(s)
    return date.fromisoformat(parsed[0]) if parsed else None


def _gt_display(field: str, v) -> str:
    if _is_na(v):
        return "na"
    if field == "service_date":
        d = _gt_date(v)
        return d.isoformat() if d else str(v)
    s = str(v)
    return s[:-2] if re.fullmatch(r"\d+\.0", s) else s


def compare(field: str, gt, pred) -> tuple[bool, str]:
    """Returns (correct, marker)."""
    if _is_na(gt):
        return pred is None, ""
    if pred is None:
        return False, ""
    if field in ("doctor_name", "patient_name"):
        return _norm_name(gt) == _norm_name(pred), ""
    if field == "total_amount":
        return abs(float(gt) - float(pred)) < 0.005, ""
    if field == "service_date":
        g, p = _gt_date(gt), date.fromisoformat(pred)
        if g == p:
            return True, ""
        if g and g.day <= 12 and g.month <= 12:
            try:
                if date(g.year, g.day, g.month) == p:
                    return True, " (d/m)"
            except ValueError:
                pass
        return False, ""
    return _gt_display(field, gt) == str(pred).strip(), ""


def _load_dir(d: Path | None) -> dict[str, dict]:
    if d is None:
        return {}
    return {p.stem: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--light", required=True, type=Path)
    parser.add_argument("--heavy", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Optional path to also write the markdown report to.")
    args = parser.parse_args()

    gt = load_ground_truth(args.ground_truth)
    runs = {"light": _load_dir(args.light), "heavy": _load_dir(args.heavy)}

    lines = ["| receipt | field | ground truth | light | ok | heavy | ok |", "|---|---|---|---|---|---|---|"]
    tally = {eng: {f: 0 for f in FIELDS} for eng in runs}
    for doc_id in sorted(gt, key=lambda k: int(re.sub(r"\D", "", k) or 0)):
        for f in FIELDS:
            cells = [doc_id, f, _gt_display(f, gt[doc_id].get(f))]
            for eng, results in runs.items():
                pred = results.get(doc_id, {}).get(f)
                ok, marker = compare(f, gt[doc_id].get(f), pred)
                tally[eng][f] += ok
                cells += ["null" if pred is None else str(pred), ("✓" if ok else "✗") + marker]
            lines.append("| " + " | ".join(cells) + " |")

    n = len(gt)
    lines += ["", "| field | light | heavy |", "|---|---|---|"]
    for f in FIELDS:
        lines.append(f"| {f} | {tally['light'][f]}/{n} | {tally['heavy'][f]}/{n} |")
    tot = {eng: sum(t.values()) for eng, t in tally.items()}
    lines.append(f"| **all fields** | **{tot['light']}/{n * len(FIELDS)}** | **{tot['heavy']}/{n * len(FIELDS)}** |")

    report = "\n".join(lines)
    print(report)
    if args.output:
        args.output.write_text(report + "\n")


if __name__ == "__main__":
    main()
