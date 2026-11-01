"""
Rate limiter instance for slowapi integration.

Shared across route modules via import. Configured and registered in main.py.
Includes tunnel-aware and user-aware key resolution to protect against
false-positive 429 rate limit collisions when running behind Cloudflare Tunnel
or CGNAT mobile networks.
"""

import hashlib
import ipaddress
import os
import re
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

_BEARER_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-\.~+/]+=*$")


def _is_trusted_proxy(host: str | None) -> bool:
    """Return True if host is loopback (127.0.0.1, ::1) or private proxy."""
    if not host:
        return False
    if host in ("testclient", "localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return False


def _is_well_formed_token(token: str) -> bool:
    """Validate that token is non-empty and well-formed."""
    if not token or len(token) > 512:
        return False
    return bool(_BEARER_TOKEN_RE.match(token))


def get_client_identifier(request: Request) -> str:
    """Resolve rate-limiting key with proxy and user awareness.

    1. If user is authenticated via Bearer token, limit per token hash (per-user)
       if token is non-empty and well-formed.
    2. If request comes via loopback or private proxy, trust CF-Connecting-IP
       or first IP in X-Forwarded-For.
    3. Fall back to direct socket client host.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if _is_well_formed_token(token):
            # Hash to avoid retaining raw tokens in limiter keys
            return f"usr:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]}"

    client_host = request.client.host if request.client else None
    if _is_trusted_proxy(client_host):
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip and cf_ip.strip():
            return f"ip:{cf_ip.strip()}"

        x_forwarded = request.headers.get("X-Forwarded-For")
        if x_forwarded and x_forwarded.strip():
            client_ip = x_forwarded.split(",")[0].strip()
            if client_ip:
                return f"ip:{client_ip}"

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_client_identifier)


def get_rate_limit_str() -> str:
    """Return the rate limit string from env, defaulting to '120/minute'."""
    per_minute = os.getenv("RATE_LIMIT_PER_MINUTE", "120")
    return f"{per_minute}/minute"
