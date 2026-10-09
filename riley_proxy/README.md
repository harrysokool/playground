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

- The TCP peer address must be in `RILEY_PROXY_ALLOWED_CLIENTS` (default `127.0.0.0/8,::1/128`).
  This runs first, for every route including `/health`; anything else gets **403
  `client_not_allowed`** and is logged by IP. Only the socket address counts —
  `X-Forwarded-For` and similar headers are ignored.
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
| Client IP not in allowlist | 403 `client_not_allowed` |
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

`config.py` refuses to start if:

- the endpoint is not `https://<name>.cognitiveservices.azure.com/` (or `.openai.azure.com`)
- the client id is not a GUID, or the token is shorter than 32 characters
- `RILEY_PROXY_HOST` is `0.0.0.0` or `::` (never allowed) or not an IP address
- `RILEY_PROXY_HOST` is not loopback and either `RILEY_PROXY_ALLOW_NON_LOOPBACK=1` or
  `RILEY_PROXY_ALLOWED_CLIENTS` is missing
- an allowlist entry is not a CIDR with zero host bits, or is broader than /16 (IPv4) or /64 (IPv6)

The default is still `127.0.0.1` with a loopback-only allowlist. The prepared Docker settings
are commented out at the bottom of `.env.example`.

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

146 tests. A real `AsyncAzureOpenAI` client is pointed at an in-memory mock transport and the
token provider is a fake, so the actual SDK request and streaming code is exercised without any
network access or real credentials. Coverage: health; missing/invalid/malformed tokens;
successful completions (URL, api-version, Azure bearer token, parameter translation, token cap);
streaming text and streamed tool-call deltas; tool-calling request/response round trips;
model/deployment restrictions; unsupported parameters; Azure 400/401/403/404/429/5xx, connection
errors, timeouts, managed identity failure; mid-stream errors and dropped connections;
body size limits (declared and chunked), content type, malformed JSON, invalid messages;
unknown routes and disabled docs; no CORS; nothing sensitive in logs; config validation;
that the token provider uses `ManagedIdentityCredential` with the right client id and scope;
and the client allowlist: loopback default, the prepared Docker allowlist (permitted and
rejected peers, IPv4-mapped IPv6, spoofed `X-Forwarded-For`), token still required for permitted
clients, streaming through the middleware, and invalid allowlist/bind configurations.

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

## Connecting OpenClaw (prepared, not deployed)

Design: the proxy binds to `172.17.0.1` (the host's `docker0` address, not routable from outside
the VM) and only accepts connections from the `openclaw_default` subnet (`172.18.0.0/16`) and the
host itself (`172.17.0.1/32`). OpenClaw calls `http://172.17.0.1:8787/v1` and sends the proxy
token from its process environment. Using the IP literal means the Gateway does not depend on
`host.docker.internal` being configured.

Nothing in this section changes OpenClaw's tool profile, sandbox mode, Docker networks, the host
firewall or the managed identity. Container and project names below match the diagnostics
(`openclaw-openclaw-gateway-1`, service `openclaw-gateway`, network `openclaw_default`).

### Step 0 — read-only checks

Run these in the OpenClaw checkout directory. The Python filter prints only the env-file paths,
hosts, ports and networks. It never prints environment values, because `docker compose config`
resolves them.

```bash
docker compose config --format json | python3 -c 'import json,sys; s=json.load(sys.stdin)["services"]["openclaw-gateway"]; [print(k+":", s.get(k)) for k in ("env_file","extra_hosts","ports","networks")]'
```

Expected: `env_file` lists the `.env` in that directory. If it does not, the token will not reach
the Gateway in step 2 and you need either a reviewed compose change
(`environment: { RILEY_PROXY_TOKEN: ${RILEY_PROXY_TOKEN} }`) or the `~/.openclaw/.env` fallback
described in step 2.

Confirm the subnet the allowlist assumes:

```bash
docker network inspect openclaw_default --format '{{(index .IPAM.Config 0).Subnet}}'
```

It should print `172.18.0.0/16`. If it does not, use that value in step 1.

### Step 1 — move the proxy to the docker0 address

```bash
cd ~/cloudfiles/code/Users/<your-user>/playground && git pull && cd riley_proxy
```

```bash
~/.venvs/riley_proxy/bin/pip install -r requirements-dev.txt && ~/.venvs/riley_proxy/bin/python -m pytest -q
```

Stop the running proxy (Ctrl+C in its terminal). Then add these lines to `.env`. They are the
commented block at the end of `.env.example`.

```
RILEY_PROXY_HOST=172.17.0.1
RILEY_PROXY_ALLOW_NON_LOOPBACK=1
RILEY_PROXY_ALLOWED_CLIENTS=172.18.0.0/16,172.17.0.1/32
```

