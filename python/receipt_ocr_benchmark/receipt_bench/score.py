"""Score benchmark results from any number of approaches against the hand-checked ground truth.

Usage:
    python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
        --approach paddle_light=results/extracted_general_light \
        --approach paddle_heavy=results/extracted_general_heavy \
        --approach azure_di=results/di/20260929T073615Z \
        --approach azure_di_aoai=results/di_aoai/20260929T081700Z \
        --output-dir results/scores

Each of the six fields of each receipt is marked:
- Correct: the field is on the receipt and the approach returned the same value.
- Wrong:   the field is on the receipt and the approach returned a different value or nothing.
           A receipt with no result file, a failed run, or a result with no extracted fields
           counts as nothing, so failures can only lower accuracy.
- N/A:     the field is not on the receipt (ground truth "na"); excluded from accuracy. If the
           approach returned a value anyway it is counted separately as "invented".

Accuracy = Correct / applicable (non-N/A) fields x 100, overall and per field.

Normalization: names ignore case, punctuation, spacing and titles (Dr / 醫生 / 医生). Dates are
compared as calendar dates: ground truth must be ISO YYYY-MM-DD text; a Chinese date (2026年6月9日) is
read as written; any other non-ISO predicted date
is read day-first (Hong Kong convention). Amounts are equal within 0.005. Other fields are an
exact string match.

Result files: one JSON per receipt named like receipt1.json (a run's summary.json is skipped).
- Paddle extraction output (extract_cli): the six fields at the top level.
- Azure DI + AOAI runner output: the fields under "benchmark_fields".
- Anything else (e.g. raw Azure DI OCR with no extracted fields) counts as no result.
Field-name aliases (FIELD_ALIASES, e.g. visit_date -> service_date) fill a standard field that
is empty; for DI + AOAI they are also looked up in the full "aoai_output".

Outputs in --output-dir: report.md, summary.csv (one row per approach) and detail.csv (one row
per receipt x field x approach).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from receipt_bench.extraction_tuned import parse_amount, parse_date

FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]

# Other names an approach may use for a standard field.
FIELD_ALIASES = {"visit_date": "service_date"}

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
    """Returns {"receipt1": {field: value or None}}. Dates must be ISO text, so an Excel
    auto-converted date (a serial number like 46205) fails loudly instead of being guessed."""
    rows = read_sheet(path, "Ground Truth")
    header = [h.strip() if h else "" for h in rows[0]]
    missing = [f for f in FIELDS if f not in header]
    if missing:
        raise ValueError(f"ground truth is missing columns: {missing}")
    gt = {}
    for row in rows[1:]:
        rec = {h: (row[i] if i < len(row) else None) for i, h in enumerate(header)}
        rid = (rec.get("receipt_id") or "").strip()
        if not rid:
            continue
        values = {f: None if _is_na(rec.get(f)) else str(rec[f]).strip() for f in FIELDS}
        if values["service_date"] is not None:
            try:
                date.fromisoformat(values["service_date"])
            except ValueError:
                raise ValueError(f"{rid}: service_date must be ISO YYYY-MM-DD text, got {values['service_date']!r}")
        gt[re.sub(r"^r(\d+)$", r"receipt\1", rid)] = values
    return gt


def _is_na(v) -> bool:
    return v is None or str(v).strip().lower() in {"", "na", "n/a", "none", "null", "-"}


def _norm_name(v: str) -> str:
    t = str(v).lower().replace("醫生", "").replace("医生", "")
    t = re.sub(r"\bdr\b\.?", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Traditional Chinese date, e.g. 2026年6月9日. Read here in the scorer only, so a correct answer
# copied as printed counts; the extraction rules' own date parsing is unchanged.
_ZH_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def _to_date(v) -> date | None:
    s = str(v).strip()
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    if m := _ZH_DATE.search(s):
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    parsed = parse_date(s)  # day-first
    return date.fromisoformat(parsed[0]) if parsed else None


def _to_amount(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    parsed = parse_amount(str(v))
    return parsed[0] if parsed else None


def matches(field: str, gt: str, pred) -> bool:
    if field in ("doctor_name", "patient_name"):
        return _norm_name(gt) == _norm_name(pred)
    if field == "service_date":
        return date.fromisoformat(gt) == _to_date(pred)
    if field == "total_amount":
        p = _to_amount(pred)
        return p is not None and abs(float(gt) - p) < 0.005
    return str(gt).strip() == str(pred).strip()


def read_result(raw: dict) -> tuple[dict | None, float | None]:
    """Returns (fields, processing_ms) for one result JSON. fields is None when the file holds no
    usable result; otherwise it has exactly FIELDS, with None for anything not found."""
    if "benchmark_fields" in raw:  # Azure DI + AOAI runner
        secs = raw.get("timings_seconds") or {}
        ms = secs["total"] * 1000 if "total" in secs else None
        if raw.get("status") != "ok" or not raw["benchmark_fields"]:
            return None, ms
        fields, extra = dict(raw["benchmark_fields"]), raw.get("aoai_output") or {}
    elif any(f in raw for f in FIELDS):  # Paddle extraction output
        t = raw.get("timings") or {}
        ms = t["ocr_predict_ms"] + t.get("extract_ms", 0) if "ocr_predict_ms" in t else None
        fields, extra = {f: raw.get(f) for f in FIELDS}, raw
    else:  # e.g. raw Azure DI OCR: text only, no fields
        secs = raw.get("timings_seconds") or {}
        return None, (sum(secs.values()) * 1000 if secs else None)
    for alias, f in FIELD_ALIASES.items():
        for source in (fields, extra):
            if _is_na(fields.get(f)) and not _is_na(source.get(alias)):
                fields[f] = source[alias]
    return {f: None if _is_na(fields.get(f)) else fields[f] for f in FIELDS}, ms


def load_results(directory: Path) -> dict[str, tuple[dict | None, float | None]]:
    return {p.stem: read_result(json.loads(p.read_text())) for p in sorted(Path(directory).glob("*.json"))
            if p.stem != "summary"}


def score_approach(gt: dict, results: dict) -> dict:
    """Marks every receipt x field and totals them for one approach."""
    per_field = {f: {"correct": 0, "applicable": 0, "invented": 0} for f in FIELDS}
    detail, times, no_result = [], [], 0
    for doc_id in gt:
        fields, ms = results.get(doc_id, (None, None))
        no_result += fields is None
        if ms is not None:
            times.append(ms)
        for f in FIELDS:
            g, pred = gt[doc_id][f], (fields or {}).get(f)
            if g is None:
                mark = "N/A" if pred is None else "N/A (invented)"
                per_field[f]["invented"] += pred is not None
            else:
                mark = "Correct" if pred is not None and matches(f, g, pred) else "Wrong"
                per_field[f]["applicable"] += 1
                per_field[f]["correct"] += mark == "Correct"
            detail.append({"receipt": doc_id, "field": f, "ground_truth": "na" if g is None else g,
                           "predicted": "" if pred is None else pred, "result": mark})
    correct = sum(v["correct"] for v in per_field.values())
    applicable = sum(v["applicable"] for v in per_field.values())
    return {
        "correct": correct,
        "applicable": applicable,
        "accuracy_pct": _pct(correct, applicable),
        "invented": sum(v["invented"] for v in per_field.values()),
        "no_result_receipts": no_result,
        "mean_ms_per_receipt": round(sum(times) / len(times)) if times else None,
        "fields": {f: {**v, "accuracy_pct": _pct(v["correct"], v["applicable"])} for f, v in per_field.items()},
        "detail": detail,
    }


def aoai_token_usage(directory: Path) -> dict | None:
    """Total Azure OpenAI tokens recorded in a DI + AOAI result directory (aoai.usage), or None if
    the approach recorded no token usage. Reporting only; not part of the accuracy score."""
    totals, receipts = {"input": 0, "output": 0, "reasoning": 0}, 0
    for p in sorted(Path(directory).glob("*.json")):
        usage = (json.loads(p.read_text()).get("aoai") or {}).get("usage") if p.stem != "summary" else None
        if not usage:
            continue
        receipts += 1
        totals["input"] += usage.get("prompt_tokens") or 0
        totals["output"] += usage.get("completion_tokens") or 0
        totals["reasoning"] += (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    return {**totals, "receipts": receipts} if receipts else None


def _pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def render_markdown(scores: dict[str, dict], n_receipts: int) -> str:
    names = list(scores)
    head = "| | " + " | ".join(names) + " |\n|---|" + "---|" * len(names)
    lines = ["## Overall", "", head]
    rows = [
        ("Correct / applicable", lambda s: f"{s['correct']}/{s['applicable']}"),
        ("**Accuracy**", lambda s: f"**{s['accuracy_pct']}%**"),
        ("Invented values (field not on receipt)", lambda s: str(s["invented"])),
        (f"Receipts processed successfully (of {n_receipts})", lambda s: str(n_receipts - s["no_result_receipts"])),
        (f"Receipts with no result (of {n_receipts})", lambda s: str(s["no_result_receipts"])),
        ("Mean processing time per receipt", lambda s: "n/a" if s["mean_ms_per_receipt"] is None
         else f"{s['mean_ms_per_receipt'] / 1000:.1f} s"),
    ]
    if any(scores[n].get("aoai_tokens") for n in names):
        tok = lambda k: (lambda s: "—" if not s.get("aoai_tokens") else
                         f"{s['aoai_tokens'][k]:,} ({s['aoai_tokens'][k] / s['aoai_tokens']['receipts']:.0f}/receipt)")
        rows += [("AOAI input tokens (total, per receipt)", tok("input")),
                 ("AOAI output tokens incl. reasoning", tok("output")),
                 ("of which reasoning tokens", tok("reasoning"))]
    lines += [f"| {label} | " + " | ".join(fn(scores[n]) for n in names) + " |" for label, fn in rows]
    lines += ["", "## Accuracy by field (correct / applicable)", "", head]
    for f in FIELDS:
        cells = [f"{scores[n]['fields'][f]['correct']}/{scores[n]['fields'][f]['applicable']}"
                 + (f" ({scores[n]['fields'][f]['accuracy_pct']}%)" if scores[n]['fields'][f]['applicable'] else " (all N/A)")
                 for n in names]
        lines.append(f"| {f} | " + " | ".join(cells) + " |")
    lines += ["", "## Detail", "", "| receipt | field | ground truth | " + " | ".join(names) + " |",
              "|---|---|---|" + "---|" * len(names)]
    for i, row in enumerate(scores[names[0]]["detail"]):
        cells = [f"{scores[n]['detail'][i]['predicted'] or 'null'} → {scores[n]['detail'][i]['result']}" for n in names]
        lines.append(f"| {row['receipt']} | {row['field']} | {row['ground_truth']} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_outputs(scores: dict[str, dict], out_dir: Path, n_receipts: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text(render_markdown(scores, n_receipts))
    with open(out_dir / "summary.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["approach", "correct", "applicable", "accuracy_pct", "invented", "no_result_receipts",
                    "mean_ms_per_receipt"] + [f"{f}_accuracy_pct" for f in FIELDS] +
                   ["aoai_input_tokens", "aoai_output_tokens", "aoai_reasoning_tokens"])
        for name, s in scores.items():
            t = s.get("aoai_tokens") or {}
            w.writerow([name, s["correct"], s["applicable"], s["accuracy_pct"], s["invented"], s["no_result_receipts"],
                        s["mean_ms_per_receipt"]] + [s["fields"][f]["accuracy_pct"] for f in FIELDS] +
                       [t.get("input"), t.get("output"), t.get("reasoning")])
    with open(out_dir / "detail.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["approach", "receipt", "field", "ground_truth", "predicted", "result"])
        w.writeheader()
        for name, s in scores.items():
            w.writerows({"approach": name, **row} for row in s["detail"])


def _sort_key(doc_id: str) -> int:
    return int(re.sub(r"\D", "", doc_id) or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--approach", required=True, action="append", metavar="NAME=DIR",
                        help="An approach name and its directory of per-receipt result JSON. Repeat per approach.")
    parser.add_argument("--output-dir", type=Path, help="Optional directory for report.md, summary.csv, detail.csv.")
    args = parser.parse_args()

    gt = dict(sorted(load_ground_truth(args.ground_truth).items(), key=lambda kv: _sort_key(kv[0])))
    scores = {}
    for spec in args.approach:
        name, sep, directory = spec.partition("=")
        if not sep or not Path(directory).is_dir():
            parser.error(f"--approach must be NAME=DIR with an existing directory, got {spec!r}")
        scores[name] = score_approach(gt, load_results(Path(directory)))
        scores[name]["aoai_tokens"] = aoai_token_usage(Path(directory))

    report = render_markdown(scores, len(gt))
    print(report)
    if args.output_dir:
        write_outputs(scores, args.output_dir, len(gt))


if __name__ == "__main__":
    main()
