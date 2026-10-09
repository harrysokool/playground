"""Riley proxy: a small OpenAI-compatible front door to one fixed Azure OpenAI deployment.

OpenClaw (in Docker) -> this proxy (host, 127.0.0.1) -> Azure OpenAI (managed identity).

Only two routes exist:
    GET  /health               unauthenticated liveness check, never calls Azure
    POST /v1/chat/completions  bearer-token protected, normal and streaming
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional, Sequence

import anyio
import openai
from azure.core.exceptions import ClientAuthenticationError
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import AZURE_SCOPE, ConfigError, IPNetwork, Settings, load_settings

logger = logging.getLogger("riley_proxy")

# Chat Completions parameters forwarded to Azure. Anything else is rejected, which keeps
# Azure-only extensions such as `data_sources` (On Your Data) out of reach of the client.
ALLOWED_PARAMS = frozenset(
    {
        "model",
        "messages",
        "stream",
        "stream_options",
        "temperature",
        "top_p",
        "n",
        "stop",
        "max_tokens",
        "max_completion_tokens",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "logprobs",
        "top_logprobs",
        "seed",
        "user",
        "tools",
        "tool_choice",
        "parallel_tool_calls",
        "response_format",
        "reasoning_effort",
        "store",
    }
)
VALID_ROLES = frozenset({"system", "developer", "user", "assistant", "tool"})
MAX_UPSTREAM_MESSAGE_CHARS = 1000

TokenProvider = Callable[[], Awaitable[str]]


class ProxyError(Exception):
    """An error that is returned to the client in OpenAI's error format."""

    def __init__(
        self,
        status: int,
        message: str,
        type_: str = "invalid_request_error",
        code: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.type = type_
        self.code = code
        self.headers = headers

    def payload(self) -> Dict[str, Any]:
        return {"error": {"message": self.message, "type": self.type, "param": None, "code": self.code}}

    def response(self) -> JSONResponse:
        return JSONResponse(self.payload(), status_code=self.status, headers=self.headers)


# --- client source-IP allowlist ---------------------------------------------------------


def client_allowed(host: Optional[str], networks: Sequence[IPNetwork]) -> bool:
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return any(ip in network for network in networks)


class ClientAllowlistMiddleware:
    """Rejects connections whose TCP peer address is not in the allowlist, before routing,
    token checks or body parsing. Uses the socket address only; forwarded headers are ignored."""

    def __init__(self, app: Any, networks: Sequence[IPNetwork]) -> None:
        self.app = app
        self.networks = tuple(networks)

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] in ("http", "websocket"):
            host = (scope.get("client") or (None,))[0]
            if not client_allowed(host, self.networks):
                logger.warning("rejected request from non-allowlisted client %s", host)
                if scope["type"] == "http":
                    error = ProxyError(403, "Client address not allowed", "permission_error", "client_not_allowed")
                    await error.response()(scope, receive, send)
                else:
                    await send({"type": "websocket.close", "code": 1008})
                return
        await self.app(scope, receive, send)


# --- Azure client -----------------------------------------------------------------------


def build_token_provider(settings: Settings) -> TokenProvider:
    """Managed identity token provider, same approach as the working reference test.

    azure-identity caches the token and refreshes it before expiry; the OpenAI SDK calls
    the provider on every request. The sync call runs in a thread so a refresh never
    blocks the event loop.
    """
    from azure.identity import ManagedIdentityCredential, get_bearer_token_provider

    credential = ManagedIdentityCredential(client_id=settings.azure_client_id)
    sync_provider = get_bearer_token_provider(credential, AZURE_SCOPE)

    async def provider() -> str:
        return await run_in_threadpool(sync_provider)

    return provider


def build_client(
    settings: Settings,
    token_provider: TokenProvider,
    http_client: Any = None,
    max_retries: int = 2,
) -> openai.AsyncAzureOpenAI:
    # azure_deployment pins the URL to /openai/deployments/<deployment>/..., so the
    # client-supplied `model` can never select a different deployment.
    return openai.AsyncAzureOpenAI(
        azure_endpoint=settings.azure_endpoint,
        azure_deployment=settings.azure_deployment,
        api_version=settings.azure_api_version,
        azure_ad_token_provider=token_provider,
        timeout=openai.Timeout(settings.upstream_timeout, connect=10.0),
        max_retries=max_retries,
        http_client=http_client,
    )


