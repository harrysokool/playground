## Overall

| | aoai_original | aoai_v2_rows |
|---|---|---|
| Correct / applicable | 18/25 | 18/25 |
| **Accuracy** | **72.0%** | **72.0%** |
| Invented values (field not on receipt) | 1 | 1 |
| Receipts processed successfully (of 6) | 6 | 6 |
| Receipts with no result (of 6) | 0 | 0 |
| Mean processing time per receipt | 5.4 s | 6.2 s |
| AOAI input tokens (total, per receipt) | 3,279 (546/receipt) | 5,435 (906/receipt) |
| AOAI output tokens incl. reasoning | 1,698 (283/receipt) | 2,134 (356/receipt) |
| of which reasoning tokens | 1,344 (224/receipt) | 1,728 (288/receipt) |

## Accuracy by field (correct / applicable)

| | aoai_original | aoai_v2_rows |
|---|---|---|
| doctor_name | 4/6 (66.7%) | 5/6 (83.3%) |
| registration_number | 0/0 (all N/A) | 0/0 (all N/A) |
| patient_name | 4/4 (100.0%) | 4/4 (100.0%) |
| receipt_number | 3/3 (100.0%) | 2/3 (66.7%) |
| service_date | 1/6 (16.7%) | 1/6 (16.7%) |
| total_amount | 6/6 (100.0%) | 6/6 (100.0%) |

## Detail

| receipt | field | ground truth | aoai_original | aoai_v2_rows |
|---|---|---|---|---|
| receipt1 | doctor_name | Dr. Lau Sai Kit, Lawrence | Dr. Lau Sai Kit, Lawrence → Correct | Dr. Lau Sai Kit, Lawrence → Correct |
| receipt1 | registration_number | na | null → N/A | null → N/A |
| receipt1 | patient_name | na | null → N/A | null → N/A |
| receipt1 | receipt_number | na | null → N/A | null → N/A |
| receipt1 | service_date | 2026-02-07 | 2020-02-07 → Wrong | 2020-02-07 → Wrong |
| receipt1 | total_amount | 1540 | 1540.0 → Correct | 1540.0 → Correct |
| receipt2 | doctor_name | 李俊年 | 李俊年醫生 → Correct | 李俊年醫生 → Correct |
| receipt2 | registration_number | na | null → N/A | 18228 → N/A (invented) |
| receipt2 | patient_name | Carol Tse | Carol Tse → Correct | Carol Tse → Correct |
| receipt2 | receipt_number | na | 18228 → N/A (invented) | null → N/A |
| receipt2 | service_date | 2026-07-11 | 2020-07-11 → Wrong | 2020-07-11 → Wrong |
| receipt2 | total_amount | 998 | 998.0 → Correct | 998.0 → Correct |
| receipt3 | doctor_name | Lee Tin Tin, Becky | Lee Tin Tin, Becky → Correct | Lee Tin Tin, Becky → Correct |
| receipt3 | registration_number | na | null → N/A | null → N/A |
| receipt3 | patient_name | na | null → N/A | null → N/A |
| receipt3 | receipt_number | 967157032 | 967157032 → Correct | 967157032 → Correct |
| receipt3 | service_date | 2026-01-07 | 2020-01-07 → Wrong | 2020-01-07 → Wrong |
| receipt3 | total_amount | 10 | 10.0 → Correct | 10.0 → Correct |
| receipt4 | doctor_name | Angel Tseng, Lok Yi Choi | Angel Tseng → Wrong | Dr. Lok Vichol → Wrong |
| receipt4 | registration_number | na | null → N/A | null → N/A |
| receipt4 | patient_name | Fuk Jai | Fuk Jai → Correct | Fuk Jai → Correct |
| receipt4 | receipt_number | 369303 | 369303 → Correct | 369303 → Correct |
| receipt4 | service_date | 2023-02-09 | 2023-02-09 → Correct | 2023-02-09 → Correct |
| receipt4 | total_amount | 1361 | 1361.0 → Correct | 1361.0 → Correct |
| receipt5 | doctor_name | Dr. Fung Ka Kit Paul | Dr. Fung Ka Kit Paul → Correct | Dr. Fung Ka Kit Paul → Correct |
| receipt5 | registration_number | na | null → N/A | null → N/A |
| receipt5 | patient_name | Happy Lam | Happy Lam → Correct | Happy Lam → Correct |
| receipt5 | receipt_number | na | null → N/A | null → N/A |
| receipt5 | service_date | 2026-01-09 | 2020-01-09 → Wrong | 2020-01-09 → Wrong |
| receipt5 | total_amount | 20 | 20.0 → Correct | 20.0 → Correct |
| receipt6 | doctor_name | Dr Jessica Sterenborg | Dr Jessica Sterenborg Picton Medical Centre → Wrong | Dr Jessica Sterenborg → Correct |
| receipt6 | registration_number | na | null → N/A | null → N/A |
| receipt6 | patient_name | Nikita Hubber | Nikita Hubber → Correct | Nikita Hubber → Correct |
| receipt6 | receipt_number | 9990000505906 | 9990000505906 → Correct | null → Wrong |
| receipt6 | service_date | 2017-03-24 | 2017-03-01 → Wrong | 2017-03-01 → Wrong |
| receipt6 | total_amount | 51.2 | 51.2 → Correct | 51.2 → Correct |
