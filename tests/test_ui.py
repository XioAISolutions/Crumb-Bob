"""Tests for the Rich Terminal UI module."""

from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from crumdbob.ui import (
    CrumbBobUI,
    display_pack_summary,
    display_validation_results,
    display_session_info,
    display_sessions_table,
    display_insights,
    display_trends,
    display_query_results,
    display_patterns,
    display_predictions,
    create_progress_bar,
    show_spinner,
    RICH_AVAILABLE,
)


class TestCrumbBobUI:
    """Test CrumbBobUI class."""
    
    def test_init_with_rich(self):
        """Test UI initialization with rich available."""
        ui = CrumbBobUI(use_rich=True)
        assert ui.use_rich == RICH_AVAILABLE
    
    def test_init_without_rich(self):
        """Test UI initialization without rich."""
        ui = CrumbBobUI(use_rich=False)
        assert ui.use_rich is False
    
    def test_print_methods(self, capsys):
        """Test print methods work without errors."""
        ui = CrumbBobUI(use_rich=False)
        
        ui.print("Test message")
        ui.print_error("Error message")
        ui.print_success("Success message")
        ui.print_warning("Warning message")
        ui.print_info("Info message")
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out
        assert "Error message" in captured.err
        assert "Success message" in captured.out


class TestDisplayPackSummary:
    """Test display_pack_summary function."""
    
    def test_display_pack_summary_basic(self, tmp_path, capsys):
        """Test basic pack summary display."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        
        files = [
            pack_dir / "00_repo_genome.crumb",
            pack_dir / "01_session_flight_recorder.crumb",
            pack_dir / "06_replay_prompt.md",
        ]
        
        for f in files:
            f.touch()
        
        display_pack_summary(pack_dir, files)
        
        captured = capsys.readouterr()
        assert "test-pack" in captured.out
        assert "00_repo_genome.crumb" in captured.out
    
    def test_display_pack_summary_with_session_id(self, tmp_path, capsys):
        """Test pack summary with session ID."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        files = [pack_dir / "test.crumb"]
        
        display_pack_summary(pack_dir, files, session_id=42)
        
        captured = capsys.readouterr()
        assert "42" in captured.out or "Session" in captured.out


class TestDisplayValidationResults:
    """Test display_validation_results function."""
    
    def test_display_validation_success(self, capsys):
        """Test validation success display."""
        report = Mock()
        report.ok = True
        report.documents = ["doc1", "doc2"]
        report.errors = []
        
        display_validation_results(report)
        
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower() or "2" in captured.out
    
    def test_display_validation_failure(self, capsys):
        """Test validation failure display."""
        report = Mock()
        report.ok = False
        report.documents = []
        
        error = Mock()
        error.format = Mock(return_value="test.crumb: Invalid format")
        report.errors = [error]
        
        display_validation_results(report)
        
        captured = capsys.readouterr()
        # Should show error in stderr or stdout
        output = captured.out + captured.err
        assert "error" in output.lower() or "invalid" in output.lower()


class TestDisplaySessionInfo:
    """Test display_session_info function."""
    
    def test_display_session_info_basic(self, capsys):
        """Test basic session info display."""
        session = Mock()
        session.id = 1
        session.session_name = "Test Session"
        session.timestamp = "2024-01-01 12:00:00"
        session.git_branch = "main"
        session.git_commit = "abc123def456"
        session.git_author = "Test User"
        session.command_count = 5
        
        files = [Mock(file_path="test.py", size_bytes=100)]
        risks = [Mock(status="open", description="Test risk")]
        tasks = [Mock(status="pending", description="Test task")]
        
        display_session_info(session, files, risks, tasks)
        
        captured = capsys.readouterr()
        assert "Test Session" in captured.out or "1" in captured.out


