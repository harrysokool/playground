"""Generate the eight printable receipt PDFs (and previews) from receipts_spec.json.

    python data/receipts_v2/generate_receipts.py     (from python/receipt_ocr_benchmark/)

Each receipt type has its own HTML/CSS template; headless Google Chrome prints it to PDF.
Every PDF is an A4 page with the receipt drawn at its real size (A4, A5 portrait, A5 landscape
or an 80 mm till slip). Smaller receipts get trim marks so they can be cut out after printing.
Every value printed comes from the spec; the templates add no dates, numbers, names or amounts.

Writes printable/receiptN.pdf, preview/receiptN.png and preview/contact_sheet.png, then checks
each PDF's text against the spec (validate_pdfs). Needs Google Chrome, pdftotext/pdftoppm
(Poppler) and Pillow. macOS fonts are used for Chinese (PingFang, LiSong, Kaiti).
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PRINTABLE, PREVIEW = HERE / "printable", HERE / "preview"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SANS_ZH = '"PingFang HK", "PingFang TC", "Heiti TC"'
MING_ZH = '"LiSong Pro", "Songti TC"'
KAI_ZH = '"Kaiti TC", "BiauKaiHK"'


def e(s) -> str:
    return html.escape(str(s))


def money(x: float) -> str:
    return f"{x:,.2f}"


def addr2(a: str) -> str:
    """Address on two lines, broken after the comma nearest the middle."""
    commas = [i for i, c in enumerate(a) if c == ","]
    if not commas:
        return e(a)
    i = min(commas, key=lambda k: abs(k - len(a) / 2))
    return f"{e(a[:i + 1])}<br>{e(a[i + 1:].strip())}"


def person(r: dict, role_prefix: str) -> dict | None:
    return next((p for p in r["people"] if p["role"].startswith(role_prefix)), None)


def date_of(r: dict, role_prefix: str) -> dict | None:
    return next((d for d in r["dates"] if d["role"].startswith(role_prefix)), None)


def number(r: dict, label_start: str) -> dict:
    return next(n for n in r["other_numbers"] if n["label"].startswith(label_start))


def split_label(label: str) -> tuple[str, str]:
    """'Policy No. 保單編號 (Evergreen Assurance)' -> ('Policy No. 保單編號', 'Evergreen Assurance')."""
    m = re.match(r"(.*?)\s*\((.*)\)$", label)
    return (m[1], m[2]) if m else (label, "")


SAMPLE = '<div class="sample">SAMPLE / 測試樣本</div>'
BASE_CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; color: #1d1d1d; }
.sheet { width: 210mm; height: 297mm; position: relative; overflow: hidden; }
.receipt { position: absolute; }
.sample { position: absolute; font: 6.5pt Helvetica, "PingFang HK"; color: #8a8a8a; border: 0.3mm solid #b5b5b5;
          padding: 0.6mm 1.6mm; letter-spacing: 0.3px; }
.mark { position: absolute; background: #9a9a9a; }
table { border-collapse: collapse; }
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
"""


def trim_marks(x: float, y: float, w: float, h: float) -> str:
    """Corner trim marks (mm) just outside the receipt rectangle."""
    out, L, G = [], 5, 1.5
    for cx, cy in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
        hx = cx - G - L if cx == x else cx + G
        vy = cy - G - L if cy == y else cy + G
        out.append(f'<div class="mark" style="left:{hx}mm;top:{cy - 0.1}mm;width:{L}mm;height:0.2mm"></div>')
        out.append(f'<div class="mark" style="left:{cx - 0.1}mm;top:{vy}mm;width:0.2mm;height:{L}mm"></div>')
    return "".join(out)


def page(css: str, body: str, box: tuple[float, float, float, float | None], marks: bool) -> str:
    x, y, w, h = box
    size = f"left:{x}mm;top:{y}mm;width:{w}mm;" + (f"height:{h}mm;" if h else "")
    marks_html = trim_marks(x, y, w, h) if marks and h else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}{css}</style></head>'
            f'<body><div class="sheet">{marks_html}<div class="receipt" style="{size}">{body}</div></div></body></html>')


# =========================================================================== 1. GP clinic (A5 letterhead)
def gp(r):
    doc, pat = person(r, "attending"), person(r, "patient")
    d, pno = r["dates"][0], number(r, "Patient No.")
    rows = "".join(f"<tr><td>{e(li['description'])}</td><td class='num'>{money(li['amount'])}</td></tr>"
                   for li in r["line_items"])
    pay = r["payments"][0]
    css = f"""
    .gp {{ width:148mm; height:210mm; padding:13mm 13mm 10mm; font:9.5pt Helvetica, {SANS_ZH}; position:relative;
          border:0.3mm solid #c8d8d2; }}
    .gp .logo {{ width:11mm; height:11mm; border-radius:50%; background:#1f6f5c; margin:0 auto 2.5mm; position:relative; }}
    .gp .logo:before, .gp .logo:after {{ content:""; position:absolute; background:#fff; }}
    .gp .logo:before {{ left:4.5mm; top:2.2mm; width:2mm; height:6.6mm; }}
    .gp .logo:after {{ left:2.2mm; top:4.5mm; width:6.6mm; height:2mm; }}
    .gp h1 {{ font:normal 17pt Georgia, serif; color:#1f6f5c; text-align:center; margin:0; }}
    .gp .addr {{ text-align:center; font-size:8pt; color:#555; margin-top:1.2mm; line-height:1.4; }}
    .gp .docblk {{ text-align:center; margin:4mm 0 3mm; padding:2.5mm 0; border-top:0.3mm solid #1f6f5c;
                   border-bottom:0.3mm solid #1f6f5c; line-height:1.45; }}
    .gp .docblk .lbl {{ font-size:7.5pt; color:#1f6f5c; text-transform:uppercase; letter-spacing:1px; }}
    .gp .docblk b {{ font:bold 11.5pt Georgia, serif; }}
    .gp h2 {{ text-align:center; letter-spacing:5px; font:bold 12pt Georgia, serif; margin:3mm 0 3.5mm; }}
    .gp .cols {{ display:flex; justify-content:space-between; margin-bottom:4mm; line-height:1.7; }}
    .gp .cols span {{ color:#666; display:inline-block; width:23mm; }}
    .gp table {{ width:100%; }}
    .gp th {{ text-align:left; font-size:8pt; color:#1f6f5c; border-bottom:0.4mm solid #1f6f5c; padding:1.5mm 0; }}
    .gp th.num {{ text-align:right; }}
    .gp td {{ padding:1.8mm 0; border-bottom:0.2mm dotted #9bb; }}
    .gp tr.tot td {{ border-bottom:none; border-top:0.4mm solid #1f6f5c; font-weight:bold; font-size:10.5pt; padding-top:2.2mm; }}
    .gp .paid {{ margin-top:2.5mm; display:flex; justify-content:space-between; color:#333; }}
    .gp .foot {{ position:absolute; left:13mm; right:13mm; bottom:16mm; font-size:7.5pt; color:#666; display:flex;
                 justify-content:space-between; align-items:flex-end; }}
    .gp .sig {{ width:42mm; border-top:0.3mm solid #444; text-align:center; padding-top:1mm; }}
    .gp .sample {{ right:5mm; bottom:5mm; }}"""
    body = f"""<div class="gp">
      <div class="logo"></div><h1>{e(r['provider']['name'])}</h1>
      <div class="addr">{e(r['provider']['address'])}<br>Tel: {e(r['provider']['phone'])}</div>
      <div class="docblk"><div class="lbl">{e(doc['label'])}</div><b>{e(doc['printed_as'])}</b><br>{e(doc['qualification'])}
        &nbsp;·&nbsp; {e(doc['registration']['label'])} {e(doc['registration']['value'])}</div>
      <h2>{e(r['document']['title'])}</h2>
      <div class="cols">
        <div><span>{e(pat['label'])}:</span>{e(pat['printed_as'])}<br><span>{e(pno['label'])}:</span>{e(pno['value'])}</div>
        <div><span>{e(r['document']['number_label'])}:</span>{e(r['document']['number'])}<br><span>{e(d['label'])}:</span>{e(d['printed_as'])}</div>
      </div>
      <table><tr><th>Description</th><th class="num">Amount (HK$)</th></tr>{rows}
        <tr class="tot"><td>{e(r['total']['label'])}</td><td class="num">HK${money(r['total']['amount'])}</td></tr></table>
      <div class="paid"><span>{e(pay['label'])}</span><span class="num">HK${money(pay['amount'])}</span></div>
      <div class="foot"><div>Thank you for your visit.<br>Please keep this receipt for insurance claims.</div>
        <div class="sig">Clinic stamp / signature</div></div>
      {SAMPLE}</div>"""
    return page(css, body, (31, 22, 148, 210), marks=True)


