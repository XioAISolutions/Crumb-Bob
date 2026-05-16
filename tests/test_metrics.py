"""Tests for web.api.metrics — Prometheus text exposition."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from web.api.metrics import (
    MetricsMiddleware,
    _Counter,
    _Gauge,
    metrics_response,
    render_metrics,
)


class TestCounter:
    def test_starts_at_zero_after_inc(self):
        c = _Counter("test_counter", "A test counter")
        c.inc()
        assert "test_counter 1.0" in c.render()

    def test_accumulates(self):
        c = _Counter("test_counter", "A test counter")
        for _ in range(5):
            c.inc()
        assert "test_counter 5.0" in c.render()

    def test_labels_appear_in_output(self):
        c = _Counter("test_counter", "A test counter")
        c.inc(method="GET", path="/x")
        rendered = c.render()
        assert 'method="GET"' in rendered
        assert 'path="/x"' in rendered

    def test_includes_help_and_type_lines(self):
        c = _Counter("test_c", "Help text here")
        c.inc()
        rendered = c.render()
        assert "# HELP test_c Help text here" in rendered
        assert "# TYPE test_c counter" in rendered

    def test_label_values_escaped(self):
        c = _Counter("c", "h")
        c.inc(path='/api/x"with"quotes')
        rendered = c.render()
        # Quote inside label value should be escaped
        assert '\\"' in rendered


class TestGauge:
    def test_set_overrides(self):
        g = _Gauge("test_gauge", "A gauge")
        g.set(1.0)
        g.set(42.5)
        assert "test_gauge 42.5" in g.render()

    def test_type_is_gauge(self):
        g = _Gauge("g", "h")
        g.set(0)
        assert "# TYPE g gauge" in g.render()


class TestRenderMetrics:
    def test_includes_all_registered_metrics(self):
        output = render_metrics()
        for expected in [
            "crumdbob_http_requests_total",
            "crumdbob_http_request_duration_seconds_sum",
            "crumdbob_http_errors_total",
            "crumdbob_rate_limited_total",
            "crumdbob_auth_failures_total",
            "crumdbob_process_start_time_seconds",
        ]:
            assert expected in output

    def test_output_ends_with_newline(self):
        # Prometheus parsers tolerate either, but matching the spec doesn't cost anything.
        assert render_metrics().endswith("\n")


class TestMetricsResponse:
    def test_content_type_matches_spec(self):
        response = metrics_response()
        assert response.media_type.startswith("text/plain")
        assert "version=0.0.4" in response.media_type


class TestMetricsMiddleware:
    def test_increments_request_counter(self):
        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)
        before = render_metrics()
        client.get("/test")
        after = render_metrics()
        # We don't compare exact counts (other tests share the module-level
        # metrics), but the after-state must have grown for /test.
        assert "/test" in after
        # Counter for /test should be present in after but not before.
        assert after.count('path="/test"') > before.count('path="/test"')

    def test_records_status_label(self):
        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/err")
        def errors():
            raise HTTPException(status_code=503)

        client = TestClient(app)
        client.get("/err")
        output = render_metrics()
        assert 'status="503"' in output
