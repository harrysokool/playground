## Overall

| | paddle_light_improved | azure_di_improved | aoai_original | aoai_v2_rows | aoai_v2_plain | aoai_v2_rows_image |
|---|---|---|---|---|---|---|
| Correct / applicable | 45/51 | 44/51 | 45/51 | 49/51 | 49/51 | 49/51 |
| **Accuracy** | **88.2%** | **86.3%** | **88.2%** | **96.1%** | **96.1%** | **96.1%** |
| Invented values (field not on receipt) | 0 | 0 | 0 | 0 | 0 | 0 |
| Receipts processed successfully (of 9) | 9 | 9 | 9 | 9 | 9 | 9 |
| Receipts with no result (of 9) | 0 | 0 | 0 | 0 | 0 | 0 |
| Mean processing time per receipt | 13.9 s | 3.8 s | 6.2 s | 6.4 s | 6.5 s | 8.4 s |
| AOAI input tokens (total, per receipt) | — | — | 5,421 (602/receipt) | 8,659 (962/receipt) | 8,544 (949/receipt) | 17,634 (1959/receipt) |
| AOAI output tokens incl. reasoning | — | — | 2,368 (263/receipt) | 2,188 (243/receipt) | 2,455 (273/receipt) | 2,209 (245/receipt) |
| of which reasoning tokens | — | — | 1,728 (192/receipt) | 1,536 (171/receipt) | 1,728 (192/receipt) | 1,536 (171/receipt) |

## Accuracy by field (correct / applicable)

| | paddle_light_improved | azure_di_improved | aoai_original | aoai_v2_rows | aoai_v2_plain | aoai_v2_rows_image |
|---|---|---|---|---|---|---|
| doctor_name | 8/9 (88.9%) | 8/9 (88.9%) | 6/9 (66.7%) | 8/9 (88.9%) | 8/9 (88.9%) | 8/9 (88.9%) |
| registration_number | 6/6 (100.0%) | 6/6 (100.0%) | 5/6 (83.3%) | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| patient_name | 7/9 (77.8%) | 7/9 (77.8%) | 9/9 (100.0%) | 9/9 (100.0%) | 9/9 (100.0%) | 9/9 (100.0%) |
| receipt_number | 7/9 (77.8%) | 7/9 (77.8%) | 9/9 (100.0%) | 9/9 (100.0%) | 9/9 (100.0%) | 9/9 (100.0%) |
| service_date | 8/9 (88.9%) | 8/9 (88.9%) | 8/9 (88.9%) | 8/9 (88.9%) | 8/9 (88.9%) | 8/9 (88.9%) |
| total_amount | 9/9 (100.0%) | 8/9 (88.9%) | 8/9 (88.9%) | 9/9 (100.0%) | 9/9 (100.0%) | 9/9 (100.0%) |

## Detail