```bash
set -a && . ./.env && set +a && ~/.venvs/riley_proxy/bin/python app.py
```

Verify from a second terminal. The listener should be `172.17.0.1:8787` only, with no
`127.0.0.1`, `0.0.0.0` or `*`:

```bash
ss -ltn | grep ':8787 '
```

Host health check (allowed through `172.17.0.1/32`):

```bash
curl -s -w ' %{http_code}\n' http://172.17.0.1:8787/health
```

From a throwaway container on `openclaw_default` (expect `HTTP 200`):

```bash
docker run --rm --network openclaw_default --entrypoint node ghcr.io/openclaw/openclaw:latest -e 'fetch("http://172.17.0.1:8787/health",{signal:AbortSignal.timeout(5000)}).then(r=>console.log("HTTP",r.status)).catch(e=>console.log("failed:",e.cause?.code||e.message))'
```

From a container on the default bridge, which is not allowlisted (expect `HTTP 403`):

```bash
docker run --rm --network bridge --entrypoint node ghcr.io/openclaw/openclaw:latest -e 'fetch("http://172.17.0.1:8787/health",{signal:AbortSignal.timeout(5000)}).then(r=>console.log("HTTP",r.status)).catch(e=>console.log("failed:",e.cause?.code||e.message))'
```

The proxy terminal should show `rejected request from non-allowlisted client 172.17.0.x` for
the second container.

### Step 2 — give the Gateway the token without putting it in openclaw.json

OpenClaw's stock compose file loads the checkout's `.env` into the Gateway with `env_file`, so a
line there becomes a process environment variable inside the container. Append it from the
proxy's `.env` without printing it. Run this in the OpenClaw checkout directory, and first make
sure the file has no `RILEY_PROXY_TOKEN` line already:

```bash
grep -c '^RILEY_PROXY_TOKEN=' .env; grep '^RILEY_PROXY_TOKEN=' ~/cloudfiles/code/Users/<your-user>/playground/riley_proxy/.env >> .env && chmod 600 .env
```

Only the proxy token goes into OpenClaw's `.env`. Do not copy the `AZURE_*` values. Because
`env_file` passes every line in that file into the container, Azure settings there would hand
the container details it does not need.

Fallback if the compose file has no `env_file`: OpenClaw also reads `~/.openclaw/.env` (the
mounted config directory) at startup. The token is then in a file inside the container's mount
rather than its environment. The exposure is similar; it is still not in `openclaw.json`.

### Step 3 — add the provider to openclaw.json

Back up the file first:

```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-riley
```

Merge in the following. Leave `tools` and `agents.defaults.sandbox` untouched. The `apiKey` is a
SecretRef that OpenClaw resolves from the process environment when the provider is used, so the
token never appears in the JSON. The inline form `"apiKey": "${RILEY_PROXY_TOKEN}"` also works;
the SecretRef is preferred because nothing can expand it and write the resolved value back. Set
`contextWindow` and `maxTokens` to your deployment's real limits.

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "riley-azure": {
        "baseUrl": "http://172.17.0.1:8787/v1",
        "apiKey": { "source": "env", "provider": "default", "id": "RILEY_PROXY_TOKEN" },
        "api": "openai-completions",
        "models": [
          { "id": "<AZURE_DEPLOYMENT>", "name": "Riley (Azure)", "contextWindow": 128000, "maxTokens": 16384 }
        ]
      }
    }
  },
  "agents": { "defaults": { "model": { "primary": "riley-azure/<AZURE_DEPLOYMENT>" } } }
}
```

### Step 4 — start the Gateway and verify the token path

`env_file` is read when the container is created, so recreate it. Run this in the OpenClaw
checkout:

```bash
docker compose up -d --force-recreate openclaw-gateway
```

Check that the token is present in the Gateway's environment. This prints only its length:

```bash
docker exec openclaw-openclaw-gateway-1 node -e 'const t=process.env.RILEY_PROXY_TOKEN||""; console.log(t ? "present, "+t.length+" chars" : "MISSING")'
```

Check that the token is not in openclaw.json (expect `0`):

```bash
grep -cFf <(grep '^RILEY_PROXY_TOKEN=' ~/cloudfiles/code/Users/<your-user>/playground/riley_proxy/.env | cut -d= -f2-) ~/.openclaw/openclaw.json
```

Check that tool restrictions are unchanged (expect `minimal`, the same deny list, and sandbox `off`):

```bash
python3 -c 'import json,os; c=json.load(open(os.path.expanduser("~/.openclaw/openclaw.json"))); t=c.get("tools",{}); print(t.get("profile"), t.get("deny"), c.get("agents",{}).get("defaults",{}).get("sandbox",{}).get("mode"))'
```

Call the proxy directly from the Gateway container with a synthetic prompt. It prints the HTTP
status and the reply only:

```bash
docker exec openclaw-openclaw-gateway-1 node -e 'fetch("http://172.17.0.1:8787/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+process.env.RILEY_PROXY_TOKEN},body:JSON.stringify({model:"<AZURE_DEPLOYMENT>",messages:[{role:"user",content:"Reply with: pong"}]})}).then(async r=>{const j=await r.json(); console.log(r.status, j.choices?.[0]?.message?.content ?? j.error)})'
```

Check which ports the Gateway publishes (see limitations):

```bash
docker port openclaw-openclaw-gateway-1
```

### Step 5 — Riley's first response

Send Riley a synthetic message through your usual OpenClaw entry point (Control UI or channel).
The proxy terminal should show `POST /v1/chat/completions HTTP/1.1" 200` from a `172.18.0.x`
address. If OpenClaw sends a parameter the proxy does not accept, OpenClaw's error contains
`Unsupported parameter(s): <name>`. Review that parameter before adding it to `ALLOWED_PARAMS`.