# =========================================================================== 2. Specialist (A4 receipt)
def specialist(r):
    doc, ref, pat = person(r, "attending"), person(r, "referring"), person(r, "patient")
    svc, iss, fno = date_of(r, "service"), date_of(r, "issue"), number(r, "File No.")
    rows = "".join(f"<tr><td>{i}</td><td>{e(li['description'])}</td><td class='c'>{li['qty']}</td>"
                   f"<td class='num'>{money(li['amount'])}</td></tr>" for i, li in enumerate(r["line_items"], 1))
    pay = r["payments"][0]
    css = f"""
    .sp {{ width:210mm; height:297mm; padding:20mm 20mm 18mm; font:10pt "Helvetica Neue", Helvetica, {SANS_ZH}; position:relative; }}
    .sp .top {{ display:flex; justify-content:space-between; align-items:flex-start; }}
    .sp .brand {{ display:flex; gap:4mm; }}
    .sp .heart {{ font-size:26pt; color:#b8233a; line-height:1; }}
    .sp .brand h1 {{ margin:0; font:600 16pt "Helvetica Neue", Helvetica; color:#1b2f5b; }}
    .sp .brand .addr {{ font-size:8.5pt; color:#555; margin-top:1mm; line-height:1.45; }}
    .sp .box {{ border:0.4mm solid #1b2f5b; width:72mm; }}
    .sp .box .t {{ background:#1b2f5b; color:#fff; font-weight:600; letter-spacing:2px; padding:2mm 3mm; font-size:10.5pt; }}
    .sp .box div.r {{ display:flex; justify-content:space-between; padding:1.6mm 3mm; font-size:9pt; border-top:0.2mm solid #d4d9e4; }}
    .sp .box div.r span {{ color:#5a6377; }}
    .sp .doc {{ margin-top:9mm; padding:4mm 5mm; background:#f2f4f8; line-height:1.55; }}
    .sp .doc .lbl {{ font-size:8pt; color:#5a6377; text-transform:uppercase; letter-spacing:1px; }}
    .sp .doc b {{ font-size:12.5pt; color:#1b2f5b; }}
    .sp .pt {{ margin:7mm 0 5mm; line-height:1.9; }}
    .sp .pt span {{ display:inline-block; width:32mm; color:#5a6377; }}
    .sp table {{ width:100%; border:0.3mm solid #1b2f5b; }}
    .sp th {{ background:#e3e7f0; color:#1b2f5b; text-align:left; padding:2.2mm 3mm; font-size:9pt; border:0.3mm solid #1b2f5b; }}
    .sp td {{ padding:2.6mm 3mm; border:0.3mm solid #b9c1d3; }}
    .sp td.c, .sp th.c {{ text-align:center; width:14mm; }}
    .sp .sum {{ width:92mm; margin:6mm 0 0 auto; }}
    .sp .sum div {{ display:flex; justify-content:space-between; padding:1.8mm 0; border-bottom:0.2mm solid #d4d9e4; }}
    .sp .sum .tot {{ font-weight:700; font-size:12pt; color:#1b2f5b; border-bottom:0.5mm solid #1b2f5b; }}
    .sp .sign {{ position:absolute; left:20mm; right:20mm; bottom:30mm; display:flex; justify-content:space-between;
                 align-items:flex-end; font-size:8.5pt; color:#555; }}
    .sp .sign .line {{ width:65mm; border-top:0.3mm solid #333; padding-top:1.2mm; text-align:center; }}
    .sp .sample {{ right:20mm; bottom:12mm; }}"""
    body = f"""<div class="sp">
      <div class="top"><div class="brand"><div class="heart">&#9829;</div><div><h1>{e(r['provider']['name'])}</h1>
          <div class="addr">{addr2(r['provider']['address'])}<br>Tel: {e(r['provider']['phone'])}</div></div></div>
        <div class="box"><div class="t">{e(r['document']['title'])}</div>
          <div class="r"><span>{e(r['document']['number_label'])}</span><b>{e(r['document']['number'])}</b></div>
          <div class="r"><span>{e(svc['label'])}</span>{e(svc['printed_as'])}</div>
          <div class="r"><span>{e(iss['label'])}</span>{e(iss['printed_as'])}</div>
          <div class="r"><span>{e(fno['label'])}</span>{e(fno['value'])}</div></div></div>
      <div class="doc"><div class="lbl">{e(doc['label'])}</div><b>{e(doc['printed_as'])}</b><br>{e(doc['qualification'])}
        &nbsp;|&nbsp; {e(doc['registration']['label'])} {e(doc['registration']['value'])}</div>
      <div class="pt"><span>{e(pat['label'])}:</span>{e(pat['printed_as'])}<br><span>{e(ref['label'])}:</span>{e(ref['printed_as'])}</div>
      <table><tr><th class="c">No.</th><th>Description</th><th class="c">Qty</th><th class="num">Amount (HK$)</th></tr>{rows}</table>
      <div class="sum"><div class="tot"><span>{e(r['total']['label'])}</span><span class="num">HK${money(r['total']['amount'])}</span></div>
        <div><span>{e(pay['label'])}</span><span class="num">HK${money(pay['amount'])}</span></div>
        <div><span>{e(r['balance']['label'])}</span><span class="num">HK${money(r['balance']['amount'])}</span></div></div>
      <div class="sign"><div>Payment received with thanks.</div><div class="line">For {e(r['provider']['name'])}</div></div>
      {SAMPLE}</div>"""
    return page(css, body, (0, 0, 210, 297), marks=False)