| receipt | field | ground truth | paddle_light_improved | azure_di_improved | aoai_original | aoai_v2_rows | aoai_v2_plain | aoai_v2_rows_image |
|---|---|---|---|---|---|---|---|---|
| receipt1 | doctor_name | Dr. Tsang Hoi Lam | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct | Dr. Tsang Hoi Lam → Correct |
| receipt1 | registration_number | M17642 | M17642 → Correct | M17642 → Correct | MBBS (HK) · Reg. No. M17642 → Wrong | M17642 → Correct | M17642 → Correct | M17642 → Correct |
| receipt1 | patient_name | Leung Wai Kei | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct | Leung Wai Kei → Correct |
| receipt1 | receipt_number | HFC-260314-0087 | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct | HFC-260314-0087 → Correct |
| receipt1 | service_date | 2026-03-14 | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct | 2026-03-14 → Correct |
| receipt1 | total_amount | 550 | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct | 550.0 → Correct |
| receipt2 | doctor_name | Dr. Ng Chun Yip | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct | Dr. Ng Chun Yip → Correct |
| receipt2 | registration_number | M20581 | M20581 → Correct | M20581 → Correct | M20581 → Correct | M20581 → Correct | M20581 → Correct | M20581 → Correct |
| receipt2 | patient_name | Ho Siu Ming | Ho Siu Ming → Correct | Ho Siu Ming → Correct | Ho Siu Ming → Correct | Ho Siu Ming → Correct | Ho Siu Ming → Correct | Ho Siu Ming → Correct |
| receipt2 | receipt_number | SC2026/01593 | SC2026/01593 → Correct | SC2026/01593 → Correct | SC2026/01593 → Correct | SC2026/01593 → Correct | SC2026/01593 → Correct | SC2026/01593 → Correct |
| receipt2 | service_date | 2026-04-22 | 2026-04-22 → Correct | 2026-04-22 → Correct | 2026-04-22 → Correct | 2026-04-22 → Correct | 2026-04-22 → Correct | 2026-04-22 → Correct |
| receipt2 | total_amount | 1880 | 1880.0 → Correct | 1880.0 → Correct | 1880.0 → Correct | 1880.0 → Correct | 1880.0 → Correct | 1880.0 → Correct |
| receipt3 | doctor_name | Dr. Chow Ka Ho | Dr. Chow Ka Ho → Correct | Dr. Chow Ka Ho → Correct | Dr. Chow Ka Ho → Correct | Dr. Chow Ka Ho → Correct | Dr. Chow Ka Ho → Correct | Dr. Chow Ka Ho → Correct |
| receipt3 | registration_number | na | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A |
| receipt3 | patient_name | TAM KA YAN | TAM KA YAN → Correct | TAM KA YAN → Correct | TAM KA YAN → Correct | TAM KA YAN → Correct | TAM KA YAN → Correct | TAM KA YAN → Correct |
| receipt3 | receipt_number | OPI-2026-0048213 | OPI-2026-0048213 → Correct | OPI-2026-0048213 → Correct | OPI-2026-0048213 → Correct | OPI-2026-0048213 → Correct | OPI-2026-0048213 → Correct | OPI-2026-0048213 → Correct |
| receipt3 | service_date | 2026-05-18 | 2026-05-18 → Correct | 2026-05-18 → Correct | 2026-05-18 → Correct | 2026-05-18 → Correct | 2026-05-18 → Correct | 2026-05-18 → Correct |
| receipt3 | total_amount | 2195.5 | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct | 2195.5 → Correct |
| receipt4 | doctor_name | 葉卓謙 | 葉卓謙 → Correct | 葉卓謙 → Correct | 葉卓謙 → Correct | 葉卓謙 → Correct | 葉卓謙 → Correct | 葉卓謙 → Correct |
| receipt4 | registration_number | 006821 | 006821 → Correct | 006821 → Correct | 006821 → Correct | 006821 → Correct | 006821 → Correct | 006821 → Correct |
| receipt4 | patient_name | 麥詠琳 | 麥詠琳 → Correct | 麥詠琳 → Correct | 麥詠琳 → Correct | 麥詠琳 → Correct | 麥詠琳 → Correct | 麥詠琳 → Correct |
| receipt4 | receipt_number | Y2605117 | Y2605117 → Correct | Y2605117 → Correct | Y2605117 → Correct | Y2605117 → Correct | Y2605117 → Correct | Y2605117 → Correct |
| receipt4 | service_date | 2026-06-09 | 2026-06-09 → Correct | 2026-06-09 → Correct | 2026年6月9日 → Correct | 2026年6月9日 → Correct | 2026年6月9日 → Correct | 2026年6月9日 → Correct |
| receipt4 | total_amount | 790 | 790.0 → Correct | 790.0 → Correct | 790.0 → Correct | 790.0 → Correct | 790.0 → Correct | 790.0 → Correct |
| receipt5 | doctor_name | Dr. Ho Ching Yee | Dr. Ho Ching Yee → Correct | Dr. Ho Ching Yee → Correct | Dr. Ho Ching Yee, BDS (HK) → Wrong | Dr. Ho Ching Yee → Correct | Dr. Ho Ching Yee → Correct | Dr. Ho Ching Yee → Correct |
| receipt5 | registration_number | D03158 | D03158 → Correct | D03158 → Correct | D03158 → Correct | D03158 → Correct | D03158 → Correct | D03158 → Correct |
| receipt5 | patient_name | 馮浩霖 | 馮浩霖 → Correct | 馮浩霖 → Correct | 馮浩霖 → Correct | 馮浩霖 → Correct | 馮浩霖 → Correct | 馮浩霖 → Correct |
| receipt5 | receipt_number | DEN-77342 | DEN-77342 → Correct | DEN-77342 → Correct | DEN-77342 → Correct | DEN-77342 → Correct | DEN-77342 → Correct | DEN-77342 → Correct |
| receipt5 | service_date | 2026-06-27 | 2026-06-27 → Correct | 2026-06-27 → Correct | 2026-06-27 → Correct | 2026-06-27 → Correct | 2026-06-27 → Correct | 2026-06-27 → Correct |
| receipt5 | total_amount | 1575 | 1575.0 → Correct | 1750.0 → Wrong | 1575.0 → Correct | 1575.0 → Correct | 1575.0 → Correct | 1575.0 → Correct |
| receipt6 | doctor_name | CHEUNG Hoi Ying | CHEUNG Hoi Ying → Correct | CHEUNG Hoi Ying → Correct | CHEUNG Hoi Ying → Correct | CHEUNG Hoi Ying → Correct | CHEUNG Hoi Ying → Correct | CHEUNG Hoi Ying → Correct |
| receipt6 | registration_number | PT004175 | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct | PT004175 → Correct |
| receipt6 | patient_name | Yeung Tsz Kit | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct | Yeung Tsz Kit → Correct |
| receipt6 | receipt_number | RCP-10388 | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct | RCP-10388 → Correct |
| receipt6 | service_date | 2026-07-16 | 2026-07-16 → Correct | 2026-07-16 → Correct | 2026-07-16 → Correct | 2026-07-16 → Correct | 2026-07-16 → Correct | 2026-07-16 → Correct |
| receipt6 | total_amount | 1200 | 1200.0 → Correct | 1200.0 → Correct | 1200.0 → Correct | 1200.0 → Correct | 1200.0 → Correct | 1200.0 → Correct |
| receipt8 | doctor_name | Dr. Siu Ka Wai | Dr. Siu Ka Wai → Correct | Dr. Siu Ka Wai → Correct | Dr. Siu Ka Wai → Correct | Dr. Siu Ka Wai → Correct | Dr. Siu Ka Wai → Correct | Dr. Siu Ka Wai → Correct |
| receipt8 | registration_number | M19903 | M19903 → Correct | M19903 → Correct | M19903 → Correct | M19903 → Correct | M19903 → Correct | M19903 → Correct |
| receipt8 | patient_name | 蔡嘉穎 | 蔡嘉穎 → Correct | 蔡嘉穎 → Correct | 蔡嘉穎 → Correct | 蔡嘉穎 → Correct | 蔡嘉穎 → Correct | 蔡嘉穎 → Correct |
| receipt8 | receipt_number | MC-2609-3391 | MC-2609-3391 → Correct | MC-2609-3391 → Correct | MC-2609-3391 → Correct | MC-2609-3391 → Correct | MC-2609-3391 → Correct | MC-2609-3391 → Correct |
| receipt8 | service_date | 2026-09-03 | 2026-09-03 → Correct | 2026-09-03 → Correct | 2026-09-03 → Correct | 2026-09-03 → Correct | 2026-09-03 → Correct | 2026-09-03 → Correct |
| receipt8 | total_amount | 795 | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct | 795.0 → Correct |
| receipt9 | doctor_name | Angel Tseng, Lok Yi Choi | null → Wrong | Dr. Lok Vichol → Wrong | Angel Tseng → Wrong | Dr. Lok Vichol → Wrong | Angel Tseng; Dr. Lok Vichol → Wrong | Dr. Lok Vichol → Wrong |
| receipt9 | registration_number | na | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A |
| receipt9 | patient_name | Fuk Jai | null → Wrong | null → Wrong | Fuk Jai → Correct | Fuk Jai → Correct | Fuk Jai → Correct | Fuk Jai → Correct |
| receipt9 | receipt_number | 369303 | 380048 → Wrong | 380048 → Wrong | 369303 → Correct | 369303 → Correct | 369303 → Correct | 369303 → Correct |
| receipt9 | service_date | 2023-02-09 | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct | 2023-02-09 → Correct |
| receipt9 | total_amount | 1361 | 1361.0 → Correct | 1361.0 → Correct | 1361.5 → Wrong | 1361.0 → Correct | 1361.0 → Correct | 1361.0 → Correct |
| receipt10 | doctor_name | Dr Jessica Sterenborg | Dr. Jessica Sterenborg → Correct | Dr. Jessica Sterenborg → Correct | Dr Jessica Sterenborg Picton Medical Centre → Wrong | Dr Jessica Sterenborg → Correct | Dr Jessica Sterenborg → Correct | Dr Jessica Sterenborg → Correct |
| receipt10 | registration_number | na | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A | null → N/A |
| receipt10 | patient_name | Nikita Hubber | null → Wrong | null → Wrong | Nikita Hubber → Correct | Nikita Hubber → Correct | Nikita Hubber → Correct | Nikita Hubber → Correct |
| receipt10 | receipt_number | 9990000505906 | null → Wrong | null → Wrong | 9990000505906 → Correct | 9990000505906 → Correct | 9990000505906 → Correct | 9990000505906 → Correct |
| receipt10 | service_date | 2017-03-24 | 2017-03-01 → Wrong | 2017-03-01 → Wrong | 2017-03-01 → Wrong | 2017-03-01 → Wrong | 2017-03-01 → Wrong | 2017-03-01 → Wrong |
| receipt10 | total_amount | 51.2 | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct | 51.2 → Correct |
