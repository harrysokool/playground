"""Configuration for the Riley Azure OpenAI proxy.

All values come from environment variables. Nothing about the Azure resource is
hardcoded; validation here is deliberately strict so that a typo or a malicious
value cannot point the proxy at an unexpected destination.
"""

from __future__ import annotations

import ipaddress
import os
import re
from dataclasses import dataclass
from typing import FrozenSet, Mapping, Optional
from urllib.parse import urlsplit

AZURE_SCOPE = "https://cognitiveservices.azure.com/.default"

# Only Azure OpenAI / Azure AI Services hostnames are accepted as upstreams.
ALLOWED_ENDPOINT_SUFFIXES = (".cognitiveservices.azure.com", ".openai.azure.com")

_DEPLOYMENT_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_API_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(-preview)?$")
_GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")

MIN_TOKEN_LENGTH = 32


class ConfigError(ValueError):
    """Raised when the environment does not contain a valid configuration."""


@dataclass(frozen=True)
class Settings:
    azure_endpoint: str
    azure_deployment: str
    azure_client_id: str
    azure_api_version: str
    proxy_token: str
    allowed_models: FrozenSet[str]
    host: str = "127.0.0.1"
    port: int = 8787
    max_body_bytes: int = 4 * 1024 * 1024
    max_completion_tokens: int = 16384
    upstream_timeout: float = 180.0

    def __repr__(self) -> str:  # never print the proxy token
        return (
            f"Settings(azure_deployment={self.azure_deployment!r}, "
            f"azure_api_version={self.azure_api_version!r}, host={self.host!r}, port={self.port})"
        )


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required")
    return value


def _int(env: Mapping[str, str], name: str, default: int, minimum: int, maximum: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer") from None
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}")
    return value


def _validate_endpoint(raw: str) -> str:
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https":
        raise ConfigError("AZURE_ENDPOINT must use https")
    if parts.username or parts.password or parts.query or parts.fragment or parts.port:
        raise ConfigError("AZURE_ENDPOINT must not contain credentials, a port, a query or a fragment")
    if parts.path not in ("", "/"):
        raise ConfigError("AZURE_ENDPOINT must be the resource root, e.g. https://<name>.cognitiveservices.azure.com/")
    if not host.endswith(ALLOWED_ENDPOINT_SUFFIXES):
        raise ConfigError("AZURE_ENDPOINT must be an Azure OpenAI hostname (" + ", ".join(ALLOWED_ENDPOINT_SUFFIXES) + ")")
    return f"https://{host}/"


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = os.environ if env is None else env

    endpoint = _validate_endpoint(_required(env, "AZURE_ENDPOINT"))

    deployment = _required(env, "AZURE_DEPLOYMENT")
    if not _DEPLOYMENT_RE.match(deployment):
        raise ConfigError("AZURE_DEPLOYMENT may only contain letters, digits, '.', '_' and '-'")

    client_id = _required(env, "AZURE_CLIENT_ID")
    if not _GUID_RE.match(client_id):
        raise ConfigError("AZURE_CLIENT_ID must be a GUID")

    api_version = _required(env, "AZURE_API_VERSION")
    if not _API_VERSION_RE.match(api_version):
        raise ConfigError("AZURE_API_VERSION must look like 2024-12-01-preview")

    token = _required(env, "RILEY_PROXY_TOKEN")
    if len(token) < MIN_TOKEN_LENGTH:
        raise ConfigError(f"RILEY_PROXY_TOKEN must be at least {MIN_TOKEN_LENGTH} characters")

    # Model names clients may send. Every one of them maps to the single fixed deployment.
    aliases = {a.strip() for a in env.get("RILEY_PROXY_MODEL_ALIASES", "").split(",") if a.strip()}
    for alias in aliases:
        if not _DEPLOYMENT_RE.match(alias):
            raise ConfigError("RILEY_PROXY_MODEL_ALIASES entries may only contain letters, digits, '.', '_' and '-'")

    host = env.get("RILEY_PROXY_HOST", "127.0.0.1").strip() or "127.0.0.1"
    if not _is_loopback(host) and env.get("RILEY_PROXY_ALLOW_NON_LOOPBACK", "") != "1":
        raise ConfigError(
            "RILEY_PROXY_HOST is not a loopback address. Review the Docker networking design first, "
            "then set RILEY_PROXY_ALLOW_NON_LOOPBACK=1 to confirm."
        )

    return Settings(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        azure_client_id=client_id,
        azure_api_version=api_version,
        proxy_token=token,
        allowed_models=frozenset({deployment} | aliases),
        host=host,
        port=_int(env, "RILEY_PROXY_PORT", 8787, 1024, 65535),
        max_body_bytes=_int(env, "RILEY_PROXY_MAX_BODY_BYTES", 4 * 1024 * 1024, 1024, 32 * 1024 * 1024),
        max_completion_tokens=_int(env, "RILEY_PROXY_MAX_COMPLETION_TOKENS", 16384, 1, 200000),
        upstream_timeout=float(_int(env, "RILEY_PROXY_UPSTREAM_TIMEOUT", 180, 5, 900)),
    )
