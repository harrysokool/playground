# Receipt OCR Benchmark

A disposable benchmark, **not production code**, comparing approaches for turning medical
receipts into structured data. It exists to answer one question: is the extra cost and
complexity of Azure Document Intelligence + Azure OpenAI justified over simpler alternatives?

**Active benchmark: three approaches**

1. PaddleOCR Light (PP-OCRv5 mobile) + manually written extraction rules
2. Azure Document Intelligence + manually written extraction rules
3. Azure Document Intelligence + Azure OpenAI. Two results are kept: the original prompt
   (Version 2: 45/51, 88.2%) and the improved prompt v2 (49/51, 96.1%). The prompt v2 result
   is from the development receipts it was written against, not an independent or production
   accuracy figure.

### PaddleOCR Heavy (discontinued)

PaddleOCR Heavy (PP-OCRv5 server models) was dropped from the active benchmark in October 2026.
In the tested configuration it was less accurate than Light (Version 2, improved rules: 33/51
vs 45/51) and about four times slower (53.3 s vs 13.9 s per receipt). Its whole accuracy gap
came from two receipts where it returned almost no OCR text (3 and 0 text blocks, against 42
and 45 for Light), and it extracted no field that Light missed. The cause of the missing text
was not confirmed, so this is a result for this benchmark, not a general verdict on the model.

Its historical outputs and scores are kept unchanged (`results/v2/paddle_heavy/`,
`results/v2/extracted_*_heavy/`, `results/v2/scores/`, `results/v2/scores_improved/`, and the
Version 1 results at tag `ocr-benchmark-v1`). The configs are in `configs/archive/` to reproduce
those runs; they are not used by any active command.

**Phase 1**: raw OCR only. Run a receipt image/PDF through the PaddleOCR Light
configuration and get back a normalized JSON of text, confidence, coordinates, and timing.

**Phase 3** (current): deterministic rule-based extraction of 6 fields (doctor/provider name,
registration number, patient name, receipt number, service date, total amount) from the raw
OCR JSON — label matching, regex, and nearby-block lookup by coordinates. No line items yet,
no Azure DI, no LLM. If a field has no reliable simple rule, it's left `null` with a warning
rather than guessed.

## Setup

Requires Python 3.9–3.13 (pinned `paddlepaddle==3.2.2` only ships CPU wheels for those versions).
3.2.2 rather than 3.3.x on purpose: 3.3.1 crashes on x86 CPUs (see the Azure notes below).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Models (fully offline)

The configs load PaddleOCR models from local directories instead of downloading them, so the
benchmark runs with no internet access (required on the Azure VM). Extract the four PP-OCRv5
model archives under `models/` (not committed to Git — see `models/README.md`):

```
models/
├── PP-OCRv5_mobile_det_infer/   # configs/paddle_light.yaml
├── PP-OCRv5_mobile_rec_infer/   # configs/paddle_light.yaml
├── PP-OCRv5_server_det_infer/   # optional: discontinued configs/archive/paddle_heavy*.yaml
└── PP-OCRv5_server_rec_infer/   # optional: discontinued configs/archive/paddle_heavy*.yaml
```

Commands must be run from the project root (`configs/*.yaml` reference `models/...` as a
relative path).

## Usage

```bash
# Light OCR (PP-OCRv5 mobile)
python -m receipt_bench.cli --config configs/paddle_light.yaml --input data/raw --output results/paddle_light
```

`--input` may be a single image/PDF file or a directory of them. One JSON file per input document
is written to `--output`, containing the normalized raw OCR result (see `receipt_bench/raw_ocr.py`).

## Extraction (Phase 3)

Runs deterministic rules over already-generated raw OCR JSON (from `## Usage` above), not
over the receipt files directly:

```bash
python -m receipt_bench.extract_cli --input results/paddle_light --output results/paddle_light_extracted
```

