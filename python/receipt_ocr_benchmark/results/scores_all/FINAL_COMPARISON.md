# Receipt OCR Benchmark: Final Comparison

**Question:** is Azure Document Intelligence + Azure OpenAI worth its extra cost and complexity
compared with simpler options?

**Setup:**
- **Receipts:** 6 mock medical receipts (4 layouts; 4 handwritten, 2 printed).
- **Fields:** 6, scored against one hand-checked ground truth with `receipt_bench/score.py`.
  25 of the 36 receipt × field cells have a value on the receipt; the other 11 are N/A
  (registration number appears on none).
- **Where it ran:** all runs were on Azure ML compute on 13 Oct 2026. Source data is in
  `report.md`, `summary.csv` and `detail.csv` next to this file.

## 1. Comparison of the four approaches

| | Paddle Light | Paddle Heavy | Azure DI | Azure DI + AOAI |
|---|---|---|---|---|
| How fields are extracted | general rules | general rules | general rules | gpt-5-mini (text only) |
| **Accuracy** (correct / applicable) | **72%** (18/25) | **72%** (18/25) | 60% (15/25) | **72%** (18/25) |
| Invented values (field not on receipt) | 0 | 0 | 0 | 1 |
| **Mean time per receipt** | 8.7 s | 35.8 s | **2.6 s** | 5.4 s |
| Time range | 5.1–11.8 s | 15.4–47.6 s | 2.2–4.0 s | 5.0–5.7 s |
| Receipts processed successfully | 6/6 | 6/6 | 6/6 | 6/6 |
| Runs offline, no per-call cost | yes | yes | no | no |

*Accuracy* is about extraction quality. *Processed successfully* only means the run produced
a result (no crash, timeout or API error), and all four did on every receipt.

## 2. Accuracy by field

| Field (applicable receipts) | Paddle Light | Paddle Heavy | Azure DI | Azure DI + AOAI | All approaches |
|---|---|---|---|---|---|
| doctor_name (6) | 3/6 | 3/6 | 4/6 | 4/6 | 14/24 |
| patient_name (4) | 2/4 | 2/4 | 2/4 | **4/4** | 10/16 |
| receipt_number (3) | 2/3 | 2/3 | 2/3 | **3/3** | 9/12 |
| service_date (6) | **5/6** | **5/6** | 1/6 | 1/6 | 12/24 |
| total_amount (6) | 6/6 | 6/6 | 6/6 | 6/6 | 24/24 |
| registration_number | N/A | N/A | N/A | N/A | not on any receipt |

## 3. Processing time

| | OCR step | Extraction step | Total per receipt |
|---|---|---|---|
| Paddle Light | 8.7 s (CPU) | ~9 ms (rules) | 8.7 s |
| Paddle Heavy | 35.7 s (CPU) | ~8 ms (rules) | 35.8 s |
| Azure DI | 2.6 s (API call) | ~10 ms (rules) | 2.6 s |
| Azure DI + AOAI | 2.3 s (API call) | 3.1 s (AOAI call) | 5.4 s |

How these times were measured:
- **Paddle:** CPU inference on the Azure ML compute, paddlepaddle 3.2.2 with oneDNN, model
  loading excluded.
- **Azure:** wall-clock time of each call (upload, processing, polling), so it includes
  network time.
- **Not measured:** none of the approaches was run in parallel. Throughput at volume
  wasn't tested.

## 4. Reliability

| | Final run | Issues found and fixed during the benchmark |
|---|---|---|
| Paddle Light | 6/6 | none |
| Paddle Heavy | 6/6 | crashed on paddlepaddle 3.3.1 (oneDNN error, then a segfault without oneDNN); fixed by pinning 3.2.2 |
| Azure DI | 6/6, no errors | none |
| Azure DI + AOAI | 6/6, no errors or timeouts; AOAI 2.7–3.4 s | the 29 Sep version timed out on 2–3 of 6 receipts at ~100 s (48-field schema, free-text reasoning, image probably sent); replaced by a 6-field schema, text only, reasoning effort `low` |

## 5. AOAI token usage (gpt-5-mini, reasoning effort `low`, actual)

| | Per receipt (mean) | 6 receipts | Per 1,000 receipts (projected) |
|---|---|---|---|
| Input tokens | 547 (390–830) | 3,279 | ~547,000 |
| Output tokens, incl. reasoning | 283 (186–377) | 1,698 | ~283,000 |
| of which reasoning | 224 | 1,344 | ~224,000 |
| Cached input tokens | 0 | 0 | — |

## 6. Estimated cost per 1,000 receipts

All quantities below are measured. **Prices are not filled in, because none were provided.**
Each formula is cost = quantity × your price.

| Approach | Compute | Azure DI | Azure OpenAI | Total |
|---|---|---|---|---|
| Paddle Light | 2.42 VM-hours × **[VM $/h]** | — | — | 2.42 × VM $/h |
| Paddle Heavy | 9.93 VM-hours × **[VM $/h]** | — | — | 9.93 × VM $/h |
| Azure DI | (0.71 VM-hours, optional†) | 1,000 pages × **[DI Read $/1,000 pages]** | — | DI price + optional compute |
| Azure DI + AOAI | (1.50 VM-hours, optional†) | 1,000 pages × **[DI Read $/1,000 pages]** | 0.547 M input × **[$/1M input]** + 0.283 M output × **[$/1M output]** | DI + AOAI (+ optional compute) |