# =========================================================================== 3. Hospital outpatient invoice (A4 billing)
HOSP_CODES = ["OPC-0120", "RAD-1140", "LAB-2071", "PHM-9003"]


def hospital(r):
    doc, pat = person(r, "attending"), person(r, "patient")
    svc, iss = date_of(r, "service"), date_of(r, "issue")
    pno, epi, pol = number(r, "Patient No."), number(r, "Episode No."), number(r, "Policy No.")
    pol_label, insurer = split_label(pol["label"])
    hosp_en, hosp_zh_dept = r["provider"]["name"].split(" – ")
    rows = "".join(f"<tr><td>{HOSP_CODES[i]}</td><td>{e(li['description'])}</td><td class='c'>{li['qty']}</td>"
                   f"<td class='num'>{money(li['unit_price'])}</td><td class='num'>{money(li['amount'])}</td></tr>"
                   for i, li in enumerate(r["line_items"]))
    grid = [(r["document"]["number_label"], r["document"]["number"]), (iss["label"], iss["printed_as"]),
            (pat["label"], pat["printed_as"]), (pno["label"], pno["value"]),
            (svc["label"], svc["printed_as"]), (epi["label"], epi["value"]),
            (doc["label"], doc["printed_as"]), (pol_label, pol["value"]), ("Insurer 保險公司", insurer)]
    grid_html = "".join(f"<div class='g'><span>{e(k)}</span><b>{e(v)}</b></div>" for k, v in grid)
    grid_html += "<div class='g'></div>"  # keep the two-column grid even
    ins, pt = r["payments"]
    css = f"""
    .hp {{ width:210mm; height:297mm; padding:16mm 16mm 14mm; font:9.2pt Arial, {SANS_ZH}; position:relative; }}
    .hp .hdr {{ display:flex; justify-content:space-between; align-items:center; padding-bottom:3mm; border-bottom:0.8mm solid #00677f; }}
    .hp .hdr .nm {{ display:flex; align-items:center; gap:3mm; }}
    .hp .hdr .lg {{ width:12mm; height:12mm; border:0.9mm solid #00677f; border-radius:2mm; color:#00677f;
                   font:bold 12pt Arial; display:flex; align-items:center; justify-content:center; }}
    .hp .hdr h1 {{ margin:0; font:bold 14pt Arial, {SANS_ZH}; color:#00677f; }}
    .hp .hdr .dept {{ font-size:9pt; color:#333; }}
    .hp .hdr .addr {{ text-align:right; font-size:8pt; color:#444; line-height:1.5; }}
    .hp .title {{ text-align:center; font:bold 13pt Arial, {SANS_ZH}; letter-spacing:1px; margin:5mm 0 4mm; }}
    .hp .grid {{ display:grid; grid-template-columns:1fr 1fr; border:0.3mm solid #8fb3bd; }}
    .hp .g {{ display:flex; padding:1.8mm 2.5mm; border-bottom:0.2mm solid #d0e0e4; }}
    .hp .g:nth-child(odd) {{ border-right:0.2mm solid #d0e0e4; }}
    .hp .g:nth-last-child(-n+2) {{ border-bottom:none; }}
    .hp .g:empty {{ border-right:none; }}
    .hp .g span {{ width:43mm; color:#4f6a72; font-size:8.4pt; }}
    .hp .g b {{ font-weight:600; }}
    .hp table {{ width:100%; margin-top:6mm; }}
    .hp th {{ background:#00677f; color:#fff; text-align:left; padding:2mm; font-size:8.4pt; font-weight:600; }}
    .hp th.num {{ text-align:right; }}
    .hp td {{ padding:2.1mm 2mm; border-bottom:0.2mm solid #cfdde1; }}
    .hp td.c, .hp th.c {{ text-align:center; width:14mm; }}
    .hp th.code {{ width:24mm; }} .hp th.money {{ width:27mm; }}
    .hp td {{ word-break:keep-all; }}
    .hp tr:nth-child(odd) td {{ background:#f3f8f9; }}
    .hp .tot {{ width:110mm; margin:4mm 0 0 auto; }}
    .hp .tot div {{ display:flex; justify-content:space-between; padding:1.7mm 2mm; }}
    .hp .tot .big {{ font-weight:bold; font-size:10.5pt; border-top:0.5mm solid #00677f; border-bottom:0.2mm solid #cfdde1; }}
    .hp .tot .bal {{ font-weight:bold; border-top:0.4mm solid #333; }}
    .hp .ins {{ margin-top:6mm; border:0.3mm dashed #00677f; padding:3mm 4mm; font-size:8.6pt; line-height:1.55; color:#244; }}
    .hp .foot {{ position:absolute; left:16mm; right:16mm; bottom:20mm; font-size:7.8pt; color:#666;
                 border-top:0.2mm solid #bbb; padding-top:2mm; display:flex; justify-content:space-between; }}
    .hp .sample {{ right:16mm; bottom:11mm; }}"""
    body = f"""<div class="hp">
      <div class="hdr"><div class="nm"><div class="lg">LB</div><div><h1>{e(hosp_en)}</h1><div class="dept">{e(hosp_zh_dept)}</div></div></div>
        <div class="addr">{addr2(r['provider']['address'])}<br>Tel: {e(r['provider']['phone'])}</div></div>
      <div class="title">{e(r['document']['title'])}</div>
      <div class="grid">{grid_html}</div>
      <table><tr><th class="code">Item Code<br>項目編號</th><th>Description<br>項目</th><th class="c">Qty<br>數量</th>
        <th class="num money">Unit Price (HK$)<br>單價</th><th class="num money">Amount (HK$)<br>金額</th></tr>{rows}</table>
      <div class="tot"><div class="big"><span>{e(r['total']['label'])}</span><span class="num">{money(r['total']['amount'])}</span></div>
        <div><span>Less: {e(ins['label'])}</span><span class="num">({money(ins['amount'])})</span></div>
        <div><span>Less: {e(pt['label'])}</span><span class="num">({money(pt['amount'])})</span></div>
        <div class="bal"><span>{e(r['balance']['label'])}</span><span class="num">{money(r['balance']['amount'])}</span></div></div>
      <div class="ins">Direct billing arranged with {e(insurer)} under the policy shown above.
        直接付款安排由上述保單之保險公司處理。</div>
      <div class="foot"><span>This is a computer-generated invoice. 此乃電腦發出之發票。</span><span>Page 1 of 1</span></div>
      {SAMPLE}</div>"""
    return page(css, body, (0, 0, 210, 297), marks=False)


