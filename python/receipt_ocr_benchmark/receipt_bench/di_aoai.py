"""Azure Document Intelligence (prebuilt-read) OCR + Azure OpenAI field extraction.

For each receipt:
  1. DI prebuilt-read reads the text, reusing `azure_di` (the same call and conversion as Phase 3).
  2. The OCR text (DI lines in reading order, nothing else - no image) goes to the Azure OpenAI
     deployment with one fixed prompt. A strict JSON schema makes the reply exactly the six fields.
  3. The reply is parsed and normalized (dates to ISO day-first, amounts to numbers), then saved
     in the same per-receipt shape as the other approaches, so `score.py` reads it unchanged.

The model is told to copy values from the text and to return null for anything not there. It is
NOT told to fix OCR errors, so a year DI misread (e.g. "2020" for a handwritten "2026") stays
as read: this measures extraction from the available evidence.

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

Output per receipt in --output:
- receiptN.json: status "ok", the six fields, the model's raw values, warnings, the OCR text
  sent, token usage, and timings (di_ms, aoai_ms, total_ms).
  On failure it is written with status "error", the stage ("di" / "aoai"), the error and
  timings, and no fields, so the scorer counts the receipt as having no result.
- di_response/receiptN.json: the full DI response (same format as `azure_di`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from receipt_bench import azure_di
from receipt_bench.extraction_tuned import parse_amount, parse_date

FIELDS = ["doctor_name", "registration_number", "patient_name", "receipt_number", "service_date", "total_amount"]

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
MAX_COMPLETION_TOKENS = 4000  # includes reasoning tokens; too low a cap returns empty content


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


def build_messages(ocr_text: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"OCR text:\n{ocr_text}"}]


def call_aoai(client, cfg: dict, ocr_text: str) -> tuple[dict, dict, float]:
    """Returns (raw model fields, metadata incl. token usage, aoai_ms)."""
    start = time.perf_counter()
    resp = client.chat.completions.create(model=cfg["deployment"], messages=build_messages(ocr_text),
                                          response_format=RESPONSE_SCHEMA, reasoning_effort=cfg["reasoning_effort"],
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


def process_receipt(path: Path, di_client, aoai, cfg: dict, response_dir: Path, reuse_di: Path | None) -> tuple[dict, bool]:
    """Returns (result record, fatal)."""
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
    ocr_text = azure_di.di_to_raw_ocr(doc, di_result, di_ms).pages[0].plain_text if di_result.get("pages") else ""

    start = time.perf_counter()
    try:
        raw, meta, aoai_ms = call_aoai(aoai, cfg, ocr_text)
    except Exception as exc:
        timings["aoai_ms"] = (time.perf_counter() - start) * 1000
        timings["total_ms"] = di_ms + timings["aoai_ms"]
        message, fatal = (str(exc), False) if isinstance(exc, ExtractionError) else explain_aoai_error(exc, cfg)
        return {"document_id": doc, "status": "error", "error_stage": "aoai", "error": message,
                "input_text": ocr_text, "timings": timings}, fatal

    fields, warnings = normalize_fields(raw)
    timings.update({"aoai_ms": aoai_ms, "total_ms": di_ms + aoai_ms,
                    # generic names score.py reads: OCR step + extraction step
                    "ocr_predict_ms": di_ms, "extract_ms": aoai_ms})
    return {"document_id": doc, "status": "ok", **fields, "raw_fields": raw, "warnings": warnings,
            "input_text": ocr_text,
            "aoai": {"deployment": cfg["deployment"], "api_version": cfg["api_version"],
                     "reasoning_effort": cfg["reasoning_effort"], **meta},
            "timings": timings}, False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="A receipt file or directory of receipts.")
    parser.add_argument("--output", required=True, type=Path, help="Directory for per-receipt JSON results.")
    parser.add_argument("--reuse-di", type=Path,
                        help="Development only: directory of saved DI responses to use instead of calling DI.")
    args = parser.parse_args()

    cfg = settings()
    files = (sorted(p for p in args.input.iterdir() if p.suffix.lower() in azure_di.SUPPORTED_SUFFIXES)
             if args.input.is_dir() else [args.input])
    di_client = None if args.reuse_di else azure_di._client()
    aoai = aoai_client(cfg)
    response_dir = args.output / "di_response"
    response_dir.mkdir(parents=True, exist_ok=True)

    failed, tokens = 0, 0
    for path in files:
        print(f"Processing {path} ...")
        record, fatal = process_receipt(path, di_client, aoai, cfg, response_dir, args.reuse_di)
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