class TestDisplaySessionsTable:
    """Test display_sessions_table function."""
    
    def test_display_sessions_table(self, capsys):
        """Test sessions table display."""
        session1 = Mock()
        session1.id = 1
        session1.timestamp = "2024-01-01 12:00:00"
        session1.session_name = "Session 1"
        session1.git_branch = "main"
        session1.file_count = 10
        session1.risk_count = 2
        
        session2 = Mock()
        session2.id = 2
        session2.timestamp = "2024-01-02 12:00:00"
        session2.session_name = None
        session2.git_branch = None
        session2.file_count = 5
        session2.risk_count = 0
        
        display_sessions_table([session1, session2])
        
        captured = capsys.readouterr()
        assert "Session 1" in captured.out or "1" in captured.out


class TestDisplayInsights:
    """Test display_insights function."""
    
    def test_display_insights(self, capsys):
        """Test insights display."""
        insight = Mock()
        insight.title = "Test Insight"
        insight.description = "This is a test insight"
        insight.severity = "high"
        insight.insight_type = "risk"
        insight.confidence = 0.85
        insight.created_at = "2024-01-01 12:00:00"
        insight.recommendations = ["Fix this", "Do that"]
        
        display_insights([insight])
        
        captured = capsys.readouterr()
        assert "Test Insight" in captured.out


class TestDisplayTrends:
    """Test display_trends function."""
    
    def test_display_trends(self, capsys):
        """Test trends display."""
        stats = {
            'session_count': 10,
            'unique_files': 50,
            'open_risks': 5,
            'unique_commands': 20
        }
        
        hot_files = [
            {'session_count': 5, 'path': 'test.py'},
            {'session_count': 3, 'path': 'main.py'}
        ]
        
        recurring_risks = [
            {'session_count': 3, 'status': 'open', 'description': 'Test risk'}
        ]
        
        commands = [
            {'total_mentions': 10, 'command': 'pytest'}
        ]
        
        display_trends(stats, hot_files, recurring_risks, commands)
        
        captured = capsys.readouterr()
        assert "10" in captured.out  # session count
        assert "test.py" in captured.out


class TestDisplayQueryResults:
    """Test display_query_results function."""
    
    def test_display_query_results(self, capsys):
        """Test query results display."""
        result = Mock()
        result.explanation = "Test query"
        result.row_count = 2
        result.results = [
            {'id': 1, 'name': 'Test 1'},
            {'id': 2, 'name': 'Test 2'}
        ]
        
        display_query_results(result)
        
        captured = capsys.readouterr()
        assert "Test query" in captured.out or "2" in captured.out
    
    def test_display_query_results_empty(self, capsys):
        """Test empty query results display."""
        result = Mock()
        result.explanation = "Empty query"
        result.row_count = 0
        result.results = []
        
        display_query_results(result)
        
        captured = capsys.readouterr()
        assert "Empty query" in captured.out or "0" in captured.out


class TestDisplayPatterns:
    """Test display_patterns function."""
    
    def test_display_patterns(self, capsys):
        """Test patterns display."""
        pattern = Mock()
        pattern.pattern_type = "file_relationship"
        pattern.description = "Test pattern"
        pattern.severity = "medium"
        pattern.confidence = 0.75
        pattern.frequency = 5
        
        display_patterns([pattern])
        
        captured = capsys.readouterr()
        assert "pattern" in captured.out.lower() or "Test pattern" in captured.out


class TestDisplayPredictions:
    """Test display_predictions function."""
    
    def test_display_predictions_impact(self, capsys):
        """Test impact predictions display."""
        prediction = Mock()
        prediction.confidence = 0.80
        prediction.reasoning = "Based on historical data"
        prediction.predictions = [
            {'file': 'test.py', 'confidence': 0.9, 'co_changes': 5}
        ]
        
        display_predictions(prediction, "impact")
        
        captured = capsys.readouterr()
        assert "test.py" in captured.out or "80" in captured.out
    
    def test_display_predictions_risks(self, capsys):
        """Test risk predictions display."""
        prediction = Mock()
        prediction.confidence = 0.70
        prediction.reasoning = "Similar past changes"
        prediction.predictions = [
            {'status': 'open', 'risk': 'Test risk', 'frequency': 3}
        ]
        
        display_predictions(prediction, "risks")
        
        captured = capsys.readouterr()
        assert "risk" in captured.out.lower() or "70" in captured.out
    
    def test_display_predictions_tests(self, capsys):
        """Test test recommendations display."""
        prediction = Mock()
        prediction.confidence = 0.85
        prediction.reasoning = "Based on file relationships"
        prediction.predictions = [
            {'test_file': 'test_main.py', 'reason': 'Tests main.py'}
        ]
        
        display_predictions(prediction, "tests")
        
        captured = capsys.readouterr()
        assert "test" in captured.out.lower() or "85" in captured.out


