# Multilingual rules baseline (retrospective)

**Purpose:** a fairer rules comparison. The original general rules
(`receipt_bench/extraction_general.py`, 37.3% on PaddleOCR Light and 41.2% on Azure DI) knew English
labels only. This baseline adds common Chinese label translations and basic bilingual handling, and
nothing else.

**This is a retrospective baseline, not an independent test.** We have already examined the nine
Version 2 receipts, so the results cannot be treated as accuracy on unseen receipts. To limit
tuning:
- the rules below were written and committed **before** the baseline was scored;
- they are not changed after scoring.

**Implementation:** `receipt_bench/extraction_multilingual.py`, run with
`extract_cli --rules multilingual`. It is a separate module: the original general rules, the
improved rules and all saved results are unchanged.

## What was not done

- Nothing is taken from the improved rules (`extraction_improved.py`), and none of its mechanisms are
  reused: distractor labels, card layouts, total fallback order, qualification stripping, and so on.
- No receipt-specific patterns and no new label concepts. Only labels that already exist in English
  get a translation.
- No changes to the geometry, value checks or field logic of the original rules.

## Rules added

### 1. Label translations

Each existing English label gets its common Traditional Chinese (HK) and Simplified Chinese
equivalents. An English label is skipped when there is no single common receipt translation.

| Field | English label (original) | Traditional | Simplified |
|---|---|---|---|
| Doctor | attending doctor | 主診醫生 | 主诊医生 |
| | doctor name | 醫生姓名 | 医生姓名 |
| | doctor | 醫生 | 医生 |
| | physician | 醫師 | 医师 |
| | veterinarian | 獸醫 | 兽医 |
| | medical practitioner, practitioner, clinician, prescriber, provider (name) | not translated | |
| Patient | patient name / name of patient | 病人姓名, 患者姓名 | 病人姓名, 患者姓名 |
| | patient | 病人, 患者 | 病人, 患者 |
| | client name, customer name | 客戶姓名 | 客户姓名 |
| | pet name | 寵物名稱 | 宠物名称 |
| | name | 姓名 | 姓名 |
| Registration no. | registration number / no, reg. no | 註冊編號, 註冊號碼 | 注册编号, 注册号码 |
| | licence no / license no | 牌照號碼 | 牌照号码 |
| Receipt no. | receipt number / no / # | 收據編號, 收據號碼 | 收据编号, 收据号码 |
| | invoice number / no / # | 發票編號, 發票號碼 | 发票编号, 发票号码 |
| | bill number / no | 單據編號 | 单据编号 |
| | reference no / ref no | 參考編號 | 参考编号 |
| | transaction no | 交易編號 | 交易编号 |
| Service date (first tier) | service date / date of service | 服務日期 | 服务日期 |
| | consultation date | 診症日期 | 诊症日期 |
| | visit date | 就診日期 | 就诊日期 |
| | treatment date | 治療日期 | 治疗日期 |
| | admission date | 入院日期 | 入院日期 |
| Document date (second tier) | invoice date | 發票日期 | 发票日期 |
| | receipt date | 收據日期 | 收据日期 |
| | bill date | 單據日期 | 单据日期 |
| | date | 日期 | 日期 |
| Total | grand total | 總計 | 总计 |
| | total amount (due) | 總金額, 總額 | 总金额, 总额 |
| | total payable | 應付總額 | 应付总额 |
| | total | 合計, 總數 | 合计, 总数 |
| Paid | payment received | 已收款項 | 已收款项 |
| | amount paid | 已付金額 | 已付金额 |
| | paid | 已付 | 已付 |
| Subtotal | subtotal | 小計 | 小计 |
| Tax / charge | tax | 稅項, 稅 | 税项, 税 |
| | service charge | 服務費 | 服务费 |
| Balance | balance due | 尚欠餘額 | 尚欠余额 |
| | amount due | 應付金額 | 应付金额 |
| | balance | 餘額, 結餘 | 余额, 结余 |

English labels keep their original order. The Chinese labels of each group follow them, longest
first, so the more specific label wins, as in the original rules.

A Chinese label must be followed by a separator, a space or the end of the block. For example, 病人
does not match 病人編號 ("patient number"); this follows the original word-boundary rule.

### 2. Basic bilingual support

1. **Full-width colon:** `：` counts as a separator, the same as `:`.
2. **A translation is not a value:** if the text right after a matched label is a label in the other
   language (e.g. "Patient 病人" or "病人 Patient"), it is skipped. The value is then looked for as
   before: the rest of the block, then the block to the right, then the block below. A following label
   in the same language is left alone, so English-only text behaves exactly as in the original rules.
