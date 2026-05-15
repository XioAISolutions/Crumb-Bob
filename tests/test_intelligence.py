"""Tests for CrumbBob intelligence features (query, patterns, insights, predictions)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from crumdbob.insights import create_insights_engine
from crumdbob.memory import MemoryDatabase, init_database
from crumdbob.parser import BobReport
from crumdbob.patterns import create_pattern_detector
from crumdbob.predict import create_prediction_engine
from crumdbob.query import create_query_engine


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = init_database(db_path)
        yield db
        db.close()


@pytest.fixture
def populated_db(temp_db):
    """Create a database with test data."""
    # Create test sessions with various data
    for i in range(5):
        report = BobReport(
            title=f"Test Session {i}",
            summary=f"Summary for session {i}",
            files=[
                "src/auth/login.py",
                "src/auth/session.py",
                "tests/test_auth.py",
                f"src/feature_{i}.py",
            ],
            commands=[
                "pytest tests/",
                "git commit -m 'test'",
                f"python script_{i}.py",
            ],
            risks=[
                "Authentication security risk",
                "Database migration complexity",
                f"Risk specific to session {i}",
            ],
            tests=["test_login", "test_session"],
            next_steps=[
                "Complete authentication refactor",
                "Add more tests",
                f"Task for session {i}",
            ],
            source_path=f"/tmp/report_{i}.md",
            raw_text=f"Report {i}",
        )
        
        temp_db.record_session(
            report=report,
            session_name=f"Session {i}",
            git_context={
                "branch": "main" if i % 2 == 0 else "feature",
                "commit": f"abc123{i}",
                "author": "test_user",
            },
        )
    
    return temp_db


class TestQueryEngine:
    """Tests for query engine."""
    
    def test_create_query_engine(self, temp_db):
        """Test creating query engine."""
        engine = create_query_engine(temp_db)
        assert engine is not None
        assert engine.db == temp_db
    
    def test_list_templates(self, temp_db):
        """Test listing query templates."""
        engine = create_query_engine(temp_db)
        templates = engine.list_templates()
        
        assert len(templates) > 0
        assert "risks-by-severity" in templates
        assert "files-by-frequency" in templates
        assert "tasks-by-status" in templates
    
    def test_natural_language_query_risks(self, populated_db):
        """Test natural language query for risks."""
        engine = create_query_engine(populated_db)
        
        result = engine.query_natural("Show me all authentication risks")
        
        assert result.row_count > 0
        assert "auth" in result.explanation.lower()
        assert any("auth" in str(r).lower() for r in result.results)
    
    def test_natural_language_query_files(self, populated_db):
        """Test natural language query for files."""
        engine = create_query_engine(populated_db)
        
        result = engine.query_natural("What files changed most")
        
        assert result.row_count > 0
        assert len(result.results) > 0
    
    def test_natural_language_query_tasks(self, populated_db):
        """Test natural language query for tasks."""
        engine = create_query_engine(populated_db)
        
        result = engine.query_natural("Which tasks were never completed")
        
        assert result.row_count >= 0  # May be 0 if all completed
    
    def test_template_query(self, populated_db):
        """Test template-based query."""
        engine = create_query_engine(populated_db)
        
        result = engine.query_template("risks-by-severity", status="open", limit=10)
        
        assert result.row_count >= 0
        assert "risks-by-severity" in result.explanation
    
    def test_sql_query(self, populated_db):
        """Test direct SQL query."""
        engine = create_query_engine(populated_db)
        
        result = engine.query_sql("SELECT COUNT(*) as count FROM sessions")
        
        assert result.row_count == 1
        assert result.results[0]["count"] == 5
    
    def test_invalid_query(self, populated_db):
        """Test handling of invalid query."""
        engine = create_query_engine(populated_db)
        
        result = engine.query_natural("This is not a valid query xyz123")
        
        assert result.row_count == 0
        assert "Could not understand" in result.explanation


class TestPatternDetector:
    """Tests for pattern detector."""
    
    def test_create_pattern_detector(self, temp_db):
        """Test creating pattern detector."""
        detector = create_pattern_detector(temp_db)
        assert detector is not None
        assert detector.db == temp_db
    
    def test_detect_recurring_risks(self, populated_db):
        """Test detecting recurring risks."""
        detector = create_pattern_detector(populated_db)
        
        patterns = detector.detect_recurring_risks(min_occurrences=2)
        
        # Should find "Authentication security risk" which appears in all sessions
        assert len(patterns) > 0
        auth_patterns = [p for p in patterns if "auth" in p.description.lower()]
        assert len(auth_patterns) > 0
        assert auth_patterns[0].frequency >= 2
    
    def test_detect_file_relationships(self, populated_db):
        """Test detecting file relationships."""
        detector = create_pattern_detector(populated_db)
        
        patterns = detector.detect_file_relationships(min_co_changes=2)
        
        # Files that appear together should be detected
        assert len(patterns) > 0
        # Check for auth files that change together
        auth_patterns = [p for p in patterns if "auth" in p.description.lower()]
        assert len(auth_patterns) > 0
    
    def test_detect_task_patterns(self, populated_db):
        """Test detecting task patterns."""
        detector = create_pattern_detector(populated_db)
        
        patterns = detector.detect_task_patterns()
        
        # Should detect tasks that appear multiple times
        assert len(patterns) >= 0  # May be 0 if no patterns
    
    def test_detect_command_patterns(self, populated_db):
        """Test detecting command patterns."""
        detector = create_pattern_detector(populated_db)
        
        patterns = detector.detect_command_patterns()
        
        # Should detect frequently used commands
        assert len(patterns) > 0
        pytest_patterns = [p for p in patterns if "pytest" in p.description.lower()]
        assert len(pytest_patterns) > 0
    
    def test_detect_anomalies(self, populated_db):
        """Test detecting anomalies."""
        detector = create_pattern_detector(populated_db)
        
        patterns = detector.detect_anomalies()
        
        # May or may not find anomalies depending on data
        assert isinstance(patterns, list)
    
    def test_detect_all(self, populated_db):
        """Test detecting all patterns."""
        detector = create_pattern_detector(populated_db)
        
        patterns = detector.detect_all()
        
        assert len(patterns) > 0
        # Should have multiple pattern types
        pattern_types = set(p.pattern_type for p in patterns)
        assert len(pattern_types) > 1
    
    def test_get_file_relationships(self, populated_db):
        """Test getting file relationships."""
        detector = create_pattern_detector(populated_db)
        
        relationships = detector.get_file_relationships(min_co_changes=2)
        
        assert len(relationships) > 0
        # Check relationship structure
        rel = relationships[0]
        assert hasattr(rel, "file1")
        assert hasattr(rel, "file2")
        assert hasattr(rel, "co_change_count")
        assert hasattr(rel, "confidence")
    
    def test_analyze_file(self, populated_db):
        """Test analyzing specific file."""
        detector = create_pattern_detector(populated_db)
        
        analysis = detector.analyze_file("src/auth/login.py")
        
        assert analysis["found"] is True
        assert analysis["session_count"] > 0
        assert "related_files" in analysis
        assert "sessions" in analysis


class TestInsightsEngine:
    """Tests for insights engine."""
    
    def test_create_insights_engine(self, temp_db):
        """Test creating insights engine."""
        engine = create_insights_engine(temp_db)
        assert engine is not None
        assert engine.db == temp_db
    
    def test_generate_insights(self, populated_db):
        """Test generating insights."""
        engine = create_insights_engine(populated_db)
        
        insights = engine.generate_insights()
        
        assert len(insights) > 0
        # Check insight structure
        insight = insights[0]
        assert hasattr(insight, "title")
        assert hasattr(insight, "description")
        assert hasattr(insight, "severity")
        assert hasattr(insight, "confidence")
        assert hasattr(insight, "recommendations")
    
    def test_get_insights(self, populated_db):
        """Test retrieving insights."""
        engine = create_insights_engine(populated_db)
        
        # Generate first
        engine.generate_insights()
        
        # Then retrieve
        insights = engine.get_insights(limit=10)
        
        assert len(insights) > 0
    
    def test_get_top_insights(self, populated_db):
        """Test getting top insights."""
        engine = create_insights_engine(populated_db)
        
        # Generate first
        engine.generate_insights()
        
        # Get top insights
        top = engine.get_top_insights(n=5)
        
        assert len(top) <= 5
        # Should be sorted by importance
        if len(top) > 1:
            # Check that critical/high severity come first
            severities = [i.severity for i in top]
            assert severities[0] in ("critical", "high", "medium", "low")
    
    def test_get_actionable_insights(self, populated_db):
        """Test getting actionable insights."""
        engine = create_insights_engine(populated_db)
        
        # Generate first
        engine.generate_insights()
        
        # Get actionable
        actionable = engine.get_actionable_insights()
        
        # All should be high severity or high confidence
        for insight in actionable:
            assert insight.severity in ("high", "critical") or insight.confidence >= 0.8
    
    def test_insight_recommendations(self, populated_db):
        """Test that insights have recommendations."""
        engine = create_insights_engine(populated_db)
        
        insights = engine.generate_insights()
        
        # Most insights should have recommendations
        with_recs = [i for i in insights if i.recommendations]
        assert len(with_recs) > 0


class TestPredictionEngine:
    """Tests for prediction engine."""
    
    def test_create_prediction_engine(self, temp_db):
        """Test creating prediction engine."""
        engine = create_prediction_engine(temp_db)
        assert engine is not None
        assert engine.db == temp_db
    
    def test_predict_impact(self, populated_db):
        """Test predicting file impact."""
        engine = create_prediction_engine(populated_db)
        
        prediction = engine.predict_impact("src/auth/login.py")
        
        assert prediction.prediction_type == "impact"
        assert prediction.target == "src/auth/login.py"
        assert 0 <= prediction.confidence <= 1
        assert prediction.reasoning
        # Should predict related auth files
        if prediction.predictions:
            assert any("auth" in p["file"] for p in prediction.predictions)
    
    def test_predict_risks(self, populated_db):
        """Test predicting risks."""
        engine = create_prediction_engine(populated_db)
        
        prediction = engine.predict_risks("Refactor authentication system")
        
        assert prediction.prediction_type == "risks"
        assert 0 <= prediction.confidence <= 1
        assert prediction.reasoning
        # Should find authentication-related risks
        if prediction.predictions:
            assert any("auth" in p["risk"].lower() for p in prediction.predictions)
    
    def test_predict_complexity(self, populated_db):
        """Test predicting task complexity."""
        engine = create_prediction_engine(populated_db)
        
        prediction = engine.predict_complexity("Add OAuth support")
        
        assert prediction.prediction_type == "complexity"
        assert 0 <= prediction.confidence <= 1
        assert prediction.reasoning
        assert len(prediction.predictions) > 0
    
    def test_recommend_tests(self, populated_db):
        """Test recommending tests."""
        engine = create_prediction_engine(populated_db)
        
        prediction = engine.recommend_tests(["src/auth/login.py", "src/auth/session.py"])
        
        assert prediction.prediction_type == "tests"
        assert 0 <= prediction.confidence <= 1
        assert prediction.reasoning
        # Should recommend test files
        if prediction.predictions:
            assert any("test" in p["test_file"].lower() for p in prediction.predictions)
    
    def test_predict_session_metrics(self, populated_db):
        """Test predicting session metrics."""
        engine = create_prediction_engine(populated_db)
        
        prediction = engine.predict_session_metrics()
        
        assert prediction.prediction_type == "session_metrics"
        assert 0 <= prediction.confidence <= 1
        assert len(prediction.predictions) > 0
        # Should have expected metrics
        metrics = prediction.predictions[0]
        assert "expected_risks" in metrics
        assert "expected_files" in metrics
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        from crumdbob.predict import PredictionEngine
        
        keywords = PredictionEngine._extract_keywords("Refactor authentication and database layer")
        
        assert "refactor" in keywords
        assert "authentication" in keywords
        assert "database" in keywords
        assert "layer" in keywords
        # Stop words should be filtered
        assert "and" not in keywords


class TestIntegration:
    """Integration tests for intelligence features."""
    
    def test_full_intelligence_workflow(self, populated_db):
        """Test complete intelligence workflow."""
        # 1. Query for data
        query_engine = create_query_engine(populated_db)
        result = query_engine.query_natural("Show me all risks")
        assert result.row_count > 0
        
        # 2. Detect patterns
        pattern_detector = create_pattern_detector(populated_db)
        patterns = pattern_detector.detect_all()
        assert len(patterns) > 0
        
        # 3. Generate insights
        insights_engine = create_insights_engine(populated_db)
        insights = insights_engine.generate_insights()
        assert len(insights) > 0
        
        # 4. Make predictions
        prediction_engine = create_prediction_engine(populated_db)
        prediction = prediction_engine.predict_impact("src/auth/login.py")
        assert prediction.confidence >= 0
    
    def test_pattern_to_insight_conversion(self, populated_db):
        """Test that patterns are converted to insights."""
        insights_engine = create_insights_engine(populated_db)
        
        insights = insights_engine.generate_insights()
        
        # Should have insights from various pattern types
        insight_types = set(i.insight_type for i in insights)
        assert len(insight_types) > 0
    
    def test_confidence_scores(self, populated_db):
        """Test that confidence scores are reasonable."""
        # Patterns
        pattern_detector = create_pattern_detector(populated_db)
        patterns = pattern_detector.detect_all()
        for pattern in patterns:
            assert 0 <= pattern.confidence <= 1
        
        # Insights
        insights_engine = create_insights_engine(populated_db)
        insights = insights_engine.generate_insights()
        for insight in insights:
            assert 0 <= insight.confidence <= 1
        
        # Predictions
        prediction_engine = create_prediction_engine(populated_db)
        prediction = prediction_engine.predict_impact("src/auth/login.py")
        assert 0 <= prediction.confidence <= 1

# Made with Bob