### Rollback

1. In the proxy `.env`, remove the three lines from step 1 and restart the proxy (back to
   `127.0.0.1`).
2. Restore `~/.openclaw/openclaw.json.bak-riley`.
3. Delete the `RILEY_PROXY_TOKEN` line from OpenClaw's `.env`.
4. Run `docker compose up -d --force-recreate openclaw-gateway`.

### Phase 2 (pending approval, not part of these steps)

Block the instance metadata service and WireServer for containers with `DOCKER-USER` rules, and
optionally add `INPUT` rules so non-allowlisted containers cannot open a TCP connection at all.
See the networking proposal; nothing here applies those rules.

## Remaining security limitations

- **The subnet allowlist does not identify Riley.** It admits any process whose packets come
  from `172.18.0.0/16`, plus anything on the host via `172.17.0.1/32`. That includes:
  - every container on `openclaw_default`, such as other compose services or future sidecars
  - any container someone attaches with `docker run --network openclaw_default`
  - every process inside the Gateway container, including plugins and anything its tools start
  - any process on the host

  If the network is recreated with a different subnet, the allowlist stops matching and the
  proxy fails closed. The bearer token is the real authenticator; the allowlist only shrinks who
  can try. Stronger options, each needing a reviewed change:
  - a dedicated network holding only the Gateway, with a fixed IP and a `/32` allowlist
  - `INPUT` firewall rules
  - mTLS
- **Docker access is root-equivalent.** Anyone who can run `docker` on the host can read the
  token (`docker inspect`, `docker exec`), join `openclaw_default`, or read the proxy `.env`.
- **The token is visible inside the Gateway container.** It sits in the process environment, so
  every process in the container can read it. With sandbox mode `off`, tools run in that
  container; `exec`, `process`, `write`, `edit`, `apply_patch` and `browser` are currently denied.
  Rotation is manual: change both `.env` files, restart the proxy, recreate the Gateway.
- **The instance metadata service is reachable from containers** (diagnostics returned HTTP
  200). The host's identity comes from Azure ML's local `MSI_ENDPOINT`, which needs `MSI_SECRET`
  (present only on the host). Whether the metadata service would also issue tokens to a container
  is unverified, because checking would mean requesting one. Until the phase 2 `DOCKER-USER` rule
  is approved and applied, assume it might.
- **Rejected clients still complete a TCP handshake.** The allowlist is enforced in the
  application; only firewall rules would stop the connection itself.
- **The Gateway's own ports.** OpenClaw's stock compose file publishes 18789, 18790 and 3978 on
  all interfaces. This is separate from the proxy; check `docker port` and the compute instance's
  NSG after starting the Gateway.
- **One static shared token** that any holder can use.
- **No per-client rate limit or spend limit.** Controls are the completion-token cap, body size
  limit, 32 concurrent connections, and Azure's own quota on the deployment.
- **Plain HTTP over the Docker bridge.** It is not routable off the host, but root on the host can
  observe it.
- **Content is not inspected.** Prompts go to Azure as-is; Azure content filtering is the only
  filter. `image_url` parts with remote URLs are forwarded, so Azure may fetch URLs supplied by
  the client (from Azure's network, not this host).
- **Shallow schema validation.** The proxy checks types and roles; Azure is the authority on the
  rest. Azure's message for a 400 is returned to the caller (but not logged).
- **Not a managed service.** It runs as a foreground process; it does not restart on failure or
  when the compute instance restarts.
- **`/health` reveals only that the proxy is up**, and only to allowlisted clients.
- **Dependencies are pinned by version, not by hash.** Use your company's package mirror or add
  `--require-hashes` if your policy requires it.