# =========================================================================== 4. Chinese medicine (A5 traditional receipt)
CN_DIGITS = "零壹貳參肆伍陸柒捌玖"


def cn_upper(amount: float) -> str:
    """Whole-dollar amounts below 10,000 in formal Chinese numerals, e.g. 790 -> 柒佰玖拾圓正."""
    n = round(amount)
    assert abs(amount - n) < 0.005 and 0 < n < 10000, amount
    out, zero = "", False
    for value, unit in ((1000, "仟"), (100, "佰"), (10, "拾"), (1, "")):
        digit, n = divmod(n, value)
        if digit:
            out += ("零" if zero and out else "") + CN_DIGITS[digit] + unit
            zero = False
        else:
            zero = True
    return out + "圓正"


def tcm(r):
    doc, pat = person(r, "attending"), person(r, "patient")
    svc, nxt, rec = date_of(r, "service"), date_of(r, "next"), number(r, "病歷編號")
    rows = "".join(f"<tr><td>{e(li['description'])}</td><td class='c'>{li['qty']}</td>"
                   f"<td class='num'>{money(li['unit_price'])}</td><td class='num'>{money(li['amount'])}</td></tr>"
                   for li in r["line_items"])
    pay = r["payments"][0]
    css = f"""
    .tc {{ width:148mm; height:210mm; padding:7mm; font:10pt {MING_ZH}, serif; position:relative; }}
    .tc .frame {{ border:0.9mm double #b22222; height:100%; padding:7mm 8mm; position:relative; }}
    .tc h1 {{ margin:0; text-align:center; font:normal 19pt {MING_ZH}; letter-spacing:3px; color:#8b1a1a; }}
    .tc .addr {{ text-align:center; font-size:8.3pt; color:#444; margin-top:1.5mm; line-height:1.5; }}
    .tc .ttl {{ display:flex; justify-content:space-between; align-items:flex-end; margin:5mm 0 3mm; }}
    .tc .ttl h2 {{ margin:0; font:normal 20pt {MING_ZH}; letter-spacing:12px; color:#b22222; }}
    .tc .ttl div {{ font-size:9.5pt; }}
    .tc table {{ width:100%; }}
    .tc .info td {{ border:0.3mm solid #b22222; padding:1.9mm 2.5mm; font-size:9.6pt; }}
    .tc .info td.k {{ width:31mm; background:#fbeeee; color:#8b1a1a; }}
    .tc .items {{ margin-top:4mm; }}
    .tc .items th {{ border-bottom:0.5mm solid #b22222; color:#8b1a1a; font-weight:normal; padding:1.6mm 1mm; text-align:left; }}
    .tc .items th.num, .tc .items th.c {{ text-align:right; }}
    .tc .items th.c, .tc .items td.c {{ text-align:center; width:13mm; }}
    .tc .items td {{ padding:1.9mm 1mm; border-bottom:0.2mm dashed #d9a3a3; }}
    .tc .sum {{ margin-top:3mm; line-height:1.85; }}
    .tc .sum .big {{ font-size:12pt; }}
    .tc .sum span.k {{ display:inline-block; width:27mm; color:#8b1a1a; }}
    .tc .next {{ margin-top:2.5mm; font-size:9.3pt; color:#333; }}
    .tc .seal {{ position:absolute; right:12mm; bottom:20mm; width:19mm; height:19mm; border:0.8mm solid #c0282d;
                 color:#c0282d; font:17pt/1.05 {KAI_ZH}; display:flex; flex-wrap:wrap; align-content:center;
                 justify-content:center; text-align:center; letter-spacing:0; opacity:0.9; }}
    .tc .seal span {{ width:8mm; }}
    .tc .signline {{ position:absolute; left:8mm; bottom:22mm; font-size:9pt; }}
    .tc .signline div {{ width:52mm; border-top:0.3mm solid #444; margin-top:9mm; padding-top:1mm; }}
    .tc .sample {{ left:8mm; bottom:5mm; }}"""
    seal_chars = r["provider"]["name"][:4]
    body = f"""<div class="tc"><div class="frame">
      <h1>{e(r['provider']['name'])}</h1>
      <div class="addr">{e(r['provider']['address'])}<br>電話：{e(r['provider']['phone'])}</div>
      <div class="ttl"><h2>{e(r['document']['title'])}</h2><div>{e(r['document']['number_label'])}：{e(r['document']['number'])}</div></div>
      <table class="info">
        <tr><td class="k">{e(pat['label'])}</td><td>{e(pat['printed_as'])}</td></tr>
        <tr><td class="k">{e(rec['label'])}</td><td>{e(rec['value'])}</td></tr>
        <tr><td class="k">{e(svc['label'])}</td><td>{e(svc['printed_as'])}</td></tr>
        <tr><td class="k">{e(doc['label'])}</td><td>{e(doc['printed_as'])}</td></tr>
        <tr><td class="k">{e(doc['registration']['label'])}</td><td>{e(doc['registration']['value'])}</td></tr></table>
      <table class="items"><tr><th>項目</th><th class="c">數量</th><th class="num">單價（港幣）</th><th class="num">金額（港幣）</th></tr>{rows}</table>
      <div class="sum"><div class="big"><span class="k">{e(r['total']['label'])}</span>港幣 ${money(r['total']['amount'])}</div>
        <div><span class="k">大寫</span>{cn_upper(r['total']['amount'])}</div>
        <div><span class="k">{e(pay['label'])}</span>${money(pay['amount'])}</div></div>
      <div class="next">{e(nxt['label'])}：{e(nxt['printed_as'])}</div>
      <div class="signline"><div>中醫師簽署</div></div>
      <div class="seal">{''.join(f'<span>{c}</span>' for c in seal_chars)}</div>
      {SAMPLE}</div></div>"""
    return page(css, body, (31, 22, 148, 210), marks=True)


