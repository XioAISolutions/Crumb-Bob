"""Multi-session memory database for CrumbBob.

Provides persistent storage and querying of pack sessions across time.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import subprocess  # nosec B404
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from . import __version__
from .migrations import SCHEMA_VERSION, run_migrations
from .parser import BobReport, parse_bob_report
from .validator import dependency_edges

# Re-export so callers that imported SCHEMA_VERSION from this module continue
# to work; the canonical definition lives in crumdbob.migrations.
__all__ = ["SCHEMA_VERSION", "MemoryDatabase"]
GIT_EXECUTABLE = "git"


@dataclass
class Session:
    """Represents a recorded pack session."""

    id: int
    timestamp: str
    session_name: str | None
    pack_version: int
    git_branch: str | None
    git_commit: str | None
    git_author: str | None
    source_report_path: str
    source_report_hash: str
    pack_directory: str | None
    file_count: int
    command_count: int
    risk_count: int
    task_count: int


@dataclass
class PackRecord:
    """Represents a pack version record."""

    id: int
    session_id: int
    version: int
    timestamp: str
    crumdbob_version: str
    proof_chain_hash: str | None


@dataclass
class FileRecord:
    """Represents a file mentioned in a session."""

    id: int
    session_id: int
    path: str
    first_seen: str
    last_seen: str
    mention_count: int


@dataclass
class CommandRecord:
    """Represents a command captured in a session."""

    id: int
    session_id: int
    command: str
    first_seen: str
    last_seen: str
    mention_count: int


@dataclass
class RiskRecord:
    """Represents a risk identified in a session."""

    id: int
    session_id: int
    description: str
    first_seen: str
    last_seen: str
    status: Literal["open", "mitigated", "accepted"]


@dataclass
class TaskRecord:
    """Represents a task/next step from a session."""

    id: int
    session_id: int
    description: str
    first_seen: str
    last_seen: str
    status: Literal["pending", "in_progress", "completed"]


class MemoryDatabase:
    """SQLite-based memory database for CrumbBob sessions."""

    def __init__(self, db_path: str | Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Tune SQLite for concurrent reads + safer writes.
        # WAL: readers don't block writers; foreign_keys: enforce CASCADE on session deletes.
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=NORMAL")

    def close(self) -> None:
        """Close database connection, committing any pending work."""
        if self.conn:
            with contextlib.suppress(sqlite3.Error):
                self.conn.commit()
            self.conn.close()

    def __enter__(self) -> MemoryDatabase:
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        if exc_type is not None:
            with contextlib.suppress(sqlite3.Error):
                self.conn.rollback()
        self.close()

    def init_database(self) -> None:
        """Initialize database schema with all tables and indexes.

        Idempotent: safe to call on a fresh database or one that's already
        at the latest schema. The CREATE TABLE IF NOT EXISTS statements
        below establish the v1 baseline; ``run_migrations()`` then brings
        the database up to ``SCHEMA_VERSION`` by applying any subsequent
        migrations (audit_log table, etc.).
        """
        cursor = self.conn.cursor()

        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_name TEXT,
                pack_version INTEGER NOT NULL DEFAULT 1,
                git_branch TEXT,
                git_commit TEXT,
                git_author TEXT,
                source_report_path TEXT NOT NULL,
                source_report_hash TEXT NOT NULL,
                pack_directory TEXT,
                file_count INTEGER NOT NULL DEFAULT 0,
                command_count INTEGER NOT NULL DEFAULT 0,
                risk_count INTEGER NOT NULL DEFAULT 0,
                task_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Packs table (version history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                crumdbob_version TEXT NOT NULL,
                proof_chain_hash TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                mention_count INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Commands table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                mention_count INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Risks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Relationships table (for CRUMB refs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                source_crumb TEXT NOT NULL,
                target_crumb TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Insights table (for future AI-generated insights)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
            )
        """)

        # LLM cache table (for caching LLM responses)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL UNIQUE,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_used INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # LLM config table (for storing LLM provider configuration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                api_key_env TEXT NOT NULL,
                temperature REAL DEFAULT 0.7,
                max_tokens INTEGER DEFAULT 2000,
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_git_branch ON sessions(git_branch)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_git_author ON sessions(git_author)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_packs_session_id ON packs(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_session_id ON files(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_session_id ON commands(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risks_session_id ON risks(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risks_status ON risks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risks_description ON risks(description)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_status_description ON tasks(status, description)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_command ON commands(command)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_session_id ON tasks(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationships_session_id ON relationships(session_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_session_id ON insights(session_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_cache_prompt_hash ON llm_cache(prompt_hash)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_cache_created_at ON llm_cache(created_at)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_config_enabled ON llm_config(enabled)")

        # Create views for common queries
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS session_summary AS
            SELECT
                s.id,
                s.timestamp,
                s.session_name,
                s.git_branch,
                s.git_author,
                s.file_count,
                s.command_count,
                s.risk_count,
                s.task_count,
                COUNT(DISTINCT p.id) as pack_versions
            FROM sessions s
            LEFT JOIN packs p ON s.id = p.session_id
            GROUP BY s.id
        """)

        cursor.execute("""
            CREATE VIEW IF NOT EXISTS file_history AS
            SELECT
                f.path,
                f.first_seen,
                f.last_seen,
                COUNT(DISTINCT f.session_id) as session_count,
                SUM(f.mention_count) as total_mentions
            FROM files f
            GROUP BY f.path
        """)

        cursor.execute("""
            CREATE VIEW IF NOT EXISTS risk_summary AS
            SELECT
                r.description,
                r.status,
                r.first_seen,
                r.last_seen,
                COUNT(DISTINCT r.session_id) as session_count
            FROM risks r
            GROUP BY r.description, r.status
        """)

        cursor.execute("""
            CREATE VIEW IF NOT EXISTS command_frequency AS
            SELECT
                c.command,
                COUNT(DISTINCT c.session_id) as session_count,
                SUM(c.mention_count) as total_mentions,
                MIN(c.first_seen) as first_seen,
                MAX(c.last_seen) as last_seen
            FROM commands c
            GROUP BY c.command
            ORDER BY total_mentions DESC
        """)

        self.conn.commit()

        # Bring schema up to current version (creates audit_log etc.).
        # Migration #1 is a no-op (just marks the v1 baseline above as
        # applied); later migrations add new tables idempotently.
        run_migrations(self.conn)

    def record_session(
        self,
        report: BobReport,
        pack_directory: str | Path | None = None,
        session_name: str | None = None,
        git_context: dict[str, str] | None = None,
        proof_chain_hash: str | None = None,
        crumdbob_version: str = __version__,
    ) -> int:
        """Record a complete pack session to database.

        Args:
            report: Parsed Bob report
            pack_directory: Optional path to pack directory
            session_name: Optional custom session name
            git_context: Optional Git context (branch, commit, author)
            proof_chain_hash: Optional proof chain hash
            crumdbob_version: CrumbBob version used

        Returns:
            Session ID
        """
        cursor = self.conn.cursor()
        timestamp = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

        git_context = git_context or {}

        # Insert session
        cursor.execute(
            """
            INSERT INTO sessions (
                timestamp, session_name, pack_version,
                git_branch, git_commit, git_author,
                source_report_path, source_report_hash, pack_directory,
                file_count, command_count, risk_count, task_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                session_name,
                1,
                git_context.get("branch"),
                git_context.get("commit"),
                git_context.get("author"),
                report.source_path,
                self._hash_content(report.raw_text),
                str(pack_directory) if pack_directory else None,
                len(report.files),
                len(report.commands),
                len(report.risks),
                len(report.next_steps),
            ),
        )

        session_id = cursor.lastrowid
        if session_id is None:
            raise RuntimeError("Failed to insert session record")

        # Insert pack version
        cursor.execute(
            """
            INSERT INTO packs (
                session_id, version, timestamp, crumdbob_version, proof_chain_hash
            ) VALUES (?, ?, ?, ?, ?)
        """,
            (session_id, 1, timestamp, crumdbob_version, proof_chain_hash),
        )

        # Insert files
        for file_path in report.files:
            cursor.execute(
                """
                INSERT INTO files (session_id, path, first_seen, last_seen, mention_count)
                VALUES (?, ?, ?, ?, ?)
            """,
                (session_id, file_path, timestamp, timestamp, 1),
            )

        # Insert commands
        for command in report.commands:
            cursor.execute(
                """
                INSERT INTO commands (session_id, command, first_seen, last_seen, mention_count)
                VALUES (?, ?, ?, ?, ?)
            """,
                (session_id, command, timestamp, timestamp, 1),
            )

        # Insert risks
        for risk in report.risks:
            cursor.execute(
                """
                INSERT INTO risks (session_id, description, first_seen, last_seen, status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (session_id, risk, timestamp, timestamp, "open"),
            )

        # Insert tasks
        for task in report.next_steps:
            cursor.execute(
                """
                INSERT INTO tasks (session_id, description, first_seen, last_seen, status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (session_id, task, timestamp, timestamp, "pending"),
            )

        self.conn.commit()
        return session_id

    def get_session(self, session_id: int) -> Session | None:
        """Retrieve session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session object or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Session(
            id=row["id"],
            timestamp=row["timestamp"],
            session_name=row["session_name"],
            pack_version=row["pack_version"],
            git_branch=row["git_branch"],
            git_commit=row["git_commit"],
            git_author=row["git_author"],
            source_report_path=row["source_report_path"],
            source_report_hash=row["source_report_hash"],
            pack_directory=row["pack_directory"],
            file_count=row["file_count"],
            command_count=row["command_count"],
            risk_count=row["risk_count"],
            task_count=row["task_count"],
        )

    def list_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        git_branch: str | None = None,
        git_author: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Session]:
        """List all sessions with optional filters.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            git_branch: Filter by Git branch
            git_author: Filter by Git author
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)

        Returns:
            List of Session objects
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []

        if git_branch:
            query += " AND git_branch = ?"
            params.append(git_branch)

        if git_author:
            query += " AND git_author = ?"
            params.append(git_author)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            Session(
                id=row["id"],
                timestamp=row["timestamp"],
                session_name=row["session_name"],
                pack_version=row["pack_version"],
                git_branch=row["git_branch"],
                git_commit=row["git_commit"],
                git_author=row["git_author"],
                source_report_path=row["source_report_path"],
                source_report_hash=row["source_report_hash"],
                pack_directory=row["pack_directory"],
                file_count=row["file_count"],
                command_count=row["command_count"],
                risk_count=row["risk_count"],
                task_count=row["task_count"],
            )
            for row in rows
        ]

    def search_files(self, pattern: str) -> list[FileRecord]:
        """Find files across sessions matching pattern.

        Args:
            pattern: SQL LIKE pattern (use % for wildcard)

        Returns:
            List of FileRecord objects
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM files
            WHERE path LIKE ?
            ORDER BY last_seen DESC
        """,
            (pattern,),
        )

        return [
            FileRecord(
                id=row["id"],
                session_id=row["session_id"],
                path=row["path"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                mention_count=row["mention_count"],
            )
            for row in cursor.fetchall()
        ]

    def search_risks(
        self,
        pattern: str | None = None,
        status: Literal["open", "mitigated", "accepted"] | None = None,
    ) -> list[RiskRecord]:
        """Find risks across sessions.

        Args:
            pattern: Optional SQL LIKE pattern for description
            status: Optional status filter

        Returns:
            List of RiskRecord objects
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM risks WHERE 1=1"
        params: list[Any] = []

        if pattern:
            query += " AND description LIKE ?"
            params.append(pattern)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY last_seen DESC"

        cursor.execute(query, params)

        return [
            RiskRecord(
                id=row["id"],
                session_id=row["session_id"],
                description=row["description"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                status=row["status"],
            )
            for row in cursor.fetchall()
        ]

    def get_session_timeline(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get chronological session history with key metrics.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session timeline entries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                timestamp,
                session_name,
                git_branch,
                git_author,
                file_count,
                command_count,
                risk_count,
                task_count
            FROM sessions
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_session_files(self, session_id: int) -> list[FileRecord]:
        """Get all files for a session.

        Args:
            session_id: Session ID

        Returns:
            List of FileRecord objects
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files WHERE session_id = ?", (session_id,))

        return [
            FileRecord(
                id=row["id"],
                session_id=row["session_id"],
                path=row["path"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                mention_count=row["mention_count"],
            )
            for row in cursor.fetchall()
        ]

    def get_session_commands(self, session_id: int) -> list[CommandRecord]:
        """Get all commands for a session.

        Args:
            session_id: Session ID

        Returns:
            List of CommandRecord objects
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM commands WHERE session_id = ?", (session_id,))

        return [
            CommandRecord(
                id=row["id"],
                session_id=row["session_id"],
                command=row["command"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                mention_count=row["mention_count"],
            )
            for row in cursor.fetchall()
        ]

    def get_session_risks(self, session_id: int) -> list[RiskRecord]:
        """Get all risks for a session.

        Args:
            session_id: Session ID

        Returns:
            List of RiskRecord objects
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM risks WHERE session_id = ?", (session_id,))

        return [
            RiskRecord(
                id=row["id"],
                session_id=row["session_id"],
                description=row["description"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                status=row["status"],
            )
            for row in cursor.fetchall()
        ]

    def get_session_tasks(self, session_id: int) -> list[TaskRecord]:
        """Get all tasks for a session.

        Args:
            session_id: Session ID

        Returns:
            List of TaskRecord objects
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE session_id = ?", (session_id,))

        return [
            TaskRecord(
                id=row["id"],
                session_id=row["session_id"],
                description=row["description"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                status=row["status"],
            )
            for row in cursor.fetchall()
        ]

    def record_relationships(self, session_id: int, edges: list[tuple[str, str, str]]) -> None:
        """Populate relationships table from CRUMB dependency edges.

        Args:
            session_id: Session the edges belong to
            edges: List of (source_crumb, target_crumb, relationship_type) tuples
        """
        if not edges:
            return
        cursor = self.conn.cursor()
        cursor.executemany(
            "INSERT INTO relationships (session_id, source_crumb, target_crumb, relationship_type) VALUES (?, ?, ?, ?)",
            [(session_id, src, tgt, kind) for src, tgt, kind in edges],
        )
        self.conn.commit()

    def get_session_relationships(self, session_id: int) -> list[dict[str, Any]]:
        """Get all CRUMB dependency edges for a session."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT source_crumb, target_crumb, relationship_type FROM relationships WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_hot_files(self, min_sessions: int = 2, limit: int = 20) -> list[dict[str, Any]]:
        """Files appearing across multiple sessions — cross-session hotspots.

        Args:
            min_sessions: Minimum number of sessions a file must appear in
            limit: Maximum results to return

        Returns:
            List of dicts with path, session_count, total_mentions, first_seen, last_seen
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT path, session_count, total_mentions, first_seen, last_seen
            FROM file_history
            WHERE session_count >= ?
            ORDER BY session_count DESC, total_mentions DESC
            LIMIT ?
        """,
            (min_sessions, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recurring_risks(self, min_sessions: int = 2) -> list[dict[str, Any]]:
        """Risks surfaced in multiple sessions — persistent, unresolved problems.

        Args:
            min_sessions: Minimum number of sessions a risk must appear in

        Returns:
            List of dicts with description, status, session_count, first_seen, last_seen
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT description, status, session_count, first_seen, last_seen
            FROM risk_summary
            WHERE session_count >= ?
            ORDER BY session_count DESC, last_seen DESC
        """,
            (min_sessions,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_command_frequency(self, limit: int = 20) -> list[dict[str, Any]]:
        """Most frequently used commands across all sessions.

        Args:
            limit: Maximum results to return

        Returns:
            List of dicts with command, session_count, total_mentions, first_seen, last_seen
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT command, session_count, total_mentions, first_seen, last_seen
            FROM command_frequency
            LIMIT ?
        """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict[str, int]:
        """Overall memory database statistics.

        Returns:
            Dict with session_count, unique_files, open_risks, unique_commands
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as n FROM sessions")
        session_count = cursor.fetchone()["n"]

        cursor.execute("SELECT COUNT(DISTINCT path) as n FROM files")
        unique_files = cursor.fetchone()["n"]

        cursor.execute("SELECT COUNT(*) as n FROM risks WHERE status = 'open'")
        open_risks = cursor.fetchone()["n"]

        cursor.execute("SELECT COUNT(DISTINCT command) as n FROM commands")
        unique_commands = cursor.fetchone()["n"]

        return {
            "session_count": session_count,
            "unique_files": unique_files,
            "open_risks": open_risks,
            "unique_commands": unique_commands,
        }

    def save_llm_config(
        self,
        provider: str,
        model: str,
        api_key_env: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        enabled: bool = True,
    ) -> int:
        """Save LLM configuration to database.

        Args:
            provider: LLM provider (openai, anthropic, local)
            model: Model name
            api_key_env: Environment variable name for API key
            temperature: Temperature setting
            max_tokens: Max tokens setting
            enabled: Whether configuration is enabled

        Returns:
            Configuration ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO llm_config (provider, model, api_key_env, temperature, max_tokens, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (provider, model, api_key_env, temperature, max_tokens, 1 if enabled else 0),
        )
        self.conn.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to save LLM configuration")
        return cursor.lastrowid

    def get_llm_config(self) -> dict[str, Any] | None:
        """Get active LLM configuration.

        Returns:
            Configuration dict or None if not configured
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT provider, model, api_key_env, temperature, max_tokens
            FROM llm_config
            WHERE enabled = 1
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_llm_config(self, config_id: int, **kwargs: Any) -> None:
        """Update LLM configuration.

        Args:
            config_id: Configuration ID
            **kwargs: Fields to update
        """
        allowed_fields = {
            "provider",
            "model",
            "api_key_env",
            "temperature",
            "max_tokens",
            "enabled",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = [*list(updates.values()), config_id]

        cursor = self.conn.cursor()
        # Columns are restricted to allowed_fields; values stay parameterized.
        query = f"UPDATE llm_config SET {set_clause} WHERE id = ?"  # nosec B608  # noqa: S608
        cursor.execute(query, values)
        self.conn.commit()

    def get_llm_cache_stats(self) -> dict[str, Any]:
        """Get LLM cache statistics.

        Returns:
            Dict with cache stats
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as n FROM llm_cache")
        total_cached = cursor.fetchone()["n"]

        cursor.execute("SELECT SUM(tokens_used) as n FROM llm_cache WHERE tokens_used IS NOT NULL")
        total_tokens = cursor.fetchone()["n"] or 0

        cursor.execute("""
            SELECT provider, COUNT(*) as count
            FROM llm_cache
            GROUP BY provider
        """)
        by_provider = {row["provider"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_cached": total_cached,
            "total_tokens_saved": total_tokens,
            "by_provider": by_provider,
        }

    def clear_llm_cache(self, older_than_days: int | None = None) -> int:
        """Clear LLM cache.

        Args:
            older_than_days: Only clear entries older than this many days (None = all)

        Returns:
            Number of entries cleared
        """
        cursor = self.conn.cursor()

        if older_than_days is None:
            cursor.execute("DELETE FROM llm_cache")
        else:
            cursor.execute(
                """
                DELETE FROM llm_cache
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """,
                (older_than_days,),
            )

        deleted = cursor.rowcount
        self.conn.commit()
        return deleted

    @staticmethod
    def _hash_content(content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _is_within(child: Path, parent: Path) -> bool:
    """True iff *child* lives at or beneath *parent* after resolution."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def get_default_db_path() -> Path:
    """Get default database path (~/.crumdbob/memory.db)."""
    return Path.home() / ".crumdbob" / "memory.db"


def init_database(db_path: str | Path | None = None) -> MemoryDatabase:
    """Initialize memory database with schema.

    Args:
        db_path: Optional database path (default: ~/.crumdbob/memory.db)

    Returns:
        Initialized MemoryDatabase instance
    """
    if db_path is None:
        db_path = get_default_db_path()

    db = MemoryDatabase(db_path)
    db.init_database()
    return db


def record_pack_to_db(
    pack_dir: str | Path,
    db_path: str | Path | None = None,
    session_name: str | None = None,
) -> int:
    """Record a pack directory to the database.

    Args:
        pack_dir: Path to pack directory
        db_path: Optional database path
        session_name: Optional custom session name

    Returns:
        Session ID
    """
    pack_path = Path(pack_dir)

    # Read proof chain once for all metadata
    proof_chain_path = pack_path / "08_proof_chain.json"
    proof_chain_hash = None
    crumdbob_version = __version__
    source_report_path = None

    if proof_chain_path.exists():
        try:
            raw_proof = proof_chain_path.read_text(encoding="utf-8")
            proof_data = json.loads(raw_proof)
            proof_chain_hash = MemoryDatabase._hash_content(raw_proof)
            crumdbob_version = proof_data.get("crumdbob_version", __version__)
            source_report_path = proof_data.get("source_report", {}).get("path")
        except (json.JSONDecodeError, OSError):
            pass

    if source_report_path:
        # Preserve historical behaviour: proof chains record paths relative to
        # the cwd that ran `crumdbob pack`. Try that first, then fall back to
        # paths relative to the pack itself. Apply a path-traversal guard so a
        # malicious proof chain can't point at /etc/passwd or arbitrary files
        # outside the pack's ancestor tree.
        raw_path = Path(source_report_path)
        candidates: list[Path] = []
        if raw_path.is_absolute():
            candidates.append(raw_path)
        else:
            candidates.extend(
                [
                    (Path.cwd() / raw_path),
                    (pack_path / raw_path),
                    (pack_path.parent / raw_path),
                ]
            )

        chosen: Path | None = None
        # Allow paths anywhere under cwd or under the pack's ancestor chain.
        cwd_resolved = Path.cwd().resolve()
        pack_resolved = pack_path.resolve()
        allowed_roots = {cwd_resolved, pack_resolved, pack_resolved.parent}
        for candidate in candidates:
            resolved = candidate.resolve()
            if not resolved.exists():
                continue
            if any(_is_within(resolved, root) for root in allowed_roots):
                chosen = resolved
                break
        source_report_path = chosen  # may be None if all candidates failed the guard

    if not source_report_path:
        # Try parent directory
        source_report_path = pack_path.parent / "bob-report.md"
        if not source_report_path.exists():
            raise FileNotFoundError(f"Could not find source bob-report.md for pack: {pack_dir}")

    # Parse report
    report = parse_bob_report(source_report_path)

    # Get Git context
    git_context = _get_git_context(pack_path)

    # Record to database
    if db_path is None:
        db_path = get_default_db_path()

    with MemoryDatabase(db_path) as db:
        # Always idempotent — CREATE TABLE IF NOT EXISTS means this is safe on existing DBs.
        db.init_database()

        session_id = db.record_session(
            report=report,
            pack_directory=pack_dir,
            session_name=session_name,
            git_context=git_context,
            proof_chain_hash=proof_chain_hash,
            crumdbob_version=crumdbob_version,
        )

        # Populate relationships from CRUMB dependency graph in the pack.
        if pack_path.is_dir():
            try:
                edges, _ = dependency_edges(pack_path)
                db.record_relationships(session_id, edges)
            except (OSError, ValueError):
                pass  # relationships are enrichment; never block a record

    return session_id


def _get_git_context(path: Path) -> dict[str, str]:
    """Extract Git context (branch, commit, author) from directory."""
    context: dict[str, str] = {}

    try:
        # Get branch
        result = subprocess.run(
            [GIT_EXECUTABLE, "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            context["branch"] = result.stdout.strip()

        # Get commit
        result = subprocess.run(
            [GIT_EXECUTABLE, "rev-parse", "HEAD"],
            cwd=path,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            context["commit"] = result.stdout.strip()[:12]

        # Get author
        result = subprocess.run(
            [GIT_EXECUTABLE, "config", "user.name"],
            cwd=path,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            context["author"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return context


# Made with Bob
