"""Proxy tests. Azure is never contacted: a real AsyncAzureOpenAI client is wired to an
in-memory mock transport, and the managed identity token provider is a fake.
All endpoints, IDs and tokens below are synthetic."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest
from azure.core.exceptions import ClientAuthenticationError
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as proxy  # noqa: E402
from config import ConfigError, load_settings  # noqa: E402

try:  # openai>=3 uses httpx2; older SDKs use httpx
    import httpx2 as sdk_http
except ImportError:  # pragma: no cover
    import httpx as sdk_http

PROXY_TOKEN = "test-proxy-token-0123456789abcdefghijklmnop"
FAKE_AZURE_TOKEN = "fake-azure-access-token"
DEPLOYMENT = "riley-test-deployment"
ENDPOINT_HOST = "example-resource.cognitiveservices.azure.com"
AUTH = {"Authorization": f"Bearer {PROXY_TOKEN}"}

BASE_ENV = {
    "AZURE_ENDPOINT": f"https://{ENDPOINT_HOST}/",
    "AZURE_DEPLOYMENT": DEPLOYMENT,
    "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000000",
    "AZURE_API_VERSION": "2024-12-01-preview",
    "RILEY_PROXY_TOKEN": PROXY_TOKEN,
    "RILEY_PROXY_MODEL_ALIASES": "riley",
    "RILEY_PROXY_MAX_BODY_BYTES": "4096",
    "RILEY_PROXY_MAX_COMPLETION_TOKENS": "1000",
}

COMPLETION = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "gpt-test-2024-01-01",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello from the mock.", "refusal": None},
            "finish_reason": "stop",
            "logprobs": None,
            "content_filter_results": {"hate": {"filtered": False, "severity": "safe"}},
        }
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9},
    "prompt_filter_results": [{"prompt_index": 0, "content_filter_results": {}}],
    "system_fingerprint": "fp_test",
}

TOOL_COMPLETION = {
    "id": "chatcmpl-tool",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "gpt-test-2024-01-01",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": "{\"city\": \"Hong Kong\"}"},
                    }
                ],
            },
            "finish_reason": "tool_calls",
            "logprobs": None,
        }
    ],
    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
}

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the weather for a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    },
}


def chat_body(**overrides: Any) -> Dict[str, Any]:
    body: Dict[str, Any] = {"model": DEPLOYMENT, "messages": [{"role": "user", "content": "Say hello."}]}
    body.update(overrides)
    return body


def sse_body(events: List[Any], done: bool = True) -> bytes:
    lines = [f"data: {json.dumps(e)}\n\n" for e in events]
    if done:
        lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


def parse_sse(text: str) -> List[Any]:
    out = []
    for block in text.strip().split("\n\n"):
        assert block.startswith("data: "), block
        data = block[len("data: "):]
        out.append(data if data == "[DONE]" else json.loads(data))
    return out


class Upstream:
    """Mock Azure OpenAI: records requests and answers with a configurable handler."""

    def __init__(self) -> None:
        self.requests: List[Any] = []
        self.handler: Callable[[Any], Any] = lambda req: sdk_http.Response(200, json=COMPLETION)

    def __call__(self, request: Any) -> Any:
        self.requests.append(request)
        return self.handler(request)

    @property
    def last_json(self) -> Dict[str, Any]:
        return json.loads(self.requests[-1].content)


@pytest.fixture
def settings():
    return load_settings(BASE_ENV)


@pytest.fixture
def upstream():
    return Upstream()


@pytest.fixture
def token_provider():
    state = {"calls": 0, "error": None}

    async def provider() -> str:
        state["calls"] += 1
        if state["error"] is not None:
            raise state["error"]
        return FAKE_AZURE_TOKEN

    provider.state = state  # type: ignore[attr-defined]
    return provider


@pytest.fixture
def client(settings, upstream, token_provider):
    http_client = sdk_http.AsyncClient(transport=sdk_http.MockTransport(upstream))
    azure = proxy.build_client(settings, token_provider, http_client=http_client, max_retries=0)
    with TestClient(proxy.create_app(settings, azure)) as test_client:
        yield test_client


# --- 1. health ------------------------------------------------------------------------


def test_health_needs_no_token_and_does_not_call_azure(client, upstream, token_provider):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert upstream.requests == []
    assert token_provider.state["calls"] == 0


# --- 2. proxy token -------------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong-token"},
        {"Authorization": f"Bearer {PROXY_TOKEN}x"},
        {"Authorization": f"Bearer {PROXY_TOKEN[:-1]}"},
        {"Authorization": f"Basic {PROXY_TOKEN}"},
        {"Authorization": "Bearer "},
        {"Authorization": PROXY_TOKEN},
        {"api-key": PROXY_TOKEN},
    ],
)
def test_missing_or_invalid_token_is_rejected(client, upstream, headers):
    resp = client.post("/v1/chat/completions", json=chat_body(), headers=headers)
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"
    assert resp.json()["error"]["code"] == "invalid_proxy_token"
    assert upstream.requests == []


def test_token_in_query_string_is_not_accepted(client, upstream):
    resp = client.post(f"/v1/chat/completions?api_key={PROXY_TOKEN}", json=chat_body())
    assert resp.status_code == 401
    assert upstream.requests == []


def test_auth_is_checked_before_body_is_parsed(client):
    resp = client.post("/v1/chat/completions", content=b"not json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 401


def test_bearer_scheme_is_case_insensitive(client):
    resp = client.post("/v1/chat/completions", json=chat_body(), headers={"Authorization": f"bearer {PROXY_TOKEN}"})
    assert resp.status_code == 200


# --- 3. successful chat completion ----------------------------------------------------


def test_chat_completion_is_forwarded_to_fixed_deployment(client, upstream):
    resp = client.post("/v1/chat/completions", json=chat_body(temperature=0.2), headers=AUTH)

    assert resp.status_code == 200
    assert resp.json() == COMPLETION  # including Azure-specific filter fields

    sent = upstream.requests[-1]
    assert sent.url.host == ENDPOINT_HOST
    assert sent.url.path == f"/openai/deployments/{DEPLOYMENT}/chat/completions"
    assert sent.url.params["api-version"] == "2024-12-01-preview"
    assert sent.headers["authorization"] == f"Bearer {FAKE_AZURE_TOKEN}"
    assert "api-key" not in sent.headers
    body = upstream.last_json
    assert body["messages"] == [{"role": "user", "content": "Say hello."}]
    assert body["temperature"] == 0.2
    assert body["max_completion_tokens"] == 1000  # proxy default cap applied
    assert "max_tokens" not in body


def test_proxy_token_is_not_forwarded_to_azure(client, upstream):
    client.post("/v1/chat/completions", json=chat_body(), headers=AUTH)
    sent = upstream.requests[-1]
    assert PROXY_TOKEN not in str(sent.headers)
    assert PROXY_TOKEN.encode() not in sent.content


def test_token_provider_called_per_request(client, token_provider):
    for _ in range(3):
        assert client.post("/v1/chat/completions", json=chat_body(), headers=AUTH).status_code == 200
    assert token_provider.state["calls"] == 3


def test_max_tokens_is_translated_to_max_completion_tokens(client, upstream):
    client.post("/v1/chat/completions", json=chat_body(max_tokens=50), headers=AUTH)
    assert upstream.last_json["max_completion_tokens"] == 50
    assert "max_tokens" not in upstream.last_json


def test_max_completion_tokens_is_capped(client, upstream):
    client.post("/v1/chat/completions", json=chat_body(max_completion_tokens=999999), headers=AUTH)
    assert upstream.last_json["max_completion_tokens"] == 1000


def test_store_false_is_accepted_and_not_forwarded(client, upstream):
    assert client.post("/v1/chat/completions", json=chat_body(store=False), headers=AUTH).status_code == 200
    assert "store" not in upstream.last_json


# --- 4. streaming ---------------------------------------------------------------------


def _chunk(delta: Dict[str, Any], finish: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    chunk = {
        "id": "chatcmpl-stream",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "gpt-test-2024-01-01",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    chunk.update(extra)
    return chunk


def test_streaming_response(client, upstream):
    events = [
        {"id": "", "object": "", "created": 0, "model": "", "choices": [], "prompt_filter_results": []},
        _chunk({"role": "assistant", "content": ""}),
        _chunk({"content": "Hel"}),
        _chunk({"content": "lo"}),
        _chunk({}, "stop"),
    ]
    upstream.handler = lambda req: sdk_http.Response(
        200, content=sse_body(events), headers={"content-type": "text/event-stream"}
    )

    resp = client.post(
        "/v1/chat/completions",
        json=chat_body(stream=True, stream_options={"include_usage": True}),
        headers=AUTH,
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    received = parse_sse(resp.text)
    assert received[-1] == "[DONE]"
    assert received[:-1] == events
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in received[1:-1])
    assert text == "Hello"
    assert upstream.last_json["stream"] is True
    assert upstream.last_json["stream_options"] == {"include_usage": True}


def test_streaming_tool_call_deltas_are_preserved(client, upstream):
    events = [
        _chunk({"role": "assistant", "content": None, "tool_calls": [
            {"index": 0, "id": "call_abc123", "type": "function", "function": {"name": "get_weather", "arguments": ""}}
        ]}),
        _chunk({"tool_calls": [{"index": 0, "function": {"arguments": "{\"city\": "}}]}),
        _chunk({"tool_calls": [{"index": 0, "function": {"arguments": "\"Hong Kong\"}"}}]}),
        _chunk({}, "tool_calls"),
    ]
    upstream.handler = lambda req: sdk_http.Response(
        200, content=sse_body(events), headers={"content-type": "text/event-stream"}
    )

    resp = client.post("/v1/chat/completions", json=chat_body(stream=True, tools=[WEATHER_TOOL]), headers=AUTH)

    received = parse_sse(resp.text)
    assert received[:-1] == events
    args = "".join(c["choices"][0]["delta"]["tool_calls"][0]["function"]["arguments"] for c in received[:3])
    assert json.loads(args) == {"city": "Hong Kong"}


def test_streaming_upstream_error_before_first_byte_returns_http_error(client, upstream):
    upstream.handler = lambda req: sdk_http.Response(429, json={"error": {"code": "429", "message": "slow down"}})
    resp = client.post("/v1/chat/completions", json=chat_body(stream=True), headers=AUTH)
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "rate_limited"


def test_streaming_error_mid_stream_emits_error_event_without_done(client, upstream):
    events = [_chunk({"role": "assistant", "content": "Hi"}), {"error": {"message": "internal secret detail", "code": "server_error"}}]
    upstream.handler = lambda req: sdk_http.Response(
        200, content=sse_body(events, done=False), headers={"content-type": "text/event-stream"}
    )

    resp = client.post("/v1/chat/completions", json=chat_body(stream=True), headers=AUTH)

    received = parse_sse(resp.text)
    assert received[0] == events[0]
    assert received[-1]["error"]["code"] == "upstream_error"
    assert "[DONE]" not in received
    assert "internal secret detail" not in resp.text


def test_streaming_connection_drop_mid_stream_emits_error_event(client, upstream):
    class Broken(sdk_http.AsyncByteStream):
        async def __aiter__(self):
            yield sse_body([_chunk({"content": "partial"})], done=False)
            raise sdk_http.ReadError("connection reset")

    upstream.handler = lambda req: sdk_http.Response(200, stream=Broken(), headers={"content-type": "text/event-stream"})

    resp = client.post("/v1/chat/completions", json=chat_body(stream=True), headers=AUTH)

    received = parse_sse(resp.text)
    assert received[0]["choices"][0]["delta"]["content"] == "partial"
    assert received[-1]["error"]["code"] == "upstream_unreachable"


# --- 5. tool calling ------------------------------------------------------------------


def test_tool_calling_request_and_response_are_preserved(client, upstream):
    upstream.handler = lambda req: sdk_http.Response(200, json=TOOL_COMPLETION)
    resp = client.post(
        "/v1/chat/completions",
        json=chat_body(tools=[WEATHER_TOOL], tool_choice="auto", parallel_tool_calls=False),
        headers=AUTH,
    )

    assert resp.status_code == 200
    assert resp.json() == TOOL_COMPLETION
    body = upstream.last_json
    assert body["tools"] == [WEATHER_TOOL]
    assert body["tool_choice"] == "auto"
    assert body["parallel_tool_calls"] is False


def test_tool_result_round_trip_is_forwarded(client, upstream):
    messages = [
        {"role": "system", "content": "You are Riley."},
        {"role": "user", "content": "Weather in Hong Kong?"},
        TOOL_COMPLETION["choices"][0]["message"],
        {"role": "tool", "tool_call_id": "call_abc123", "content": "{\"temp_c\": 28}"},
    ]
    resp = client.post(
        "/v1/chat/completions",
        json=chat_body(messages=messages, tools=[WEATHER_TOOL], tool_choice={"type": "function", "function": {"name": "get_weather"}}),
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = upstream.last_json
    assert body["messages"][2]["tool_calls"] == TOOL_COMPLETION["choices"][0]["message"]["tool_calls"]
    assert body["messages"][3] == messages[3]
    assert body["tool_choice"] == {"type": "function", "function": {"name": "get_weather"}}


# --- 6. deployment restrictions -------------------------------------------------------


@pytest.mark.parametrize("model", ["gpt-4o", "other-deployment", f"{DEPLOYMENT}/../x", "../deployments/x", ""])
def test_unauthorized_models_are_rejected(client, upstream, model):
    resp = client.post("/v1/chat/completions", json=chat_body(model=model), headers=AUTH)
    assert resp.status_code in (400, 403)
    assert upstream.requests == []


def test_missing_model_is_rejected(client, upstream):
    body = chat_body()
    del body["model"]
    assert client.post("/v1/chat/completions", json=body, headers=AUTH).status_code == 400
    assert upstream.requests == []


def test_alias_maps_to_fixed_deployment(client, upstream):
    resp = client.post("/v1/chat/completions", json=chat_body(model="riley"), headers=AUTH)
    assert resp.status_code == 200
    assert upstream.requests[-1].url.path == f"/openai/deployments/{DEPLOYMENT}/chat/completions"
    assert upstream.last_json["model"] == DEPLOYMENT


# --- 7. unsupported parameters --------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        {"data_sources": [{"type": "azure_search", "parameters": {"endpoint": "https://evil.example"}}]},
        {"extra_body": {"x": 1}},
        {"functions": [{"name": "f"}]},
        {"audio": {"voice": "alloy"}},
        {"web_search_options": {}},
        {"base_url": "https://evil.example"},
        {"api_version": "2099-01-01"},
        {"n": 2},
        {"store": True},
        {"metadata": {"a": "b"}},
    ],
)
def test_unsupported_parameters_are_rejected(client, upstream, extra):
    resp = client.post("/v1/chat/completions", json=chat_body(**extra), headers=AUTH)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unsupported_parameter"
    assert upstream.requests == []


# --- 8. Azure failures ----------------------------------------------------------------


@pytest.mark.parametrize(
    "status,expected_status,expected_code",
    [
        (401, 502, "upstream_auth_failed"),
        (403, 502, "upstream_auth_failed"),
        (404, 502, "upstream_not_found"),
        (500, 502, "upstream_error"),
        (503, 502, "upstream_error"),
    ],
)
def test_azure_errors_are_mapped_without_leaking_details(client, upstream, status, expected_status, expected_code):
    upstream.handler = lambda req: sdk_http.Response(
        status, json={"error": {"code": "X", "message": f"detail about https://{ENDPOINT_HOST} and {DEPLOYMENT}"}}
    )
    resp = client.post("/v1/chat/completions", json=chat_body(), headers=AUTH)
    assert resp.status_code == expected_status
    assert resp.json()["error"]["code"] == expected_code
    assert ENDPOINT_HOST not in resp.text
    assert DEPLOYMENT not in resp.text


def test_azure_bad_request_passes_safe_message_and_code(client, upstream):
    upstream.handler = lambda req: sdk_http.Response(
        400, json={"error": {"code": "content_filter", "message": "The prompt was filtered."}}
    )
    resp = client.post("/v1/chat/completions", json=chat_body(), headers=AUTH)
    assert resp.status_code == 400
    assert resp.json()["error"] == {
        "message": "The prompt was filtered.",
        "type": "invalid_request_error",
        "param": None,
        "code": "content_filter",
    }


def test_azure_rate_limit_preserves_retry_after(client, upstream):
    upstream.handler = lambda req: sdk_http.Response(429, json={"error": {"code": "429"}}, headers={"retry-after": "7"})
    resp = client.post("/v1/chat/completions", json=chat_body(), headers=AUTH)
    assert resp.status_code == 429
    assert resp.headers["retry-after"] == "7"


def test_azure_connection_failure(client, upstream):
    def fail(req):
        raise sdk_http.ConnectError("boom")

    upstream.handler = fail
    resp = client.post("/v1/chat/completions", json=chat_body(), headers=AUTH)
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "upstream_unreachable"


def test_azure_timeout(client, upstream):
    def slow(req):
        raise sdk_http.ReadTimeout("too slow")

    upstream.handler = slow
    resp = client.post("/v1/chat/completions", json=chat_body(), headers=AUTH)
    assert resp.status_code == 504
    assert resp.json()["error"]["code"] == "upstream_timeout"


def test_managed_identity_failure(client, upstream, token_provider):
    token_provider.state["error"] = ClientAuthenticationError("IMDS unreachable for client 0000")
    resp = client.post("/v1/chat/completions", json=chat_body(), headers=AUTH)
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "upstream_auth_unavailable"
    assert "IMDS" not in resp.text
    assert upstream.requests == []


# --- 9. request validation and security controls -------------------------------------


def test_oversized_body_rejected_by_content_length(client, upstream):
    big = chat_body(messages=[{"role": "user", "content": "x" * 5000}])
    resp = client.post("/v1/chat/completions", json=big, headers=AUTH)
    assert resp.status_code == 413
    assert upstream.requests == []


def test_oversized_chunked_body_rejected(client, upstream):
    def chunks():
        yield b'{"model": "riley-test-deployment", "messages": [{"role": "user", "content": "'
        for _ in range(10):
            yield b"x" * 1000
        yield b'"}]}'

    resp = client.post(
        "/v1/chat/completions", content=chunks(), headers={**AUTH, "Content-Type": "application/json"}
    )
    assert resp.status_code == 413
    assert upstream.requests == []


@pytest.mark.parametrize(
    "content,content_type,status",
    [
        (b"{not json", "application/json", 400),
        (b"[1, 2, 3]", "application/json", 400),
        (b'"a string"', "application/json", 400),
        (b"model=x", "application/x-www-form-urlencoded", 415),
        (b'{"model": "x"}', "text/plain", 415),
    ],
)
def test_malformed_bodies_are_rejected(client, upstream, content, content_type, status):
    resp = client.post("/v1/chat/completions", content=content, headers={**AUTH, "Content-Type": content_type})
    assert resp.status_code == status
    assert "error" in resp.json()
    assert upstream.requests == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"messages": []},
        {"messages": "hello"},
        {"messages": [{"content": "no role"}]},
        {"messages": [{"role": "root", "content": "x"}]},
        {"messages": ["not an object"]},
        {"stream": "yes"},
        {"stream_options": {"include_usage": True}},  # without stream=true
        {"tools": {"type": "function"}},
        {"max_tokens": 0},
        {"max_tokens": "100"},
        {"max_completion_tokens": True},
    ],
)
def test_invalid_requests_are_rejected(client, upstream, overrides):
    resp = client.post("/v1/chat/completions", json=chat_body(**overrides), headers=AUTH)
    assert resp.status_code == 400
    assert upstream.requests == []


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/v1/chat/completions"),
        ("GET", "/v1/models"),
        ("POST", "/v1/embeddings"),
        ("POST", "/v1/completions"),
        ("POST", "/v1/responses"),
        ("POST", f"/openai/deployments/{DEPLOYMENT}/chat/completions"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("GET", "/redoc"),
        ("GET", "/https://evil.example/v1/chat/completions"),
    ],
)
def test_unsupported_routes_are_rejected(client, upstream, method, path):
    resp = client.request(method, path, headers=AUTH)
    assert resp.status_code in (404, 405)
    assert "error" in resp.json()
    assert upstream.requests == []


def test_no_cors_headers(client):
    resp = client.options(
        "/v1/chat/completions",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_logs_do_not_contain_tokens_or_bodies(client, upstream, caplog):
    secret_prompt = "synthetic-sensitive-prompt-text"
    upstream.handler = lambda req: sdk_http.Response(500, json={"error": {"message": secret_prompt}})
    with caplog.at_level(logging.DEBUG):
        client.post("/v1/chat/completions", json=chat_body(messages=[{"role": "user", "content": secret_prompt}]), headers=AUTH)
        client.post("/v1/chat/completions", json=chat_body(), headers={"Authorization": "Bearer guess-token"})
    logged = caplog.text
    assert PROXY_TOKEN not in logged
    assert FAKE_AZURE_TOKEN not in logged
    assert "guess-token" not in logged
    assert secret_prompt not in logged


# --- configuration --------------------------------------------------------------------


def test_settings_repr_hides_token(settings):
    assert PROXY_TOKEN not in repr(settings)
    assert PROXY_TOKEN not in str(settings)


def test_settings_defaults():
    env = {k: v for k, v in BASE_ENV.items() if not k.startswith("RILEY_PROXY_") or k == "RILEY_PROXY_TOKEN"}
    s = load_settings(env)
    assert s.host == "127.0.0.1"
    assert s.allowed_models == frozenset({DEPLOYMENT})
    assert s.azure_endpoint == f"https://{ENDPOINT_HOST}/"


@pytest.mark.parametrize(
    "override",
    [
        {"AZURE_ENDPOINT": f"http://{ENDPOINT_HOST}/"},
        {"AZURE_ENDPOINT": "https://evil.example/"},
        {"AZURE_ENDPOINT": "https://cognitiveservices.azure.com.evil.example/"},
        {"AZURE_ENDPOINT": f"https://{ENDPOINT_HOST}/openai/deployments/x"},
        {"AZURE_ENDPOINT": f"https://user:pw@{ENDPOINT_HOST}/"},
        {"AZURE_ENDPOINT": f"https://{ENDPOINT_HOST}:8443/"},
        {"AZURE_ENDPOINT": ""},
        {"AZURE_DEPLOYMENT": "../other"},
        {"AZURE_DEPLOYMENT": "a/b"},
        {"AZURE_CLIENT_ID": "not-a-guid"},
        {"AZURE_API_VERSION": "latest"},
        {"RILEY_PROXY_TOKEN": "short"},
        {"RILEY_PROXY_TOKEN": ""},
        {"RILEY_PROXY_MODEL_ALIASES": "ok,bad/alias"},
        {"RILEY_PROXY_HOST": "0.0.0.0"},
        {"RILEY_PROXY_HOST": "172.17.0.1"},
        {"RILEY_PROXY_PORT": "80"},
        {"RILEY_PROXY_MAX_BODY_BYTES": "lots"},
    ],
)
def test_invalid_configuration_is_rejected(override):
    with pytest.raises(ConfigError):
        load_settings({**BASE_ENV, **override})


def test_non_loopback_host_requires_explicit_opt_in():
    s = load_settings({**BASE_ENV, "RILEY_PROXY_HOST": "172.17.0.1", "RILEY_PROXY_ALLOW_NON_LOOPBACK": "1"})
    assert s.host == "172.17.0.1"


def test_token_provider_uses_managed_identity_with_client_id_and_scope(settings, monkeypatch):
    import asyncio

    import azure.identity

    seen = {}

    class FakeCredential:
        def __init__(self, client_id=None):
            seen["client_id"] = client_id

    def fake_get_bearer_token_provider(credential, *scopes):
        seen["credential"] = credential
        seen["scopes"] = scopes
        return lambda: "token-from-fake-credential"

    monkeypatch.setattr(azure.identity, "ManagedIdentityCredential", FakeCredential)
    monkeypatch.setattr(azure.identity, "get_bearer_token_provider", fake_get_bearer_token_provider)

    provider = proxy.build_token_provider(settings)

    assert seen["client_id"] == BASE_ENV["AZURE_CLIENT_ID"]
    assert seen["scopes"] == ("https://cognitiveservices.azure.com/.default",)
    assert asyncio.run(provider()) == "token-from-fake-credential"
