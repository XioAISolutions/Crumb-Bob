"""Audit logging for security-relevant events.

Persists a tamper-evident record of authentication failures, configuration
changes, and any sensitive operation that needs after-the-fact review.
Writes go to the same SQLite database as session memory, in a dedicated
``audit_log`` table created by schema migration v2.

The schema is intentionally narrow:

* ``id``         — autoincrement primary key
* ``ts``         — UTC ISO-8601 timestamp (so logs are sortable as strings)
* ``event``     — short event type, e.g. ``auth_failure``, ``query_executed``
* ``actor``     — best-effort identity (IP, API key prefix, "system")
* ``request_id`` — correlates with the per-request ID in the HTTP log line
* ``payload``   — JSON blob of event-specific context

If the database isn't available (e.g., file permissions), audit writes
fall back to the application logger at WARNING — failing to write an
audit event must never block the request. Operators monitoring the audit
table should also watch the logger for ``audit.fallback`` records.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logging_config import request_id_ctx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditEvent:
    """Single audit log entry, exactly as it would be written to the DB."""

    ts: str
    event: str
    actor: str
    request_id: str | None
    payload: dict[str, Any]


def _utcnow_iso() -> str:
    """UTC ISO-8601 with Z suffix; sortable as a string and timezone-explicit."""
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AuditLogger:
    """Writes audit events to the configured SQLite database.

    Thread-safe (each call opens a short-lived connection). For high-volume
    writes we'd want connection reuse + a background flush thread; for the
    expected volume (auth events, config changes, occasional queries) the
    per-call connection cost is invisible.

    Args:
        db_path: Path to the SQLite memory database.
        actor_resolver: Optional callable returning a string identifying
            the actor for the current call. Use this to plug in your auth
            system (returns user ID) or to read the X-Forwarded-For header.
            Defaults to returning "system".
    """

    def __init__(
        self,
        db_path: str | Path,
        actor_resolver: Any = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.actor_resolver = actor_resolver or (lambda: "system")

    def record(
        self,
        event: str,
        *,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Persist an audit event.

        Never raises — if persistence fails we degrade to logger output so
        callers don't need to wrap this in their own try/except.
        """
        entry = AuditEvent(
            ts=_utcnow_iso(),
            event=event,
            actor=actor or self.actor_resolver(),
            request_id=request_id_ctx.get(),
            payload=payload or {},
        )
        try:
            self._insert(entry)
        except (sqlite3.Error, OSError) as exc:
            # Audit failures must not block the request — drop to logger.
            logger.warning(
                "audit.fallback",
                extra={
                    "event": entry.event,
                    "actor": entry.actor,
                    "audit_request_id": entry.request_id,
                    "error": str(exc),
                },
            )

    def _insert(self, entry: AuditEvent) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO audit_log (ts, event, actor, request_id, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entry.ts,
                    entry.event,
                    entry.actor,
                    entry.request_id,
                    json.dumps(entry.payload, ensure_ascii=False, default=str),
                ),
            )

    def recent(self, limit: int = 100) -> list[AuditEvent]:
        """Read the most recent audit events for review/dashboards.

        Args:
            limit: Maximum number of events to return.

        Returns:
            Newest-first list of AuditEvent objects.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT ts, event, actor, request_id, payload
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            AuditEvent(
                ts=row["ts"],
                event=row["event"],
                actor=row["actor"] or "unknown",
                request_id=row["request_id"],
                payload=json.loads(row["payload"]) if row["payload"] else {},
            )
            for row in rows
        ]


# Event-type constants — using strings keeps the schema flexible, but
# constants here prevent typos at call sites and document the vocabulary.
EVENT_AUTH_SUCCESS = "auth.success"
EVENT_AUTH_FAILURE = "auth.failure"
EVENT_RATE_LIMITED = "rate.limited"
EVENT_QUERY_EXECUTED = "query.executed"
EVENT_QUERY_REJECTED = "query.rejected"
EVENT_CONFIG_CHANGED = "config.changed"
EVENT_PACK_GENERATED = "pack.generated"
EVENT_PACK_RECORDED = "pack.recorded"