# =========================================================================== 5. Dental (A5 landscape treatment invoice)
def dental(r):
    doc, pat = person(r, "attending"), person(r, "patient")
    svc, rec, pid = date_of(r, "service"), date_of(r, "next"), number(r, "Patient ID")
    rows = "".join(f"<tr><td>{e(li['description'])}</td><td class='c'>{li['qty']}</td>"
                   f"<td class='num'>{money(li['unit_price'])}</td><td class='num'>{money(li['amount'])}</td></tr>"
                   for li in r["line_items"])
    adj, pay = r["adjustments"][0], r["payments"][0]
    css = f"""
    .dn {{ width:210mm; height:148mm; padding:9mm 14mm 8mm; font:8.6pt "Avenir Next", Avenir, {SANS_ZH}; position:relative;
           border-top:0.3mm solid #cfe7e7; border-bottom:0.3mm solid #cfe7e7; }}
    .dn .top {{ display:flex; justify-content:space-between; align-items:center; }}
    .dn .brand {{ display:flex; align-items:center; gap:3mm; }}
    .dn .brand svg {{ width:12mm; height:12mm; }}
    .dn .brand h1 {{ margin:0; font:600 14pt "Avenir Next", Avenir, {SANS_ZH}; color:#0e7c7b; }}
    .dn .addr {{ text-align:right; font-size:7.8pt; color:#4b5b5b; line-height:1.45; }}
    .dn .band {{ margin-top:3.5mm; background:#0e7c7b; color:#fff; border-radius:2mm; display:flex;
                 justify-content:space-between; padding:2mm 4mm; font-size:9.5pt; }}
    .dn .band b {{ letter-spacing:2px; }}
    .dn .info {{ display:grid; grid-template-columns:1.05fr 1fr; gap:1mm 8mm; margin:3mm 0 2.5mm; line-height:1.5; }}
    .dn .info span {{ color:#5d7070; display:inline-block; width:41mm; }}
    .dn table {{ width:100%; }}
    .dn th {{ text-align:left; color:#0e7c7b; font-weight:600; border-bottom:0.4mm solid #0e7c7b; padding:1.3mm 1mm; }}
    .dn th.num {{ text-align:right; }}
    .dn th.c, .dn td.c {{ text-align:center; width:12mm; }}
    .dn td {{ padding:1.5mm 1mm; border-bottom:0.2mm solid #d7eaea; }}
    .dn .low {{ display:flex; justify-content:space-between; align-items:flex-start; margin-top:2.5mm; }}
    .dn .recall {{ background:#e9f5f5; border-radius:2mm; padding:2.2mm 3.5mm; width:72mm; line-height:1.5; color:#234; }}
    .dn .stack {{ width:86mm; }}
    .dn .stack div {{ display:flex; justify-content:space-between; padding:0.8mm 0; }}
    .dn .stack .t {{ font-weight:700; font-size:10pt; color:#0e7c7b; border-top:0.4mm solid #0e7c7b; margin-top:0.6mm; padding-top:1.4mm; }}
    .dn .sample {{ left:14mm; bottom:4mm; }}"""
    tooth = ('<svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="19" fill="#0e7c7b"/><path d="M11 13c0-4 4-5 9-3'
             ' 5-2 9-1 9 3 0 5-2 8-3 12-1 4-2 7-4 7s-2-6-2-8-1-3-1-3-1 1-1 3-1 8-2 8-3-3-4-7c-1-4-3-7-3-12z"'
             ' fill="#fff"/></svg>')
    body = f"""<div class="dn">
      <div class="top"><div class="brand">{tooth}<h1>{e(r['provider']['name'])}</h1></div>
        <div class="addr">{addr2(r['provider']['address'])}<br>Tel 電話: {e(r['provider']['phone'])}</div></div>
      <div class="band"><b>{e(r['document']['title'])}</b><span>{e(r['document']['number_label'])}: {e(r['document']['number'])}</span></div>
      <div class="info">
        <div><span>{e(pat['label'])}:</span>{e(pat['printed_as'])}</div>
        <div><span>{e(doc['label'])}:</span>{e(doc['printed_as'])}, {e(doc['qualification'])}</div>
        <div><span>{e(pid['label'])}:</span>{e(pid['value'])}</div>
        <div><span>{e(doc['registration']['label'])}:</span>{e(doc['registration']['value'])}</div>
        <div><span>{e(svc['label'])}:</span>{e(svc['printed_as'])}</div></div>
      <table><tr><th>Treatment 治療項目</th><th class="c">Qty</th><th class="num">Unit (HK$)</th><th class="num">Amount (HK$)</th></tr>{rows}</table>
      <div class="low"><div class="recall"><b>{e(rec['label'])}:</b> {e(rec['printed_as'])}<br>
          Regular check-ups help keep your teeth healthy. 定期檢查，保持牙齒健康。</div>
        <div class="stack"><div><span>{e(r['subtotal']['label'])}</span><span class="num">{money(r['subtotal']['amount'])}</span></div>
          <div><span>{e(adj['label'])}</span><span class="num">{money(adj['amount'])}</span></div>
          <div class="t"><span>{e(r['total']['label'])}</span><span class="num">HK${money(r['total']['amount'])}</span></div>
          <div><span>{e(pay['label'])}</span><span class="num">{money(pay['amount'])}</span></div></div></div>
      {SAMPLE}</div>"""
    return page(css, body, (0, 30, 210, 148), marks=True)


