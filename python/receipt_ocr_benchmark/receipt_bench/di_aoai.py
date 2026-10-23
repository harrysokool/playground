"""Azure Document Intelligence (prebuilt-read) OCR + Azure OpenAI field extraction.

For each receipt:
  1. DI prebuilt-read reads the text, reusing `azure_di` (the same call and conversion as Phase 3).
  2. The OCR text goes to the Azure OpenAI deployment with one fixed prompt. A strict JSON schema
     makes the reply exactly the six fields (plus, with prompt v2, the fields it is unsure of).
  3. The reply is parsed and normalized (dates to ISO day-first, amounts to numbers), then saved
     in the same per-receipt shape as the other approaches, so `score.py` reads it unchanged.

Two pipelines (chosen with --prompt / --text / --attach-image):
- baseline (`--prompt v1 --text plain`): the original Version 2 benchmark setup. DI lines in
  reading order, the original prompt, no validation. Kept unchanged so its result can be reproduced.
- improved (the default, `--prompt v2 --text rows`): DI lines regrouped into the rows of the page
  using DI's line positions, so a label and the value printed beside it stay together; a prompt
  with explicit field definitions (value only, no labels, qualifications or clinic names; final
  total, not subtotal; several practitioners; service vs print dates; an uncertain_fields list);
  and the light, general checks in `aoai_validation` (warnings and review_fields in the output).
- `--attach-image` (experiment, off by default) also sends the receipt photo, so the model can
  read text the OCR misread, e.g. a stamp or signature. More input tokens per receipt.
- `--diagnosis` (prompt v2 only) adds DIAGNOSIS_NOTE: the model also says whether a diagnosis
  comment is present / missing / needs_review and quotes it. Saved under "diagnosis", checked by
  `aoai_validation.check_diagnosis` and scored by `diagnosis_cli`, never by `score.py`. Without the
  flag the prompt and schema are exactly as before.

The model is told to copy values from the text and to return null for anything not there. It is
NOT told to fix OCR errors (unless the image is attached), so a year DI misread (e.g. "2020" for
a handwritten "2026") stays as read: this measures extraction from the available evidence.

Authentication is only the compute's user-assigned managed identity (no API keys, no fallback):
    AZURE_CLIENT_ID          client ID of the user-assigned managed identity
    AZURE_DI_ENDPOINT        https://<di-resource>.cognitiveservices.azure.com/
    AZURE_OPENAI_ENDPOINT    https://<aoai-resource>.openai.azure.com/
    AZURE_OPENAI_DEPLOYMENT  e.g. gpt-5-mini
Optional:
    AZURE_OPENAI_API_VERSION         default 2025-04-01-preview
    AZURE_OPENAI_REASONING_EFFORT    default low ("minimal" / "low" / "medium" / "high")
    AZURE_OPENAI_TIMEOUT_SECONDS     default 60, per request
    AZURE_OPENAI_MAX_RETRIES         default 2 (timeouts, 429 and 5xx are retried by the SDK)

Usage (on Azure ML compute - paid DI and AOAI calls):
    python -m receipt_bench.di_aoai --input data/raw --output results/di_aoai
Development only (skips the paid DI calls by reusing saved DI responses; AOAI is still called):
    python -m receipt_bench.di_aoai --input data/raw --reuse-di results/azure_di/di_response --output results/di_aoai_dev
Original baseline pipeline:
    python -m receipt_bench.di_aoai --prompt v1 --text plain --input ... --output ...

Output per receipt in --output:
- receiptN.json: status "ok", the six fields, the model's raw values, warnings, review_fields
  (improved pipeline), the pipeline options, the OCR text sent, token usage, and timings
  (di_ms, aoai_ms, total_ms).
  On failure it is written with status "error", the stage ("di" / "aoai"), the error and
  timings, and no fields, so the scorer counts the receipt as having no result.
- di_response/receiptN.json: the full DI response (same format as `azure_di`).
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import os
import sys
import time
from pathlib import Path

from receipt_bench import aoai_validation, azure_di
from receipt_bench.extraction_tuned import parse_amount, parse_date

FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]

# Prompt v1: the original Version 2 benchmark prompt. Do not edit - it reproduces the baseline result.
SYSTEM_PROMPT = """You extract fields from the OCR text of one medical receipt or invoice.
Rules:
- Use only the OCR text you are given. Copy each value exactly as it appears in the text.
- Do not correct, complete, reformat or guess values, even if they look like OCR errors.
- If a field is not in the text, return null. Never invent a value.

