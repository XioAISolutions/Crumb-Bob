"""Lightweight forward-only SQLite migration framework.

Each migration is a versioned (idempotent) function that takes a ``sqlite3.Connection``
and applies one logical schema change. The current version is stored in the
``metadata`` table under key ``schema_version`` and incremented after each
successful migration. On startup, ``run_migrations(conn)`` brings the
database from its current version up to ``SCHEMA_VERSION``.

Why hand-roll instead of using Alembic?

* CrumdBob's whole point is being a zero-runtime-dependency CLI. Alembic
  pulls in SQLAlchemy and a 60+ MB transitive tree.
* The schema is small and we never need to downgrade — production data is
  rare and reversibility is YAGNI.
* Migrations run inside a transaction; either the whole step lands or it
  rolls back. SQLite's ``IF NOT EXISTS`` clauses make most steps already
  idempotent, so re-running the migrator on an up-to-date DB is a no-op.

Adding a migration
==================

1. Bump ``SCHEMA_VERSION``.
2. Append a function decorated with ``@migration(N)`` where N is the new
   version.
3. The function gets a ``sqlite3.Connection``; do all DDL on it and don't
   commit (the runner wraps the whole step in a transaction).

Migrations must be **forward compatible** with older code: once shipped,
never edit a migration's body. Add a new one that fixes things instead.

Atomicity caveat
================

Python's ``sqlite3`` module in legacy isolation-level mode does NOT roll
back DDL statements (CREATE TABLE etc.) when the surrounding ``with conn:``
block raises — DDL auto-commits. The version-marker INSERT IS rolled
back, so the invariant we actually guarantee is: **a failed migration
does not advance the recorded schema_version**. The next run retries
the failed migration from scratch.

This is why every migration uses ``CREATE TABLE IF NOT EXISTS`` /
``CREATE INDEX IF NOT EXISTS`` — re-running a partially-applied
migration must be a no-op.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Bump this whenever you append a new migration below. The runner uses it
# as the upper bound when stepping versions.
SCHEMA_VERSION = 2

# Registry of migration_version -> migration_callable. Populated by the
# @migration() decorator.
_MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def migration(
    version: int,
) -> Callable[[Callable[[sqlite3.Connection], None]], Callable[[sqlite3.Connection], None]]:
    """Register a migration function for a specific schema version.

    The decorated function receives a sqlite3.Connection and should issue
    DDL/DML against it. Do NOT call ``conn.commit()`` — the runner manages
    transactions.
    """
    if version < 1:
        raise ValueError("Migration versions start at 1")
    if version in _MIGRATIONS:
        raise ValueError(f"Duplicate migration registered for version {version}")

    def register(
        fn: Callable[[sqlite3.Connection], None],
    ) -> Callable[[sqlite3.Connection], None]:
        _MIGRATIONS[version] = fn
        return fn

    return register


def _get_current_version(conn: sqlite3.Connection) -> int:
    """Read the recorded schema version, defaulting to 0 if missing."""
    try:
        row = conn.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
    except sqlite3.OperationalError:
        # metadata table doesn't exist yet → brand-new database
        return 0
    if not row:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 0


def _set_current_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', ?)",
        (str(version),),
    )


def run_migrations(conn: sqlite3.Connection) -> int:
    """Bring the database up to ``SCHEMA_VERSION``.

    Args:
        conn: An open SQLite connection.

    Returns:
        The new schema version after migrations complete.

    Raises:
        RuntimeError: If the database is at a NEWER version than this code
            supports (forward-incompatible) — refuse to operate to avoid
            corrupting newer data.
    """
    current = _get_current_version(conn)
    target = SCHEMA_VERSION

    if current > target:
        raise RuntimeError(
            f"Database schema v{current} is newer than this code "
            f"(supports v{target}). Upgrade CrumdBob to continue."
        )
    if current == target:
        return current

    for version in range(current + 1, target + 1):
        if version not in _MIGRATIONS:
            raise RuntimeError(
                f"Missing migration for version {version}. "
                "Check that all migration functions are imported."
            )
        logger.info(
            "migrations.applying",
            extra={"from_version": version - 1, "to_version": version},
        )
        try:
            with conn:  # transaction; commits on clean exit, rolls back on error
                _MIGRATIONS[version](conn)
                _set_current_version(conn, version)
        except Exception:
            logger.exception(
                "migrations.failed",
                extra={"target_version": version},
            )
            raise
        logger.info(
            "migrations.applied",
            extra={"version": version},
        )

    return target


# ---------------------------------------------------------------------------
# Migration definitions
# ---------------------------------------------------------------------------
# Migration 1: baseline (matches memory.MemoryDatabase.init_database()).
# We don't redefine the full schema here because legacy databases created
# before the migration framework already have all v1 tables; the runner
# just bumps their version marker. New databases also create v1 tables via
# MemoryDatabase.init_database() before run_migrations() is called, so
# this migration is a no-op that simply marks v1 as done.
@migration(1)
def _baseline(conn: sqlite3.Connection) -> None:
    """Mark v1 schema as applied. The tables themselves are created by
    MemoryDatabase.init_database() so this migration only exists so that
    fresh databases progress through the migration sequence cleanly."""
    # No-op: v1 tables are created by init_database() before this runs.
    _ = conn  # silence "unused" warning while keeping the signature uniform


@migration(2)
def _add_audit_log(conn: sqlite3.Connection) -> None:
    """Add audit_log table for security-relevant events.

    Each row records: when, what kind of event, who, the correlation ID
    of the HTTP request that triggered it, and an arbitrary JSON payload.
    Indexed on (ts) for time-range queries and (event) for filtering by
    event type — the two access patterns the dashboard needs.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            event TEXT NOT NULL,
            actor TEXT NOT NULL,
            request_id TEXT,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log(ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_event ON audit_log(event)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor)")


__all__ = ["SCHEMA_VERSION", "migration", "run_migrations"]
