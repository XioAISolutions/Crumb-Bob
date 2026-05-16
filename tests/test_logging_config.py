"""Tests for crumdbob.logging_config — structured logging + request_id ContextVar."""

from __future__ import annotations

import json
import logging
import sys
from io import StringIO

import pytest

from crumdbob.logging_config import (
    JsonFormatter,
    PlainFormatter,
    configure_logging,
    request_id_ctx,
)


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Snapshot and restore root logger state around every test.

    Tests that call configure_logging() mutate the root logger globally;
    without restore the next test sees the previous test's handlers.
    """
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    yield
    root.handlers = saved_handlers
    root.setLevel(saved_level)
    request_id_ctx.set(None)


class TestJsonFormatter:
    def test_emits_one_line_json(self):
        record = logging.makeLogRecord(
            {
                "name": "test",
                "levelname": "INFO",
                "msg": "hello world",
            }
        )
        record.created = 1700000000.0  # frozen timestamp
        output = JsonFormatter().format(record)
        # Exactly one line (no embedded newlines)
        assert "\n" not in output
        # Parses cleanly
        payload = json.loads(output)
        assert payload["level"] == "INFO"
        assert payload["msg"] == "hello world"
        assert payload["logger"] == "test"

    def test_timestamp_is_iso_utc_with_z_suffix(self):
        record = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": ""})
        record.created = 1700000000.0
        payload = json.loads(JsonFormatter().format(record))
        # 2023-11-14T22:13:20Z (the +00:00 → Z swap is the key behaviour)
        assert payload["ts"].endswith("Z")
        assert "T" in payload["ts"]
        assert "+00:00" not in payload["ts"]

    def test_request_id_propagates_via_context_var(self):
        request_id_ctx.set("req-test-id")
        record = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": "x"})
        payload = json.loads(JsonFormatter().format(record))
        assert payload["request_id"] == "req-test-id"

    def test_request_id_absent_when_unset(self):
        request_id_ctx.set(None)
        record = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": "x"})
        payload = json.loads(JsonFormatter().format(record))
        assert "request_id" not in payload

    def test_extra_fields_appear_in_json(self):
        record = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": "x"})
        record.user_id = 42
        record.action = "test"
        payload = json.loads(JsonFormatter().format(record))
        assert payload["user_id"] == 42
        assert payload["action"] == "test"

    def test_non_json_serializable_extras_are_repr(self):
        """Don't crash on weird objects in extras — fall back to repr()."""
        record = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": "x"})
        record.weird = object()  # not JSON-serializable
        payload = json.loads(JsonFormatter().format(record))
        assert "weird" in payload
        assert isinstance(payload["weird"], str)

    def test_exception_serialised_as_string(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.makeLogRecord({"name": "x", "levelname": "ERROR", "msg": "x"})
            record.exc_info = sys.exc_info()
            payload = json.loads(JsonFormatter().format(record))
            assert "exc" in payload
            assert "ValueError" in payload["exc"]


class TestPlainFormatter:
    def test_includes_request_id_or_dash(self):
        request_id_ctx.set(None)
        record = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": "msg"})
        output = PlainFormatter().format(record)
        assert "[-]" in output  # dash for missing request_id

        request_id_ctx.set("rq-123")
        record2 = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": "msg"})
        output2 = PlainFormatter().format(record2)
        assert "[rq-123]" in output2


class TestConfigureLogging:
    def test_idempotent(self):
        """Re-running configure_logging replaces handlers, doesn't duplicate."""
        configure_logging(level="INFO", json_output=True)
        configure_logging(level="INFO", json_output=True)
        configure_logging(level="INFO", json_output=True)
        assert len(logging.getLogger().handlers) == 1

    def test_json_output_writes_parseable_lines(self):
        stream = StringIO()
        configure_logging(level="INFO", json_output=True, stream=stream)
        logging.getLogger("crumdbob.test").info("structured")
        line = stream.getvalue().strip()
        payload = json.loads(line)
        assert payload["msg"] == "structured"

    def test_env_override_json(self, monkeypatch):
        monkeypatch.setenv("CRUMDBOB_LOG_FORMAT", "json")
        stream = StringIO()
        configure_logging(level="INFO", stream=stream)
        logging.getLogger("x").info("hi")
        # If JSON was chosen, the output should parse as JSON.
        json.loads(stream.getvalue().strip())

    def test_env_override_plain(self, monkeypatch):
        monkeypatch.setenv("CRUMDBOB_LOG_FORMAT", "plain")
        stream = StringIO()
        configure_logging(level="INFO", stream=stream)
        logging.getLogger("x").info("hi")
        # Plain output is human format — not JSON-parseable.
        with pytest.raises(json.JSONDecodeError):
            json.loads(stream.getvalue().strip())

    def test_noisy_third_party_loggers_quieted(self):
        configure_logging(level="DEBUG", json_output=True)
        # We turn these down to WARNING regardless of the root level.
        assert logging.getLogger("uvicorn.access").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