Rules live in `receipt_bench/extraction.py` — see `FIELD_RULES` for the exact labels matched
per field. Each field tries a label match first (same block, or nearest block by OCR
coordinates if the label is alone), then falls back to a standalone pattern for unlabeled
values (e.g. "Dr Chan", "M12345") if no label matched anywhere. Each output JSON has the 6
fields, a `sources` map (which OCR block text each value came from), and a `warnings` list
for anything left `null`.

## Overfit extraction experiment (Phase 3b)

`receipt_bench/extraction_tuned.py` is a deliberately **overfit** rule set, tuned by hand to
the 6 receipts in `data/raw` (4 layouts), to measure how far OCR + deterministic rules can go
when you invest in layout-specific handling. It is not meant to generalize. Every rule is
tagged `[GENERAL]` or `[OVERFIT]` in the code and in each output's `rules` map. Unknown
layouts fall back to the Phase 3 baseline rules.

```bash
python -m receipt_bench.extract_cli --rules tuned --input results/paddle_light --output results/extracted_tuned_light
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach tuned_light=results/extracted_tuned_light
```

## General rules baseline (Phase 3c)

`receipt_bench/extraction_general.py` is the honest non-AI baseline: reusable deterministic
rules only (label vocabularies, same-line / below / above-right lookup, generic date and
amount parsing, totals semantics, arithmetic checks), with **no** layout detection, per-layout
handlers, receipt coordinates or ground-truth-driven fixes. It fails closed. Each output also
records `timings.ocr_predict_ms` (from the raw OCR JSON) and `timings.extract_ms`.

```bash
python -m receipt_bench.extract_cli --rules general --input results/paddle_light --output results/extracted_general_light
```

## PaddleOCR Light end to end (Phase 2 of the final comparison)

PaddleOCR uses the general rules (Phase 3c) and saves:
- raw OCR, with text, confidence, polygons and `timings.total_ms`, to `results/paddle_light/`;
- the six extracted fields, plus `sources`, `rules`, `warnings` and
  `timings.ocr_predict_ms` / `timings.extract_ms`, to `results/extracted_general_light/`.

Phase 2 originally ran Heavy as well (now discontinued; see the top of this README).

`score.py` reads the extracted files directly. Processing time = OCR predict + extraction. It
does not include model loading, which happens once per run.