How these figures were worked out:
- VM-hours = mean seconds per receipt × 1,000 ÷ 3,600, processing one receipt at a time on
  one machine.
- † For the Azure approaches the VM only waits on the API, so that cost matters only if the
  VM is dedicated to this work.
- Every receipt is 1 DI page.
- Reasoning tokens are billed as output tokens.

**Prices still needed:**
1. **Azure ML compute:** the SKU and its hourly price for the instance used (Paddle times
   depend on this hardware).
2. **Azure DI:** the `prebuilt-read` price per 1,000 pages for our resource, after any
   commitment tier or discount.
3. **Azure OpenAI:** the gpt-5-mini price per 1M input and per 1M output tokens for our
   deployment type and region (the endpoint is in Sweden Central).

## 7. Main findings

1. **Three approaches tie on accuracy at 72%:** Paddle Light, Paddle Heavy and DI + AOAI.
   Azure DI with rules is lowest at 60%.
2. **Heavy brings no benefit over Light.**
   - It extracts identical values except two doctor-name spellings (both wrong or both
     right).
   - It's about 4× slower: 35.8 s vs 8.7 s.
3. **Adding AOAI improves on DI alone by 12 points** (60% → 72%).
   - **Gains (+4):** the model finds fields the general rules miss: patient name on
     receipts 4 and 6, receipt 6's barcode receipt number, and receipt 3's doctor written
     under "Clinic Name".
   - **Losses (−1):** on receipt 6, DI puts the doctor and clinic on one line ("Dr Jessica
     Sterenborg Picton Medical Centre") and the model copied the whole line.
   - **Invented value (1):** on receipt 2 the model used an unlabelled stray number ("18228")
     as the receipt number. DI reads that number on its own line in every run.
4. **DI's recognition errors cause most of DI + AOAI's errors.**
   - DI reads the handwritten "2026" as "2020" on receipts 1, 2, 3 and 5. The OCR text sent
     to the model contains "2020" and never "2026".
   - So 4 of DI + AOAI's 7 wrong fields come from DI, not the model. By design, the model
     was not allowed to correct them.
   - The other 3 wrong fields:
     - receipt 4's doctor (the ground truth combines two names);
     - receipt 6's date (the model took the 1 Mar line-item date rather than the printed
       24 Mar date; this ground-truth value is still unconfirmed);
     - receipt 6's doctor (clinic name appended).
   - *Arithmetic only, not a measured result:* if DI had read those four years correctly,
     DI + AOAI would score 22/25 (88%) and DI + rules 19/25 (76%).
5. **Paddle's OCR reads the handwritten years correctly** (service date 5/6), which is
   where it beats both DI approaches. Its weak spots are the fields the general rules can't
   find (names in unusual boxes, unlabelled fields).
6. **Hardest fields:** service date (12/24 across all approaches, almost entirely DI's year
   misreading) and doctor name (14/24: OCR misspellings, a name in a "Clinic Name" box, two
   clinicians on one receipt). Total amount is solved (24/24).
7. **Fastest:** Azure DI (2.6 s), then DI + AOAI (5.4 s), Light (8.7 s) and Heavy (35.8 s).

## 8. Limitations of this dataset

- **Only 6 receipts (25 scored fields), so one field is 4 percentage points.** The 72% tie
  doesn't separate the approaches statistically.
- **Unrepresentative mix:**
  - 4 of 6 are handwritten mock receipts on the same template; 1 is a vet invoice; 1 is a
    2017 pharmacy printout.
  - The mix overweights handwriting, which is exactly where DI fails on years.
- **Open ground-truth questions affect the scores:**
  - day-first date order on 4 receipts;
  - receipt 4's two doctors and its invoice vs receipt number;
  - receipt 6's receipt number and date.

  See `data/ground_truth/GROUND_TRUTH_REVIEW.md`.
- **One run per approach.** LLM output can vary between runs, and repeat runs weren't
  measured. A single-receipt trial (`results/di_aoai_test`) gave the same fields with
  different reasoning-token counts.
- **The general rules were developed while looking at these same receipts,** so they
  likely do better here than they would on unseen layouts. The AOAI prompt is generic.
- **No registration numbers** appear on any receipt, so that field is untested.
- **Timing caveats:** Paddle timings depend on the (unrecorded) compute SKU. Azure timings
  include network time, and were taken one receipt at a time, not at volume.

## 9. Recommendation

On this evidence, **DI + AOAI is not yet shown to be worth its extra cost.** It ties with
Paddle Light at 72%. Its advantage on names and receipt numbers is cancelled out by DI
misreading handwritten years.

1. **Drop Paddle Heavy.** It has the same accuracy as Light at 4× the time.
2. **Drop Azure DI with rules alone.** It's the least accurate, and its speed advantage
   doesn't make up for that.
3. **Keep Paddle Light and DI + AOAI as the two candidates.**
   - Light: cheapest, offline, best on dates. Weak where fixed rules can't find a field.
   - DI + AOAI: best on names and IDs, but carries a per-receipt API cost and inherits
     DI's handwriting errors.
4. **Before deciding:**
   - fill in the three prices in section 6;
   - re-run both candidates on a larger set of real (anonymised) receipts, e.g. 50–100,
     with a realistic share of printed vs handwritten.
   - *Worth testing (untested idea):* Paddle Light OCR text + AOAI extraction. That would
     combine Paddle's correct years with the LLM's better field finding.
