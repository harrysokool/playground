# receipts_v2: Ground Truth for Review

Generated from `receipts_spec.json` by `build_ground_truth.py`; edit the JSON, not this file.

## Ground truth (the six benchmark fields)

| Receipt | Type | Language | doctor_name | registration_number | patient_name | service_date | receipt_number | total_amount |
|---|---|---|---|---|---|---|---|---|
| receipt1 | General practitioner clinic | English | Dr. Tsang Hoi Lam | M17642 | Leung Wai Kei | 2026-03-14 | HFC-260314-0087 | 550.00 |
| receipt2 | Specialist clinic | English | Dr. Ng Chun Yip | M20581 | Ho Siu Ming | 2026-04-22 | SC2026/01593 | 1,880.00 |
| receipt3 | Hospital outpatient invoice | Bilingual | Dr. Chow Ka Ho | N/A | TAM KA YAN | 2026-05-18 | OPI-2026-0048213 | 2,195.50 |
| receipt4 | Traditional Chinese medicine clinic | Traditional Chinese | 葉卓謙 | 006821 | 麥詠琳 | 2026-06-09 | Y2605117 | 790.00 |
| receipt5 | Dental clinic | Bilingual | Dr. Ho Ching Yee | D03158 | 馮浩霖 | 2026-06-27 | DEN-77342 | 1,575.00 |
| receipt6 | Physiotherapy clinic | English | CHEUNG Hoi Ying | PT004175 | Yeung Tsz Kit | 2026-07-16 | RCP-10388 | 1,200.00 |
| receipt7 | Pharmacy | Traditional Chinese | N/A | N/A | N/A | 2026-08-21 | 0726-03-004519 | 127.90 |
| receipt8 | Medical centre | Bilingual | Dr. Siu Ka Wai | M19903 | 蔡嘉穎 | 2026-09-03 | MC-2609-3391 | 795.00 |

## Planned details per receipt

### receipt1: General practitioner clinic (English)

- **Provider:** Harbourfront Family Clinic, Shop 12, G/F, Harbour View Court, 33 Kwun Tong Road, Kowloon, tel. 2000 4187
- **Layout:** A5 portrait clinic letterhead; centred clinic name, doctor block under it, two-column patient/receipt details, simple charges table, payment line at the bottom.
- **Document:** RECEIPT; Receipt No.: `HFC-260314-0087`
- **Doctor** (attending doctor): Dr. Tsang Hoi Lam, MBBS (HK); Reg. No.: `M17642`
- **Patient Name** (patient): Leung Wai Kei
- **Date** (service): printed `14/03/2026` = 2026-03-14
- **Patient No.** (distractor): `HF-20931`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| Consultation | 1 | 380.00 | 380.00 |
| Medication (3 days) | 1 | 120.00 | 120.00 |
| Sick leave certificate | 1 | 50.00 | 50.00 |
| **Total** | | | **550.00** |
| Paid by Octopus | | | 550.00 |

*Simplest receipt: one date, one doctor. Patient No. is a distractor number.*

### receipt2: Specialist clinic (English)

- **Provider:** Kowloon Heart and Vascular Centre, Room 1608, 16/F, Grand Pacific Tower, 188 Nathan Road, Tsim Sha Tsui, tel. 2000 7315
- **Layout:** A4 portrait; left-aligned letterhead with specialty line, right-hand box for receipt number and dates, referral line above a bordered charges table, payment summary bottom right.
- **Document:** OFFICIAL RECEIPT; Receipt No.: `SC2026/01593`
- **Attending Doctor** (attending doctor): Dr. Ng Chun Yip, Specialist in Cardiology; Reg. No.: `M20581`
- **Referred by** (referring doctor (distractor)): Dr. Lam Pui Shan
- **Patient** (patient): Ho Siu Ming
- **Consultation Date** (service): printed `22 April 2026` = 2026-04-22
- **Receipt Date** (issue (distractor)): printed `24 April 2026` = 2026-04-24
- **File No.** (distractor): `KHV-11872`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| Specialist consultation | 1 | 1,200.00 | 1,200.00 |
| Resting electrocardiogram (ECG) | 1 | 680.00 | 680.00 |
| **Total** | | | **1,880.00** |
| Paid by Visa (card ending 4421) | | | 1,880.00 |
| Balance | | | 0.00 |

*Two doctors: the attending specialist is the answer; the referring doctor has no registration number. Receipt issued two days after the consultation.*

### receipt3: Hospital outpatient invoice (Bilingual (English / Traditional Chinese labels))