Fields:
- doctor_name: the doctor, clinician or other practitioner who provided the service.
- registration_number: that practitioner's professional registration or licence number
  (not a patient, hospital, bed or invoice number).
- patient_name: the patient's name.
- receipt_number: the number of this receipt or invoice.
- service_date: the date the service or visit took place, exactly as written.
- total_amount: the total amount charged. If the total line is blank, use the amount paid,
  else the subtotal. Do not use an outstanding balance or amount due of zero."""

# Prompt v2: the same task with explicit, general field definitions (no examples from the
# benchmark receipts).
SYSTEM_PROMPT_V2 = """You extract fields from the OCR text of one medical receipt or invoice.
The text is laid out in rows: each line is one row of the page, read left to right, and " | "
separates blocks of text that sit side by side on that row (often a label and its value).

Rules:
- Use only the text you are given. Copy the characters of each value exactly as they appear. Do
  not correct, complete or guess values, even if they look like OCR errors.
- Return only the value itself, without its label (for example without "Reg. No.", "Receipt No."
  or "Date:") and without other text from the same line.
- If a field is not in the text, return null. Never invent a value.
- List in uncertain_fields every field you are not confident about, for example when the receipt
  shows several candidates and none is clearly labelled for that field.

Fields:
- doctor_name: the person who provided the service (doctor, dentist, clinician, therapist,
  practitioner or vet): the person's name only, keeping a title such as "Dr." if written.
  Leave out qualifications and post-nominals (degrees, fellowships, licences), job titles and
  specialties, and clinic, hospital or practice names, even when they are on the same line. If
  the receipt names more than one person as providing or signing for the service, return all of
  them separated by "; ". Do not include referring doctors, nurses or other staff.
- registration_number: that practitioner's professional registration or licence number: the
  identifier only, without its label (not a patient, hospital, bed, tax or invoice number).
- patient_name: the patient's name only.
- receipt_number: the number of this receipt or invoice document (not a payment, transaction,
  patient or policy number).
- service_date: the date the consultation, treatment, visit or supply took place, exactly as
  written. Not a print, issue, invoice or next-appointment date. If the receipt does not clearly
  show which date is the service date, return the most likely one and add service_date to
  uncertain_fields.
- total_amount: the final amount charged for this receipt, after any discounts, rounding or other
  adjustments. Not a subtotal, a single item, or an outstanding balance or amount due of zero.
  If no total is shown, use the amount paid, else the subtotal."""

IMAGE_NOTE = """
A photo of the receipt is attached. Use it to check the OCR text: where a value is misread,
missing or unclear in the OCR text (for example handwriting, a stamp or a signature), read it
from the photo. Return only text that is clearly visible, and add the field to uncertain_fields
if it is hard to read."""

# Added to prompt v2 with --diagnosis. Separate from the six fields and scored separately.
DIAGNOSIS_NOTE = """

Also report whether the receipt has a diagnosis comment: any written information about the
patient's condition, symptoms or diagnosis, with or without a label (for example under Diagnosis,
Symptoms, Condition, Chief complaint, 診斷, 症狀, 病情, or a medical comment under Notes, Remarks or
備註). Do not judge whether it is medically correct.
- diagnosis_comment: "present" if there is such a comment; "missing" if there is none, including a
  label printed with nothing after it or only "-", "N/A" or similar; "needs_review" if you cannot
  tell, for example unreadable text or a remark that may or may not be about the patient's condition.
  Names of services, treatments, tests or medicines on their own are not a diagnosis comment, and
  neither are administrative remarks (payment, insurance, appointments, opening hours).
