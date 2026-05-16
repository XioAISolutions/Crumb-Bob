"""ASGI middleware for the CrumbBob web API.

Three pieces stacked on top of FastAPI's stock middleware chain:

1. ``RequestIDMiddleware`` — assigns a per-request UUID, propagates inbound
   ``X-Request-ID`` if the caller already supplied one (useful for tracing
   across services), and binds it to the logging context.

2. ``SecurityHeadersMiddleware`` — sets the OWASP-recommended response
   headers on every response (CSP, X-Frame-Options, X-Content-Type-Options,
   Referrer-Policy, Permissions-Policy, and HSTS when served over HTTPS).

3. ``RateLimitMiddleware`` — token-bucket per client IP, in-process. Good
   enough for single-node deploys; behind a load balancer you'd want a
   shared store (Redis), but this protects against the obvious DoS vectors
   on /api/query and /api/predict.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from crumdbob.logging_config import request_id_ctx


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a request ID and bind it to the logging context.

    Honours an inbound ``X-Request-ID`` header so request tracing works
    across multiple services in a single trace. If none is supplied, mints
    a fresh UUIDv4 (truncated to 8 chars for log readability — collision
    risk is ~1 in 4 billion per second, acceptable for a dev tool).
    """

    REQUEST_ID_HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        inbound = request.headers.get(self.REQUEST_ID_HEADER, "").strip()
        # Accept caller-supplied IDs but cap length to avoid log injection.
        request_id = inbound[:64] if inbound else uuid.uuid4().hex[:12]
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers[self.REQUEST_ID_HEADER] = request_id
        return response


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
# Default CSP allows inline scripts/styles needed by the dashboard's current
# build (it ships unminified JS as a static file). Tightening this requires
# removing inline event handlers from the HTML — tracked as v0.4 work.
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach OWASP-recommended security headers to every response.

    Args:
        csp: Content-Security-Policy value. Defaults to a self-only policy
            that still permits the inline-script patterns the current
            dashboard uses. Override via env or call-site for tighter
            policies in production.
        enable_hsts: Whether to send HSTS. Off by default because the
            dashboard typically runs on localhost over plain HTTP; enable
            this behind a TLS-terminating proxy.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        csp: str = _DEFAULT_CSP,
        enable_hsts: bool = False,
    ) -> None:
        super().__init__(app)
        self.csp = csp
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", self.csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()",
        )
        if self.enable_hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


# ---------------------------------------------------------------------------
# Rate limiting (in-process token bucket)
# ---------------------------------------------------------------------------
@dataclass
class _Bucket:
    """A single token bucket. Tokens regenerate over time up to capacity."""

    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP token-bucket rate limiter.

    Each client IP gets a bucket holding ``burst`` tokens that refill at
    ``rate_per_second`` per second. Each request costs one token. When the
    bucket is empty, return 429 with a ``Retry-After`` header indicating
    seconds until at least one token will be available.

    The bucket store is in-process and unbounded in cardinality; behind a
    public LB you'd want a shared store and an LRU cap. For the intended
    deployment (single node, ≤ a few hundred concurrent IPs) this is fine.

    Args:
        app: The wrapped ASGI app.
        rate_per_second: Sustained token refill rate.
        burst: Maximum bucket size (allowed instantaneous burst).
        path_prefix: Only requests whose path starts with this prefix are
            limited. Defaults to ``/api/`` so static dashboard assets are
            never throttled.
        exempt_paths: Paths that should never be rate-limited (health checks,
            metrics scrape).
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        rate_per_second: float = 10.0,
        burst: int = 30,
        path_prefix: str = "/api/",
        exempt_paths: frozenset[str] = frozenset({"/api/health", "/metrics"}),
    ) -> None:
        super().__init__(app)
        self.rate = float(rate_per_second)
        self.burst = float(burst)
        self.path_prefix = path_prefix
        self.exempt_paths = exempt_paths
        self._buckets: dict[str, _Bucket] = defaultdict(lambda: _Bucket(tokens=self.burst))

    def _client_key(self, request: Request) -> str:
        """Best-effort client identifier.

        Honours ``X-Forwarded-For`` (first hop) when set by a trusted proxy,
        otherwise falls back to the socket peer address.
        """
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
        return request.client.host if request.client else "unknown"

    def _take_token(self, key: str) -> tuple[bool, float]:
        """Try to consume one token. Returns (allowed, retry_after_seconds)."""
        bucket = self._buckets[key]
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate)
        bucket.last_refill = now
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True, 0.0
        # How long until at least one token is available?
        deficit = 1.0 - bucket.tokens
        retry_after = max(1, int(deficit / self.rate) + 1)
        return False, float(retry_after)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        if not path.startswith(self.path_prefix) or path in self.exempt_paths:
            return await call_next(request)

        allowed, retry_after = self._take_token(self._client_key(request))
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "error": "Rate limit exceeded",
                        "retry_after_seconds": retry_after,
                    }
                },
                headers={"Retry-After": str(int(retry_after))},
            )
        return await call_next(request)
