| receipt | field | ground truth | light | light result | heavy | heavy result |
|---|---|---|---|---|---|---|
| receipt1 | doctor_name | Dr. Lau Sai Kit, Lawrence | Dr. Lau Sat Kit, Lawrenc | Wrong | Dr. Lau Sal Kit, Lawrencce | Wrong |
| receipt1 | registration_number | na | null | Correctly null | null | Correctly null |
| receipt1 | patient_name | na | null | Correctly null | null | Correctly null |
| receipt1 | receipt_number | na | null | Correctly null | null | Correctly null |
| receipt1 | service_date | 2026-07-02 | 2026-02-07 | Correct (d/m) | 2026-02-07 | Correct (d/m) |
| receipt1 | total_amount | 1540 | 1540.0 | Correct | 1540.0 | Correct |
| receipt2 | doctor_name | 李俊年 | 李俊年医生 | Correct | 李俊年醫生 | Correct |
| receipt2 | registration_number | na | null | Correctly null | null | Correctly null |
| receipt2 | patient_name | na | Carol Tse | Wrong | Carol Tse | Wrong |
| receipt2 | receipt_number | na | null | Correctly null | null | Correctly null |
| receipt2 | service_date | 2026-11-07 | 2026-07-11 | Correct (d/m) | 2026-07-11 | Correct (d/m) |
| receipt2 | total_amount | 998 | 998.0 | Correct | 998.0 | Correct |
| receipt3 | doctor_name | Lee Tin Tin, Becku | null | Missing | null | Missing |
| receipt3 | registration_number | na | null | Correctly null | null | Correctly null |
| receipt3 | patient_name | na | null | Correctly null | null | Correctly null |
| receipt3 | receipt_number | 967157032 | 967157032 | Correct | 967157032 | Correct |
| receipt3 | service_date | 2026-07-01 | 2026-01-07 | Correct (d/m) | 2026-01-07 | Correct (d/m) |
| receipt3 | total_amount | 10 | 10.0 | Correct | 10.0 | Correct |
| receipt4 | doctor_name | Angel Tseng, Lok Yi Choi | null | Missing | null | Missing |
| receipt4 | registration_number | na | null | Correctly null | null | Correctly null |
| receipt4 | patient_name | Fuk Jai | null | Missing | null | Missing |
| receipt4 | receipt_number | 369303 | 369303 | Correct | 369303 | Correct |
| receipt4 | service_date | 2023-02-09 | 2023-02-09 | Correct | 2023-02-09 | Correct |
| receipt4 | total_amount | 1361 | 1361.0 | Correct | 1361.0 | Correct |
| receipt5 | doctor_name | Dr. Fung Ka Kit Paul | Dr. Fung Ka Kit Paul | Correct | Dr. Fung Ka Kit Paul | Correct |
| receipt5 | registration_number | na | null | Correctly null | null | Correctly null |
| receipt5 | patient_name | Happy Lam | Happy Lam | Correct | Happy Lam | Correct |
| receipt5 | receipt_number | na | null | Correctly null | null | Correctly null |
| receipt5 | service_date | 2026-09-01 | 2026-01-09 | Correct (d/m) | 2026-01-09 | Correct (d/m) |
| receipt5 | total_amount | 20 | 20.0 | Correct | 20.0 | Correct |
| receipt6 | doctor_name | Dr Jessica Sterenborg | Dr. Jessica Sterenborg | Correct | Dr. Jessica Sterenborg | Correct |
| receipt6 | registration_number | na | null | Correctly null | null | Correctly null |
| receipt6 | patient_name | Nikita Hubber | null | Missing | null | Missing |
| receipt6 | receipt_number | 9990000505906 | null | Missing | null | Missing |
| receipt6 | service_date | 2017-03-24 | null | Missing | null | Missing |
| receipt6 | total_amount | 51.2 | 51.2 | Correct | 51.2 | Correct |

| field | light | heavy |
|---|---|---|
| doctor_name | 3/6 | 3/6 |
| registration_number | 6/6 | 6/6 |
| patient_name | 3/6 | 3/6 |
| receipt_number | 5/6 | 5/6 |
| service_date | 5/6 | 5/6 |
| total_amount | 6/6 | 6/6 |
| **all fields** | **28/36** | **28/36** |
| Correct | 17 | 17 |
| Correctly null | 11 | 11 |
| Wrong | 2 | 2 |
| Missing | 6 | 6 |

| engine | mean OCR predict ms | mean extraction ms |
|---|---|---|
| light | 8666 | 4.74 |
| heavy | 37000 | 5.07 |
