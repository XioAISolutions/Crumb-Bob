"""Prediction engine for CrumbBob memory database.

Predicts impact, risks, complexity, and recommends tests based on historical data.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Any

from .memory import MemoryDatabase
from .patterns import PatternDetector


@dataclass
class Prediction:
    """Represents a prediction result."""
    prediction_type: str
    target: str
    predictions: list[dict[str, Any]]
    confidence: float
    reasoning: str
    based_on: str


class PredictionEngine:
    """Predicts future outcomes based on historical patterns."""
    
    def __init__(self, db: MemoryDatabase):
        """Initialize prediction engine.
        
        Args:
            db: Memory database instance
        """
        self.db = db
        self.pattern_detector = PatternDetector(db)
    
    def predict_impact(self, file_path: str) -> Prediction:
        """Predict which files will be affected by changing a file.
        
        Args:
            file_path: Path to file being changed
            
        Returns:
            Prediction of impacted files
        """
        # Get files that historically change together
        relationships = self.pattern_detector.get_file_relationships(min_co_changes=1)
        
        # Find relationships involving this file
        related_files = []
        for rel in relationships:
            if rel.file1 == file_path:
                related_files.append({
                    "file": rel.file2,
                    "co_changes": rel.co_change_count,
                    "confidence": rel.confidence,
                })
            elif rel.file2 == file_path:
                related_files.append({
                    "file": rel.file1,
                    "co_changes": rel.co_change_count,
                    "confidence": rel.confidence,
                })
        
        # Sort by confidence
        related_files.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Calculate overall confidence
        if related_files:
            avg_confidence = sum(f["confidence"] for f in related_files) / len(related_files)
        else:
            avg_confidence = 0.0
        
        reasoning = f"Based on {len(related_files)} historical co-change patterns"
        if related_files:
            reasoning += f". Top related file: {related_files[0]['file']} ({related_files[0]['co_changes']} co-changes)"
        
        return Prediction(
            prediction_type="impact",
            target=file_path,
            predictions=related_files[:10],
            confidence=avg_confidence,
            reasoning=reasoning,
            based_on=f"{len(related_files)} file relationships",
        )
    
    def predict_risks(self, change_description: str) -> Prediction:
        """Predict risks for a planned change.
        
        Args:
            change_description: Description of planned change
            
        Returns:
            Prediction of potential risks
        """
        # Extract keywords from description
        keywords = self._extract_keywords(change_description)
        
        # Find similar past risks
        cursor = self.db.conn.cursor()
        
        similar_risks = []
        for keyword in keywords:
            cursor.execute("""
                SELECT DISTINCT r.description, COUNT(DISTINCT r.session_id) as frequency,
                       r.status, MAX(r.last_seen) as last_seen
                FROM risks r
                WHERE r.description LIKE ?
                GROUP BY r.description
                ORDER BY frequency DESC
                LIMIT 5
            """, (f"%{keyword}%",))
            
            for row in cursor.fetchall():
                similar_risks.append({
                    "risk": row["description"],
                    "frequency": row["frequency"],
                    "status": row["status"],
                    "last_seen": row["last_seen"],
                    "keyword": keyword,
                })
        
        # Remove duplicates and sort by frequency
        seen = set()
        unique_risks = []
        for risk in similar_risks:
            if risk["risk"] not in seen:
                seen.add(risk["risk"])
                unique_risks.append(risk)
        
        unique_risks.sort(key=lambda x: x["frequency"], reverse=True)
        
        # Calculate confidence based on keyword matches and frequency
        if unique_risks:
            max_frequency = max(r["frequency"] for r in unique_risks)
            confidence = min(0.9, 0.5 + (max_frequency * 0.1))
        else:
            confidence = 0.3
        
        reasoning = f"Based on {len(unique_risks)} similar past risks"
        if unique_risks:
            reasoning += f". Most common: '{unique_risks[0]['risk'][:50]}...' ({unique_risks[0]['frequency']}x)"
        
        return Prediction(
            prediction_type="risks",
            target=change_description,
            predictions=unique_risks[:10],
            confidence=confidence,
            reasoning=reasoning,
            based_on=f"{len(keywords)} keywords matched against historical risks",
        )
    
    def predict_complexity(self, task_description: str) -> Prediction:
        """Predict task complexity based on similar past tasks.
        
        Args:
            task_description: Description of task
            
        Returns:
            Prediction of task complexity
        """
        # Extract keywords
        keywords = self._extract_keywords(task_description)
        
        # Find similar past tasks
        cursor = self.db.conn.cursor()
        
        similar_tasks = []
        for keyword in keywords:
            cursor.execute("""
                SELECT t.description, t.status,
                       julianday(t.last_seen) - julianday(t.first_seen) as duration_days,
                       t.first_seen, t.last_seen
                FROM tasks t
                WHERE t.description LIKE ?
                AND duration_days > 0
                ORDER BY t.last_seen DESC
                LIMIT 10
            """, (f"%{keyword}%",))
            
            for row in cursor.fetchall():
                similar_tasks.append({
                    "task": row["description"],
                    "status": row["status"],
                    "duration_days": row["duration_days"],
                    "first_seen": row["first_seen"],
                    "last_seen": row["last_seen"],
                    "keyword": keyword,
                })
        
        # Calculate average duration
        if similar_tasks:
            completed_tasks = [t for t in similar_tasks if t["status"] == "completed"]
            
            if completed_tasks:
                avg_duration = sum(t["duration_days"] for t in completed_tasks) / len(completed_tasks)
                min_duration = min(t["duration_days"] for t in completed_tasks)
                max_duration = max(t["duration_days"] for t in completed_tasks)
                
                # Estimate range
                estimate_min = max(1, int(avg_duration * 0.7))
                estimate_max = int(avg_duration * 1.3)
                
                confidence = min(0.85, 0.5 + (len(completed_tasks) * 0.1))
                
                predictions = [{
                    "estimate_days": f"{estimate_min}-{estimate_max}",
                    "average_days": round(avg_duration, 1),
                    "min_days": round(min_duration, 1),
                    "max_days": round(max_duration, 1),
                    "similar_tasks_count": len(completed_tasks),
                }]
                
                reasoning = f"Based on {len(completed_tasks)} similar completed tasks"
            else:
                # No completed tasks, use in-progress tasks
                avg_duration = sum(t["duration_days"] for t in similar_tasks) / len(similar_tasks)
                
                predictions = [{
                    "estimate_days": f"{int(avg_duration)}-{int(avg_duration * 2)}",
                    "note": "Estimate based on in-progress tasks (less reliable)",
                    "similar_tasks_count": len(similar_tasks),
                }]
                
                confidence = 0.4
                reasoning = f"Based on {len(similar_tasks)} similar in-progress tasks (no completed tasks found)"
        else:
            # No similar tasks found
            predictions = [{
                "estimate_days": "3-7",
                "note": "Default estimate (no similar tasks found)",
            }]
            confidence = 0.2
            reasoning = "No similar historical tasks found, using default estimate"
        
        return Prediction(
            prediction_type="complexity",
            target=task_description,
            predictions=predictions,
            confidence=confidence,
            reasoning=reasoning,
            based_on=f"{len(similar_tasks)} similar tasks analyzed",
        )
    
    def recommend_tests(self, file_paths: list[str]) -> Prediction:
        """Recommend tests based on files being changed.
        
        Args:
            file_paths: List of file paths being changed
            
        Returns:
            Prediction of recommended tests
        """
        # Get all related files (files that change together)
        all_related = set()
        for file_path in file_paths:
            impact = self.predict_impact(file_path)
            for pred in impact.predictions:
                all_related.add(pred["file"])
        
        # Find test files in related files
        test_files = []
        test_patterns = ["test_", "_test.", "spec.", ".test.", "/tests/", "/test/"]
        
        for file_path in all_related:
            if any(pattern in file_path.lower() for pattern in test_patterns):
                test_files.append(file_path)
        
        # Also look for test files that historically appear with these files
        cursor = self.db.conn.cursor()
        
        test_recommendations = []
        for file_path in file_paths:
            cursor.execute("""
                SELECT f2.path, COUNT(DISTINCT f1.session_id) as co_occurrence
                FROM files f1
                JOIN files f2 ON f1.session_id = f2.session_id
                WHERE f1.path = ?
                AND (f2.path LIKE '%test%' OR f2.path LIKE '%spec%')
                GROUP BY f2.path
                ORDER BY co_occurrence DESC
                LIMIT 5
            """, (file_path,))
            
            for row in cursor.fetchall():
                test_recommendations.append({
                    "test_file": row["path"],
                    "co_occurrence": row["co_occurrence"],
                    "related_to": file_path,
                })
        
        # Combine and deduplicate
        all_tests = set(test_files)
        for rec in test_recommendations:
            all_tests.add(rec["test_file"])
        
        predictions = [
            {"test_file": test, "reason": "Historically changes with modified files"}
            for test in sorted(all_tests)
        ]
        
        # Add recommendations based on file types
        for file_path in file_paths:
            if file_path.endswith(".py"):
                test_name = file_path.replace(".py", "_test.py").replace("src/", "tests/")
                predictions.append({
                    "test_file": test_name,
                    "reason": "Conventional test file location",
                })
            elif file_path.endswith(".js") or file_path.endswith(".ts"):
                test_name = file_path.replace(".js", ".test.js").replace(".ts", ".test.ts")
                predictions.append({
                    "test_file": test_name,
                    "reason": "Conventional test file location",
                })
        
        confidence = min(0.8, 0.4 + (len(test_recommendations) * 0.1))
        
        reasoning = f"Based on {len(test_recommendations)} historical test patterns"
        if test_recommendations:
            reasoning += f" and {len(test_files)} related test files"
        
        return Prediction(
            prediction_type="tests",
            target=", ".join(file_paths),
            predictions=predictions[:15],
            confidence=confidence,
            reasoning=reasoning,
            based_on=f"{len(file_paths)} files analyzed",
        )
    
    def predict_session_metrics(self) -> Prediction:
        """Predict metrics for next session based on trends.
        
        Returns:
            Prediction of next session metrics
        """
        cursor = self.db.conn.cursor()
        
        # Get recent session metrics
        cursor.execute("""
            SELECT risk_count, file_count, command_count, task_count
            FROM sessions
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        recent_sessions = [dict(row) for row in cursor.fetchall()]
        
        if not recent_sessions:
            return Prediction(
                prediction_type="session_metrics",
                target="next_session",
                predictions=[],
                confidence=0.0,
                reasoning="No historical sessions to base prediction on",
                based_on="0 sessions",
            )
        
        # Calculate averages
        avg_risks = sum(s["risk_count"] for s in recent_sessions) / len(recent_sessions)
        avg_files = sum(s["file_count"] for s in recent_sessions) / len(recent_sessions)
        avg_commands = sum(s["command_count"] for s in recent_sessions) / len(recent_sessions)
        avg_tasks = sum(s["task_count"] for s in recent_sessions) / len(recent_sessions)
        
        predictions = [{
            "expected_risks": round(avg_risks, 1),
            "expected_files": round(avg_files, 1),
            "expected_commands": round(avg_commands, 1),
            "expected_tasks": round(avg_tasks, 1),
        }]
        
        confidence = min(0.75, 0.5 + (len(recent_sessions) * 0.05))
        
        return Prediction(
            prediction_type="session_metrics",
            target="next_session",
            predictions=predictions,
            confidence=confidence,
            reasoning=f"Based on average of last {len(recent_sessions)} sessions",
            based_on=f"{len(recent_sessions)} recent sessions",
        )
    
    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract meaningful keywords from text with basic stemming.

        Returns both the stemmed form and the original so that LIKE queries
        catch common variations (e.g. "authentication" -> also search "auth").
        """
        words = re.findall(r'\b\w+\b', text.lower())

        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "should", "could", "may", "might", "must", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
        }

        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Add stemmed variants for longer words so LIKE queries match more
        expanded: list[str] = []
        for kw in keywords:
            expanded.append(kw)
            for suffix in ("tion", "sion", "ment", "ness", "ing", "ity", "ous", "ive", "ed", "ly", "er", "es", "s"):
                if kw.endswith(suffix) and len(kw) - len(suffix) >= 3:
                    stem = kw[: -len(suffix)]
                    if stem not in expanded:
                        expanded.append(stem)
                    break

        return list(dict.fromkeys(expanded))[:15]


def create_prediction_engine(db: MemoryDatabase) -> PredictionEngine:
    """Create a prediction engine instance.
    
    Args:
        db: Memory database instance
        
    Returns:
        PredictionEngine instance
    """
    return PredictionEngine(db)

# Made with Bob
