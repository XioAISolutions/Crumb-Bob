"""Tests for crumdbob.migrations — forward-only migration framework."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from crumdbob import migrations
from crumdbob.memory import MemoryDatabase
from crumdbob.migrations import SCHEMA_VERSION, run_migrations


@pytest.fixture
def conn():
    """In-memory SQLite — fastest possible test setup."""
    c = sqlite3.connect(":memory:")
    try:
        c.row_factory = sqlite3.Row
        # The runner needs a metadata table to track version state.
        c.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
        yield c
    finally:
        c.close()


class TestRunMigrations:
    def test_fresh_db_runs_through_all_migrations(self, conn):
        new_version = run_migrations(conn)
        assert new_version == SCHEMA_VERSION
        # audit_log table should exist (migration v2)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
        ).fetchall()
        assert len(rows) == 1

    def test_already_at_target_is_no_op(self, conn):
        # First run brings it to current.
        run_migrations(conn)
        before_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

        # Second run should be a no-op (same version returned).
        result = run_migrations(conn)
        after_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

        assert result == SCHEMA_VERSION
        assert before_count == after_count

    def test_refuses_newer_db(self, conn):
        # Simulate a database written by a newer CrumdBob.
        conn.execute("INSERT INTO metadata (key, value) VALUES ('schema_version', '99')")
        conn.commit()
        with pytest.raises(RuntimeError, match="newer than this code"):
            run_migrations(conn)

    def test_version_is_recorded_after_each_step(self, conn):
        run_migrations(conn)
        recorded = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[
            0
        ]
        assert int(recorded) == SCHEMA_VERSION

    def test_failure_does_not_advance_version(self, conn, monkeypatch):
        """If a migration raises mid-flight, the recorded schema version
        does not advance — so the next run will re-attempt it.

        Note: Python's sqlite3 module does NOT roll back DDL statements
        inside `with conn:` when the transaction fails (DDL auto-commits
        in legacy isolation_level mode). The version-marker INSERT IS
        rolled back, which is the invariant that matters: a failed
        migration leaves the database at the previous version so the
        next run can retry. Partial DDL is tolerable because every
        migration uses ``CREATE TABLE IF NOT EXISTS`` (idempotent).
        """

        def broken_migration(c):
            # This DDL may persist (sqlite3 quirk) — that's fine, see docstring.
            c.execute("CREATE TABLE IF NOT EXISTS partial_ddl (x INTEGER)")
            raise RuntimeError("oh no")

        # Inject the broken migration at a fresh version.
        broken_version = SCHEMA_VERSION + 1
        monkeypatch.setitem(migrations._MIGRATIONS, broken_version, broken_migration)
        monkeypatch.setattr(migrations, "SCHEMA_VERSION", broken_version)

        # Bring the DB up to the real SCHEMA_VERSION first (clean baseline).
        baseline_version = SCHEMA_VERSION  # was monkeypatched, so this is the real one

        # Reset the patched constant temporarily to baseline, run, then restore.
        monkeypatch.setattr(migrations, "SCHEMA_VERSION", baseline_version)
        run_migrations(conn)
        recorded_before = conn.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        ).fetchone()[0]

        # Now bump target to the broken version and watch it fail.
        monkeypatch.setattr(migrations, "SCHEMA_VERSION", broken_version)
        with pytest.raises(RuntimeError, match="oh no"):
            run_migrations(conn)

        # The recorded version must NOT have advanced.
        recorded_after = conn.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        ).fetchone()[0]
        assert recorded_after == recorded_before


class TestAuditLogMigration:
    def test_audit_log_has_required_columns(self, conn):
        run_migrations(conn)
        cols = {row["name"] for row in conn.execute("PRAGMA table_info('audit_log')").fetchall()}
        assert {"id", "ts", "event", "actor", "request_id", "payload"} <= cols

    def test_audit_log_has_indexes(self, conn):
        run_migrations(conn)
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='audit_log'"
            ).fetchall()
        }
        assert "idx_audit_log_ts" in indexes
        assert "idx_audit_log_event" in indexes
        assert "idx_audit_log_actor" in indexes


class TestMemoryDatabaseAppliesMigrations:
    def test_init_database_creates_audit_log(self, tmp_path: Path):
        """MemoryDatabase.init_database() should run migrations."""
        db_path = tmp_path / "test.db"
        db = MemoryDatabase(db_path)
        db.init_database()
        cur = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
        )
        assert cur.fetchone() is not None
        db.close()

    def test_init_database_idempotent(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        # Call twice — should not raise, should not duplicate anything.
        for _ in range(2):
            db = MemoryDatabase(db_path)
            db.init_database()
            db.close()

        # The schema_version should be exactly SCHEMA_VERSION (not a list of values).
        db = MemoryDatabase(db_path)
        row = db.conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        assert int(row[0]) == SCHEMA_VERSION
        db.close()