- **Provider:** Lantern Bay Hospital 朗灣醫院 – Outpatient Department 門診部, 8 Lantern Bay Road, Tuen Mun, New Territories, tel. 2000 3360
- **Layout:** A4 portrait, system-generated; hospital logo block, bilingual header grid with several reference numbers, itemised charges table with codes, insurer direct-billing section, payment and balance lines.
- **Document:** OUTPATIENT INVOICE 門診發票; Invoice No. 發票編號: `OPI-2026-0048213`
- **Attending Doctor 主診醫生** (attending doctor): Dr. Chow Ka Ho
- **Patient 病人** (patient): TAM KA YAN
- **Attendance Date 就診日期** (service): printed `18 May 2026` = 2026-05-18
- **Invoice Date 發票日期** (issue (distractor)): printed `25 May 2026` = 2026-05-25
- **Patient No. 病人編號** (distractor): `LB-0371526`
- **Episode No. 診症編號** (distractor): `E2605180412`
- **Policy No. 保單編號 (Evergreen Assurance)** (distractor): `VH-58210937`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| Specialist outpatient consultation 專科門診診症 | 1 | 950.00 | 950.00 |
| Chest X-ray 胸部X光 | 1 | 620.00 | 620.00 |
| Blood test (CBC) 血液檢查 | 1 | 380.00 | 380.00 |
| Drugs 藥物 | 1 | 245.50 | 245.50 |
| **Total Charges 總收費** | | | **2,195.50** |
| Paid by insurer (direct billing) 保險公司直接付款 | | | 1,800.00 |
| Paid by patient 病人已付 | | | 395.50 |
| Balance Due 尚欠餘額 | | | 0.00 |

*No registration number is printed (common on hospital invoices). Three distractor reference numbers. Total charges are split between the insurer and the patient.*

### receipt4: Traditional Chinese medicine clinic (Traditional Chinese)

- **Provider:** 澄溪中醫診所, 九龍旺角西洋菜南街 210 號 澄溪商業大廈 7 樓 703 室, tel. 2000 6628
- **Layout:** A5 portrait, vertical-feel Chinese letterhead with red clinic chop beside the practitioner line, boxed fields for patient and dates, short itemised list, handwritten-style signature line (printed font).
- **Document:** 收據; 收據編號: `Y2605117`
- **主診中醫師** (attending practitioner): 葉卓謙; 註冊中醫編號: `006821`
- **病人姓名** (patient): 麥詠琳
- **診症日期** (service): printed `2026年6月9日` = 2026-06-09
- **覆診日期** (next visit (distractor)): printed `2026年6月16日` = 2026-06-16
- **病歷編號** (distractor): `CX-3308`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| 診金 | 1 | 180.00 | 180.00 |
| 中藥（3劑） | 3 | 120.00 | 360.00 |
| 針灸 | 1 | 250.00 | 250.00 |
| **合計** | | | **790.00** |
| 已付（現金） | | | 790.00 |

*Chinese-only. The practitioner title is in the label, not after the name. Date in 年月日 format (see the known scoring gap in the README).*

### receipt5: Dental clinic (Bilingual (English / Traditional Chinese))

- **Provider:** Silverleaf Dental 銀葉牙科診所, Unit 502, 5/F, Eastwood Centre, 95 King's Road, North Point, tel. 2000 5194
- **Layout:** A4 landscape-oriented half page; logo left, clinic details right, treatment table with tooth numbers, subtotal / discount / total stack, recall reminder footer.
- **Document:** RECEIPT 收據; Receipt No. 收據編號: `DEN-77342`
- **Dentist 牙醫** (attending dentist): Dr. Ho Ching Yee, BDS (HK); Reg. No. 註冊編號: `D03158`
- **Patient 病人** (patient): 馮浩霖
- **Treatment Date 治療日期** (service): printed `27/06/2026` = 2026-06-27
- **Next Recall 下次覆診** (next recall (distractor)): printed `27/12/2026` = 2026-12-27
- **Patient ID 病人編號** (distractor): `SL-40217`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| Scaling and polishing 洗牙及拋光 | 1 | 650.00 | 650.00 |
| Dental X-ray 牙科X光 | 2 | 150.00 | 300.00 |
| Composite filling, tooth 36 樹脂補牙 | 1 | 800.00 | 800.00 |
| **Subtotal 小計** | | | 1,750.00 |
| Member discount 10% 會員折扣 | | | -175.00 |
| **Total 總額** | | | **1,575.00** |
| Paid by EPS 易辦事 | | | 1,575.00 |

*Bilingual labels; dentist name in English only, patient name in Chinese only. Total is after the discount.*

### receipt6: Physiotherapy clinic (English)