# =========================================================================== 6. Physiotherapy (A4 session + payment summary)
def physio(r):
    pt, ref, cl = person(r, "treating"), person(r, "referring"), person(r, "patient")
    svc, iss, nxt, cno = date_of(r, "service"), date_of(r, "issue"), date_of(r, "next"), number(r, "Client No.")
    rows = "".join(f"<tr><td>{e(li['description'])}</td><td class='num'>HK${money(li['amount'])}</td></tr>"
                   for li in r["line_items"])
    pay, bal = r["payments"][0], r["balance"]
    name_parts = r["provider"]["name"].split(" ", 2)  # Northpoint / Motion / Physiotherapy Centre
    css = f"""
    .ph {{ width:210mm; height:297mm; font:10pt "Avenir Next", Avenir, Helvetica, {SANS_ZH}; position:relative; color:#22303c; }}
    .ph .hdr {{ background:#22303c; color:#fff; padding:13mm 18mm 9mm; display:flex; justify-content:space-between; align-items:flex-end; }}
    .ph .hdr .logo {{ font:700 19pt Futura, "Avenir Next"; letter-spacing:1px; }}
    .ph .hdr .logo i {{ color:#f08a3c; font-style:normal; }}
    .ph .hdr .sub {{ font-size:9pt; color:#c9d3db; letter-spacing:2px; text-transform:uppercase; }}
    .ph .hdr .addr {{ text-align:right; font-size:8.3pt; color:#dfe6eb; line-height:1.5; }}
    .ph .body {{ padding:9mm 18mm; }}
    .ph .row1 {{ display:flex; justify-content:space-between; align-items:baseline; }}
    .ph .row1 h2 {{ margin:0; font:600 20pt "Avenir Next"; letter-spacing:3px; }}
    .ph .row1 div {{ text-align:right; line-height:1.6; font-size:9.5pt; }}
    .ph .row1 span {{ color:#6b7a86; }}
    .ph .cards {{ display:flex; gap:6mm; margin:7mm 0; }}
    .ph .card {{ flex:1; border:0.3mm solid #d6dde3; border-radius:3mm; padding:4mm 5mm; line-height:1.7; }}
    .ph .card h3 {{ margin:0 0 1.5mm; font-size:8.5pt; letter-spacing:1.5px; text-transform:uppercase; color:#f08a3c; }}
    .ph .card span {{ color:#6b7a86; display:inline-block; width:27mm; }}
    .ph .sess {{ display:flex; gap:12mm; padding:3.5mm 5mm; background:#f3f5f7; border-radius:2mm; }}
    .ph .sess span {{ color:#6b7a86; margin-right:2mm; }}
    .ph table {{ width:100%; margin-top:7mm; }}
    .ph th {{ text-align:left; font-size:8.5pt; letter-spacing:1px; text-transform:uppercase; color:#6b7a86;
              border-bottom:0.4mm solid #22303c; padding:2mm 0; }}
    .ph th.num {{ text-align:right; }}
    .ph td {{ padding:3mm 0; border-bottom:0.2mm solid #e1e6ea; }}
    .ph .status {{ display:flex; margin-top:9mm; border-radius:3mm; overflow:hidden; border:0.3mm solid #d6dde3; }}
    .ph .status div {{ flex:1; padding:4mm 5mm; }}
    .ph .status span {{ display:block; font-size:8.3pt; color:#6b7a86; margin-bottom:1mm; }}
    .ph .status b {{ font-size:14pt; }}
    .ph .status .due {{ background:#fdeee2; }}
    .ph .status .due b {{ color:#c4561a; }}
    .ph .note {{ margin-top:5mm; font-size:8.8pt; color:#55636e; }}
    .ph .legal {{ position:absolute; left:18mm; bottom:22mm; font-size:8pt; color:#6b7a86; }}
    .ph .sample {{ right:18mm; bottom:12mm; }}"""
    body = f"""<div class="ph">
      <div class="hdr"><div><div class="logo">{e(name_parts[0].upper())} <i>{e(name_parts[1].upper())}</i></div>
          <div class="sub">{e(name_parts[2])}</div></div>
        <div class="addr">{addr2(r['provider']['address'])}<br>Tel: {e(r['provider']['phone'])}</div></div>
      <div class="body">
        <div class="row1"><h2>{e(r['document']['title'])}</h2><div><span>{e(r['document']['number_label'])}</span>
          <b>{e(r['document']['number'])}</b><br><span>{e(iss['label'])}</span> {e(iss['printed_as'])}</div></div>
        <div class="cards">
          <div class="card"><h3>{e(cl['label'])}</h3><span>Name</span>{e(cl['printed_as'])}<br><span>{e(cno['label'])}</span>{e(cno['value'])}<br>
            <span>{e(ref['label'])}</span>{e(ref['printed_as'])}</div>
          <div class="card"><h3>{e(pt['label'])}</h3><span>Name</span>{e(pt['printed_as'])}<br><span>Title</span>{e(pt['qualification'])}<br>
            <span>{e(pt['registration']['label'])}</span>{e(pt['registration']['value'])}</div></div>
        <div class="sess"><div><span>{e(svc['label'])}</span><b>{e(svc['printed_as'])}</b></div>
          <div><span>{e(nxt['label'])}</span>{e(nxt['printed_as'])}</div></div>
        <table><tr><th>Service</th><th class="num">Fee</th></tr>{rows}</table>
        <div class="status"><div><span>{e(r['total']['label'])}</span><b>HK${money(r['total']['amount'])}</b></div>
          <div><span>{e(pay['label'])}</span><b>HK${money(pay['amount'])}</b></div>
          <div class="due"><span>{e(bal['label'])}</span><b>HK${money(bal['amount'])}</b></div></div>
        <div class="note">Please settle the outstanding balance at your next appointment. Thank you.</div>
        <div class="legal">{e(r['provider']['name'])}</div></div>
      {SAMPLE}</div>"""
    return page(css, body, (0, 0, 210, 297), marks=False)


