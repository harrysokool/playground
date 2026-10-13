## Overall

| | paddle_light_general | paddle_light_improved | paddle_heavy_general | paddle_heavy_improved | azure_di_general | azure_di_improved | azure_di_aoai |
|---|---|---|---|---|---|---|---|
| Correct / applicable | 19/51 | 45/51 | 15/51 | 33/51 | 21/51 | 44/51 | 45/51 |
| **Accuracy** | **37.3%** | **88.2%** | **29.4%** | **64.7%** | **41.2%** | **86.3%** | **88.2%** |
| Invented values (field not on receipt) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Receipts processed successfully (of 9) | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| Receipts with no result (of 9) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Mean processing time per receipt | 13.9 s | 13.9 s | 53.3 s | 53.3 s | 3.8 s | 3.8 s | 6.2 s |
| AOAI input tokens (total, per receipt) | — | — | — | — | — | — | 5,421 (602/receipt) |
| AOAI output tokens incl. reasoning | — | — | — | — | — | — | 2,368 (263/receipt) |
| of which reasoning tokens | — | — | — | — | — | — | 1,728 (192/receipt) |

## Accuracy by field (correct / applicable)

| | paddle_light_general | paddle_light_improved | paddle_heavy_general | paddle_heavy_improved | azure_di_general | azure_di_improved | azure_di_aoai |
|---|---|---|---|---|---|---|---|
| doctor_name | 3/9 (33.3%) | 8/9 (88.9%) | 2/9 (22.2%) | 6/9 (66.7%) | 3/9 (33.3%) | 8/9 (88.9%) | 6/9 (66.7%) |
| registration_number | 1/6 (16.7%) | 6/6 (100.0%) | 1/6 (16.7%) | 4/6 (66.7%) | 1/6 (16.7%) | 6/6 (100.0%) | 5/6 (83.3%) |
| patient_name | 3/9 (33.3%) | 7/9 (77.8%) | 2/9 (22.2%) | 5/9 (55.6%) | 3/9 (33.3%) | 7/9 (77.8%) | 9/9 (100.0%) |
| receipt_number | 4/9 (44.4%) | 7/9 (77.8%) | 3/9 (33.3%) | 5/9 (55.6%) | 4/9 (44.4%) | 7/9 (77.8%) | 9/9 (100.0%) |
| service_date | 3/9 (33.3%) | 8/9 (88.9%) | 2/9 (22.2%) | 6/9 (66.7%) | 4/9 (44.4%) | 8/9 (88.9%) | 8/9 (88.9%) |
| total_amount | 5/9 (55.6%) | 9/9 (100.0%) | 5/9 (55.6%) | 7/9 (77.8%) | 6/9 (66.7%) | 8/9 (88.9%) | 8/9 (88.9%) |

## Detail