3. **A label is not a value:** a candidate value that starts with a known Chinese label (any field) or
   with a common Chinese form word is rejected, the same way the original English form words are.
   The English check is unchanged. Chinese form words, translating part of the original list: 地址, 電話/电话, 年齡/年龄,
   性別/性别, 金額/金额, 數量/数量, 單價/单价, 項目/项目, 備註/备注, 診所/诊所, 醫院/医院.

### 3. Chinese date format

`YYYY年M月D日` (spaces allowed) is read as a date. Every other date rule is unchanged.

## Results (retrospective, Version 2, nine receipts)

The rules above were committed in `388fad9` before any scoring. Nothing was changed after scoring.
Saved OCR was reused: no OCR or API calls.

Files:
- extraction output: `results/v2/extracted_multilingual_light/` and
  `results/v2/extracted_multilingual_azure_di/`;
- scores: `results/v2/scores_multilingual/` (summary.csv, detail.csv, report.md).

| | Original rules (English only) | Multilingual baseline | AOAI, original prompt |
|---|---|---|---|
| PaddleOCR Light | 37.3% (19/51) | **51.0% (26/51)** | |
| Azure DI | 41.2% (21/51) | **70.6% (36/51)** | 88.2% (45/51) |

- **Fixed and broken:** PaddleOCR Light fixed 7 fields and broke 0; Azure DI fixed 15 and broke 0.
- **No invented values,** and all 9 receipts were processed by every approach.

### Accuracy by field

| Field (applicable receipts) | Light original | Light multilingual | DI original | DI multilingual | AOAI original |
|---|---|---|---|---|---|
| Doctor (9) | 33.3% | 44.4% | 33.3% | 55.6% | 66.7% |
| Registration no. (6) | 16.7% | 16.7% | 16.7% | 50.0% | 83.3% |
| Patient (9) | 33.3% | 66.7% | 33.3% | 77.8% | 100.0% |
| Receipt no. (9) | 44.4% | 55.6% | 44.4% | 88.9% | 100.0% |
| Service date (9) | 33.3% | 44.4% | 44.4% | 66.7% | 88.9% |
| Total (9) | 55.6% | 66.7% | 66.7% | 77.8% | 88.9% |

### Remaining errors (no further tuning)

**Azure DI, 15 errors.** PaddleOCR Light makes all of these too.

| Cause | Fields |
|---|---|
| A label concept the original English rules never had, so by design it was not translated: "Attendance Date", 主診中醫師 / 註冊中醫編號 (Chinese-medicine practitioner), "Dentist" | receipt3 date (fell back to the invoice date), receipt4 doctor and reg. no., receipt5 doctor |
| The label is in the middle of a line ("MBBS (HK) · Reg. No. M17642"); the original rules only match labels that start a block | receipt1 and receipt2 reg. no. |
| Layout logic the original rules lack: the amount is beyond the distance limit, so the column sum (the subtotal) is used; a role header with a "Name" row under it; an issue date taken for the service date; amounts in a card row | receipt5 total, receipt6 doctor (the referring doctor was taken), date, total |
| The two receipts carried over from Version 1: OCR misread the signature, two practitioners in the ground truth; "FPatient:" OCR artefact; no labels at all; the open print-date question | receipt9 doctor and patient, receipt10 patient, receipt no. and date |

**PaddleOCR Light, 10 more errors, all from how the OCR wrote the labels:**
- words glued together: "Patient病人：", "Reg.No.註冊編號：", "TreatmentDate治療日期", "VisitDate就診日期",
  "AttendingDoctor";
- Simplified characters inside Traditional labels: "收據编號", "註冊编號", "發票编號";
- "HKS" read for "HK$" in front of a total.

The exact-match labels do not recognise these forms (receipt2 total, receipt3 receipt no., receipt5
patient, receipt no., reg. no. and date, receipt8 doctor, receipt no., reg. no. and date). On receipt8 the
glued "AttendingDoctor" label was missed, so the unlabelled "<name>醫生" pattern also picked up 主診醫生
as a second doctor candidate, and the doctor was left empty as ambiguous. Handling these would need
OCR-tolerant label matching, which is a further rule change and was not made.

### What this means

- **Language support explains part of the gap, not all of it.**
  - Adding Chinese labels brought Azure DI + rules from 41.2% to 70.6%, against 88.2% for AOAI with its
    original prompt.
  - PaddleOCR Light gained less (51.0%), because its OCR output distorts bilingual labels.
- **What remains needs more scenario-specific logic.** The remaining rule errors need new label
  concepts, labels inside lines, layout handling or OCR-tolerant matching: the kind of logic the
  improved rules added after reviewing these receipts.
- **Retrospective only.** These receipts were already known when the rules were written, so neither
  figure is an estimate for new receipts.
