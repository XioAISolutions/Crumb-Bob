"""Pattern detection engine for CrumbBob memory database.

Detects recurring patterns, relationships, and anomalies across sessions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .memory import MemoryDatabase


@dataclass
class Pattern:
    """Represents a detected pattern."""

    id: str
    pattern_type: str
    description: str
    confidence: float
    evidence: list[dict[str, Any]]
    first_seen: str
    last_seen: str
    frequency: int
    severity: str  # low, medium, high, critical


@dataclass
class FileRelationship:
    """Represents files that change together."""

    file1: str
    file2: str
    co_change_count: int
    confidence: float
    sessions: list[int]


class PatternDetector:
    """Detects patterns across sessions in memory database."""

    def __init__(self, db: MemoryDatabase):
        """Initialize pattern detector.

        Args:
            db: Memory database instance
        """
        self.db = db

    def detect_all(self) -> list[Pattern]:
        """Run all pattern detectors.

        Returns:
            List of detected patterns
        """
        patterns = []
        patterns.extend(self.detect_recurring_risks())
        patterns.extend(self.detect_file_relationships())
        patterns.extend(self.detect_task_patterns())
        patterns.extend(self.detect_command_patterns())
        patterns.extend(self.detect_anomalies())

        return patterns

    def detect_recurring_risks(self, min_occurrences: int = 2) -> list[Pattern]:
        """Detect risks that appear across multiple sessions.

        Args:
            min_occurrences: Minimum number of sessions for a risk to be considered recurring

        Returns:
            List of recurring risk patterns
        """
        patterns = []

        # Get recurring risks from database
        recurring = self.db.get_recurring_risks(min_sessions=min_occurrences)

        for risk in recurring:
            # Calculate severity based on frequency
            session_count = risk["session_count"]
            if session_count >= 5:
                severity = "critical"
            elif session_count >= 3:
                severity = "high"
            elif session_count >= 2:
                severity = "medium"
            else:
                severity = "low"

            # Get evidence (sessions where this risk appeared)
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT r.session_id, s.timestamp, s.session_name, s.git_branch
                FROM risks r
                JOIN sessions s ON r.session_id = s.id
                WHERE r.description = ?
                ORDER BY s.timestamp DESC
            """,
                (risk["description"],),
            )
            evidence = [dict(row) for row in cursor.fetchall()]

            pattern = Pattern(
                id=f"recurring_risk_{hash(risk['description']) % 10000}",
                pattern_type="recurring_risk",
                description=f"Risk appears in {session_count} sessions: {risk['description'][:100]}",
                confidence=min(0.9, 0.5 + (session_count * 0.1)),
                evidence=evidence,
                first_seen=risk["first_seen"],
                last_seen=risk["last_seen"],
                frequency=session_count,
                severity=severity,
            )
            patterns.append(pattern)

        return patterns

    def _compute_co_changes(self) -> dict[tuple[str, str], list[int]]:
        """Compute file co-change pairs across all sessions."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT session_id, path
            FROM files
            ORDER BY session_id, path
        """)

        session_files: dict[int, set[str]] = defaultdict(set)
        for row in cursor.fetchall():
            session_files[row["session_id"]].add(row["path"])

        co_changes: dict[tuple[str, str], list[int]] = defaultdict(list)
        for session_id, files in session_files.items():
            file_list = sorted(files)
            for i, file1 in enumerate(file_list):
                for file2 in file_list[i + 1 :]:
                    co_changes[(file1, file2)].append(session_id)

        return co_changes

    def detect_file_relationships(self, min_co_changes: int = 2) -> list[Pattern]:
        """Detect files that always change together.

        Args:
            min_co_changes: Minimum number of co-changes to consider a relationship

        Returns:
            List of file relationship patterns
        """
        patterns = []
        co_changes = self._compute_co_changes()

        for (file1, file2), sessions in co_changes.items():
            if len(sessions) >= min_co_changes:
                confidence = min(0.95, len(sessions) / 10.0)

                if len(sessions) >= 5:
                    severity = "high"
                elif len(sessions) >= 3:
                    severity = "medium"
                else:
                    severity = "low"

                pattern = Pattern(
                    id=f"file_coupling_{hash((file1, file2)) % 10000}",
                    pattern_type="file_coupling",
                    description=f"Files always change together: {file1} ↔ {file2}",
                    confidence=confidence,
                    evidence=[{"file1": file1, "file2": file2, "sessions": sessions}],
                    first_seen="",
                    last_seen="",
                    frequency=len(sessions),
                    severity=severity,
                )
                patterns.append(pattern)

        return patterns

    def detect_task_patterns(self) -> list[Pattern]:
        """Detect patterns in task completion.

        Returns:
            List of task-related patterns
        """
        patterns = []

        # Find tasks that are never completed
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT description, COUNT(DISTINCT session_id) as occurrence_count,
                   MIN(first_seen) as first_seen, MAX(last_seen) as last_seen
            FROM tasks
            WHERE status != 'completed'
            GROUP BY description
            HAVING occurrence_count >= 2
            ORDER BY occurrence_count DESC
        """)

        for row in cursor.fetchall():
            occurrence_count = row["occurrence_count"]

            # High severity if task appears many times without completion
            if occurrence_count >= 5:
                severity = "critical"
            elif occurrence_count >= 3:
                severity = "high"
            else:
                severity = "medium"

            pattern = Pattern(
                id=f"abandoned_task_{hash(row['description']) % 10000}",
                pattern_type="abandoned_task",
                description=f"Task never completed ({occurrence_count}x): {row['description'][:100]}",
                confidence=min(0.9, 0.6 + (occurrence_count * 0.1)),
                evidence=[dict(row)],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                frequency=occurrence_count,
                severity=severity,
            )
            patterns.append(pattern)

        # Find tasks that take unusually long
        cursor.execute("""
            SELECT t.description,
                   julianday(t.last_seen) - julianday(t.first_seen) as duration_days,
                   t.status, t.first_seen, t.last_seen
            FROM tasks t
            WHERE duration_days > 7 AND t.status = 'in_progress'
            ORDER BY duration_days DESC
            LIMIT 10
        """)

        for row in cursor.fetchall():
            duration = row["duration_days"]

            if duration >= 30:
                severity = "high"
            elif duration >= 14:
                severity = "medium"
            else:
                severity = "low"

            pattern = Pattern(
                id=f"long_task_{hash(row['description']) % 10000}",
                pattern_type="long_running_task",
                description=f"Task in progress for {int(duration)} days: {row['description'][:100]}",
                confidence=0.8,
                evidence=[dict(row)],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                frequency=1,
                severity=severity,
            )
            patterns.append(pattern)

        return patterns

    def detect_command_patterns(self) -> list[Pattern]:
        """Detect patterns in command usage.

        Returns:
            List of command-related patterns
        """
        patterns = []

        # Find most frequently used commands
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT command, session_count, total_mentions
            FROM command_frequency
            WHERE total_mentions >= 5
            ORDER BY total_mentions DESC
            LIMIT 10
        """)

        for row in cursor.fetchall():
            total_mentions = row["total_mentions"]

            pattern = Pattern(
                id=f"frequent_command_{hash(row['command']) % 10000}",
                pattern_type="frequent_command",
                description=f"Frequently used command ({total_mentions}x): {row['command'][:100]}",
                confidence=0.9,
                evidence=[dict(row)],
                first_seen="",
                last_seen="",
                frequency=total_mentions,
                severity="low",
            )
            patterns.append(pattern)

        # Detect command sequences (commands that often appear together)
        cursor.execute("""
            SELECT c1.command as cmd1, c2.command as cmd2,
                   COUNT(DISTINCT c1.session_id) as co_occurrence
            FROM commands c1
            JOIN commands c2 ON c1.session_id = c2.session_id AND c1.command < c2.command
            GROUP BY c1.command, c2.command
            HAVING co_occurrence >= 3
            ORDER BY co_occurrence DESC
            LIMIT 10
        """)

        for row in cursor.fetchall():
            co_occurrence = row["co_occurrence"]

            pattern = Pattern(
                id=f"command_sequence_{hash((row['cmd1'], row['cmd2'])) % 10000}",
                pattern_type="command_sequence",
                description=f"Commands often used together ({co_occurrence}x): {row['cmd1'][:50]} → {row['cmd2'][:50]}",
                confidence=min(0.9, 0.5 + (co_occurrence * 0.1)),
                evidence=[dict(row)],
                first_seen="",
                last_seen="",
                frequency=co_occurrence,
                severity="low",
            )
            patterns.append(pattern)

        return patterns

    def detect_anomalies(self) -> list[Pattern]:
        """Detect anomalous patterns in sessions.

        Returns:
            List of anomaly patterns
        """
        patterns: list[Pattern] = []

        # Get session statistics
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT AVG(risk_count) as avg_risks,
                   AVG(file_count) as avg_files,
                   AVG(command_count) as avg_commands
            FROM sessions
        """)
        stats = cursor.fetchone()

        if not stats:
            return patterns

        avg_risks = stats["avg_risks"] or 0
        avg_files = stats["avg_files"] or 0

        # Find sessions with unusually high risk counts
        cursor.execute(
            """
            SELECT id, timestamp, session_name, risk_count, file_count, command_count
            FROM sessions
            WHERE risk_count > ?
            ORDER BY risk_count DESC
            LIMIT 5
        """,
            (avg_risks * 2,),
        )

        for row in cursor.fetchall():
            pattern = Pattern(
                id=f"high_risk_session_{row['id']}",
                pattern_type="anomaly_high_risks",
                description=f"Session with unusually high risk count ({row['risk_count']} vs avg {avg_risks:.1f})",
                confidence=0.8,
                evidence=[dict(row)],
                first_seen=row["timestamp"],
                last_seen=row["timestamp"],
                frequency=1,
                severity="high",
            )
            patterns.append(pattern)

        # Find sessions with unusually high file counts
        cursor.execute(
            """
            SELECT id, timestamp, session_name, file_count
            FROM sessions
            WHERE file_count > ?
            ORDER BY file_count DESC
            LIMIT 5
        """,
            (avg_files * 2,),
        )

        for row in cursor.fetchall():
            pattern = Pattern(
                id=f"high_file_session_{row['id']}",
                pattern_type="anomaly_high_files",
                description=f"Session touched unusually many files ({row['file_count']} vs avg {avg_files:.1f})",
                confidence=0.7,
                evidence=[dict(row)],
                first_seen=row["timestamp"],
                last_seen=row["timestamp"],
                frequency=1,
                severity="medium",
            )
            patterns.append(pattern)

        return patterns

    def get_file_relationships(self, min_co_changes: int = 2) -> list[FileRelationship]:
        """Get detailed file relationship information.

        Args:
            min_co_changes: Minimum number of co-changes

        Returns:
            List of FileRelationship objects
        """
        co_changes = self._compute_co_changes()
        relationships = []

        for (file1, file2), sessions in co_changes.items():
            if len(sessions) >= min_co_changes:
                confidence = min(0.95, len(sessions) / 10.0)
                relationships.append(
                    FileRelationship(
                        file1=file1,
                        file2=file2,
                        co_change_count=len(sessions),
                        confidence=confidence,
                        sessions=sessions,
                    )
                )

        return sorted(relationships, key=lambda r: r.co_change_count, reverse=True)

    def analyze_file(self, file_path: str) -> dict[str, Any]:
        """Analyze patterns for a specific file.

        Args:
            file_path: Path to file

        Returns:
            Analysis results
        """
        cursor = self.db.conn.cursor()

        # Get file statistics
        cursor.execute(
            """
            SELECT COUNT(DISTINCT session_id) as session_count,
                   SUM(mention_count) as total_mentions,
                   MIN(first_seen) as first_seen,
                   MAX(last_seen) as last_seen
            FROM files
            WHERE path = ?
        """,
            (file_path,),
        )

        stats = cursor.fetchone()

        if not stats or stats["session_count"] == 0:
            return {
                "file_path": file_path,
                "found": False,
                "message": "File not found in any session",
            }

        # Get related files (files that change together)
        relationships: list[dict[str, Any]] = []
        for rel in self.get_file_relationships(min_co_changes=1):
            if file_path in (rel.file1, rel.file2):
                other_file = rel.file2 if rel.file1 == file_path else rel.file1
                relationships.append(
                    {
                        "file": other_file,
                        "co_changes": rel.co_change_count,
                        "confidence": rel.confidence,
                    }
                )

        # Get sessions where file appeared
        cursor.execute(
            """
            SELECT s.id, s.timestamp, s.session_name, s.git_branch
            FROM files f
            JOIN sessions s ON f.session_id = s.id
            WHERE f.path = ?
            ORDER BY s.timestamp DESC
        """,
            (file_path,),
        )

        sessions = [dict(row) for row in cursor.fetchall()]

        return {
            "file_path": file_path,
            "found": True,
            "session_count": stats["session_count"],
            "total_mentions": stats["total_mentions"],
            "first_seen": stats["first_seen"],
            "last_seen": stats["last_seen"],
            "related_files": sorted(
                relationships, key=lambda r: int(r["co_changes"]), reverse=True
            )[:10],
            "sessions": sessions,
        }


def create_pattern_detector(db: MemoryDatabase) -> PatternDetector:
    """Create a pattern detector instance.

    Args:
        db: Memory database instance

    Returns:
        PatternDetector instance
    """
    return PatternDetector(db)


# Made with Bob