- diagnosis_evidence: the comment copied exactly from the text, with its label if it has one; null
  if diagnosis_comment is "missing"."""

PROMPTS = {"v1": SYSTEM_PROMPT, "v2": SYSTEM_PROMPT_V2}
BASELINE = {"prompt": "v1", "text": "plain", "image": False}
IMPROVED = {"prompt": "v2", "text": "rows", "image": False}

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "receipt_fields",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {f: {"type": ["string", "null"]} for f in FIELDS},
            "required": FIELDS,
            "additionalProperties": False,
        },
    },
}
RESPONSE_SCHEMA_V2 = json.loads(json.dumps(RESPONSE_SCHEMA))
RESPONSE_SCHEMA_V2["json_schema"]["schema"]["properties"]["uncertain_fields"] = {
    "type": "array", "items": {"type": "string", "enum": FIELDS}}
RESPONSE_SCHEMA_V2["json_schema"]["schema"]["required"] = FIELDS + ["uncertain_fields"]
DIAGNOSIS_KEYS = ["diagnosis_comment", "diagnosis_evidence"]
RESPONSE_SCHEMA_V2_DIAGNOSIS = json.loads(json.dumps(RESPONSE_SCHEMA_V2))
RESPONSE_SCHEMA_V2_DIAGNOSIS["json_schema"]["schema"]["properties"].update({
    "diagnosis_comment": {"type": "string", "enum": list(aoai_validation.DIAGNOSIS_STATUSES)},
    "diagnosis_evidence": {"type": ["string", "null"]}})
RESPONSE_SCHEMA_V2_DIAGNOSIS["json_schema"]["schema"]["required"] = FIELDS + ["uncertain_fields"] + DIAGNOSIS_KEYS
MAX_COMPLETION_TOKENS = 4000  # includes reasoning tokens; too low a cap returns empty content
IMAGE_MAX_PX = 2000  # longest side of the attached photo


class ExtractionError(Exception):
    """The model replied, but not with usable fields (empty, truncated, refused, not JSON)."""


def settings() -> dict:
    missing = [v for v in ("AZURE_CLIENT_ID", "AZURE_DI_ENDPOINT", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
               if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing environment variable(s): {', '.join(missing)}. AZURE_CLIENT_ID is the client ID of the "
                 "user-assigned managed identity on this compute; AZURE_DI_ENDPOINT and AZURE_OPENAI_ENDPOINT are "
                 "the service endpoints; AZURE_OPENAI_DEPLOYMENT is the deployment name (e.g. gpt-5-mini).")
    for v in ("AZURE_DI_ENDPOINT", "AZURE_OPENAI_ENDPOINT"):
        if not os.environ[v].startswith("https://"):
            sys.exit(f"{v} must start with https://, got {os.environ[v]!r}.")
    return {
        "client_id": os.environ["AZURE_CLIENT_ID"],
        "endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
        "deployment": os.environ["AZURE_OPENAI_DEPLOYMENT"],
        "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        "reasoning_effort": os.environ.get("AZURE_OPENAI_REASONING_EFFORT", "low"),
        "timeout": float(os.environ.get("AZURE_OPENAI_TIMEOUT_SECONDS", "60")),
        "max_retries": int(os.environ.get("AZURE_OPENAI_MAX_RETRIES", "2")),
    }


def aoai_client(cfg: dict):
    """Azure OpenAI client authenticated with the user-assigned managed identity."""
    from azure.identity import ManagedIdentityCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    token_provider = get_bearer_token_provider(ManagedIdentityCredential(client_id=cfg["client_id"]),
                                               "https://cognitiveservices.azure.com/.default")
    return AzureOpenAI(azure_endpoint=cfg["endpoint"], azure_ad_token_provider=token_provider,
                       api_version=cfg["api_version"], timeout=cfg["timeout"], max_retries=cfg["max_retries"])


def rows_text(page: dict) -> str:
    """DI lines regrouped into the rows of the page: lines whose vertical centres are within half a
    line height of each other (after undoing the page's skew angle) form one row, left to right,
    joined with " | ". Reading order is otherwise kept: rows run top to bottom."""
    a = -math.radians(page.get("angle") or 0)
    items = []
    for ln in page.get("lines", []):
        flat = ln.get("polygon") or []
        xs, ys = flat[0::2], flat[1::2]
        if not xs:
            continue
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        y = cx * math.sin(a) + cy * math.cos(a)
        x = min(xs) * math.cos(a) - cy * math.sin(a)
        items.append((y, x, max(ys) - min(ys), ln["content"]))
    rows = []
    for y, x, h, text in sorted(items):
        if rows and abs(y - rows[-1]["y"]) < 0.5 * min(h, rows[-1]["h"]):
            rows[-1]["items"].append((x, text))
        else:
            rows.append({"y": y, "h": h, "items": [(x, text)]})
    return "\n".join(" | ".join(t for _, t in sorted(r["items"])) for r in rows)


def ocr_text_for(di_result: dict, doc: str, di_ms: float, text_format: str) -> str:
    if not di_result.get("pages"):
        return ""
    if text_format == "rows":
        return rows_text(di_result["pages"][0])
    return azure_di.di_to_raw_ocr(doc, di_result, di_ms).pages[0].plain_text


def image_data_url(path: Path) -> str:
    """The receipt photo, turned upright (EXIF) and downscaled, as a JPEG data URL."""
    from PIL import Image, ImageOps

    with Image.open(path) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    img.thumbnail((IMAGE_MAX_PX, IMAGE_MAX_PX))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_messages(ocr_text: str, prompt: str = "v1", image_url: str | None = None,
                   diagnosis: bool = False) -> list[dict]:
    system = PROMPTS[prompt] + (DIAGNOSIS_NOTE if diagnosis else "") + (IMAGE_NOTE if image_url else "")
    user = f"OCR text:\n{ocr_text}"
    content = user if not image_url else [{"type": "text", "text": user},
                                          {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}]
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def call_aoai(client, cfg: dict, ocr_text: str, prompt: str = "v1", image_url: str | None = None,
              diagnosis: bool = False) -> tuple[dict, dict, float]:
    """Returns (raw model fields, metadata incl. token usage, aoai_ms)."""
    schema = RESPONSE_SCHEMA if prompt == "v1" else RESPONSE_SCHEMA_V2_DIAGNOSIS if diagnosis else RESPONSE_SCHEMA_V2
    start = time.perf_counter()
    resp = client.chat.completions.create(model=cfg["deployment"],
                                          messages=build_messages(ocr_text, prompt, image_url, diagnosis),
                                          response_format=schema,
                                          reasoning_effort=cfg["reasoning_effort"],
                                          max_completion_tokens=MAX_COMPLETION_TOKENS)
    aoai_ms = (time.perf_counter() - start) * 1000
    choice = resp.choices[0]
    meta = {"model": getattr(resp, "model", None), "finish_reason": choice.finish_reason,
            "usage": resp.usage.model_dump() if getattr(resp, "usage", None) is not None else None}
    return parse_reply(choice.message.content, choice.finish_reason, getattr(choice.message, "refusal", None)), meta, aoai_ms


def parse_reply(content: str | None, finish_reason: str | None = "stop", refusal: str | None = None) -> dict:
    """The model's JSON reply -> {field: raw value}. Raises ExtractionError if it is unusable."""
    if refusal:
        raise ExtractionError(f"model refused: {refusal}")
    if not content:
        hint = " - output hit max_completion_tokens (reasoning tokens count too)" if finish_reason == "length" else ""
        raise ExtractionError(f"empty reply (finish_reason={finish_reason}){hint}")
    if finish_reason not in (None, "stop"):
        raise ExtractionError(f"incomplete reply (finish_reason={finish_reason})")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"reply is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ExtractionError("reply is not a JSON object")
    return data


def normalize_fields(raw: dict) -> tuple[dict, list[str]]:
    """Exactly FIELDS (missing -> null, extras ignored), stripped strings, ISO dates (day-first,
    like the general rules), numeric amounts. Values that cannot be normalized are kept as written
    (and will score as wrong) - nothing is guessed."""
    warnings = [f"ignored unexpected field {k!r}" for k in raw if k not in FIELDS]
    fields = {}
    for f in FIELDS:
        if f not in raw:
            warnings.append(f"{f}: missing from reply, set to null")
        v = raw.get(f)
        v = v.strip() if isinstance(v, str) else v
        if v in (None, "", "-", "null", "N/A", "n/a"):
            v = None
        elif f == "service_date":
            parsed = parse_date(str(v))
            if parsed:
                if "ambiguous" in parsed[1]:
                    warnings.append(f"service_date: {v!r} read day-first as {parsed[0]}")
                v = parsed[0]
            else:
                warnings.append(f"service_date: could not parse {v!r}, kept as written")
        elif f == "total_amount":
            parsed = parse_amount(str(v))
            if parsed:
                v = parsed[0]
            else:
                warnings.append(f"total_amount: could not parse {v!r}, kept as written")
        fields[f] = v
    return fields, warnings


def explain_aoai_error(exc: Exception, cfg: dict) -> tuple[str, bool]:
    """Returns (message, fatal). Matched by class name / status code, so tests need no openai
    package. Fatal = would fail every receipt the same way, so the run stops."""
    names = {c.__name__ for c in type(exc).__mro__}
    status = getattr(exc, "status_code", None)
    detail = f"({type(exc).__name__}: {exc})"
    if "APITimeoutError" in names:
        return (f"Azure OpenAI timed out after {cfg['timeout']:.0f}s per attempt, {cfg['max_retries']} retries. "
                f"{detail}"), False
    if "ClientAuthenticationError" in names and status is None:
        return azure_di.explain_error(exc)
    if status in (401, 403):
        return (f"Azure OpenAI refused the managed identity (HTTP {status}). Grant it the 'Cognitive Services "
                f"OpenAI User' role on the Azure OpenAI resource. {detail}"), True
    if status == 404:
        return (f"Azure OpenAI deployment {cfg['deployment']!r} not found at {cfg['endpoint']!r} "
                f"(check AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_DEPLOYMENT). {detail}"), True
    if status == 400:
        return (f"Azure OpenAI rejected the request (HTTP 400). Check that AZURE_OPENAI_API_VERSION "
                f"({cfg['api_version']}) supports structured outputs and reasoning_effort for this deployment. "
                f"{detail}"), True
    if "APIConnectionError" in names:
        return f"Could not reach Azure OpenAI at {cfg['endpoint']!r}. {detail}", True
    return detail.strip("()"), False


def process_receipt(path: Path, di_client, aoai, cfg: dict, response_dir: Path, reuse_di: Path | None,
                    pipeline: dict = IMPROVED) -> tuple[dict, bool]:
    """Returns (result record, fatal). `pipeline` is BASELINE, IMPROVED or a variant of them."""
    doc = path.stem
    timings = {}
    try:
        if reuse_di:
            di_result, di_ms, error = azure_di._load_saved_response(reuse_di / f"{doc}.json")
            if error or di_result is None:
                raise RuntimeError(f"saved DI response has no result: {error}")
        else:
            di_result, di_ms = azure_di.analyze(di_client, path)
        (response_dir / f"{doc}.json").write_text(json.dumps(
            {"di_ms": di_ms, "result": di_result, **({"reused_from": str(reuse_di)} if reuse_di else {})},
            indent=2, ensure_ascii=False))
    except Exception as exc:
        message, fatal = azure_di.explain_error(exc)
        return {"document_id": doc, "status": "error", "error_stage": "di", "error": message, "timings": timings}, fatal
    timings["di_ms"] = di_ms
    ocr_text = ocr_text_for(di_result, doc, di_ms, pipeline["text"])

    start = time.perf_counter()
    try:
        image_url = image_data_url(path) if pipeline["image"] else None
        raw, meta, aoai_ms = call_aoai(aoai, cfg, ocr_text, pipeline["prompt"], image_url,
                                       pipeline.get("diagnosis", False))
    except Exception as exc:
        timings["aoai_ms"] = (time.perf_counter() - start) * 1000
        timings["total_ms"] = di_ms + timings["aoai_ms"]
        message, fatal = (str(exc), False) if isinstance(exc, ExtractionError) else explain_aoai_error(exc, cfg)
        return {"document_id": doc, "status": "error", "error_stage": "aoai", "error": message,
                "input_text": ocr_text, "timings": timings}, fatal

    raw = dict(raw)
    uncertain = raw.pop("uncertain_fields", None) if pipeline["prompt"] != "v1" else None
    diagnosis = None
    if pipeline.get("diagnosis"):
        reply = {k: raw.pop(k, None) for k in DIAGNOSIS_KEYS}
        status, checks = aoai_validation.check_diagnosis(reply["diagnosis_comment"], reply["diagnosis_evidence"],
                                                         ocr_text, pipeline["image"])
        diagnosis = {"status": status, "evidence": reply["diagnosis_evidence"], "model_status":
                     reply["diagnosis_comment"], "warnings": checks}
    fields, warnings = normalize_fields(raw)
    review = None
    if pipeline["prompt"] != "v1":
        fields, checks, review = aoai_validation.validate(fields, ocr_text, uncertain)
        warnings += checks
    timings.update({"aoai_ms": aoai_ms, "total_ms": di_ms + aoai_ms,
                    # generic names score.py reads: OCR step + extraction step
                    "ocr_predict_ms": di_ms, "extract_ms": aoai_ms})
    return {"document_id": doc, "status": "ok", **fields, "raw_fields": raw, "warnings": warnings,
            **({"review_fields": review, "uncertain_fields": uncertain or []} if review is not None else {}),
            **({"diagnosis": diagnosis} if diagnosis is not None else {}),
            "pipeline": dict(pipeline), "input_text": ocr_text,
            "aoai": {"deployment": cfg["deployment"], "api_version": cfg["api_version"],
                     "reasoning_effort": cfg["reasoning_effort"], **meta},
            "timings": timings}, False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="A receipt file or directory of receipts.")
    parser.add_argument("--output", required=True, type=Path, help="Directory for per-receipt JSON results.")
    parser.add_argument("--reuse-di", type=Path,
                        help="Development only: directory of saved DI responses to use instead of calling DI.")
    parser.add_argument("--prompt", choices=sorted(PROMPTS), default=IMPROVED["prompt"],
                        help="v2 (default): improved prompt + validation. v1: the original benchmark prompt.")
    parser.add_argument("--text", choices=["rows", "plain"], default=IMPROVED["text"],
                        help="rows (default): DI lines grouped into page rows. plain: DI lines in reading order.")
    parser.add_argument("--attach-image", action="store_true",
                        help="Experiment: also send the receipt photo to the model (more input tokens).")
    parser.add_argument("--diagnosis", action="store_true",
                        help="Prompt v2 only: also report whether a diagnosis comment is present, with evidence "
                             "(saved under 'diagnosis'; scored by diagnosis_cli, not by score.py).")
    args = parser.parse_args()
    if args.diagnosis and args.prompt == "v1":
        parser.error("--diagnosis needs prompt v2 (prompt v1 is the frozen baseline)")
    pipeline = {"prompt": args.prompt, "text": args.text, "image": args.attach_image}
    if args.diagnosis:
        pipeline["diagnosis"] = True

    cfg = settings()
    files = (sorted(p for p in args.input.iterdir() if p.suffix.lower() in azure_di.SUPPORTED_SUFFIXES)
             if args.input.is_dir() else [args.input])
    di_client = None if args.reuse_di else azure_di._client()
    aoai = aoai_client(cfg)
    response_dir = args.output / "di_response"
    response_dir.mkdir(parents=True, exist_ok=True)

    failed, tokens = 0, 0
    print(f"Pipeline: prompt {pipeline['prompt']}, text {pipeline['text']}, image {pipeline['image']}")
    for path in files:
        print(f"Processing {path} ...")
        record, fatal = process_receipt(path, di_client, aoai, cfg, response_dir, args.reuse_di, pipeline)
        (args.output / f"{path.stem}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
        t = record["timings"]
        if record["status"] == "ok":
            usage = record["aoai"].get("usage") or {}
            tokens += usage.get("total_tokens") or 0
            print(f"  -> DI {t['di_ms']:.0f} ms + AOAI {t['aoai_ms']:.0f} ms, {usage.get('total_tokens')} tokens")
        else:
            failed += 1
            print(f"  FAILED ({record['error_stage']}): {record['error']}", file=sys.stderr)
            if fatal:
                sys.exit(f"Stopped: this error would affect every receipt. {record['error']}")
    print(f"Done: {len(files) - failed}/{len(files)} ok, {tokens} AOAI tokens in total.")
    if failed:
        print(f"{failed} receipt(s) failed - see status/error in {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
