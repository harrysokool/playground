# riley_proxy

A small, local, OpenAI-compatible proxy that lets the OpenClaw agent **Riley** use one fixed
Azure OpenAI deployment without giving the OpenClaw container any Azure credentials.

```
OpenClaw container ──HTTP + proxy token──▶ riley_proxy (host, 127.0.0.1:8787)
                                              │  ManagedIdentityCredential (client id)
                                              ▼  scope https://cognitiveservices.azure.com/.default
                                           Azure OpenAI /openai/deployments/<AZURE_DEPLOYMENT>/chat/completions
```

The managed identity stays on the host. OpenClaw only ever holds the proxy token, which is
useful for nothing except calling this proxy.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | FastAPI app, request validation, Azure client, error mapping, `python app.py` runner |
| `config.py` | Reads and strictly validates environment variables |
| `requirements.txt` | Runtime dependencies (pinned, tested together) |
| `requirements-dev.txt` | Adds `pytest` and `httpx` for the tests |
| `.env.example` | Configuration template, placeholders only |
| `tests/test_proxy.py` | Unit tests; Azure is mocked, no network calls |

## What the proxy does

Routes (everything else returns an OpenAI-style 404/405 error; `/docs` and `/openapi.json` are disabled):

| Route | Auth | Behaviour |
| --- | --- | --- |
| `GET /health` | none | `{"status": "ok"}`. Never calls Azure. |
| `POST /v1/chat/completions` | `Authorization: Bearer <RILEY_PROXY_TOKEN>` | Forwards to the fixed deployment; normal and streaming (SSE). |

Request handling:

- The token is compared in constant time (`hmac.compare_digest`) **before** the body is read.
- Body must be `application/json`, a JSON object, and at most `RILEY_PROXY_MAX_BODY_BYTES`
  (default 4 MiB, enforced on `Content-Length` and while streaming the body in).
- `model` must be `AZURE_DEPLOYMENT` or one of `RILEY_PROXY_MODEL_ALIASES`; otherwise **403**.
  The upstream URL is pinned to `AZURE_ENDPOINT` + `AZURE_DEPLOYMENT`, so the client can never pick
  another resource, deployment, endpoint or API version.
- Only these parameters are accepted (anything else is **400 `unsupported_parameter`**):
  `model, messages, stream, stream_options, temperature, top_p, n (=1 only), stop, max_tokens,
  max_completion_tokens, presence_penalty, frequency_penalty, logit_bias, logprobs, top_logprobs,
  seed, user, tools, tool_choice, parallel_tool_calls, response_format, reasoning_effort, store (=false only)`.
  Notably rejected: `data_sources` (Azure "On Your Data", which would let a client point Azure at
  other resources), `functions`, `audio`, `web_search_options`, `extra_body`, `metadata`.
- `max_tokens` is translated to `max_completion_tokens` (as in the working reference test) and
  capped at `RILEY_PROXY_MAX_COMPLETION_TOKENS` (default 16384). The cap is also applied when
  the client sends no limit.