- **Provider:** Northpoint Motion Physiotherapy Centre, Flat B, 11/F, Java Commercial Centre, 128 Java Road, North Point, tel. 2000 8452
- **Layout:** A4 portrait, modern minimal design; header bar with logo text, two side-by-side info cards (client / practitioner), session details, charges, payment status block highlighting the outstanding balance.
- **Document:** RECEIPT; Receipt No.: `RCP-10388`
- **Physiotherapist** (treating physiotherapist): CHEUNG Hoi Ying, Registered Physiotherapist; Reg. No.: `PT004175`
- **Referred by** (referring doctor (distractor)): Dr. Kwok Man Hin
- **Client** (patient): Yeung Tsz Kit
- **Session Date** (service): printed `16 Jul 2026` = 2026-07-16
- **Date Issued** (issue (distractor)): printed `17 Jul 2026` = 2026-07-17
- **Next Appointment** (next appointment (distractor)): printed `23 Jul 2026` = 2026-07-23
- **Client No.** (distractor): `NM-5582`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| Initial physiotherapy assessment | 1 | 650.00 | 650.00 |
| Treatment: manual therapy and interferential therapy | 1 | 550.00 | 550.00 |
| **Total** | | | **1,200.00** |
| Amount Paid (FPS) | | | 700.00 |
| Outstanding Balance | | | 500.00 |

*The service provider is the physiotherapist (the answer), not the referring doctor. Three dates; only one is the session. Partly paid: the total is 1,200, not the 700 paid or the 500 outstanding.*

### receipt7: Pharmacy (Traditional Chinese (product names partly English))

- **Provider:** 晨曦藥房（荃灣店）, 新界荃灣沙咀道 68 號地下 5 號舖, tel. 2000 9036
- **Layout:** 80 mm thermal till receipt; centred shop header, till/cashier line, item lines with quantities, member discount, Octopus payment with remaining card value, footer slogan.
- **Document:** 收據; 收據編號: `0726-03-004519`
- **日期** (service): printed `21/08/2026 14:37` = 2026-08-21
- **收銀機** (distractor): `03`
- **收銀員** (distractor): `1187`
- **會員號碼** (distractor): `88301274`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| 撲熱息痛 Paracetamol 500mg 20粒 | 1 | 38.90 | 38.90 |
| 維他命C泡騰片 Vitamin C 20片 | 1 | 59.00 | 59.00 |
| 外科口罩 50個 | 1 | 45.00 | 45.00 |
| **小計** | | | 142.90 |
| 會員優惠 | | | -15.00 |
| **合計** | | | **127.90** |
| 八達通付款 | | | 127.90 |
| 八達通餘額 (remaining card value, distractor) | | | 96.50 |

*Over-the-counter purchase: no practitioner and no patient name, so three fields are N/A (tests whether approaches invent values). The Octopus remaining value is a distractor amount.*

### receipt8: Medical centre (Bilingual (English / Traditional Chinese))

- **Provider:** Crestview Medical Centre 嶺景醫療中心, 3/F, Crestview Plaza, 21 Sha Tin Centre Street, Sha Tin, tel. 2000 2759
- **Layout:** A4 portrait; corporate-style header with centre name in both languages, patient and plan details in a two-column grid, services table naming who performed each, plan coverage and co-payment section.
- **Document:** RECEIPT 收據; Receipt No. 收據編號: `MC-2609-3391`
- **Attending Doctor 主診醫生** (attending doctor): Dr. Siu Ka Wai; Reg. No. 註冊編號: `M19903`
- **Nurse 護士 (vaccination)** (nurse (distractor)): Wan Man Yi
- **Patient 病人** (patient): 蔡嘉穎
- **Visit Date 就診日期** (service): printed `3 Sep 2026` = 2026-09-03
- **Printed 列印日期** (print (same day)): printed `03/09/2026 16:52` = 2026-09-03
- **Plan Member No. 計劃會員編號 (Lumen Health Plan)** (distractor): `CP-6610428`

| Item | Qty | Unit price | Amount |
|---|---|---|---|
| General consultation 普通科診症 | 1 | 420.00 | 420.00 |
| Influenza vaccine 流感疫苗 | 1 | 280.00 | 280.00 |
| Medication (2 items) 藥物 | 1 | 95.00 | 95.00 |
| **Total 合計** | | | **795.00** |
| Covered by plan 計劃承保 | | | 695.00 |
| Co-payment paid (cash) 病人自付 | | | 100.00 |

*A doctor and a nurse both appear; the attending doctor is the answer. The print date is the same day as the visit, so it cannot change the answer. The plan pays most of the total; the patient pays a 100 co-payment.*
