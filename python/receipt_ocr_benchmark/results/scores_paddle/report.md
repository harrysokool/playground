## Overall

| | paddle_light | paddle_heavy |
|---|---|---|
| Correct / applicable | 18/25 | 18/25 |
| **Accuracy** | **72.0%** | **72.0%** |
| Invented values (field not on receipt) | 0 | 0 |
| Receipts with no result (of 6) | 0 | 0 |
| Mean processing time per receipt | 8.7 s | 35.8 s |

## Accuracy by field (correct / applicable)

| | paddle_light | paddle_heavy |
|---|---|---|
| doctor_name | 3/6 (50.0%) | 3/6 (50.0%) |
| registration_number | 0/0 (all N/A) | 0/0 (all N/A) |
| patient_name | 2/4 (50.0%) | 2/4 (50.0%) |
| receipt_number | 2/3 (66.7%) | 2/3 (66.7%) |
| service_date | 5/6 (83.3%) | 5/6 (83.3%) |
| total_amount | 6/6 (100.0%) | 6/6 (100.0%) |

## Detail

| receipt | field | ground truth | paddle_light | paddle_heavy |
|---|---|---|---|---|
| receipt1 | doctor_name | Dr. Lau Sai Kit, Lawrence | Dr. Lau Sat Kit, Lawrenc → Wrong | Dr. Lau Sal Kit, Lawrencce → Wrong |
| receipt1 | registration_number | na | null → N/A | null → N/A |
| receipt1 | patient_name | na | null → N/A | null → N/A |
| receipt1 | receipt_number | na | null → N/A | null → N/A |
| receipt1 | service_date | 2026-02-07 | 2026-02-07 → Correct | 2026-02-07 → Correct |
| receipt1 | total_amount | 1540 | 1540.0 → Correct | 1540.0 → Correct |
| receipt2 | doctor_name | 李俊年 | 李俊年医生 → Correct | 李俊年醫生 → Correct |
| receipt2 | registration_number | na | null → N/A | null → N/A |
| receipt2 | patient_name | Carol Tse | Carol Tse → Correct | Carol Tse → Correct |
| receipt2 | receipt_number | na | null → N/A | null → N/A |
| receipt2 | service_date | 2026-07-11 | 2026-07-11 → Correct | 2026-07-11 → Correct |
| receipt2 | total_amount | 998 | 998.0 → Correct | 998.0 → Correct |
| receipt3 | doctor_name | Lee Tin Tin, Becky | null → Wrong | null → Wrong |
| receipt3 | registration_number | na | null → N/A | null → N/A |
| receipt3 | patient_name | na | null → N/A | null → N/A |
| receipt3 | receipt_number | 967157032 | 967157032 → Correct | 967157032 → Correct |
| receipt3 | service_date | 2026-01-07 | 2026-01-07 → Correct | 2026-01-07 → Correct |
| receipt3 | total_amount | 10 | 10.0 → Correct | 10.0 → Correct |
| receipt4 | doctor_name | Angel Tseng, Lok Yi Choi | null → Wrong | null → Wrong |
| receipt4 | registration_number | na | null → N/A | null → N/A |
| receipt4 | patient_name | Fuk Jai | null → Wrong | null → Wrong |
| receipt4 | receipt_number | 369303 | 369303 → Correct | 369303 → Correct |
| receipt4 | service_date | 2023-02-09 | 2023-02-09 → Correct | 2023-02-09 → Correct |
| receipt4 | total_amount | 1361 | 1361.0 → Correct | 1361.0 → Correct |
| receipt5 | doctor_name | Dr. Fung Ka Kit Paul | Dr. Fung Ka Kit Paul → Correct | Dr. Fung Ka Kit Paul → Correct |
| receipt5 | registration_number | na | null → N/A | null → N/A |
| receipt5 | patient_name | Happy Lam | Happy Lam → Correct | Happy Lam → Correct |
| receipt5 | receipt_number | na | null → N/A | null → N/A |
| receipt5 | service_date | 2026-01-09 | 2026-01-09 → Correct | 2026-01-09 → Correct |
| receipt5 | total_amount | 20 | 20.0 → Correct | 20.0 → Correct |
| receipt6 | doctor_name | Dr Jessica Sterenborg | Dr. Jessica Sterenborg → Correct | Dr. Jessica Sterenborg → Correct |
| receipt6 | registration_number | na | null → N/A | null → N/A |
| receipt6 | patient_name | Nikita Hubber | null → Wrong | null → Wrong |
| receipt6 | receipt_number | 9990000505906 | null → Wrong | null → Wrong |
| receipt6 | service_date | 2017-03-24 | null → Wrong | null → Wrong |
| receipt6 | total_amount | 51.2 | 51.2 → Correct | 51.2 → Correct |
