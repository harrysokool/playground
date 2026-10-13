"""Validate receipts_spec.json, then write the ground truth files for the receipts_v2 dataset.

    python data/receipts_v2/build_ground_truth.py     (from python/receipt_ocr_benchmark/)

Writes, next to this script:
- ground_truth.xlsx  same "Ground Truth" sheet layout as data/ground_truth/, so score.py reads it
                     unchanged (dates as ISO text, amounts as numbers, absent fields as N/A)
- GROUND_TRUTH.md    readable review table plus each receipt's planned details

Stops with a list of problems if any check fails; nothing is written in that case.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]
REG_FORMATS = {  # plausible formats; fictional numbers
    "medical": r"M\d{5}",            # Medical Council of Hong Kong style
    "dental": r"D\d{5}",             # dental register style
    "chinese_medicine": r"\d{6}",    # registered Chinese medicine practitioner style
    "physiotherapy": r"PT\d{6}",     # physiotherapists register style
}
LATEST_SERVICE_DATE = date(2026, 9, 30)  # receipts are printed and photographed after this
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                      "dec"], 1)}


def printed_date(s: str) -> date | None:
    """Reads the printed forms used in the spec: DD/MM/YYYY [hh:mm], D Month YYYY, YYYY年M月D日."""
    if m := re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})( \d{2}:\d{2})?", s):
        return date(int(m[3]), int(m[2]), int(m[1]))
    if m := re.fullmatch(r"(\d{1,2}) ([A-Za-z]+) (\d{4})", s):
        return date(int(m[3]), MONTHS[m[2][:3].lower()], int(m[1]))
    if m := re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", s):
        return date(int(m[1]), int(m[2]), int(m[3]))
    return None


def cents(x: float) -> int:
    return round(x * 100)


def validate(spec: dict) -> list[str]:
    errors = []
    rs = spec["receipts"]

    def dup(values, what):
        for v, n in Counter(values).items():
            if n > 1:
                errors.append(f"duplicate {what}: {v!r}")

    dup([r["receipt_id"] for r in rs], "receipt_id")
    dup([r["file_stem"] for r in rs], "file_stem")
    dup([r["type"] for r in rs], "receipt type")
    dup([r["provider"]["name"] for r in rs], "provider name")
    dup([r["provider"]["address"] for r in rs], "address")
    dup([r["provider"]["phone"] for r in rs], "phone")
    dup([p["printed_as"] for r in rs for p in r["people"]], "person name")
    dup([r["document"]["number"] for r in rs], "receipt number")
    dup([r["document"]["number"] for r in rs] + [p["registration"]["value"] for r in rs for p in r["people"]
         if "registration" in p] + [n["value"] for r in rs for n in r["other_numbers"] if len(n["value"]) > 3],
        "identifier")

    for r in rs:
        rid, gt = r["receipt_id"], r["ground_truth"]
        if set(gt) != set(FIELDS):
            errors.append(f"{rid}: ground truth must have exactly {FIELDS}")
            continue
        for f in FIELDS:
            if gt[f] in (None, ""):
                errors.append(f"{rid}: {f} is empty - use 'N/A' for an absent field")

        # amounts
        for li in r["line_items"]:
            if cents(li["qty"] * li["unit_price"]) != cents(li["amount"]):
                errors.append(f"{rid}: line {li['description']!r}: {li['qty']} x {li['unit_price']} != {li['amount']}")
        lines = sum(cents(li["amount"]) for li in r["line_items"])
        before_adj = cents(r["subtotal"]["amount"]) if r["subtotal"] else lines
        if r["subtotal"] and lines != before_adj:
            errors.append(f"{rid}: line items {lines / 100} != subtotal {before_adj / 100}")
        total = cents(r["total"]["amount"])
        if before_adj + sum(cents(a["amount"]) for a in r["adjustments"]) != total:
            errors.append(f"{rid}: subtotal/lines + adjustments != total {total / 100}")
        paid = sum(cents(p["amount"]) for p in r["payments"]) + (cents(r["balance"]["amount"]) if r["balance"] else 0)
        if paid != total:
            errors.append(f"{rid}: payments + balance {paid / 100} != total {total / 100}")
        if not isinstance(gt["total_amount"], (int, float)) or cents(gt["total_amount"]) != total:
            errors.append(f"{rid}: total_amount must be the numeric document total {total / 100}")

        # dates
        service = [d for d in r["dates"] if d["role"] == "service"]
        if len(service) != 1:
            errors.append(f"{rid}: needs exactly one service date, has {len(service)}")
        for d in r["dates"]:
            try:
                iso = date.fromisoformat(d["iso"])
            except ValueError:
                errors.append(f"{rid}: invalid date {d['iso']!r}")
                continue
            try:
                shown = printed_date(d["printed_as"])
            except (ValueError, KeyError):
                shown = None
            if shown != iso:
                errors.append(f"{rid}: printed date {d['printed_as']!r} does not match {d['iso']}")
            if d["role"] != "service" and service and d["iso"] == service[0]["iso"] and "same day" not in d["role"]:
                errors.append(f"{rid}: distractor date {d['label']!r} equals the service date")
        valid_service = []
        for d in service:
            try:
                valid_service.append(date.fromisoformat(d["iso"]))
            except ValueError:
                pass
        if valid_service:
            if gt["service_date"] != service[0]["iso"]:
                errors.append(f"{rid}: service_date {gt['service_date']} != spec service date {service[0]['iso']}")
            if valid_service[0] > LATEST_SERVICE_DATE:
                errors.append(f"{rid}: service date is after {LATEST_SERVICE_DATE}")

        # receipt number
        if gt["receipt_number"] != r["document"]["number"]:
            errors.append(f"{rid}: receipt_number must be the document's own number {r['document']['number']!r}")

        # people
        providers = [p for p in r["people"] if p["role"].startswith(("attending", "treating"))]
        patients = [p for p in r["people"] if p["role"] == "patient"]
        if len(providers) > 1 or len(patients) > 1:
            errors.append(f"{rid}: at most one attending/treating practitioner and one patient")
        expected_doc = providers[0]["printed_as"] if providers else "N/A"
        if gt["doctor_name"] != expected_doc:
            errors.append(f"{rid}: doctor_name {gt['doctor_name']!r} != attending/treating {expected_doc!r}")
        reg = providers[0].get("registration") if providers else None
        if gt["registration_number"] != (reg["value"] if reg else "N/A"):
            errors.append(f"{rid}: registration_number must be the attending practitioner's number or N/A")
        if gt["patient_name"] != (patients[0]["printed_as"] if patients else "N/A"):
            errors.append(f"{rid}: patient_name must match the patient on the receipt or N/A")
        for p in r["people"]:
            name = p["printed_as"]
            if re.search(r"[A-Za-z]", name) and re.search(r"[一-鿿]", name):
                errors.append(f"{rid}: {name!r} mixes English and Chinese - print each name in one script")
            if re.match(r"(Mr|Mrs|Ms|Miss|Prof)\.?\s", name) or re.search(r"(先生|女士|小姐|中醫師|醫師)$", name):
                errors.append(f"{rid}: {name!r} carries a title the scorer does not strip (only Dr / 醫生)")
            if "registration" in p:
                fmt = p["registration"]["format"]
                if not re.fullmatch(REG_FORMATS[fmt], p["registration"]["value"]):
                    errors.append(f"{rid}: registration {p['registration']['value']!r} is not {fmt} format")
    return errors


# --------------------------------------------------------------------------- writers


def write_xlsx(path: Path, rows: list[list]) -> None:
    """Minimal workbook: one "Ground Truth" sheet, strings as inline text cells, numbers as numbers."""
    def cell(ref, v):
        if isinstance(v, (int, float)):
            return f'<c r="{ref}"><v>{v:g}</v></c>'
        return f'<c r="{ref}" t="inlineStr" s="1"><is><t>{escape(str(v))}</t></is></c>'

    sheet_rows = "".join(f'<row r="{i}">' + "".join(cell(f"{chr(65 + j)}{i}", v) for j, v in enumerate(r)) + "</row>"
                         for i, r in enumerate(rows, 1))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    parts = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>',
        "_rels/.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml":
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook {ns} xmlns:r="{rel}">'
            '<sheets><sheet name="Ground Truth" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{rel}/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml":  # style 1 = Text (@), so Excel never auto-converts dates or numbers typed into those cells
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet {ns}>'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>'
            '</styleSheet>',
        "xl/worksheets/sheet1.xml":
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet {ns}>'
            f'<sheetData>{sheet_rows}</sheetData></worksheet>',
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, xml in parts.items():
            z.writestr(name, xml)


def money(x: float) -> str:
    return f"{x:,.2f}"


def write_markdown(path: Path, spec: dict) -> None:
    rs = spec["receipts"]
    out = ["# receipts_v2: Ground Truth for Review", "",
           "Generated from `receipts_spec.json` by `build_ground_truth.py`; edit the JSON, not this file.", "",
           "## Ground truth (the six benchmark fields)", "",
           "| Receipt | Type | Language | doctor_name | registration_number | patient_name | service_date "
           "| receipt_number | total_amount |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
        g = r["ground_truth"]
        out.append(f"| {r['file_stem']} | {r['type']} | {r['language'].split(' (')[0]} | {g['doctor_name']} | "
                   f"{g['registration_number']} | {g['patient_name']} | {g['service_date']} | {g['receipt_number']} | "
                   f"{money(g['total_amount'])} |")
    out += ["", "## Planned details per receipt", ""]
    for r in rs:
        d = r["document"]
        out += [f"### {r['file_stem']}: {r['type']} ({r['language']})", "",
                f"- **Provider:** {r['provider']['name']}, {r['provider']['address']}, tel. {r['provider']['phone']}",
                f"- **Layout:** {r['layout']}",
                f"- **Document:** {d['title']}; {d['number_label']}: `{d['number']}`"]
        for p in r["people"]:
            extra = f", {p['qualification']}" if p.get("qualification") else ""
            reg = f"; {p['registration']['label']}: `{p['registration']['value']}`" if p.get("registration") else ""
            out.append(f"- **{p['label']}** ({p['role']}): {p['printed_as']}{extra}{reg}")
        for dt in r["dates"]:
            out.append(f"- **{dt['label']}** ({dt['role']}): printed `{dt['printed_as']}` = {dt['iso']}")
        for n in r["other_numbers"]:
            out.append(f"- **{n['label']}** (distractor): `{n['value']}`")
        out += ["", "| Item | Qty | Unit price | Amount |", "|---|---|---|---|"]
        out += [f"| {li['description']} | {li['qty']} | {money(li['unit_price'])} | {money(li['amount'])} |"
                for li in r["line_items"]]
        if r["subtotal"]:
            out.append(f"| **{r['subtotal']['label']}** | | | {money(r['subtotal']['amount'])} |")
        out += [f"| {a['label']} | | | {money(a['amount'])} |" for a in r["adjustments"]]
        out.append(f"| **{r['total']['label']}** | | | **{money(r['total']['amount'])}** |")
        out += [f"| {p['label']} | | | {money(p['amount'])} |" for p in r["payments"]]
        if r["balance"]:
            out.append(f"| {r['balance']['label']} | | | {money(r['balance']['amount'])} |")
        out += [f"| {e['label']} | | | {money(e['amount'])} |" for e in r.get("extra_amounts", [])]
        out += ["", f"*{r['notes']}*", ""]
    path.write_text("\n".join(out))


def main() -> None:
    spec = json.loads((HERE / "receipts_spec.json").read_text())
    errors = validate(spec)
    if errors:
        sys.exit("Validation failed:\n- " + "\n- ".join(errors))
    rows = [["receipt_id"] + FIELDS] + [[r["receipt_id"]] + [r["ground_truth"][f] for f in FIELDS]
                                        for r in spec["receipts"]]
    write_xlsx(HERE / "ground_truth.xlsx", rows)
    write_markdown(HERE / "GROUND_TRUTH.md", spec)
    print(f"All checks passed for {len(spec['receipts'])} receipts. Wrote ground_truth.xlsx and GROUND_TRUTH.md.")


if __name__ == "__main__":
    main()
