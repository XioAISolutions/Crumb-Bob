"""Prometheus-compatible metrics for the CrumbBob web API.

Deliberately zero-dependency — implements the Prometheus text exposition
format (v0.0.4) directly rather than pulling in `prometheus_client`. This
keeps the optional `[web]` install lean.

If you ever need histograms or summaries, switch to `prometheus_client`;
for the current set (counters + a gauge) the stdlib is enough.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response


class _Counter:
    """Thread-safe monotonic counter with optional label dimensions."""

    def __init__(self, name: str, help_text: str) -> None:
        self.name = name
        self.help = help_text
        self._values: dict[tuple[tuple[str, str], ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            self._values[key] += amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        with self._lock:
            items = list(self._values.items())
        for label_pairs, value in items:
            if label_pairs:
                rendered_labels = ",".join(f'{k}="{_escape_label(v)}"' for k, v in label_pairs)
                lines.append(f"{self.name}{{{rendered_labels}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class _Gauge:
    """Thread-safe gauge with optional label dimensions."""

    def __init__(self, name: str, help_text: str) -> None:
        self.name = name
        self.help = help_text
        self._values: dict[tuple[tuple[str, str], ...], float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            self._values[key] = value

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} gauge"]
        with self._lock:
            items = list(self._values.items())
        for label_pairs, value in items:
            if label_pairs:
                rendered_labels = ",".join(f'{k}="{_escape_label(v)}"' for k, v in label_pairs)
                lines.append(f"{self.name}{{{rendered_labels}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


def _escape_label(value: str) -> str:
    """Escape a Prometheus label value per the text exposition spec."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# Registered metrics. Adding new ones is a single line at module level.
http_requests_total = _Counter(
    "crumdbob_http_requests_total",
    "Total HTTP requests processed by the CrumdBob API.",
)
http_request_duration_seconds_sum = _Counter(
    "crumdbob_http_request_duration_seconds_sum",
    "Total request duration in seconds, summed.",
)
http_request_duration_seconds_count = _Counter(
    "crumdbob_http_request_duration_seconds_count",
    "Total number of duration observations.",
)
http_errors_total = _Counter(
    "crumdbob_http_errors_total",
    "Total HTTP responses with status >= 500.",
)
rate_limited_total = _Counter(
    "crumdbob_rate_limited_total",
    "Total requests rejected due to rate limiting.",
)
auth_failures_total = _Counter(
    "crumdbob_auth_failures_total",
    "Total requests rejected due to missing or invalid API key.",
)
process_start_time_seconds = _Gauge(
    "crumdbob_process_start_time_seconds",
    "Unix timestamp when this process started serving traffic.",
)
process_start_time_seconds.set(time.time())


def render_metrics() -> str:
    """Render all registered metrics in Prometheus text format."""
    blocks = [
        http_requests_total.render(),
        http_request_duration_seconds_sum.render(),
        http_request_duration_seconds_count.render(),
        http_errors_total.render(),
        rate_limited_total.render(),
        auth_failures_total.render(),
        process_start_time_seconds.render(),
    ]
    return "\n\n".join(blocks) + "\n"


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request counts and durations.

    Buckets by ``method`` and the routed path template (or raw path if no
    route matched), so cardinality stays bounded — emitting one metric
    label per unique URL would explode for path-param routes like
    ``/api/sessions/{id}``.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start = time.perf_counter()
        method = request.method
        # Use the route's path template when available; fall back to raw path.
        path = request.url.path
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            duration = time.perf_counter() - start
            http_requests_total.inc(method=method, path=path, status="500")
            http_errors_total.inc(method=method, path=path)
            http_request_duration_seconds_sum.inc(duration, method=method, path=path)
            http_request_duration_seconds_count.inc(method=method, path=path)
            raise

        duration = time.perf_counter() - start
        http_requests_total.inc(method=method, path=path, status=status)
        http_request_duration_seconds_sum.inc(duration, method=method, path=path)
        http_request_duration_seconds_count.inc(method=method, path=path)
        if response.status_code >= 500:
            http_errors_total.inc(method=method, path=path)
        if response.status_code == 429:
            rate_limited_total.inc(method=method, path=path)
        if response.status_code == 401:
            auth_failures_total.inc(method=method, path=path)
        return response


def metrics_response() -> Response:
    """FastAPI handler that returns the metrics in the right content-type."""
    return PlainTextResponse(
        render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