| receipt | field | ground truth | paddle_light_general | paddle_light_improved | paddle_heavy_general | paddle_heavy_improved | azure_di_general | azure_di_improved | azure_di_aoai |
|---|---|---|---|---|---|---|---|---|---|
| receipt1 | doctor_name | Dr. Tsang Hoi Lam | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct |
| receipt1 | registration_number | M17642 | null → Wrong | M17642 → Correct | null → Wrong | M17642 → Correct | null → Wrong | M17642 → Correct | MBBS (HK) · Reg. No. M17642 → Wrong |
| receipt1 | patient_name | Leung Wai Kei | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct |
| receipt1 | receipt_number | HFC-260314-0087 | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct |
| receipt1 | service_date | 2026-03-14 | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct |
| receipt1 | total_amount | 550 | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct |
| receipt2 | doctor_name | Dr. Ng Chun Yip | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct | null → Wrong | null → Wrong | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct |
| receipt2 | registration_number | M20581 | null → Wrong | M20581 → Correct | null → Wrong | null → Wrong | null → Wrong | M20581 → Correct | M20581 → Correct |
| receipt2 | patient_name | Ho Siu Ming | Ho Siu Ming → Correct | Ho Siu Ming → Correct | null → Wrong | null → Wrong | Ho Siu Ming → Correct | Ho Siu Ming → Correct | Ho Siu Ming → Correct |
| receipt2 | receipt_number | SC2026/01593 | SC2026/01593 → Correct | SC2026/01593 → Correct | null → Wrong | null → Wrong | SC2026/01593 → Correct | SC2026/01593 → Correct | SC2026/01593 → Correct |
| receipt2 | service_date | 2026-04-22 | 2026-04-22 → Correct | 2026-04-22 → Correct | null → Wrong | null → Wrong | 2026-04-22 → Correct | 2026-04-22 → Correct | 2026-04-22 → Correct |
| receipt2 | total_amount | 1880 | null → Wrong | 1880.0 → Correct | null → Wrong | null → Wrong | 1880.0 → Correct | 1880.0 → Correct | 1880.0 → Correct |
| receipt3 | doctor_name | Dr. Chow Ka Ho | 主診醫生 → Wrong | Dr. Chow Ka Ho → Correct | 主诊醫生 → Wrong | Dr. Chow Ka Ho → Correct | 主診醫生 → Wrong | Dr. Chow Ka Ho → Correct | Dr. Chow Ka Ho → Correct |
| receipt3 | registration_number | na | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A |
| receipt3 | patient_name | TAM KA YAN | 病人 → Wrong | TAM KA YAN → Correct | null → Wrong | TAM KA YAN → Correct | 病人 → Wrong | TAM KA YAN → Correct | TAM KA YAN → Correct |
| receipt3 | receipt_number | OPI-2026-0048213 | null → Wrong | OPI-2026-0048213 → Correct | null → Wrong | OPI-2026-0048213 → Correct | null → Wrong | OPI-2026-0048213 → Correct | OPI-2026-0048213 → Correct |
| receipt3 | service_date | 2026-05-18 | null → Wrong | 2026-05-18 → Correct | null → Wrong | 2026-05-18 → Correct | null → Wrong | 2026-05-18 → Correct | 2026-05-18 → Correct |
| receipt3 | total_amount | 2195.5 | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct |
| receipt4 | doctor_name | 葉卓謙 | null → Wrong | 葉卓謙 → Correct | null → Wrong | 葉卓謙 → Correct | null → Wrong | 葉卓謙 → Correct | 葉卓謙 → Correct |
| receipt4 | registration_number | 006821 | null → Wrong | 006821 → Correct | null → Wrong | 006821 → Correct | null → Wrong | 006821 → Correct | 006821 → Correct |
| receipt4 | patient_name | 麥詠琳 | null → Wrong | 麥詠琳 → Correct | null → Wrong | 麥詠琳 → Correct | null → Wrong | 麥詠琳 → Correct | 麥詠琳 → Correct |
| receipt4 | receipt_number | Y2605117 | null → Wrong | Y2605117 → Correct | null → Wrong | Y2605117 → Correct | null → Wrong | Y2605117 → Correct | Y2605117 → Correct |
| receipt4 | service_date | 2026-06-09 | null → Wrong | 2026-06-09 → Correct | null → Wrong | 2026-06-09 → Correct | null → Wrong | 2026-06-09 → Correct | 2026年6月9日 → Correct |
| receipt4 | total_amount | 790 | null → Wrong | 790.0 → Correct | null → Wrong | 790.0 → Correct | null → Wrong | 790.0 → Correct | 790.0 → Correct |
| receipt5 | doctor_name | Dr. Ho Ching Yee | null → Wrong | Dr. Ho Ching Yee → Correct | null → Wrong | null → Wrong | null → Wrong | Dr. Ho Ching Yee → Correct | Dr. Ho Ching Yee, BDS (HK) → Wrong |
| receipt5 | registration_number | D03158 | null → Wrong | D03158 → Correct | null → Wrong | null → Wrong | null → Wrong | D03158 → Correct | D03158 → Correct |
| receipt5 | patient_name | 馮浩霖 | null → Wrong | 馮浩霖 → Correct | null → Wrong | null → Wrong | 病人 → Wrong | 馮浩霖 → Correct | 馮浩霖 → Correct |
| receipt5 | receipt_number | DEN-77342 | null → Wrong | DEN-77342 → Correct | null → Wrong | null → Wrong | null → Wrong | DEN-77342 → Correct | DEN-77342 → Correct |
| receipt5 | service_date | 2026-06-27 | null → Wrong | 2026-06-27 → Correct | null → Wrong | null → Wrong | null → Wrong | 2026-06-27 → Correct | 2026-06-27 → Correct |
| receipt5 | total_amount | 1575 | 1750.0 → Wrong | 1575.0 → Correct | null → Wrong | null → Wrong | 1750.0 → Wrong | 1750.0 → Wrong | 1575.0 → Correct |
| receipt6 | doctor_name | CHEUNG Hoi Ying | Dr. Kwok Man Hin → Wrong | CHEUNG Hoi Ying → Correct | Dr. Kwok Man Hin → Wrong | CHEUNG Hoi Ying → Correct | Dr. Kwok Man Hin → Wrong | CHEUNG Hoi Ying → Correct | CHEUNG Hoi Ying → Correct |
| receipt6 | registration_number | PT004175 | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct |
| receipt6 | patient_name | Yeung Tsz Kit | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct |
| receipt6 | receipt_number | RCP-10388 | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct |
| receipt6 | service_date | 2026-07-16 | 2026-07-17 → Wrong | 2026-07-16 → Correct | 2026-07-17 → Wrong | 2026-07-16 → Correct | 2026-07-17 → Wrong | 2026-07-16 → Correct | 2026-07-16 → Correct |
| receipt6 | total_amount | 1200 | null → Wrong | 1200.0 → Correct | null → Wrong | 1200.0 → Correct | null → Wrong | 1200.0 → Correct | 1200.0 → Correct |
| receipt8 | doctor_name | Dr. Siu Ka Wai | null → Wrong | Dr. Siu Ka Wai → Correct | 主診醫生 → Wrong | Dr. Siu Ka Wai → Correct | 主診醫生 → Wrong | Dr. Siu Ka Wai → Correct | Dr. Siu Ka Wai → Correct |
| receipt8 | registration_number | M19903 | null → Wrong | M19903 → Correct | null → Wrong | M19903 → Correct | null → Wrong | M19903 → Correct | M19903 → Correct |
| receipt8 | patient_name | 蔡嘉穎 | 病人 → Wrong | 蔡嘉穎 → Correct | 病人 → Wrong | 蔡嘉穎 → Correct | 病人 → Wrong | 蔡嘉穎 → Correct | 蔡嘉穎 → Correct |
| receipt8 | receipt_number | MC-2609-3391 | null → Wrong | MC-2609-3391 → Correct | null → Wrong | MC-2609-3391 → Correct | null → Wrong | MC-2609-3391 → Correct | MC-2609-3391 → Correct |
| receipt8 | service_date | 2026-09-03 | null → Wrong | 2026-09-03 → Correct | null → Wrong | 2026-09-03 → Correct | 2026-09-03 → Correct | 2026-09-03 → Correct | 2026-09-03 → Correct |
| receipt8 | total_amount | 795 | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct |
| receipt9 | doctor_name | Angel Tseng, Lok Yi Choi | null → Wrong | null → Wrong | null → Wrong | null → Wrong | Dr. Lok Vichol → Wrong | Dr. Lok Vichol → Wrong | Angel Tseng → Wrong |
| receipt9 | registration_number | na | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A |
| receipt9 | patient_name | Fuk Jai | null → Wrong | null → Wrong | null → Wrong | null → Wrong | null → Wrong | null → Wrong | Fuk Jai → Correct |
| receipt9 | receipt_number | 369303 | 369303 → Correct | 380048 → Wrong | 369303 → Correct | 380048 → Wrong | 369303 → Correct | 380048 → Wrong | 369303 → Correct |
| receipt9 | service_date | 2023-02-09 | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct |
| receipt9 | total_amount | 1361 | 1361.0 → Correct | 1361.0 → Correct | 1361.0 → Correct | 1361.0 → Correct | 1361.0 → Correct | 1361.0 → Correct | 1361.5 → Wrong |
| receipt10 | doctor_name | Dr Jessica Sterenborg | Dr. Jessica Sterenborg → Correct | Dr. Jessica Sterenborg → Correct | Dr. Jessica Sterenborg → Correct | Dr. Jessica Sterenborg → Correct | Dr. Jessica Sterenborg → Correct | Dr. Jessica Sterenborg → Correct | Dr Jessica Sterenborg Picton Medical Centre → Wrong |
| receipt10 | registration_number | na | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A |
| receipt10 | patient_name | Nikita Hubber | null → Wrong | null → Wrong | null → Wrong | null → Wrong | null → Wrong | null → Wrong | Nikita Hubber → Correct |
| receipt10 | receipt_number | 9990000505906 | null → Wrong | null → Wrong | null → Wrong | null → Wrong | null → Wrong | null → Wrong | 9990000505906 → Correct |
| receipt10 | service_date | 2017-03-24 | null → Wrong | 2017-03-01 → Wrong | null → Wrong | null → Wrong | null → Wrong | 2017-03-01 → Wrong | 2017-03-01 → Wrong |
| receipt10 | total_amount | 51.2 | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct |
