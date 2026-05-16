"""Tests for crumdbob.audit — audit log persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from crumdbob.audit import (
    EVENT_AUTH_FAILURE,
    EVENT_QUERY_EXECUTED,
    AuditLogger,
)
from crumdbob.logging_config import request_id_ctx
from crumdbob.memory import MemoryDatabase


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Bootstrap a database with the audit_log table (via migrations)."""
    p = tmp_path / "audit-test.db"
    db = MemoryDatabase(p)
    db.init_database()
    db.close()
    return p


class TestAuditLogger:
    def test_records_basic_event(self, db_path):
        logger = AuditLogger(db_path)
        logger.record(EVENT_AUTH_FAILURE, actor="1.2.3.4")
        events = logger.recent()
        assert len(events) == 1
        assert events[0].event == EVENT_AUTH_FAILURE
        assert events[0].actor == "1.2.3.4"

    def test_request_id_captured_from_contextvar(self, db_path):
        logger = AuditLogger(db_path)
        request_id_ctx.set("req-abc-123")
        try:
            logger.record(EVENT_QUERY_EXECUTED, actor="test")
        finally:
            request_id_ctx.set(None)
        events = logger.recent()
        assert events[0].request_id == "req-abc-123"

    def test_payload_serialized_roundtrip(self, db_path):
        logger = AuditLogger(db_path)
        payload = {"path": "/api/v1/x", "method": "POST", "nested": {"k": [1, 2]}}
        logger.record(EVENT_AUTH_FAILURE, actor="x", payload=payload)
        events = logger.recent()
        assert events[0].payload == payload

    def test_recent_orders_newest_first(self, db_path):
        logger = AuditLogger(db_path)
        for i in range(5):
            logger.record(EVENT_QUERY_EXECUTED, actor=f"user{i}")
        events = logger.recent()
        assert events[0].actor == "user4"
        assert events[-1].actor == "user0"

    def test_recent_respects_limit(self, db_path):
        logger = AuditLogger(db_path)
        for i in range(20):
            logger.record(EVENT_QUERY_EXECUTED, actor=f"u{i}")
        events = logger.recent(limit=3)
        assert len(events) == 3

    def test_actor_resolver_default_is_system(self, db_path):
        logger = AuditLogger(db_path)
        logger.record(EVENT_QUERY_EXECUTED)
        events = logger.recent()
        assert events[0].actor == "system"

    def test_actor_resolver_custom(self, db_path):
        calls = []

        def resolver():
            calls.append("called")
            return "alice@example.com"

        logger = AuditLogger(db_path, actor_resolver=resolver)
        logger.record(EVENT_QUERY_EXECUTED)
        assert calls == ["called"]
        assert logger.recent()[0].actor == "alice@example.com"

    def test_explicit_actor_overrides_resolver(self, db_path):
        logger = AuditLogger(db_path, actor_resolver=lambda: "resolver-actor")
        logger.record(EVENT_AUTH_FAILURE, actor="explicit-actor")
        assert logger.recent()[0].actor == "explicit-actor"

    def test_persistence_failure_does_not_raise(self, tmp_path, caplog):
        """If the DB is unreachable, fall back to a logger warning."""
        # Point at a path that doesn't exist and never will (no parent dir).
        bad_path = tmp_path / "nonexistent" / "audit.db"
        logger = AuditLogger(bad_path)
        # Should not raise.
        logger.record(EVENT_AUTH_FAILURE, actor="test")

    def test_non_json_payload_value_uses_default_str(self, db_path):
        """Objects that aren't JSON-serializable fall through default=str."""

        class Custom:
            def __str__(self) -> str:
                return "custom-string-rep"

        logger = AuditLogger(db_path)
        logger.record(
            EVENT_AUTH_FAILURE,
            actor="x",
            payload={"obj": Custom()},  # type: ignore[dict-item]
        )
        events = logger.recent()
        assert "custom-string-rep" in str(events[0].payload["obj"])
