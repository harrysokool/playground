"""DI + Azure OpenAI tests with fake clients - no Azure SDK, no openai package, no network, no cost."""

import json
import sys
import types

import pytest

from receipt_bench import di_aoai
from receipt_bench.di_aoai import (ExtractionError, build_messages, explain_aoai_error, normalize_fields,
                                   parse_reply, process_receipt)
from receipt_bench.score import read_result

CFG = {"client_id": "cid", "endpoint": "https://aoai.openai.azure.com/", "deployment": "gpt-5-mini",
       "api_version": "2025-04-01-preview", "reasoning_effort": "low", "timeout": 60.0, "max_retries": 2}


def _di_result(lines):
    """Minimal prebuilt-read result: one line + one word per text."""
    content, di_lines, words = "", [], []
    for i, text in enumerate(lines):
        di_lines.append({"content": text, "polygon": [0, i * 40, 300, i * 40, 300, i * 40 + 30, 0, i * 40 + 30],
                         "spans": [{"offset": len(content), "length": len(text)}]})
        words.append({"content": text, "confidence": 0.9, "span": {"offset": len(content), "length": len(text)}})
        content += text + "\n"
    return {"modelId": "prebuilt-read", "apiVersion": "2024-11-30", "content": content,
            "pages": [{"pageNumber": 1, "width": 1000, "height": 1400, "unit": "pixel", "lines": di_lines, "words": words}]}


RECEIPT_LINES = ["MEDICAL INVOICE", "Dr. Lau Sai Kit, Lawrence", "Admission Date", "07/02/2020", "TOTAL", "1540.00"]


class FakeCompletions:
    def __init__(self, reply=None, exc=None, finish_reason="stop"):
        self.reply, self.exc, self.finish_reason, self.calls = reply, exc, finish_reason, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        message = types.SimpleNamespace(content=self.reply, refusal=None)
        usage = types.SimpleNamespace(model_dump=lambda: {"prompt_tokens": 400, "completion_tokens": 120, "total_tokens": 520})
        return types.SimpleNamespace(model="gpt-5-mini", usage=usage,
                                     choices=[types.SimpleNamespace(message=message, finish_reason=self.finish_reason)])


def _aoai(**kwargs):
    completions = FakeCompletions(**kwargs)
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions)), completions


def _reply(**fields):
    return json.dumps({f: fields.get(f) for f in di_aoai.FIELDS})


@pytest.fixture
def di(monkeypatch):
    """Fake DI call returning RECEIPT_LINES in 2300 ms."""
    monkeypatch.setattr(di_aoai.azure_di, "analyze", lambda client, path: (_di_result(RECEIPT_LINES), 2300.0))


# --- managed identity authentication --------------------------------------------------------


@pytest.fixture
def fake_sdk(monkeypatch):
    calls = {}

    class ManagedIdentityCredential:
        def __init__(self, *, client_id):
            calls["client_id"] = client_id

    def get_bearer_token_provider(credential, *scopes):
        calls["provider"] = (type(credential).__name__, scopes)
        return lambda: "token"

    class AzureOpenAI:
        def __init__(self, **kwargs):
            calls["aoai"] = kwargs

    for name in ("azure", "azure.ai"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "azure.identity", types.SimpleNamespace(
        ManagedIdentityCredential=ManagedIdentityCredential, get_bearer_token_provider=get_bearer_token_provider))
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(AzureOpenAI=AzureOpenAI))
    for var, value in {"AZURE_CLIENT_ID": "cid-123", "AZURE_DI_ENDPOINT": "https://di.cognitiveservices.azure.com/",
                       "AZURE_OPENAI_ENDPOINT": "https://aoai.openai.azure.com/",
                       "AZURE_OPENAI_DEPLOYMENT": "gpt-5-mini"}.items():
        monkeypatch.setenv(var, value)
    return calls


def test_aoai_client_uses_user_assigned_managed_identity(fake_sdk):
    di_aoai.aoai_client(di_aoai.settings())
    assert fake_sdk["client_id"] == "cid-123"
    assert fake_sdk["provider"] == ("ManagedIdentityCredential", ("https://cognitiveservices.azure.com/.default",))
    kw = fake_sdk["aoai"]
    assert kw["azure_endpoint"] == "https://aoai.openai.azure.com/" and kw["api_version"] == "2025-04-01-preview"
    assert (kw["timeout"], kw["max_retries"]) == (60.0, 2)
    assert "api_key" not in kw