# =========================================================================== 7. Pharmacy (80 mm thermal till slip)
def pharmacy(r):
    till, cashier, member = number(r, "收銀機"), number(r, "收銀員"), number(r, "會員號碼")
    d = r["dates"][0]
    items = "".join(f"<div class='it'>{e(li['description'])}</div><div class='ln'><span>{li['qty']} x {money(li['unit_price'])}</span>"
                    f"<span>{money(li['amount'])}</span></div>" for li in r["line_items"])
    adj, pay, extra = r["adjustments"][0], r["payments"][0], r["extra_amounts"][0]
    extra_label = split_label(extra["label"])[0]
    bars = "".join(f'<i style="width:{w}mm"></i>' for w in [0.4, 0.8, 0.3, 0.3, 1.0, 0.4, 0.6, 0.3, 0.9, 0.4, 0.3, 0.7,
                                                         0.5, 0.3, 1.0, 0.3, 0.6, 0.4, 0.8, 0.3, 0.5, 0.9, 0.3, 0.4,
                                                         0.7, 0.3, 0.6, 1.0, 0.4, 0.3, 0.8, 0.5, 0.3])
    css = f"""
    .tp {{ width:80mm; padding:6mm 5mm 6mm; font:9pt Menlo, "Courier New", {SANS_ZH}; position:relative; background:#fff;
           outline:0.2mm dashed #aaa; }}
    .tp .c {{ text-align:center; }}
    .tp .shop {{ font:bold 12.5pt {SANS_ZH}; margin-bottom:1mm; }}
    .tp .small {{ font-size:7.8pt; line-height:1.45; }}
    .tp .hr {{ border-top:0.35mm dashed #333; margin:2.2mm 0; }}
    .tp .kv {{ display:flex; justify-content:space-between; line-height:1.55; }}
    .tp .it {{ margin-top:1.4mm; }}
    .tp .ln {{ display:flex; justify-content:space-between; padding-left:3mm; }}
    .tp .tot {{ font-weight:bold; font-size:11.5pt; margin:1mm 0; }}
    .tp .bars {{ display:flex; justify-content:center; gap:0.35mm; height:10mm; margin:3mm 0 2mm; }}
    .tp .bars i {{ background:#111; display:block; }}
    .tp .sample {{ position:static; display:inline-block; margin-top:2.5mm; }}"""
    body = f"""<div class="tp">
      <div class="c shop">{e(r['provider']['name'])}</div>
      <div class="c small">{e(r['provider']['address'])}<br>電話：{e(r['provider']['phone'])}</div>
      <div class="hr"></div>
      <div class="c" style="font-weight:bold;letter-spacing:4px">{e(r['document']['title'])}</div>
      <div class="kv"><span>{e(r['document']['number_label'])}:</span><span>{e(r['document']['number'])}</span></div>
      <div class="kv"><span>{e(d['label'])}:</span><span>{e(d['printed_as'])}</span></div>
      <div class="kv"><span>{e(till['label'])}: {e(till['value'])}</span><span>{e(cashier['label'])}: {e(cashier['value'])}</span></div>
      <div class="kv"><span>{e(member['label'])}:</span><span>{e(member['value'])}</span></div>
      <div class="hr"></div>{items}<div class="hr"></div>
      <div class="kv"><span>{e(r['subtotal']['label'])}</span><span>{money(r['subtotal']['amount'])}</span></div>
      <div class="kv"><span>{e(adj['label'])}</span><span>{money(adj['amount'])}</span></div>
      <div class="kv tot"><span>{e(r['total']['label'])}</span><span>HK${money(r['total']['amount'])}</span></div>
      <div class="kv"><span>{e(pay['label'])}</span><span>{money(pay['amount'])}</span></div>
      <div class="kv"><span>{e(extra_label)}</span><span>{money(extra['amount'])}</span></div>
      <div class="hr"></div>
      <div class="bars">{bars}</div>
      <div class="c small">多謝惠顧 Thank you<br>貨品售出，恕不退換</div>
      <div class="c">{SAMPLE}</div></div>"""
    return page(css, body, (65, 20, 80, None), marks=False)


# =========================================================================== 8. Medical centre (A4 structured payment receipt)
def medical_centre(r):
    doc, nurse, pat = person(r, "attending"), person(r, "nurse"), person(r, "patient")
    svc, prt, plan = date_of(r, "service"), date_of(r, "print"), number(r, "Plan Member No.")
    plan_label, plan_name = split_label(plan["label"])
    nurse_label = split_label(nurse["label"])[0]
    performed = [f"{doc['printed_as']}", f"{nurse_label}: {nurse['printed_as']}", "Dispensary 配藥處"]
    rows = "".join(f"<tr><td>{e(li['description'])}</td><td>{e(performed[i])}</td><td class='num'>{money(li['amount'])}</td></tr>"
                   for i, li in enumerate(r["line_items"]))
    plan_pay, co_pay = r["payments"]
    en, zh = r["provider"]["name"].split(" ", 3)[:3], r["provider"]["name"].split(" ")[-1]
    css = f"""
    .mc {{ width:210mm; height:297mm; padding:18mm 18mm 16mm; font:9.6pt "Helvetica Neue", Helvetica, {SANS_ZH}; position:relative; color:#25213f; }}
    .mc .hdr {{ display:flex; align-items:center; gap:5mm; }}
    .mc .mark {{ width:15mm; height:15mm; background:#4b3f8f; border-radius:50% 50% 50% 0; color:#fff;
                 font:600 17pt "Gill Sans"; display:flex; align-items:center; justify-content:center; position:static; }}
    .mc .hdr h1 {{ margin:0; font:600 17pt "Gill Sans", {SANS_ZH}; color:#4b3f8f; }}
    .mc .hdr .zh {{ font:15pt {SANS_ZH}; color:#4b3f8f; letter-spacing:2px; }}
    .mc .hdr .addr {{ margin-left:auto; text-align:right; font-size:8.5pt; color:#5c5875; line-height:1.5; }}
    .mc .band {{ margin-top:7mm; display:flex; justify-content:space-between; align-items:center; border-top:0.6mm solid #4b3f8f;
                 border-bottom:0.6mm solid #4b3f8f; padding:2.5mm 0; }}
    .mc .band h2 {{ margin:0; font:600 14pt "Gill Sans", {SANS_ZH}; letter-spacing:2px; }}
    .mc .band b {{ font-family:"Helvetica Neue", Helvetica; }}
    .mc .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:2.5mm 10mm; margin:6mm 0; }}
    .mc .grid div {{ border-bottom:0.2mm solid #dcd8ee; padding-bottom:1.5mm; }}
    .mc .grid span {{ display:block; font-size:8pt; color:#77739a; }}
    .mc table {{ width:100%; }}
    .mc th {{ text-align:left; background:#eeebf8; color:#4b3f8f; padding:2.4mm 3mm; font-size:8.8pt; }}
    .mc th.num {{ text-align:right; }}
    .mc td {{ padding:2.6mm 3mm; border-bottom:0.2mm solid #e3e0f0; }}
    .mc .cov {{ display:flex; gap:8mm; margin-top:8mm; }}
    .mc .cov .note {{ flex:1; font-size:8.6pt; color:#5c5875; line-height:1.6; background:#f7f6fc; padding:4mm; border-radius:2mm; }}
    .mc .cov .fig {{ width:88mm; }}
    .mc .cov .fig div {{ display:flex; justify-content:space-between; padding:1.9mm 0; border-bottom:0.2mm solid #e3e0f0; }}
    .mc .cov .fig .t {{ font-weight:600; font-size:11.5pt; color:#4b3f8f; }}
    .mc .foot {{ position:absolute; left:18mm; right:18mm; bottom:22mm; display:flex; justify-content:space-between;
                 font-size:8.3pt; color:#77739a; border-top:0.2mm solid #dcd8ee; padding-top:2mm; }}
    .mc .sample {{ right:18mm; bottom:11mm; }}"""
    grid = [(pat["label"], pat["printed_as"]), (svc["label"], svc["printed_as"]),
            (doc["label"], doc["printed_as"]), (doc["registration"]["label"], doc["registration"]["value"]),
            (plan_label, f"{plan['value']} ({plan_name})"), (nurse["label"], nurse["printed_as"])]
    body = f"""<div class="mc">
      <div class="hdr"><div class="mark">C</div><div><h1>{e(' '.join(en))}</h1><div class="zh">{e(zh)}</div></div>
        <div class="addr">{addr2(r['provider']['address'])}<br>Tel 電話: {e(r['provider']['phone'])}</div></div>
      <div class="band"><h2>{e(r['document']['title'])}</h2><div>{e(r['document']['number_label'])}: <b>{e(r['document']['number'])}</b></div></div>
      <div class="grid">{''.join(f'<div><span>{e(k)}</span>{e(v)}</div>' for k, v in grid)}</div>
      <table><tr><th>Service 服務</th><th>Performed by 負責人員</th><th class="num">Amount 金額 (HK$)</th></tr>{rows}</table>
      <div class="cov"><div class="note">Charges covered under {e(plan_name)} are settled directly with the plan.
          The patient pays the co-payment shown. 計劃承保之費用由計劃直接支付，病人只需繳付自付額。</div>
        <div class="fig"><div class="t"><span>{e(r['total']['label'])}</span><span class="num">HK${money(r['total']['amount'])}</span></div>
          <div><span>{e(plan_pay['label'])}</span><span class="num">HK${money(plan_pay['amount'])}</span></div>
          <div><span>{e(co_pay['label'])}</span><span class="num">HK${money(co_pay['amount'])}</span></div></div></div>
      <div class="foot"><span>{e(prt['label'])}: {e(prt['printed_as'])}</span><span>Thank you for choosing {e(' '.join(en))}.</span></div>
      {SAMPLE}</div>"""
    return page(css, body, (0, 0, 210, 297), marks=False)


