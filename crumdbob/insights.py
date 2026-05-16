"""Insights engine for CrumbBob memory database.

Automatically generates actionable insights from detected patterns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .memory import MemoryDatabase
from .patterns import Pattern, PatternDetector


@dataclass
class Insight:
    """Represents an actionable insight."""

    id: int | None
    insight_type: str
    title: str
    description: str
    severity: str  # low, medium, high, critical
    confidence: float
    evidence: list[dict[str, Any]]
    recommendations: list[str]
    created_at: str
    session_id: int | None = None


class InsightsEngine:
    """Generates and manages insights from patterns."""

    def __init__(self, db: MemoryDatabase):
        """Initialize insights engine.

        Args:
            db: Memory database instance
        """
        self.db = db
        self.pattern_detector = PatternDetector(db)

    def generate_insights(self) -> list[Insight]:
        """Generate all insights from current database state.

        Returns:
            List of generated insights
        """
        insights = []

        # Detect patterns
        patterns = self.pattern_detector.detect_all()

        # Convert patterns to insights
        for pattern in patterns:
            insight = self._pattern_to_insight(pattern)
            if insight:
                insights.append(insight)

        # Generate trend insights
        insights.extend(self._generate_trend_insights())

        # Generate health insights
        insights.extend(self._generate_health_insights())

        # Store insights in database
        for insight in insights:
            self._store_insight(insight)

        return insights

    def get_insights(
        self,
        category: str | None = None,
        limit: int = 50,
        min_severity: str | None = None,
    ) -> list[Insight]:
        """Retrieve insights from database.

        Args:
            category: Filter by insight type
            limit: Maximum number of insights
            min_severity: Minimum severity level

        Returns:
            List of insights
        """
        cursor = self.db.conn.cursor()

        query = "SELECT * FROM insights WHERE 1=1"
        params: list[Any] = []

        if category:
            query += " AND insight_type = ?"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        insights = []
        for row in cursor.fetchall():
            content = json.loads(row["content"])

            insight = Insight(
                id=row["id"],
                insight_type=row["insight_type"],
                title=content.get("title", ""),
                description=content.get("description", ""),
                severity=content.get("severity", "low"),
                confidence=row["confidence"] or 0.0,
                evidence=content.get("evidence", []),
                recommendations=content.get("recommendations", []),
                created_at=row["created_at"],
                session_id=row["session_id"],
            )
            insights.append(insight)

        # Filter by severity if specified
        if min_severity:
            severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            min_level = severity_order.get(min_severity, 0)
            insights = [i for i in insights if severity_order.get(i.severity, 0) >= min_level]

        return insights

    def get_top_insights(self, n: int = 10) -> list[Insight]:
        """Get top N most important insights.

        Args:
            n: Number of insights to return

        Returns:
            List of top insights
        """
        insights = self.get_insights(limit=100)

        # Score insights by severity and confidence
        severity_scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        scored = [(i, severity_scores.get(i.severity, 1) * i.confidence) for i in insights]

        scored.sort(key=lambda x: x[1], reverse=True)

        return [insight for insight, _ in scored[:n]]

    def get_actionable_insights(self) -> list[Insight]:
        """Get insights that require action.

        Returns:
            List of actionable insights
        """
        insights = self.get_insights(limit=100)

        # Filter for high severity or high confidence
        return [i for i in insights if i.severity in ("high", "critical") or i.confidence >= 0.8]

    def _pattern_to_insight(self, pattern: Pattern) -> Insight | None:
        """Convert a pattern to an insight.

        Args:
            pattern: Detected pattern

        Returns:
            Insight or None
        """
        recommendations = []

        if pattern.pattern_type == "recurring_risk":
            recommendations = [
                "Review and address this recurring risk",
                "Add mitigation steps to your workflow",
                "Consider creating a checklist to prevent this risk",
                "Document the root cause and solution",
            ]

        elif pattern.pattern_type == "file_coupling":
            recommendations = [
                "Consider refactoring to reduce coupling",
                "Review architectural boundaries",
                "Add integration tests for these files",
                "Document the relationship between these files",
            ]

        elif pattern.pattern_type == "abandoned_task":
            recommendations = [
                "Break down this task into smaller steps",
                "Reassess task priority and feasibility",
                "Consider if this task is still relevant",
                "Assign clear ownership and deadline",
            ]

        elif pattern.pattern_type == "long_running_task":
            recommendations = [
                "Review task progress and blockers",
                "Consider breaking into smaller tasks",
                "Set intermediate milestones",
                "Reassess scope and requirements",
            ]

        elif pattern.pattern_type == "frequent_command":
            recommendations = [
                "Consider creating an alias or script",
                "Add this to your automation workflow",
                "Document this command for team members",
            ]

        elif pattern.pattern_type == "command_sequence":
            recommendations = [
                "Create a script to automate this sequence",
                "Add to your CI/CD pipeline",
                "Document this workflow",
            ]

        elif pattern.pattern_type.startswith("anomaly_"):
            recommendations = [
                "Investigate the cause of this anomaly",
                "Review session details for unusual activity",
                "Consider if this indicates a problem",
            ]

        else:
            recommendations = ["Review this pattern for potential action"]

        return Insight(
            id=None,
            insight_type=pattern.pattern_type,
            title=pattern.description,
            description=pattern.description,
            severity=pattern.severity,
            confidence=pattern.confidence,
            evidence=pattern.evidence,
            recommendations=recommendations,
            created_at=datetime.now(timezone.utc).isoformat(),
            session_id=None,
        )

    def _generate_trend_insights(self) -> list[Insight]:
        """Generate insights about trends over time.

        Returns:
            List of trend insights
        """
        insights = []
        cursor = self.db.conn.cursor()

        # Risk trend
        cursor.execute("""
            SELECT
                DATE(timestamp) as date,
                AVG(risk_count) as avg_risks
            FROM sessions
            WHERE timestamp >= date('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """)

        risk_data = [dict(row) for row in cursor.fetchall()]

        if len(risk_data) >= 7:
            # Calculate trend
            recent_avg = sum(r["avg_risks"] for r in risk_data[-7:]) / 7
            older_avg = sum(r["avg_risks"] for r in risk_data[:7]) / 7

            if older_avg > 0 and recent_avg > older_avg * 1.2:
                insights.append(
                    Insight(
                        id=None,
                        insight_type="trend_risk_increase",
                        title="Risk count increasing",
                        description=f"Average risks per session increased {((recent_avg / older_avg - 1) * 100):.1f}% over last 30 days",
                        severity="high",
                        confidence=0.85,
                        evidence=[{"recent_avg": recent_avg, "older_avg": older_avg}],
                        recommendations=[
                            "Review recent changes for quality issues",
                            "Increase code review rigor",
                            "Add more automated testing",
                            "Consider technical debt sprint",
                        ],
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
            elif older_avg > 0 and recent_avg < older_avg * 0.8:
                insights.append(
                    Insight(
                        id=None,
                        insight_type="trend_risk_decrease",
                        title="Risk count decreasing",
                        description=f"Average risks per session decreased {((1 - recent_avg / older_avg) * 100):.1f}% over last 30 days",
                        severity="low",
                        confidence=0.85,
                        evidence=[{"recent_avg": recent_avg, "older_avg": older_avg}],
                        recommendations=[
                            "Document what's working well",
                            "Share best practices with team",
                            "Continue current quality practices",
                        ],
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

        # File churn trend
        cursor.execute("""
            SELECT COUNT(DISTINCT path) as unique_files
            FROM files
            WHERE last_seen >= date('now', '-7 days')
        """)
        recent_files = cursor.fetchone()["unique_files"]

        cursor.execute("""
            SELECT COUNT(DISTINCT path) as unique_files
            FROM files
            WHERE last_seen >= date('now', '-30 days')
            AND last_seen < date('now', '-7 days')
        """)
        older_files = cursor.fetchone()["unique_files"]

        if older_files > 0 and recent_files > older_files * 1.5:
            insights.append(
                Insight(
                    id=None,
                    insight_type="trend_high_churn",
                    title="High file churn detected",
                    description=f"File change rate increased significantly: {recent_files} files in last week vs {older_files} in previous weeks",
                    severity="medium",
                    confidence=0.75,
                    evidence=[{"recent_files": recent_files, "older_files": older_files}],
                    recommendations=[
                        "Review if changes are focused or scattered",
                        "Consider if refactoring is needed",
                        "Ensure adequate test coverage",
                    ],
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        return insights

    def _generate_health_insights(self) -> list[Insight]:
        """Generate insights about overall project health.

        Returns:
            List of health insights
        """
        insights = []
        cursor = self.db.conn.cursor()

        # Check open risk ratio
        cursor.execute("""
            SELECT
                COUNT(*) as total_risks,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_risks
            FROM risks
        """)

        risk_stats = cursor.fetchone()
        total_risks = risk_stats["total_risks"]
        open_risks = risk_stats["open_risks"]

        if total_risks > 0:
            open_ratio = open_risks / total_risks

            if open_ratio > 0.8:
                insights.append(
                    Insight(
                        id=None,
                        insight_type="health_high_open_risks",
                        title="High percentage of open risks",
                        description=f"{open_ratio * 100:.1f}% of risks are still open ({open_risks}/{total_risks})",
                        severity="high",
                        confidence=0.9,
                        evidence=[{"open_risks": open_risks, "total_risks": total_risks}],
                        recommendations=[
                            "Prioritize risk mitigation",
                            "Review and close resolved risks",
                            "Create action plan for open risks",
                            "Consider risk review meeting",
                        ],
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

        # Check task completion rate
        cursor.execute("""
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
            FROM tasks
        """)

        task_stats = cursor.fetchone()
        total_tasks = task_stats["total_tasks"]
        completed_tasks = task_stats["completed_tasks"]

        if total_tasks > 0:
            completion_rate = completed_tasks / total_tasks

            if completion_rate < 0.3:
                insights.append(
                    Insight(
                        id=None,
                        insight_type="health_low_completion",
                        title="Low task completion rate",
                        description=f"Only {completion_rate * 100:.1f}% of tasks completed ({completed_tasks}/{total_tasks})",
                        severity="medium",
                        confidence=0.85,
                        evidence=[{"completed_tasks": completed_tasks, "total_tasks": total_tasks}],
                        recommendations=[
                            "Review task backlog and priorities",
                            "Break down large tasks",
                            "Remove obsolete tasks",
                            "Set realistic task scopes",
                        ],
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

        # Check session frequency
        cursor.execute("""
            SELECT COUNT(*) as session_count
            FROM sessions
            WHERE timestamp >= date('now', '-7 days')
        """)

        recent_sessions = cursor.fetchone()["session_count"]

        if recent_sessions == 0:
            insights.append(
                Insight(
                    id=None,
                    insight_type="health_no_activity",
                    title="No recent activity",
                    description="No sessions recorded in the last 7 days",
                    severity="low",
                    confidence=0.9,
                    evidence=[{"recent_sessions": 0}],
                    recommendations=[
                        "Ensure CrumbBob is being used",
                        "Check if team needs training",
                        "Review integration setup",
                    ],
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        return insights

    def _store_insight(self, insight: Insight) -> None:
        """Store insight in database, skipping duplicates by type + title."""
        cursor = self.db.conn.cursor()

        # Skip if an identical insight already exists. We escape LIKE wildcards
        # in the title so backslashes, percent signs, and underscores match
        # literally instead of acting as patterns.
        safe_title = insight.title.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cursor.execute(
            "SELECT id FROM insights WHERE insight_type = ? AND content LIKE ? ESCAPE '\\'",
            (insight.insight_type, f'%"title": "{safe_title}"%'),
        )
        if cursor.fetchone():
            return

        content = {
            "title": insight.title,
            "description": insight.description,
            "severity": insight.severity,
            "evidence": insight.evidence,
            "recommendations": insight.recommendations,
        }

        cursor.execute(
            """
            INSERT INTO insights (session_id, insight_type, content, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                insight.session_id,
                insight.insight_type,
                json.dumps(content),
                insight.confidence,
                insight.created_at,
            ),
        )

        self.db.conn.commit()


def create_insights_engine(db: MemoryDatabase) -> InsightsEngine:
    """Create an insights engine instance.

    Args:
        db: Memory database instance

    Returns:
        InsightsEngine instance
    """
    return InsightsEngine(db)


# Made with Bob