# --- request handling -------------------------------------------------------------------


async def read_json_body(request: Request, max_bytes: int) -> Dict[str, Any]:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        raise ProxyError(415, "Content-Type must be application/json", code="unsupported_media_type")

    too_large = ProxyError(413, f"Request body exceeds {max_bytes} bytes", code="request_too_large")
    declared = request.headers.get("content-length")
    if declared is not None:
        if not declared.isdigit():
            raise ProxyError(400, "Invalid Content-Length header")
        if int(declared) > max_bytes:
            raise too_large

    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise too_large
        chunks.append(chunk)

    try:
        body = json.loads(b"".join(chunks))
    except ValueError:
        raise ProxyError(400, "Request body is not valid JSON") from None
    if not isinstance(body, dict):
        raise ProxyError(400, "Request body must be a JSON object")
    return body


def build_upstream_params(body: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """Validate a Chat Completions request and return the kwargs sent to Azure."""
    unsupported = sorted(str(k)[:64] for k in body if k not in ALLOWED_PARAMS)
    if unsupported:
        raise ProxyError(400, "Unsupported parameter(s): " + ", ".join(unsupported), code="unsupported_parameter")

    model = body.get("model")
    if not isinstance(model, str) or not model:
        raise ProxyError(400, "'model' is required")
    if model not in settings.allowed_models:
        raise ProxyError(403, "This model is not allowed by the proxy", "permission_error", "model_not_allowed")

    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ProxyError(400, "'messages' must be a non-empty array")
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in VALID_ROLES:
            raise ProxyError(400, "Each message must be an object with a valid 'role'")

    stream = body.get("stream", False)
    if not isinstance(stream, bool):
        raise ProxyError(400, "'stream' must be a boolean")
    if "stream_options" in body and not stream:
        raise ProxyError(400, "'stream_options' is only allowed when 'stream' is true")
    if body.get("n", 1) != 1:
        raise ProxyError(400, "Only n=1 is supported", code="unsupported_parameter")
    if body.get("store", False) is not False:
        raise ProxyError(400, "Only store=false is supported", code="unsupported_parameter")
    if "tools" in body and not isinstance(body["tools"], list):
        raise ProxyError(400, "'tools' must be an array")

    # Azure's newer models only accept max_completion_tokens; translate max_tokens and cap it.
    requested = body.get("max_completion_tokens", body.get("max_tokens"))
    if requested is None:
        requested = settings.max_completion_tokens
    if isinstance(requested, bool) or not isinstance(requested, int) or requested < 1:
        raise ProxyError(400, "'max_completion_tokens' must be a positive integer")

    params = {k: v for k, v in body.items() if k not in ("model", "max_tokens", "max_completion_tokens", "store")}
    params["model"] = settings.azure_deployment
    params["max_completion_tokens"] = min(requested, settings.max_completion_tokens)
    return params


def map_upstream_error(exc: BaseException) -> ProxyError:
    """Translate SDK/identity errors into safe client-facing errors. Never echoes tokens."""
    if isinstance(exc, ProxyError):
        return exc
    if isinstance(exc, openai.APITimeoutError):
        logger.warning("upstream timeout")
        return ProxyError(504, "Upstream request timed out", "api_error", "upstream_timeout")
    if isinstance(exc, openai.APIConnectionError):
        logger.warning("upstream connection error")
        return ProxyError(502, "Could not reach the upstream model service", "api_error", "upstream_unreachable")
    if isinstance(exc, openai.APIStatusError):
        status = exc.status_code
        body = exc.body if isinstance(exc.body, dict) else {}
        code = body.get("code") if isinstance(body.get("code"), str) else None
        logger.warning("upstream error status=%s code=%s request_id=%s", status, code, exc.request_id)
        if status in (400, 422):
            message = body.get("message") if isinstance(body.get("message"), str) else "Upstream rejected the request"
            return ProxyError(400, message[:MAX_UPSTREAM_MESSAGE_CHARS], "invalid_request_error", code)
        if status == 413:
            return ProxyError(413, "Request too large for the upstream model", code="request_too_large")
        if status == 429:
            retry_after = exc.response.headers.get("retry-after", "")
            headers = {"Retry-After": retry_after} if retry_after.isdigit() else None
            return ProxyError(429, "Upstream rate limit reached", "rate_limit_error", "rate_limited", headers)
        if status in (401, 403):
            return ProxyError(502, "Upstream authentication failed", "api_error", "upstream_auth_failed")
        if status == 404:
            return ProxyError(502, "Upstream deployment not found", "api_error", "upstream_not_found")
        if status == 408:
            return ProxyError(504, "Upstream request timed out", "api_error", "upstream_timeout")
        return ProxyError(502, "Upstream service error", "api_error", "upstream_error")
    if isinstance(exc, openai.APIError):  # e.g. an error event in the middle of a stream
        logger.warning("upstream API error type=%s", type(exc).__name__)
        return ProxyError(502, "Upstream service error", "api_error", "upstream_error")
    if isinstance(exc, ClientAuthenticationError):
        logger.error("managed identity token request failed: %s", type(exc).__name__)
        return ProxyError(502, "Could not obtain an upstream access token", "api_error", "upstream_auth_unavailable")
    logger.error("unexpected proxy error: %s", type(exc).__name__)
    return ProxyError(500, "Internal proxy error", "api_error", "internal_error")


def _sse(data: Any) -> str:
    return "data: " + json.dumps(data, separators=(",", ":")) + "\n\n"


async def stream_events(upstream: Any) -> AsyncIterator[str]:
    """Re-emit Azure chunks as OpenAI SSE events. Errors after the first byte become an
    error event (the HTTP status is already 200 by then) and the stream ends without [DONE]."""
    try:
        async for chunk in upstream:
            yield _sse(chunk.to_dict())
        yield "data: [DONE]\n\n"
    except Exception as exc:  # CancelledError (client went away) is not an Exception
        yield _sse(map_upstream_error(exc).payload())
    finally:
        with anyio.CancelScope(shield=True):
            await upstream.close()


# --- app --------------------------------------------------------------------------------


def create_app(settings: Settings, client: Optional[openai.AsyncAzureOpenAI] = None) -> FastAPI:
    if client is None:
        client = build_client(settings, build_token_provider(settings))
    expected_token = settings.proxy_token.encode("utf-8")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await client.close()

    app = FastAPI(title="riley-proxy", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(ClientAllowlistMiddleware, networks=settings.allowed_clients)

    @app.exception_handler(ProxyError)
    async def _proxy_error(_: Request, exc: ProxyError) -> JSONResponse:
        return exc.response()

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "unsupported_operation"
        return ProxyError(exc.status_code, "Unsupported operation", code=code).response()

    def require_token(request: Request) -> None:
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        supplied = supplied.strip()
        if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied.encode("utf-8"), expected_token):
            raise ProxyError(
                401,
                "Invalid or missing proxy token",
                "authentication_error",
                "invalid_proxy_token",
                {"WWW-Authenticate": "Bearer"},
            )

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/chat/completions", dependencies=[Depends(require_token)])
    async def chat_completions(request: Request) -> Any:
        params = build_upstream_params(await read_json_body(request, settings.max_body_bytes), settings)
        try:
            result = await client.chat.completions.create(**params)
        except Exception as exc:
            raise map_upstream_error(exc) from None
        if params.get("stream"):
            return StreamingResponse(
                stream_events(result),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return JSONResponse(result.to_dict())

    return app


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # These libraries can log request URLs, headers or (at debug level) bodies.
    for name in ("azure", "httpx", "httpx2", "httpcore", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)

    logger.info("starting %r", settings)
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        limit_concurrency=32,
        timeout_keep_alive=5,
        server_header=False,
        proxy_headers=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