def test_timeout_and_retries_are_configurable(fake_sdk, monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("AZURE_OPENAI_MAX_RETRIES", "1")
    di_aoai.aoai_client(di_aoai.settings())
    assert (fake_sdk["aoai"]["timeout"], fake_sdk["aoai"]["max_retries"]) == (30.0, 1)


@pytest.mark.parametrize("var", ["AZURE_CLIENT_ID", "AZURE_DI_ENDPOINT", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"])
def test_missing_configuration_gives_clear_error(fake_sdk, monkeypatch, var):
    monkeypatch.delenv(var)
    with pytest.raises(SystemExit, match=var):
        di_aoai.settings()


def test_no_api_key_or_default_credential_auth():
    source = open(di_aoai.__file__).read()
    assert "api_key" not in source and "DefaultAzureCredential" not in source


# --- DI -> AOAI input --------------------------------------------------------------------------


def test_ocr_text_is_sent_in_reading_order_without_corrections(di, tmp_path):
    aoai, completions = _aoai(reply=_reply())
    process_receipt(di_aoai.Path("receipt1.png"), None, aoai, CFG, tmp_path, None)

    call = completions.calls[0]
    user = call["messages"][1]["content"]
    assert user == "OCR text:\n" + "\n".join(RECEIPT_LINES)
    assert "2020" in user and "2026" not in json.dumps(call)  # the misread year is passed through as-is
    assert call["model"] == "gpt-5-mini" and call["reasoning_effort"] == "low"
    assert call["response_format"]["json_schema"]["schema"]["required"] == di_aoai.FIELDS


def test_prompt_is_fixed_and_forbids_invention():
    msgs_a, msgs_b = build_messages("A"), build_messages("B")
    assert msgs_a[0] == msgs_b[0]  # same system prompt for every receipt
    assert "Never invent" in msgs_a[0]["content"] and "Do not correct" in msgs_a[0]["content"]


# --- reply parsing and field normalization --------------------------------------------------


def test_parse_reply_accepts_json_and_rejects_unusable_replies():
    assert parse_reply('{"doctor_name": "Dr A"}') == {"doctor_name": "Dr A"}
    with pytest.raises(ExtractionError, match="max_completion_tokens"):
        parse_reply("", finish_reason="length")
    with pytest.raises(ExtractionError, match="not JSON"):
        parse_reply("doctor: Dr A")
    with pytest.raises(ExtractionError, match="refused"):
        parse_reply(None, refusal="cannot help")
    with pytest.raises(ExtractionError, match="content_filter"):
        parse_reply('{"doctor_name": null}', finish_reason="content_filter")


def test_normalizes_dates_and_amounts_without_changing_the_evidence():
    fields, warnings = normalize_fields({"doctor_name": " Dr. Lau ", "registration_number": None, "patient_name": "",
                                         "receipt_number": "967157032", "service_date": "07/02/2020",
                                         "total_amount": "HKD 1,540.00"})
    assert fields == {"doctor_name": "Dr. Lau", "registration_number": None, "patient_name": None,
                      "receipt_number": "967157032", "service_date": "2020-02-07", "total_amount": 1540.0}
    assert any("day-first" in w for w in warnings)


def test_missing_and_unexpected_fields_are_handled_explicitly():
    fields, warnings = normalize_fields({"doctor_name": "Dr A", "visit_date": "01/02/2026", "total_amount": "-"})
    assert set(fields) == set(di_aoai.FIELDS)
    assert fields["service_date"] is None and fields["total_amount"] is None
    assert "ignored unexpected field 'visit_date'" in warnings
    assert "patient_name: missing from reply, set to null" in warnings


def test_unparseable_values_are_kept_as_written():
    fields, _ = normalize_fields({"service_date": "sometime in spring", "total_amount": "paid"})
    assert fields["service_date"] == "sometime in spring" and fields["total_amount"] == "paid"


# --- errors, timeouts, recording failures ---------------------------------------------------


class APITimeoutError(Exception):  # same name as openai's; matched by name
    pass


class StatusError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def test_timeout_is_recorded_and_not_fatal(di, tmp_path):
    aoai, _ = _aoai(exc=APITimeoutError("Request timed out."))
    record, fatal = process_receipt(di_aoai.Path("receipt3.png"), None, aoai, CFG, tmp_path, None)
    assert not fatal
    assert record["status"] == "error" and record["error_stage"] == "aoai"
    assert "timed out after 60s per attempt, 2 retries" in record["error"]
    assert record["timings"]["di_ms"] == 2300.0 and "aoai_ms" in record["timings"]


@pytest.mark.parametrize("status, fatal, text", [
    (401, True, "Cognitive Services OpenAI User"), (403, True, "Cognitive Services OpenAI User"),
    (404, True, "AZURE_OPENAI_DEPLOYMENT"), (400, True, "AZURE_OPENAI_API_VERSION"), (500, False, "HTTP 500"),
])
def test_aoai_http_errors(status, fatal, text):
    message, is_fatal = explain_aoai_error(StatusError(status), CFG)
    assert is_fatal is fatal and text in message


def test_empty_model_reply_is_recorded_as_failure(di, tmp_path):
    aoai, _ = _aoai(reply="", finish_reason="length")
    record, fatal = process_receipt(di_aoai.Path("receipt1.png"), None, aoai, CFG, tmp_path, None)
    assert (record["status"], fatal) == ("error", False) and "finish_reason=length" in record["error"]


def test_run_stops_on_fatal_error_and_records_it(di, fake_sdk, tmp_path, monkeypatch):
    monkeypatch.setattr(di_aoai.azure_di, "_client", lambda: object())
    aoai, _ = _aoai(exc=StatusError(403))
    monkeypatch.setattr(di_aoai, "aoai_client", lambda cfg: aoai)
    for name in ("receipt1.png", "receipt2.png"):
        (tmp_path / name).write_bytes(b"img")
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["di_aoai", "--input", str(tmp_path), "--output", str(out)])

    with pytest.raises(SystemExit, match="Stopped"):
        di_aoai.main()
    assert json.loads((out / "receipt1.json").read_text())["status"] == "error"
    assert not (out / "receipt2.json").exists()


# --- scoring compatibility ------------------------------------------------------------------


def test_successful_result_is_scoring_compatible_with_usage_and_timings(di, tmp_path):
    aoai, _ = _aoai(reply=_reply(doctor_name="Dr. Lau Sai Kit, Lawrence", service_date="07/02/2020", total_amount="1540.00"))
    record, _ = process_receipt(di_aoai.Path("receipt1.png"), None, aoai, CFG, tmp_path, None)
    (tmp_path / "receipt1.json").write_text(json.dumps(record))

    fields, ms = read_result(json.loads((tmp_path / "receipt1.json").read_text()))
    assert fields == {"doctor_name": "Dr. Lau Sai Kit, Lawrence", "registration_number": None, "patient_name": None,
                      "receipt_number": None, "service_date": "2020-02-07", "total_amount": 1540.0}
    assert ms == record["timings"]["total_ms"] == 2300.0 + record["timings"]["aoai_ms"]
    assert record["aoai"]["usage"]["total_tokens"] == 520
    assert record["raw_fields"]["service_date"] == "07/02/2020"


def test_failed_result_counts_as_no_result_in_scoring(di, tmp_path):
    aoai, _ = _aoai(exc=APITimeoutError("Request timed out."))
    record, _ = process_receipt(di_aoai.Path("receipt1.png"), None, aoai, CFG, tmp_path, None)
    assert read_result(json.loads(json.dumps(record)))[0] is None


def test_reuse_di_skips_the_di_call(tmp_path, monkeypatch):
    saved = tmp_path / "saved"
    saved.mkdir()
    (saved / "receipt1.json").write_text(json.dumps({"di_ms": 2100.0, "result": _di_result(RECEIPT_LINES)}))
    monkeypatch.setattr(di_aoai.azure_di, "analyze", lambda *a: pytest.fail("DI must not be called"))
    aoai, _ = _aoai(reply=_reply(total_amount="1540.00"))
    record, _ = process_receipt(di_aoai.Path("receipt1.png"), None, aoai, CFG, tmp_path, saved)
    assert record["status"] == "ok" and record["timings"]["di_ms"] == 2100.0

