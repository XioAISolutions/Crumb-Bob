"""Natural language query engine for CrumbBob memory database.

Translates natural language questions into SQL queries and provides
template-based queries for common use cases.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Literal

from .memory import MemoryDatabase


@dataclass
class QueryResult:
    """Result of a query execution."""
    query: str
    results: list[dict[str, Any]]
    row_count: int
    explanation: str


class QueryEngine:
    """Natural language query engine for memory database."""
    
    def __init__(self, db: MemoryDatabase):
        """Initialize query engine.
        
        Args:
            db: Memory database instance
        """
        self.db = db
        self._init_templates()
        self._init_patterns()
    
    def _init_templates(self) -> None:
        """Initialize query templates."""
        self.templates = {
            "risks-by-severity": """
                SELECT r.*, s.session_name, s.timestamp, s.git_branch
                FROM risks r
                JOIN sessions s ON r.session_id = s.id
                WHERE r.status = :status
                ORDER BY r.last_seen DESC
                LIMIT :limit
            """,
            "files-by-frequency": """
                SELECT path, session_count, total_mentions, first_seen, last_seen
                FROM file_history
                ORDER BY total_mentions DESC
                LIMIT :limit
            """,
            "tasks-by-status": """
                SELECT t.*, s.session_name, s.timestamp, s.git_branch
                FROM tasks t
                JOIN sessions s ON t.session_id = s.id
                WHERE t.status = :status
                ORDER BY t.last_seen DESC
                LIMIT :limit
            """,
            "commands-by-frequency": """
                SELECT command, session_count, total_mentions, first_seen, last_seen
                FROM command_frequency
                ORDER BY total_mentions DESC
                LIMIT :limit
            """,
            "sessions-by-author": """
                SELECT * FROM sessions
                WHERE git_author = :author
                ORDER BY timestamp DESC
                LIMIT :limit
            """,
            "sessions-by-branch": """
                SELECT * FROM sessions
                WHERE git_branch = :branch
                ORDER BY timestamp DESC
                LIMIT :limit
            """,
            "recent-sessions": """
                SELECT * FROM sessions
                ORDER BY timestamp DESC
                LIMIT :limit
            """,
            "hot-files": """
                SELECT path, session_count, total_mentions, first_seen, last_seen
                FROM file_history
                WHERE session_count >= :min_sessions
                ORDER BY session_count DESC, total_mentions DESC
                LIMIT :limit
            """,
            "recurring-risks": """
                SELECT description, status, session_count, first_seen, last_seen
                FROM risk_summary
                WHERE session_count >= :min_sessions
                ORDER BY session_count DESC, last_seen DESC
            """,
        }
    
    def _init_patterns(self) -> None:
        """Initialize natural language patterns."""
        self.patterns = [
            # Risk queries — allow optional filler words like "me", "the"
            (r"(?:show|find|get|list)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:auth|authentication)\s+risks?",
             lambda _m: self._search_risks_pattern("%auth%")),
            (r"(?:show|find|get|list)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:security|sec)\s+risks?",
             lambda _m: self._search_risks_pattern("%security%")),
            (r"(?:show|find|get|list)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:open|unresolved)\s+risks?",
             lambda _m: self._search_risks_by_status("open")),
            (r"(?:show|find|get|list)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?risks?",
             lambda _m: self._search_all_risks()),

            # File queries
            (r"(?:what|which)\s+files?\s+changed\s+(?:the\s+)?most(?:\s+in\s+(?:the\s+)?last\s+(\w+))?",
             lambda m: self._hot_files_query(self._parse_time_period(m.group(1) if m.lastindex else "month"))),
            (r"(?:show|find|get|list)\s+(?:all\s+)?files?\s+(?:matching|like|containing)\s+['\"]?(\S+)['\"]?",
             lambda m: self._search_files_pattern(f"%{m.group(1)}%")),
            (r"(?:show|find|get|list)\s+hot\s+files?",
             lambda _m: self._hot_files_query()),

            # Task queries
            (r"(?:which|what)\s+tasks?\s+(?:were\s+)?never\s+completed",
             lambda _m: self._tasks_by_status("pending")),
            (r"(?:show|find|get|list)\s+(?:all\s+)?(?:pending|incomplete)\s+tasks?",
             lambda _m: self._tasks_by_status("pending")),
            (r"(?:show|find|get|list)\s+(?:all\s+)?completed\s+tasks?",
             lambda _m: self._tasks_by_status("completed")),
            (r"(?:show|find|get|list)\s+(?:all\s+)?(?:in.progress|active)\s+tasks?",
             lambda _m: self._tasks_by_status("in_progress")),

            # Command queries
            (r"(?:what|which)\s+commands?\s+(?:are\s+)?(?:used\s+)?(?:the\s+)?most(?:\s+(?:frequently|often))?",
             lambda _m: self._command_frequency_query()),
            (r"(?:show|find|get|list)\s+(?:all\s+)?commands?",
             lambda _m: self._command_frequency_query()),

            # Session queries
            (r"(?:show|find|get|list)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?sessions?",
             lambda _m: self._recent_sessions_query()),
            (r"(?:show|find|get|list)\s+(?:all\s+)?(?:recent|latest)\s+sessions?",
             lambda _m: self._recent_sessions_query()),
            (r"(?:show|find|get|list)\s+sessions?\s+(?:by|from)\s+(\w+)",
             lambda m: self._sessions_by_author_query(m.group(1))),
            (r"(?:show|find|get|list)\s+sessions?\s+(?:on|in)\s+(?:branch\s+)?(\S+)",
             lambda m: self._sessions_by_branch_query(m.group(1))),
        ]

    def query_natural(self, question: str) -> QueryResult:
        """Translate natural language question to SQL and execute.

        Args:
            question: Natural language question

        Returns:
            QueryResult with results and explanation
        """
        question_lower = question.lower().strip()

        # Every handler now accepts match — always pass it
        for pattern, handler in self.patterns:
            match = re.search(pattern, question_lower)
            if match:
                return handler(match)
        
        # No pattern matched
        return QueryResult(
            query="",
            results=[],
            row_count=0,
            explanation=f"Could not understand query: '{question}'. Try rephrasing or use a template query."
        )
    
    def query_template(self, template: str, **params: Any) -> QueryResult:
        """Execute a template query with parameters.
        
        Args:
            template: Template name
            **params: Template parameters
            
        Returns:
            QueryResult with results
        """
        if template not in self.templates:
            return QueryResult(
                query="",
                results=[],
                row_count=0,
                explanation=f"Unknown template: {template}. Available: {', '.join(self.templates.keys())}"
            )
        
        # Set default parameters
        defaults = {"limit": 20, "status": "open", "min_sessions": 2}
        query_params = {**defaults, **params}
        
        query = self.templates[template]
        cursor = self.db.conn.cursor()
        cursor.execute(query, query_params)
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=query.strip(),
            results=results,
            row_count=len(results),
            explanation=f"Template query '{template}' with params: {query_params}"
        )
    
    # Disallow any statement that could mutate the database — query_sql is a
    # read-only escape hatch for analysts, not a way to DROP TABLE.
    _FORBIDDEN_SQL_KEYWORDS = (
        "insert", "update", "delete", "drop", "alter", "create",
        "replace", "attach", "detach", "pragma", "vacuum", "truncate",
    )

    def query_sql(self, sql: str) -> QueryResult:
        """Execute a read-only SQL query.

        Statements containing any DDL/DML keywords are rejected up front and
        the connection is queried via a read-only cursor pattern (SELECT only).
        """
        normalized = sql.strip().lower()
        if not normalized:
            return QueryResult(query=sql, results=[], row_count=0,
                               explanation="SQL error: empty query")
        # Detect multiple statements (semicolons inside identifiers are rare here).
        if ";" in normalized.rstrip(";").strip():
            return QueryResult(query=sql, results=[], row_count=0,
                               explanation="SQL error: multiple statements not allowed")
        for keyword in self._FORBIDDEN_SQL_KEYWORDS:
            if re.search(rf"\b{keyword}\b", normalized):
                return QueryResult(query=sql, results=[], row_count=0,
                                   explanation=f"SQL error: '{keyword}' is not permitted (read-only mode)")

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(sql)
            results = [dict(row) for row in cursor.fetchall()]
            return QueryResult(
                query=sql,
                results=results,
                row_count=len(results),
                explanation="Direct SQL query executed"
            )
        except sqlite3.Error as e:
            return QueryResult(
                query=sql,
                results=[],
                row_count=0,
                explanation=f"SQL error: {e}"
            )
    
    def list_templates(self) -> list[str]:
        """List available query templates.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())
    
    # Helper methods for pattern handlers
    
    def _search_risks_pattern(self, pattern: str) -> QueryResult:
        """Search risks by description pattern."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT r.*, s.session_name, s.timestamp, s.git_branch
            FROM risks r
            JOIN sessions s ON r.session_id = s.id
            WHERE r.description LIKE ?
            ORDER BY r.last_seen DESC
            LIMIT 50
        """, (pattern,))
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=f"SELECT risks WHERE description LIKE '{pattern}'",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} risks matching pattern '{pattern}'"
        )
    
    def _search_risks_by_status(self, status: str) -> QueryResult:
        """Search risks by status."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT r.*, s.session_name, s.timestamp, s.git_branch
            FROM risks r
            JOIN sessions s ON r.session_id = s.id
            WHERE r.status = ?
            ORDER BY r.last_seen DESC
            LIMIT 50
        """, (status,))
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=f"SELECT risks WHERE status = '{status}'",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} {status} risks"
        )
    
    def _search_all_risks(self) -> QueryResult:
        """Get all risks."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT r.*, s.session_name, s.timestamp, s.git_branch
            FROM risks r
            JOIN sessions s ON r.session_id = s.id
            ORDER BY r.last_seen DESC
            LIMIT 100
        """)
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query="SELECT all risks",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} total risks"
        )
    
    def _hot_files_query(self, days: int = 30) -> QueryResult:
        """Get hot files (frequently changed)."""
        results = self.db.get_hot_files(min_sessions=2, limit=20)
        
        return QueryResult(
            query="SELECT hot files",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} files changed across multiple sessions"
        )
    
    def _search_files_pattern(self, pattern: str) -> QueryResult:
        """Search files by path pattern."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM files
            WHERE path LIKE ?
            ORDER BY last_seen DESC
            LIMIT 50
        """, (pattern,))
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=f"SELECT files WHERE path LIKE '{pattern}'",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} files matching pattern '{pattern}'"
        )
    
    def _tasks_by_status(self, status: str) -> QueryResult:
        """Get tasks by status."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT t.*, s.session_name, s.timestamp, s.git_branch
            FROM tasks t
            JOIN sessions s ON t.session_id = s.id
            WHERE t.status = ?
            ORDER BY t.last_seen DESC
            LIMIT 50
        """, (status,))
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=f"SELECT tasks WHERE status = '{status}'",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} {status} tasks"
        )
    
    def _command_frequency_query(self) -> QueryResult:
        """Get command frequency."""
        results = self.db.get_command_frequency(limit=20)
        
        return QueryResult(
            query="SELECT command frequency",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} most frequently used commands"
        )
    
    def _recent_sessions_query(self, limit: int = 10) -> QueryResult:
        """Get recent sessions."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=f"SELECT recent sessions LIMIT {limit}",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} recent sessions"
        )
    
    def _sessions_by_author_query(self, author: str) -> QueryResult:
        """Get sessions by author."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions
            WHERE git_author LIKE ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (f"%{author}%",))
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=f"SELECT sessions WHERE author LIKE '%{author}%'",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} sessions by author matching '{author}'"
        )
    
    def _sessions_by_branch_query(self, branch: str) -> QueryResult:
        """Get sessions by branch."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions
            WHERE git_branch = ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (branch,))
        results = [dict(row) for row in cursor.fetchall()]
        
        return QueryResult(
            query=f"SELECT sessions WHERE branch = '{branch}'",
            results=results,
            row_count=len(results),
            explanation=f"Found {len(results)} sessions on branch '{branch}'"
        )
    
    @staticmethod
    def _parse_time_period(period: str | None) -> int:
        """Parse time period to days."""
        if not period:
            return 30
        
        period_lower = period.lower()
        if "week" in period_lower:
            return 7
        elif "month" in period_lower:
            return 30
        elif "year" in period_lower:
            return 365
        elif "day" in period_lower:
            return 1
        
        return 30


def create_query_engine(db: MemoryDatabase) -> QueryEngine:
    """Create a query engine instance.
    
    Args:
        db: Memory database instance
        
    Returns:
        QueryEngine instance
    """
    return QueryEngine(db)

# Made with Bob