Run the benchmark on **Azure ML compute** (x86 Linux, CPU, Python 3.11). This setup produced
the committed results in `results/`, with the plain configs (oneDNN on). The discontinued Heavy
model peaked at about 9 GB RAM on the largest receipt, and the **16 GB RAM** compute instance was
sized for it. Copy the `models/PP-OCRv5_mobile_*_infer` folders onto the instance first (they
aren't in Git).

```bash
python3.11 -m venv ~/venvs/paddle322 && source ~/venvs/paddle322/bin/activate
pip install --upgrade pip && pip install -r requirements-dev.txt   # paddlepaddle==3.2.2
python -c "import paddle, paddleocr; print(paddle.__version__, paddleocr.__version__)"   # 3.2.2 3.7.0
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True   # never contact model hosters

python -m receipt_bench.cli --config configs/paddle_light.yaml --input data/raw --output results/paddle_light
python -m receipt_bench.extract_cli --rules general --input results/paddle_light --output results/extracted_general_light
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach paddle_light=results/extracted_general_light \
    --output-dir results/scores_paddle
```

Why 3.2.2: on this compute, paddlepaddle **3.3.1** fails both ways:
- with oneDNN on, it raises `NotImplementedError: ... ConvertPirAttribute2RuntimeAttribute not support`;
- with oneDNN off, the (now discontinued) heavy model segfaults in the plain CPU convolution
  (`Im2ColFunctor`) on the 12 MP receipts.

**Fallback:** `configs/paddle_light_azure.yaml` is the same config plus `enable_mkldnn: false`.
Use it only if oneDNN causes trouble again. CPU inference is slower without oneDNN, so keep the
same config across runs you compare.

## Azure Document Intelligence (Phase 3 of the final comparison)

`receipt_bench/azure_di.py` uses DI `prebuilt-read` **for OCR only**. It converts each DI
response into the same raw OCR format as PaddleOCR, so the unchanged general rules and
`score.py` run on it exactly as they do for Paddle. There are no DI-specific rules and no
Azure OpenAI.

- One OCR block per DI line. Each block keeps the text, the 4-point polygon and DI's line
  order as `reading_order`.
- A block's confidence is the mean of its words' confidences. DI has no line-level
  confidence, and the general rules drop blocks that have none.
- `timings.total_ms` is the DI call: upload, analysis and result polling. After extraction it
  appears as `timings.ocr_predict_ms`, next to `timings.extract_ms`. The scorer's processing
  time is the sum of the two.
- Each run writes `results/azure_di/receiptN.json` (raw OCR) and
  `results/azure_di/di_response/receiptN.json` (the full DI response, or `{"error": ...}`).
  A failed receipt gets no raw OCR file, so the scorer counts all its fields as Wrong.

Run on **Azure ML compute**. Every receipt is a paid DI call, so don't run it from a laptop.
Authentication uses **only** the compute's user-assigned managed identity
(`ManagedIdentityCredential`); there are no API keys and no fallback to other credentials. Set:

| variable | value |
|---|---|
| `AZURE_CLIENT_ID` | client ID of the user-assigned managed identity attached to the compute |
| `AZURE_DI_ENDPOINT` | the DI resource's custom-domain endpoint, `https://<resource>.cognitiveservices.azure.com/` |

The identity needs the **Cognitive Services User** role on the DI resource. The script stops
with a clear message if a variable is missing, if no token can be obtained for the identity,
if DI refuses it (401/403) or if the endpoint can't be reached. Any other per-receipt error is
recorded and the run continues.

```bash
source ~/venvs/paddle322/bin/activate && pip install -r requirements-azure-di.txt
export AZURE_CLIENT_ID="<managed-identity-client-id>"
export AZURE_DI_ENDPOINT="https://<your-resource>.cognitiveservices.azure.com/"

python -m receipt_bench.azure_di --input data/raw --output results/azure_di
python -m receipt_bench.extract_cli --rules general --input results/azure_di --output results/extracted_general_azure_di
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach paddle_light=results/extracted_general_light \
    --approach azure_di=results/extracted_general_azure_di \
    --output-dir results/scores_paddle_di
```

**Offline, with no Azure calls:** re-convert saved DI responses, e.g. after changing the
converter. This also reads the older DI runner format (`raw_di_result`).

```bash
python -m receipt_bench.azure_di --from-responses results/azure_di/di_response --output results/azure_di
```

## Azure DI + Azure OpenAI (Phase 4 of the final comparison)

`receipt_bench/di_aoai.py` runs DI `prebuilt-read` with the same call and conversion as
Phase 3. It then sends the OCR text (DI lines in reading order, no image) to the Azure OpenAI
deployment with one fixed prompt for every receipt.
- A strict JSON schema makes the reply exactly the six benchmark fields, so there's no
  `visit_date`-style mapping step.
- The model is told to copy values from the text, return `null` for anything missing, and
  never correct OCR errors. A year DI misread (e.g. "2020" for a handwritten "2026") is
  therefore *not* fixed; that's deliberate.
- Dates are normalized to ISO (day-first, as in the general rules) and amounts to numbers.
  Values that can't be normalized are kept as written.

Each `results/di_aoai/receiptN.json` has:
- the six fields, the model's raw values and warnings;
- the OCR text that was sent;
- token usage (`aoai.usage`, for cost estimates) and the reasoning effort;
- `timings.di_ms`, `timings.aoai_ms` and `timings.total_ms`.

A failed receipt is still written, with `status: "error"`, `error_stage` (`di` or `aoai`),
the error and timings, but no fields, so the scorer counts it as having no result. The full DI
responses are saved in `results/di_aoai/di_response/`.

**Configuration.** Authentication uses only the compute's user-assigned managed identity
(`ManagedIdentityCredential`); there are no API keys and no fallback. The identity needs
**Cognitive Services User** on the DI resource and **Cognitive Services OpenAI User** on the
Azure OpenAI resource.

| variable | required | value |
|---|---|---|
| `AZURE_CLIENT_ID` | yes | client ID of the user-assigned managed identity |
| `AZURE_DI_ENDPOINT` | yes | `https://<di-resource>.cognitiveservices.azure.com/` |
| `AZURE_OPENAI_ENDPOINT` | yes | `https://<aoai-resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | yes | the deployment name, e.g. `gpt-5-mini` |
| `AZURE_OPENAI_API_VERSION` | no | default `2025-04-01-preview` |
| `AZURE_OPENAI_REASONING_EFFORT` | no | default `low` |
| `AZURE_OPENAI_TIMEOUT_SECONDS` | no | default `60` per request |
| `AZURE_OPENAI_MAX_RETRIES` | no | default `2` (the SDK retries timeouts, 429 and 5xx) |

The run stops at the first receipt on errors that would hit every receipt: missing
configuration, no token for the identity, 401/403, an unknown deployment (404), a rejected
request (400) or an unreachable endpoint. Timeouts and other per-receipt errors are recorded
and the run continues.

```bash
source ~/venvs/paddle322/bin/activate && pip install -r requirements-azure-openai.txt
export AZURE_CLIENT_ID="<managed-identity-client-id>"
export AZURE_DI_ENDPOINT="https://<di-resource>.cognitiveservices.azure.com/"
export AZURE_OPENAI_ENDPOINT="https://<aoai-resource>.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-5-mini"

python -m receipt_bench.di_aoai --input data/raw --output results/di_aoai
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach paddle_light=results/extracted_general_light \
    --approach azure_di=results/extracted_general_azure_di \
    --approach azure_di_aoai=results/di_aoai \
    --output-dir results/scores_all
```

To try the prompt without paying for DI again, add `--reuse-di results/azure_di/di_response`.
That still calls AOAI, and its DI timings come from the earlier run, so use it for development
only, not the final numbers.

## Version 2 benchmark (Azure ML only)

Version 1 (six receipts) is frozen at the Git tag `ocr-benchmark-v1`, results included.
Version 2 uses nine receipt images (see `data/receipts_v2/README.md`). The approaches run
**on Azure ML compute only**, with the unchanged code, rules and prompt; outputs go to `results/v2/`.
The only scorer change is that a Traditional Chinese date such as `2026年6月9日` is now read as
written. Extraction is unchanged.

The phone photos store their pixels sideways, with an EXIF orientation tag. A preparation step
writes upright copies to `results/v2/inputs/`, which all approaches read. That way they all
get identical pixels whatever their own EXIF handling (see `data/receipts_v2/prepare_inputs.py`).
`count DIR` prints how many receipt results a step produced. Each step should show **9/9**
before you move on.

```bash
# 1. setup
cd <repo>/python/receipt_ocr_benchmark && git pull
source ~/venvs/paddle322/bin/activate
pip install -r requirements-dev.txt -r requirements-azure-openai.txt
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export AZURE_CLIENT_ID="<managed-identity-client-id>"
export AZURE_DI_ENDPOINT="https://<di-resource>.cognitiveservices.azure.com/"
export AZURE_OPENAI_ENDPOINT="https://<aoai-resource>.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-5-mini"
OUT=results/v2; IN=$OUT/inputs
count() { echo "$1: $(ls "$1"/receipt*.json 2>/dev/null | wc -l)/9"; }

# 2. tests
python -m pytest -q

# 3. inputs: nine upright images + manifest.csv
python data/receipts_v2/prepare_inputs.py

# 4. PaddleOCR Light, then the general rules
python -m receipt_bench.cli --config configs/paddle_light.yaml --input $IN --output $OUT/paddle_light && count $OUT/paddle_light
python -m receipt_bench.extract_cli --rules general --input $OUT/paddle_light --output $OUT/extracted_general_light && count $OUT/extracted_general_light

# 5. Azure DI (paid: 9 calls), then the general rules
python -m receipt_bench.azure_di --input $IN --output $OUT/azure_di && count $OUT/azure_di
python -m receipt_bench.extract_cli --rules general --input $OUT/azure_di --output $OUT/extracted_general_azure_di && count $OUT/extracted_general_azure_di

# 6. Azure DI + AOAI (paid: 9 DI + 9 AOAI calls). A failed receipt is still written, so also count status "ok"
python -m receipt_bench.di_aoai --input $IN --output $OUT/di_aoai && count $OUT/di_aoai
echo "di_aoai ok: $(grep -l '"status": "ok"' $OUT/di_aoai/receipt*.json | wc -l)/9"

# 7. score: report.md, summary.csv, detail.csv (accuracy, per field, time, failures, invented, AOAI tokens)
python -m receipt_bench.score --ground-truth data/receipts_v2/benchmark_ground_truth.xlsx \
    --approach paddle_light=$OUT/extracted_general_light \
    --approach azure_di=$OUT/extracted_general_azure_di \
    --approach azure_di_aoai=$OUT/di_aoai \
    --output-dir $OUT/scores_rerun   # a new folder: the committed results/v2/scores/ stays as it is
cat $OUT/scores_rerun/report.md | head -30
```

The committed Version 2 results in `results/v2/scores/` were produced when Heavy was still run,
so they include it.

A count below 9/9 after Azure DI means some receipts failed. The reasons are in
`$OUT/azure_di/di_response/receiptN.json`. For DI + AOAI, they're in each failed receipt's own
JSON (`status`, `error_stage`, `error`).

## Improved rules experiment (Phase 10, tuned on Version 2)

`receipt_bench/extraction_improved.py` (`extract_cli --rules improved`) is a separate,
LLM-free rule set. It adds:
- Traditional Chinese and bilingual labels;
- tolerance for OCR'd labels (glued words, full-width punctuation, simplified characters);
- distractor labels that never supply an answer;
- card layouts, and registration numbers inside a line;
- service vs issue dates, and totals vs subtotals, payments and balances.

The original general rules are unchanged. **The nine Version 2 receipts were used to develop
these rules, so their Version 2 scores are not an independent test.**

Run on Azure ML from this folder. Only extraction is re-run, on the existing raw OCR, so there
are no paid calls:

```bash
source ~/venvs/paddle322/bin/activate && git pull
python -m pytest -q tests/test_extraction_improved.py && python -m pytest -q
OUT=results/v2
python -m receipt_bench.extract_cli --rules improved --input $OUT/paddle_light --output $OUT/extracted_improved_light
python -m receipt_bench.extract_cli --rules improved --input $OUT/azure_di --output $OUT/extracted_improved_azure_di
python -m receipt_bench.score --ground-truth data/receipts_v2/benchmark_ground_truth.xlsx \
    --approach paddle_light_general=$OUT/extracted_general_light --approach paddle_light_improved=$OUT/extracted_improved_light \
    --approach azure_di_general=$OUT/extracted_general_azure_di --approach azure_di_improved=$OUT/extracted_improved_azure_di \
    --approach azure_di_aoai=$OUT/di_aoai --output-dir $OUT/scores_improved_rerun
for d in $OUT/extracted_general_light $OUT/extracted_improved_light $OUT/extracted_*_azure_di; do echo "$d: mean extraction $(grep -h '"extract_ms"' $d/*.json | awk -F': ' '{s+=$2; n++} END {printf "%.1f", s/n}') ms"; done
```

The committed `results/v2/scores_improved/` (written when Heavy was still run) also contains the
historical `paddle_heavy_general` and `paddle_heavy_improved` rows; they are kept unchanged, which
is why the command above writes to `scores_improved_rerun/`.

**Version 1 check.** This re-runs only extraction, on the Version 1 OCR outputs frozen in the
tag `ocr-benchmark-v1`. Version 1 receipts 4 and 6 are the same images as Version 2 receipts 9
and 10, so only Version 1 receipts 1, 2, 3 and 5 were unseen during development:

```bash
V1=results/v1_rerun && mkdir -p $V1
git -C "$(git rev-parse --show-toplevel)" archive ocr-benchmark-v1:python/receipt_ocr_benchmark/results paddle_light azure_di \
    extracted_general_light extracted_general_azure_di | tar -x -C $V1
python -m receipt_bench.extract_cli --rules improved --input $V1/paddle_light --output $V1/extracted_improved_light
python -m receipt_bench.extract_cli --rules improved --input $V1/azure_di --output $V1/extracted_improved_azure_di
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach paddle_light_general=$V1/extracted_general_light --approach paddle_light_improved=$V1/extracted_improved_light \
    --approach azure_di_general=$V1/extracted_general_azure_di --approach azure_di_improved=$V1/extracted_improved_azure_di \
    --output-dir $V1/scores
```

The committed result is in `results/v1_heldout/` (`extracted_*_light`, `extracted_*_azure_di`,
`scores_rules/`; `scores_rules/` also includes `aoai_v2_rows` for comparison). On the four
unseen receipts the improved rules scored the same as the original rules (Light 13/15, DI
10/15); see `results/v2/scores_improved/RULES_COMPARISON.md`, section 5.

## Improved DI + AOAI pipeline (Phase 12)

`receipt_bench/di_aoai.py` now has two pipelines. The **original benchmark pipeline is kept
unchanged** (`--prompt v1 --text plain`; a test pins the v1 prompt) and its result,
`results/v2/di_aoai` (45/51), stays the baseline. The **improved pipeline** is the default:

| Change | What it does | Targets |
|---|---|---|
| Row layout (`--text rows`) | Regroups DI lines into the rows of the page using DI's line positions (skew-corrected), so a label and the value beside it stay together: `Reg. No. 註冊編號: \| D03158` | Two-column layouts where plain reading order separates labels from values |
| Prompt v2 | Explicit, general field definitions: value only, no labels; doctor = person's name without qualifications or clinic names; several practitioners separated by `; `; final total after rounding/discounts, not subtotal; service date vs print/issue dates; an `uncertain_fields` list in the reply | Values copied with surrounding text; subtotal chosen; unclear dates |
| `receipt_bench/aoai_validation.py` | A few general checks: keep only the identifier in a registration number; strip trailing post-nominals (MBBS, BDS (HK), FHKAM …) from doctor names. Flags (value unchanged, listed in `review_fields`): clinic words in a doctor name, a value not found in the OCR text, a total equal to a subtotal line, fields the model was unsure of | The same, as a safety net for any model |
| `--attach-image` (experiment, off by default) | Also sends the receipt photo, downscaled to 2000 px | OCR misreads (stamps, signatures) |

No ground-truth value of any benchmark receipt appears in the prompt or the checks (a test
enforces this).

**Scoring change.** When the ground truth lists several people ("A, B"), all of them must be
returned, in any order, separated by `,` `;` `/` `&` or "and", with no extra names. A single
name is matched as before.

Run on Azure ML (no DI calls; at most 33 AOAI calls). Pull first, so the script never changes
while it runs:

```bash
git pull --ff-only && bash python/receipt_ocr_benchmark/scripts/aoai_improved_on_azure.sh
```

- **Resumable.** A run whose folder already holds every receipt with status "ok" is skipped, so
  running the script again repeats no AOAI call. A folder that exists but is incomplete stops the
  script; results are never overwritten or deleted (move the folder aside yourself).
- **Stops before running anything** if the original results differ from the committed version,
  or if rescoring them with the current scorer changes any of the seven original scores.
- **Commits in two steps:** the Version 2 results first (`results/v2/di_aoai_v2_*`,
  `results/v2/scores_aoai_improved/`), then the held-out Version 1 results (`results/v1_heldout/`).
  `--no-v1` stops after the Version 2 commit; `--no-push` commits without pushing.
- **Version 1 is optional.** Its photos, saved DI responses and original AOAI results are read
  from the tag `ocr-benchmark-v1` into a temporary folder. If they are not available, the step is
  skipped with a message.
- **Git lock files are never deleted by the script.** If one is present it stops: with a running
  git process it asks you to wait; without one it names the file to remove once you have checked
  nothing else (another terminal, VS Code, a Jupyter git extension) is using the repository.

## Scoring all approaches (Phase 1 of the final comparison)

`receipt_bench/score.py` scores any number of named approaches against the same ground truth
and the same six fields: `doctor_name`, `registration_number`, `patient_name`,
`receipt_number`, `service_date`, `total_amount`.

```bash
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach paddle_light=results/extracted_general_light \
    --approach azure_di=results/<azure_di_run_dir> \
    --approach azure_di_aoai=results/<azure_di_aoai_run_dir> \
    --output-dir results/scores
```

Each receipt × field is marked:

- **Correct**: the field is on the receipt and the approach returned the same value.
- **Wrong**: the field is on the receipt and the approach returned a different value or
  nothing. A missing result file, a failed run (e.g. a timeout) or a result with no extracted
  fields counts as nothing, so failures can only lower accuracy.
- **N/A**: the field is not on the receipt (ground truth `na`). These are excluded from
  accuracy. A value returned anyway is counted separately as **invented**.

`Accuracy = Correct / applicable fields × 100`, overall and for each field.

Normalization is kept simple:
- Names ignore case, punctuation, spacing and titles (Dr / 醫生 / 医生).
- Dates are compared as calendar dates with no day/month swapping. The ground truth must be
  ISO text, and a non-ISO predicted date is read day-first.
- Amounts are equal within 0.005.
- Receipt and registration numbers are an exact match.

`--output-dir` writes:
- `report.md`: overall table, per-field accuracy and a per-receipt detail table.
- `summary.csv`: one row per approach (correct, applicable, accuracy %, invented, receipts
  with no result, mean processing ms, per-field accuracy %). Use this for the deck.
- `detail.csv`: one row per approach × receipt × field.

**Adding an approach:** write one JSON per receipt (`receipt1.json`, …) into a directory and
pass it as `--approach NAME=DIR`. The scorer reads two formats today (see `read_result`):
- the six fields at the top level, as `extract_cli` writes them, with optional
  `timings.ocr_predict_ms` / `timings.extract_ms`;
- the Azure DI + AOAI runner format, with fields under `benchmark_fields`, plus `status`,
  `timings_seconds.total` and `aoai_output`.

Use the six standard field names and `null` for anything not found. Write dates as ISO
`YYYY-MM-DD` if possible. Other names for a field are mapped in `FIELD_ALIASES` (currently
`visit_date` → `service_date`); an alias only fills a standard field that is empty.

Ground-truth corrections and open questions are in `data/ground_truth/GROUND_TRUTH_REVIEW.md`.

## Decisions and investigations (outside the six-field benchmark)

**Exact doctor-database matching: not pursued (Oct 2026).**
- Exact regex matching of OCR text against the roughly 40,000 registered doctor names is
  technically feasible without AI.
- It shows whether a registered doctor's name appears on the receipt, not whether that person is
  the treating doctor.
- Cases where those differ: referring doctors, several doctors on one receipt, clinic directors,
  and doctors named from earlier consultations.
- These cases may be rare, but how often they occur is unknown. Whether that risk is acceptable
  is a business decision.
- It will not be built or benchmarked unless the business asks for it.

**Diagnosis comment present or missing:** investigation only, not implemented. See
`docs/DIAGNOSIS_COMMENT.md`.

## Data

Real receipt samples go in `data/raw/` and are **not committed to Git** (see `data/README.md`).

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

`test_paddle_engine.py` runs both configs for real against a tiny synthetic fixture receipt
(`tests/fixtures/receipt.png` — no real patient data). Requires `models/` to be populated (see above).

To run only the fast unit tests, without loading any PaddleOCR model or running OCR:

```bash
python -m pytest -k "not test_paddle_engine_processes_receipt"
```