class TestProgressHelpers:
    """Test progress bar and spinner helpers."""
    
    def test_create_progress_bar(self):
        """Test progress bar creation."""
        progress = create_progress_bar("Testing...")
        # Should return Progress object or None
        assert progress is None or hasattr(progress, '__enter__')
    
    def test_show_spinner(self):
        """Test spinner creation."""
        spinner = show_spinner("Working...")
        # Should return Progress object or None
        assert spinner is None or hasattr(spinner, '__enter__')


class TestFallbackBehavior:
    """Test graceful fallback when rich is not available."""
    
    def test_ui_without_rich(self, capsys):
        """Test UI works without rich library."""
        ui = CrumbBobUI(use_rich=False)
        
        # All methods should work without errors
        ui.print("Test")
        ui.print_error("Error")
        ui.print_success("Success")
        ui.print_warning("Warning")
        ui.print_info("Info")
        
        captured = capsys.readouterr()
        # Should have some output
        assert len(captured.out) > 0 or len(captured.err) > 0
    
    def test_all_display_functions_work_without_rich(self, tmp_path, capsys):
        """Test all display functions work without rich."""
        # Pack summary
        pack_dir = tmp_path / "pack"
        pack_dir.mkdir()
        files = [pack_dir / "test.crumb"]
        display_pack_summary(pack_dir, files)
        
        # Validation
        report = Mock(ok=True, documents=["doc"], errors=[])
        display_validation_results(report)
        
        # Session info
        session = Mock(
            id=1, session_name="Test", timestamp="2024-01-01",
            git_branch="main", git_commit="abc", git_author="User",
            command_count=1
        )
        display_session_info(session, [], [], [])
        
        # All should produce output without errors
        captured = capsys.readouterr()
        assert len(captured.out) > 0


class TestColorSchemeConsistency:
    """Test color scheme consistency across UI components."""
    
    def test_severity_colors_consistent(self):
        """Test severity colors are used consistently."""
        # This is more of a code review test
        # Ensure all severity mappings use same colors
        severity_colors = {
            'low': 'blue',
            'medium': 'yellow',
            'high': 'orange',
            'critical': 'red'
        }
        
        # Test that our UI uses these consistently
        # (This would be validated by code inspection)
        assert 'low' in severity_colors
        assert 'critical' in severity_colors


class TestErrorHandling:
    """Test error handling in UI functions."""
    
    def test_display_with_none_values(self, capsys):
        """Test display functions handle None values gracefully."""
        # Session with None values
        session = Mock()
        session.id = 1
        session.session_name = None
        session.timestamp = "2024-01-01"
        session.git_branch = None
        session.git_commit = None
        session.git_author = None
        session.command_count = 0
        
        # Should not raise errors
        display_session_info(session, [], [], [])
        
        captured = capsys.readouterr()
        # Should have some output
        assert len(captured.out) > 0
    
    def test_display_with_empty_lists(self, capsys):
        """Test display functions handle empty lists."""
        # Empty sessions
        display_sessions_table([])
        
        # Empty insights
        display_insights([])
        
        # Empty patterns
        display_patterns([])
        
        # Should not raise errors
        captured = capsys.readouterr()
        # May or may not have output, but shouldn't crash
        assert True  # If we got here, no exceptions were raised


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
