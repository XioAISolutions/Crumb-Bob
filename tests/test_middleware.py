"""Tests for web.api.middleware — request ID, security headers, rate limiting."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from web.api.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)


def _app_with(*middlewares) -> FastAPI:
    """Build a tiny FastAPI app with just the middlewares under test."""
    app = FastAPI()
    for mw, kwargs in middlewares:
        app.add_middleware(mw, **kwargs)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    return app


class TestRequestIDMiddleware:
    def test_mints_id_when_none_supplied(self):
        client = TestClient(_app_with((RequestIDMiddleware, {})))
        response = client.get("/ping")
        assert response.status_code == 200
        rid = response.headers.get("x-request-id")
        assert rid is not None
        assert len(rid) >= 8  # uuid hex prefix

    def test_echoes_supplied_id(self):
        client = TestClient(_app_with((RequestIDMiddleware, {})))
        response = client.get("/ping", headers={"X-Request-ID": "my-trace-123"})
        assert response.headers["x-request-id"] == "my-trace-123"

    def test_truncates_oversized_inbound_id(self):
        """Defense against log injection via giant header values."""
        client = TestClient(_app_with((RequestIDMiddleware, {})))
        huge = "x" * 500
        response = client.get("/ping", headers={"X-Request-ID": huge})
        assert len(response.headers["x-request-id"]) <= 64


class TestSecurityHeadersMiddleware:
    def test_default_headers_present(self):
        client = TestClient(_app_with((SecurityHeadersMiddleware, {})))
        response = client.get("/ping")
        h = response.headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert "default-src 'self'" in h["content-security-policy"]
        assert "referrer-policy" in h
        assert "permissions-policy" in h

    def test_hsts_off_by_default(self):
        client = TestClient(_app_with((SecurityHeadersMiddleware, {})))
        response = client.get("/ping")
        assert "strict-transport-security" not in response.headers

    def test_hsts_enabled_when_requested(self):
        client = TestClient(_app_with((SecurityHeadersMiddleware, {"enable_hsts": True})))
        response = client.get("/ping")
        assert "strict-transport-security" in response.headers

    def test_custom_csp_honored(self):
        custom_csp = "default-src 'none'"
        client = TestClient(_app_with((SecurityHeadersMiddleware, {"csp": custom_csp})))
        response = client.get("/ping")
        assert response.headers["content-security-policy"] == custom_csp


class TestRateLimitMiddleware:
    def test_under_limit_passes(self):
        client = TestClient(
            _app_with(
                (RateLimitMiddleware, {"rate_per_second": 1000, "burst": 1000, "path_prefix": "/"}),
            )
        )
        for _ in range(5):
            assert client.get("/ping").status_code == 200

    def test_exhausted_bucket_returns_429(self):
        client = TestClient(
            _app_with(
                (RateLimitMiddleware, {"rate_per_second": 0.001, "burst": 2, "path_prefix": "/"}),
            )
        )
        # Burn the 2 tokens
        assert client.get("/ping").status_code == 200
        assert client.get("/ping").status_code == 200
        # Third call should be denied
        response = client.get("/ping")
        assert response.status_code == 429
        assert "retry-after" in response.headers
        body = response.json()
        assert body["detail"]["error"] == "Rate limit exceeded"

    def test_only_matching_prefix_limited(self):
        client = TestClient(
            _app_with(
                (
                    RateLimitMiddleware,
                    {"rate_per_second": 0.001, "burst": 1, "path_prefix": "/api/"},
                ),
            )
        )
        # /ping is NOT /api/* — should never be limited
        for _ in range(10):
            assert client.get("/ping").status_code == 200

    def test_exempt_paths_skipped(self):
        client = TestClient(
            _app_with(
                (
                    RateLimitMiddleware,
                    {
                        "rate_per_second": 0.001,
                        "burst": 0,  # immediately exhausted
                        "path_prefix": "/",
                        "exempt_paths": frozenset({"/ping"}),
                    },
                ),
            )
        )
        # Even with empty bucket, /ping is exempt
        for _ in range(5):
            assert client.get("/ping").status_code == 200

    def test_xforwarded_for_used_as_client_key(self):
        """Different X-Forwarded-For values get different buckets."""
        client = TestClient(
            _app_with(
                (RateLimitMiddleware, {"rate_per_second": 0.001, "burst": 1, "path_prefix": "/"}),
            )
        )
        # Two requests from the same "real" IP
        assert client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
        # Same client (no XFF) → uses socket peer, exhausts
        r = client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"})
        assert r.status_code == 429

        # A different XFF gets its own bucket → still has tokens
        r2 = client.get("/ping", headers={"X-Forwarded-For": "2.2.2.2"})
        assert r2.status_code == 200