- `tools`, `tool_choice`, assistant `tool_calls` and `tool` messages are forwarded unchanged, and
  responses (including streamed tool-call deltas and Azure's content-filter fields) are returned
  unchanged.

Azure authentication: `ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)` wrapped by
`get_bearer_token_provider`, passed to `AsyncAzureOpenAI` as `azure_ad_token_provider`. The SDK asks
for a token on every request; azure-identity caches it and refreshes it before it expires.

Error mapping (always OpenAI's `{"error": {...}}` shape; Azure details are not echoed except for 400s):

| Situation | Client gets |
| --- | --- |
| Missing / wrong proxy token | 401 `invalid_proxy_token` |
| Model not allowed | 403 `model_not_allowed` |
| Unsupported parameter / invalid body | 400 |
| Body too large | 413 `request_too_large` |
| Azure 400 (e.g. content filter) | 400 with Azure's `code` and message (truncated) |
| Azure 429 | 429 `rate_limited`, `Retry-After` preserved |
| Azure 401/403 (identity/role problem) | 502 `upstream_auth_failed` |
| Azure 404 (deployment misconfigured) | 502 `upstream_not_found` |
| Azure 5xx | 502 `upstream_error` |
| Managed identity token unavailable | 502 `upstream_auth_unavailable` |
| Connection failure / timeout | 502 `upstream_unreachable` / 504 `upstream_timeout` |
| Failure in the middle of a stream | final SSE event `data: {"error": {...}}`, no `[DONE]` |

Logging: uvicorn access lines (client IP, method, path, status) plus upstream status/code/request id
on errors. Request bodies, prompts, responses and tokens are never logged; the `azure`, `httpx`,
`httpx2` and `openai` loggers are held at WARNING so they cannot log URLs, headers or bodies.

## Install (on the Azure ML compute instance)

Requires Python 3.10+ (openai 3.x needs it). Ubuntu 22.04's system `python3` is 3.10. Leave the
existing `azureml_py38` environment alone and create a dedicated venv. Put the venv on the local
disk rather than under `~/cloudfiles` (the Azure Files mount is slow for venvs):

```bash
cd ~/cloudfiles/code/Users/<your-user>/playground/riley_proxy
```

```bash
/usr/bin/python3 -m venv ~/.venvs/riley_proxy
```

If that fails because `ensurepip` is missing, create it with conda instead (no sudo needed):

```bash
conda create -y -p ~/.venvs/riley_proxy python=3.10 pip
```

```bash
~/.venvs/riley_proxy/bin/pip install -r requirements-dev.txt
```

## Configure

```bash
cp .env.example .env && chmod 600 .env
```

Fill in `.env` with the same endpoint, deployment, client id and API version as your working
`ManagedIdentityCredential` test. Generate the proxy token with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

`config.py` refuses to start if the endpoint is not `https://<name>.cognitiveservices.azure.com/`
(or `.openai.azure.com`), the client id is not a GUID, the token is shorter than 32 characters,
or the bind address is not loopback (unless `RILEY_PROXY_ALLOW_NON_LOOPBACK=1` is also set —
don't set it until the networking design has been reviewed).

## Run

```bash
set -a && . ./.env && set +a && ~/.venvs/riley_proxy/bin/python app.py
```

It listens on `127.0.0.1:8787` only. Confirm with:

```bash
ss -ltnp | grep 8787
```

Expected: `127.0.0.1:8787` and nothing on `0.0.0.0` or `*`. Uvicorn is started with
`limit_concurrency=32` (503 beyond that), keep-alive 5s, and no `Server` header. Start it with
`python app.py`, not with the `uvicorn` CLI, so the loopback check and log settings apply.

## Tests

```bash
~/.venvs/riley_proxy/bin/python -m pytest -q
```

104 tests. A real `AsyncAzureOpenAI` client is pointed at an in-memory mock transport and the
token provider is a fake, so the actual SDK request and streaming code is exercised without any
network access or real credentials. Coverage: health; missing/invalid/malformed tokens;
successful completions (URL, api-version, Azure bearer token, parameter translation, token cap);
streaming text and streamed tool-call deltas; tool-calling request/response round trips;
model/deployment restrictions; unsupported parameters; Azure 400/401/403/404/429/5xx, connection
errors, timeouts, managed identity failure; mid-stream errors and dropped connections;
body size limits (declared and chunked), content type, malformed JSON, invalid messages;
unknown routes and disabled docs; no CORS; nothing sensitive in logs; config validation;
and that the token provider uses `ManagedIdentityCredential` with the right client id and scope.

## Local curl examples

In a second terminal on the compute instance:

```bash
set -a && . ./.env && set +a
```

Health (no token):

```bash
curl -s http://127.0.0.1:8787/health
```

Rejected without a token (expect 401):

```bash
curl -s -w '\n%{http_code}\n' http://127.0.0.1:8787/v1/chat/completions -H 'Content-Type: application/json' -d '{}'
```

Normal completion:

```bash
curl -s http://127.0.0.1:8787/v1/chat/completions -H "Authorization: Bearer $RILEY_PROXY_TOKEN" -H 'Content-Type: application/json' -d "{\"model\": \"$AZURE_DEPLOYMENT\", \"messages\": [{\"role\": \"user\", \"content\": \"Reply with the single word: pong\"}], \"max_completion_tokens\": 50}"
```

Streaming (`-N` disables curl buffering):

```bash
curl -sN http://127.0.0.1:8787/v1/chat/completions -H "Authorization: Bearer $RILEY_PROXY_TOKEN" -H 'Content-Type: application/json' -d "{\"model\": \"$AZURE_DEPLOYMENT\", \"stream\": true, \"stream_options\": {\"include_usage\": true}, \"messages\": [{\"role\": \"user\", \"content\": \"Count from 1 to 5.\"}]}"
```

Tool calling (expect `finish_reason: "tool_calls"` and a `get_weather` call):

```bash
curl -s http://127.0.0.1:8787/v1/chat/completions -H "Authorization: Bearer $RILEY_PROXY_TOKEN" -H 'Content-Type: application/json' -d "{\"model\": \"$AZURE_DEPLOYMENT\", \"messages\": [{\"role\": \"user\", \"content\": \"What is the weather in Hong Kong? Use the tool.\"}], \"tools\": [{\"type\": \"function\", \"function\": {\"name\": \"get_weather\", \"description\": \"Get weather for a city\", \"parameters\": {\"type\": \"object\", \"properties\": {\"city\": {\"type\": \"string\"}}, \"required\": [\"city\"]}}}], \"tool_choice\": \"auto\"}"
```

Rejected model (expect 403) and rejected parameter (expect 400):

```bash
curl -s -w '\n%{http_code}\n' http://127.0.0.1:8787/v1/chat/completions -H "Authorization: Bearer $RILEY_PROXY_TOKEN" -H 'Content-Type: application/json' -d '{"model": "some-other-model", "messages": [{"role": "user", "content": "hi"}]}'
```

```bash
curl -s -w '\n%{http_code}\n' http://127.0.0.1:8787/v1/chat/completions -H "Authorization: Bearer $RILEY_PROXY_TOKEN" -H 'Content-Type: application/json' -d "{\"model\": \"$AZURE_DEPLOYMENT\", \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}], \"data_sources\": []}"
```

Note: `-H "Authorization: Bearer $RILEY_PROXY_TOKEN"` puts the token in curl's argv, visible
to other users via `ps` for the life of the command. Fine on a single-user compute instance.

## Manual end-to-end test against the real deployment

Use only public or synthetic prompts.

1. Pull this repo on the compute instance, install and configure as above.
2. Terminal 1: start the proxy and leave it in the foreground so you can watch its logs.
3. Terminal 2: run the curl examples above in order. Expected:
   - health → `{"status":"ok"}`; no-token → 401
   - normal completion → a `chat.completion` JSON containing "pong"
   - streaming → several `data: {...chat.completion.chunk...}` lines then `data: [DONE]`
   - tool call → `tool_calls[0].function.name == "get_weather"`, arguments contain Hong Kong
   - other model → 403; `data_sources` → 400
4. Simulate what OpenClaw will do with the OpenAI SDK as a plain OpenAI-compatible client
   (from the riley_proxy venv):

   ```bash
   ~/.venvs/riley_proxy/bin/python -c "import os; from openai import OpenAI; c = OpenAI(base_url='http://127.0.0.1:8787/v1', api_key=os.environ['RILEY_PROXY_TOKEN']); print(c.chat.completions.create(model=os.environ['AZURE_DEPLOYMENT'], messages=[{'role': 'user', 'content': 'Say hi in five words.'}]).choices[0].message.content); [print(ch.choices[0].delta.content or '', end='', flush=True) for ch in c.chat.completions.create(model=os.environ['AZURE_DEPLOYMENT'], messages=[{'role': 'user', 'content': 'Count to 5.'}], stream=True) if ch.choices]; print()"
   ```

5. Check terminal 1: only access lines (`POST /v1/chat/completions ... 200`), no prompt text,
   no tokens. A 502 `upstream_auth_failed` means the identity lacks the
   *Cognitive Services OpenAI User* role on the resource; `upstream_auth_unavailable` means the
   managed identity could not be reached at all.
6. Leave it running for more than an hour (or restart after an hour) and repeat one request to
   confirm token refresh works.
7. Stop it with Ctrl+C.

## Connecting OpenClaw (not done yet — needs review first)

Nothing here has been applied. The proxy stays on `127.0.0.1`, which a bridge-networked
container cannot reach. Steps to review before connecting Riley:

**1. Check how the OpenClaw container is networked** (read-only):

```bash
docker ps --format '{{.Names}}\t{{.Networks}}'
```

```bash
docker inspect <openclaw-container> --format '{{.HostConfig.NetworkMode}}'
```

If it is `host`, the container already shares the host's loopback and could reach the proxy (and
everything else on 127.0.0.1) directly — that is a broader exposure than intended and is worth
discussing before going further.

**2. Check the container cannot get Azure tokens by itself.** This is the most important check:
on Azure VMs the Instance Metadata Service (IMDS, `169.254.169.254`) is often reachable from
bridge-networked containers, and IMDS hands out managed identity tokens to anyone who asks with a
`Metadata: true` header. If OpenClaw can reach it, the proxy does not actually keep the identity
out of the container. A non-token-minting check (instance metadata, not the token endpoint):

```bash
docker exec <openclaw-container> sh -c 'curl -s -m 5 -o /dev/null -w "%{http_code}\n" -H Metadata:true "http://169.254.169.254/metadata/instance?api-version=2021-02-01"'
```

`200` means IMDS is reachable from the container. Also list (names only) any identity-related
environment variables inside the container:

```bash
docker exec <openclaw-container> sh -c 'env | cut -d= -f1 | grep -iE "MSI|IDENTITY|AZURE" || true'
```

If IMDS is reachable, the fix is a host firewall rule (for example in Docker's `DOCKER-USER`
iptables chain) that drops traffic from Docker bridges to `169.254.169.254`. That is a host
change and needs your approval.

**3. Pick the access path.** Recommended for review: bind the proxy to the Docker bridge gateway
address (not `0.0.0.0`) and let the container reach it via `host.docker.internal`:

- find the gateway: `docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'`
  (usually `172.17.0.1`; for a compose network use that network's name)
- in `.env`: `RILEY_PROXY_HOST=172.17.0.1` and `RILEY_PROXY_ALLOW_NON_LOOPBACK=1`
- OpenClaw's compose service needs `extra_hosts: ["host.docker.internal:host-gateway"]` if it
  doesn't have it already (that is an OpenClaw compose change — your call)
- from the container: `curl -s http://host.docker.internal:8787/health`

Trade-off: every container on that host can reach the proxy, so the proxy token is the only
access control. The bridge address is not routable from outside the VM. Not recommended:
`0.0.0.0` binding, `network_mode: host` for OpenClaw, or running the proxy in its own container
(it would then need IMDS access from containers, which is exactly what step 2 tries to rule out).

**4. Point OpenClaw at the proxy** as a custom OpenAI-compatible provider. The shape is roughly
as follows — check the exact keys against the docs for OpenClaw 2026.9.8:

```json5
{
  models: {
    mode: "merge",
    providers: {
      "riley-azure": {
        baseUrl: "http://host.docker.internal:8787/v1",
        apiKey: "${RILEY_PROXY_TOKEN}",   // the proxy token, not an Azure key
        api: "openai-completions",
        models: [{ id: "<AZURE_DEPLOYMENT>", name: "Riley (Azure)", contextWindow: 128000, maxTokens: 16384 }]
      }
    }
  },
  agents: { defaults: { model: { primary: "riley-azure/<AZURE_DEPLOYMENT>" } } }
}
```

If OpenClaw sends a parameter not on the allowlist, the proxy answers 400
`Unsupported parameter(s): <name>`. Review the parameter, then add it to `ALLOWED_PARAMS` in
`app.py` if it is safe.

## Remaining security limitations

- **IMDS reachability from containers** (above) is unverified. Until it is checked, assume a
  container on this host might be able to obtain the managed identity's tokens directly.
- **One static shared token.** Anything inside the OpenClaw container — including tools, skills
  or code the agent runs, or a prompt-injected agent — can read the token from OpenClaw's config
  and call the model. Rotation is manual (change `.env` and OpenClaw config, restart both).
- **No per-client rate limit or spend limit.** Controls are the completion-token cap, body size
  limit, 32 concurrent connections, and Azure's own quota on the deployment.
- **Plain HTTP.** Fine on loopback or the local bridge; anyone with root on the host can observe
  traffic. Do not expose it beyond the host.
- **Content is not inspected.** Prompts go to Azure as-is; Azure content filtering is the only
  filter. `image_url` parts with remote URLs are forwarded, so Azure may fetch URLs supplied by
  the client (from Azure's network, not this host).
- **Shallow schema validation.** The proxy checks types and roles; Azure is the authority on the
  rest. Azure's message for a 400 is returned to the caller (but not logged).
- **Not a managed service.** It runs as a foreground process; it does not restart on failure or
  when the compute instance restarts.
- **`/health` is unauthenticated.** It reveals only that the proxy is up.
- **Dependencies are pinned by version, not by hash.** Use your company's package mirror or add
  `--require-hashes` if your policy requires it.