TEMPLATES = {"r1": gp, "r2": specialist, "r3": hospital, "r4": tcm, "r5": dental, "r6": physio, "r7": pharmacy,
             "r8": medical_centre}


# =========================================================================== rendering and checks
def to_pdf(html_text: str, out: Path, workdir: Path) -> None:
    src = workdir / f"{out.stem}.html"
    src.write_text(html_text, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--hide-scrollbars",
                    f"--print-to-pdf={out}", src.as_uri()], check=True, capture_output=True, timeout=120)


def pdf_text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", str(pdf), "-"], check=True, capture_output=True, text=True).stdout


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def expected_strings(r: dict) -> list[str]:
    """Every value the spec says must appear on the receipt, as printed."""
    out = [r["provider"]["name"].split(" – ")[0], r["provider"]["phone"], r["document"]["number"], "SAMPLE/測試樣本"]
    for p in r["people"]:
        out.append(p["printed_as"])
        if p.get("registration"):
            out.append(p["registration"]["value"])
    out += [d["printed_as"] for d in r["dates"]]
    out += [n["value"] for n in r["other_numbers"]]
    for li in r["line_items"]:
        out += [li["description"], money(li["amount"])]
    for part in ([r["subtotal"]] if r["subtotal"] else []) + r["adjustments"] + [r["total"]] + r["payments"] + \
            ([r["balance"]] if r["balance"] else []) + r.get("extra_amounts", []):
        out.append(money(part["amount"]))
    gt = r["ground_truth"]
    out += [v if f != "total_amount" else money(v) for f, v in gt.items() if v != "N/A" and f != "service_date"]
    return out


def script_parts(s: str) -> list[str]:
    """Splits a bilingual value into its English and Chinese runs, which may wrap onto separate lines."""
    return [p for p in re.split(r"\s*([\u3000-\u9fff\uff00-\uffef]+[^A-Za-z]*)\s*", s) if p and p.strip()]


def validate_pdfs(spec: dict) -> list[str]:
    problems = []
    for r in spec["receipts"]:
        pdf = PRINTABLE / f"{r['file_stem']}.pdf"
        text = squash(pdf_text(pdf)).lower()
        for s in expected_strings(r):
            for part in script_parts(s):
                if squash(part).lower() not in text:
                    problems.append(f"{r['file_stem']}: {part!r} (from {s!r}) not found in the PDF text")
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        if not re.search(r"^Pages:\s+1$", info, re.M) or "(A4)" not in info:
            problems.append(f"{r['file_stem']}: PDF is not exactly one A4 page")
        if r["ground_truth"]["doctor_name"] == "N/A" and re.search(r"dr\.|醫生|醫師", text):
            problems.append(f"{r['file_stem']}: a practitioner appears although doctor_name is N/A")
    return problems


def previews_and_contact_sheet(spec: dict, workdir: Path) -> None:
    PREVIEW.mkdir(exist_ok=True)
    thumbs = []
    for r in spec["receipts"]:
        stem = r["file_stem"]
        subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", str(PRINTABLE / f"{stem}.pdf"),
                        str(PREVIEW / stem)], check=True)
        thumbs.append((r, Image.open(PREVIEW / f"{stem}.png").convert("RGB")))
    tw, th, pad, label_h = 420, 594, 24, 46
    sheet = Image.new("RGB", (4 * tw + 5 * pad, 2 * (th + label_h) + 3 * pad), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    for i, (r, im) in enumerate(thumbs):
        im.thumbnail((tw, th))
        x = pad + (i % 4) * (tw + pad)
        y = pad + (i // 4) * (th + label_h + pad)
        draw.rectangle([x - 1, y - 1, x + tw, y + th], outline="#999999")
        sheet.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        draw.text((x, y + th + 8), f"{r['file_stem']}: {r['type']}", fill="black", font=font)
        draw.text((x, y + th + 27), r["language"].split(" (")[0], fill="#555555", font=font)
    sheet.save(PREVIEW / "contact_sheet.png", optimize=True)


def main() -> None:
    spec = json.loads((HERE / "receipts_spec.json").read_text())
    sys.path.insert(0, str(HERE))
    from build_ground_truth import validate  # the same arithmetic / format checks as the ground truth
    errors = validate(spec)
    if errors:
        sys.exit("Spec validation failed:\n- " + "\n- ".join(errors))
    PRINTABLE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for r in spec["receipts"]:
            to_pdf(TEMPLATES[r["receipt_id"]](r), PRINTABLE / f"{r['file_stem']}.pdf", Path(tmp))
            print(f"printable/{r['file_stem']}.pdf  ({r['type']})")
        previews_and_contact_sheet(spec, Path(tmp))
    problems = validate_pdfs(spec)
    if problems:
        sys.exit("PDF check failed:\n- " + "\n- ".join(problems))
    print("All 8 PDFs contain every specified value; previews and contact sheet written to preview/.")


if __name__ == "__main__":
    main()
