"""Tests for multi-session memory database."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from crumdbob.memory import (
    MemoryDatabase,
    init_database,
    record_pack_to_db,
    get_default_db_path,
)
from crumdbob.parser import BobReport


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_report():
    """Create a sample Bob report for testing."""
    return BobReport(
        source_path="/test/bob-report.md",
        title="Test Session",
        summary="This is a test session for CrumbBob memory",
        files=["src/app.py", "src/utils.py", "tests/test_app.py"],
        commands=["pytest", "python -m mypy src/"],
        risks=["Missing error handling", "No input validation"],
        tests=["Run pytest", "Check type coverage"],
        next_steps=["Add error handling", "Implement validation"],
        raw_text="# Test Report\n\nThis is a test.",
    )


def test_init_database(temp_db):
    """Test database initialization."""
    db = init_database(temp_db)
    assert temp_db.exists()
    
    # Check that tables exist
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    expected_tables = {
        "metadata",
        "sessions",
        "packs",
        "files",
        "commands",
        "risks",
        "tasks",
        "relationships",
        "insights",
    }
    
    assert expected_tables.issubset(tables)
    db.close()


def test_record_session(temp_db, sample_report):
    """Test recording a session to database."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        
        session_id = db.record_session(
            report=sample_report,
            session_name="Test Session",
            git_context={
                "branch": "main",
                "commit": "abc123",
                "author": "Test User",
            },
        )
        
        assert session_id > 0
        
        # Verify session was recorded
        session = db.get_session(session_id)
        assert session is not None
        assert session.session_name == "Test Session"
        assert session.git_branch == "main"
        assert session.git_commit == "abc123"
        assert session.git_author == "Test User"
        assert session.file_count == 3
        assert session.command_count == 2
        assert session.risk_count == 2
        assert session.task_count == 2


def test_get_session(temp_db, sample_report):
    """Test retrieving a session by ID."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        session_id = db.record_session(report=sample_report)
        
        session = db.get_session(session_id)
        assert session is not None
        assert session.id == session_id
        assert session.file_count == 3
        
        # Test non-existent session
        assert db.get_session(9999) is None


def test_list_sessions(temp_db, sample_report):
    """Test listing sessions with filters."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        
        # Record multiple sessions
        db.record_session(
            report=sample_report,
            session_name="Session 1",
            git_context={"branch": "main", "author": "Alice"},
        )
        db.record_session(
            report=sample_report,
            session_name="Session 2",
            git_context={"branch": "feature", "author": "Bob"},
        )
        db.record_session(
            report=sample_report,
            session_name="Session 3",
            git_context={"branch": "main", "author": "Alice"},
        )
        
        # List all sessions
        sessions = db.list_sessions()
        assert len(sessions) == 3
        
        # Filter by branch
        main_sessions = db.list_sessions(git_branch="main")
        assert len(main_sessions) == 2
        
        # Filter by author
        alice_sessions = db.list_sessions(git_author="Alice")
        assert len(alice_sessions) == 2
        
        # Test limit
        limited = db.list_sessions(limit=2)
        assert len(limited) == 2


def test_search_files(temp_db, sample_report):
    """Test searching for files across sessions."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        db.record_session(report=sample_report)
        
        # Search for Python files
        files = db.search_files("%.py")
        assert len(files) == 3
        
        # Search for test files
        test_files = db.search_files("%test%")
        assert len(test_files) == 1
        assert "test_app.py" in test_files[0].path


def test_search_risks(temp_db, sample_report):
    """Test searching for risks."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        db.record_session(report=sample_report)
        
        # Search all risks
        risks = db.search_risks()
        assert len(risks) == 2
        
        # Search by pattern
        error_risks = db.search_risks(pattern="%error%")
        assert len(error_risks) == 1
        
        # Search by status
        open_risks = db.search_risks(status="open")
        assert len(open_risks) == 2


def test_get_session_entities(temp_db, sample_report):
    """Test retrieving session entities (files, commands, risks, tasks)."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        session_id = db.record_session(report=sample_report)
        
        # Get files
        files = db.get_session_files(session_id)
        assert len(files) == 3
        assert all(f.session_id == session_id for f in files)
        
        # Get commands
        commands = db.get_session_commands(session_id)
        assert len(commands) == 2
        assert any("pytest" in c.command for c in commands)
        
        # Get risks
        risks = db.get_session_risks(session_id)
        assert len(risks) == 2
        assert all(r.status == "open" for r in risks)
        
        # Get tasks
        tasks = db.get_session_tasks(session_id)
        assert len(tasks) == 2
        assert all(t.status == "pending" for t in tasks)


def test_get_session_timeline(temp_db, sample_report):
    """Test getting session timeline."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        
        # Record multiple sessions
        for i in range(5):
            db.record_session(
                report=sample_report,
                session_name=f"Session {i+1}",
            )
        
        timeline = db.get_session_timeline(limit=3)
        assert len(timeline) == 3
        
        # Check that timeline is ordered by timestamp (newest first)
        timestamps = [entry["timestamp"] for entry in timeline]
        assert timestamps == sorted(timestamps, reverse=True)


def test_record_pack_to_db(temp_db, tmp_path):
    """Test recording a pack directory to database."""
    # Create a mock pack directory
    pack_dir = tmp_path / "test-pack"
    pack_dir.mkdir()
    
    # Create bob-report.md
    report_path = pack_dir.parent / "bob-report.md"
    report_path.write_text(
        "# Test Report\n\n"
        "This is a test report.\n\n"
        "## Files\n"
        "- src/app.py\n"
        "- src/utils.py\n\n"
        "## Commands\n"
        "- pytest\n"
    )
    
    # Create proof chain
    proof_chain = {
        "schema": "crumdbob.proof-chain.v1",
        "timestamp_utc": "2024-01-01T00:00:00Z",
        "crumdbob_version": "0.2.0",
        "source_report": {
            "path": str(report_path),
            "sha256": "abc123",
            "bytes": 100,
        },
        "generated_files": [],
    }
    (pack_dir / "08_proof_chain.json").write_text(json.dumps(proof_chain))
    
    # Initialize database first
    db = init_database(temp_db)
    db.close()
    
    # Record to database
    session_id = record_pack_to_db(
        pack_dir=pack_dir,
        db_path=temp_db,
        session_name="Test Pack",
    )
    
    assert session_id > 0
    
    # Verify session
    with MemoryDatabase(temp_db) as db:
        session = db.get_session(session_id)
        assert session is not None
        assert session.session_name == "Test Pack"
        assert session.pack_directory == str(pack_dir)


def test_database_context_manager(temp_db):
    """Test database context manager."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        assert db.conn is not None
    
    # Connection should be closed after context
    # (We can't easily test this without accessing private attributes)


def test_multiple_sessions_same_files(temp_db, sample_report):
    """Test recording multiple sessions with overlapping files."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        
        # Record two sessions with same files
        session1 = db.record_session(report=sample_report, session_name="Session 1")
        session2 = db.record_session(report=sample_report, session_name="Session 2")
        
        # Both sessions should have their own file records
        files1 = db.get_session_files(session1)
        files2 = db.get_session_files(session2)
        
        assert len(files1) == 3
        assert len(files2) == 3
        assert files1[0].session_id != files2[0].session_id


def test_empty_report(temp_db):
    """Test recording a report with no entities."""
    empty_report = BobReport(
        source_path="/test/empty.md",
        title="Empty Report",
        summary="Nothing to see here",
        raw_text="# Empty\n",
    )
    
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        session_id = db.record_session(report=empty_report)
        
        session = db.get_session(session_id)
        assert session is not None
        assert session.file_count == 0
        assert session.command_count == 0
        assert session.risk_count == 0
        assert session.task_count == 0


def test_get_default_db_path():
    """Test getting default database path."""
    db_path = get_default_db_path()
    assert db_path == Path.home() / ".crumdbob" / "memory.db"


def test_database_indexes(temp_db):
    """Test that indexes are created."""
    db = init_database(temp_db)
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}
    
    # Check for some key indexes
    expected_indexes = {
        "idx_sessions_timestamp",
        "idx_sessions_git_branch",
        "idx_files_path",
        "idx_risks_status",
    }
    
    assert expected_indexes.issubset(indexes)
    db.close()


def test_database_views(temp_db):
    """Test that views are created."""
    db = init_database(temp_db)
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
    views = {row[0] for row in cursor.fetchall()}
    
    expected_views = {
        "session_summary",
        "file_history",
        "risk_summary",
        "command_frequency",
    }
    
    assert expected_views == views
    db.close()


def test_record_relationships(temp_db, sample_report):
    """Test recording CRUMB dependency edges."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        session_id = db.record_session(report=sample_report)

        edges = [
            ("00_repo_genome.crumb", "01_session_flight_recorder.crumb", "refs"),
            ("02_next_task.crumb", "00_repo_genome.crumb", "handoff"),
        ]
        db.record_relationships(session_id, edges)

        stored = db.get_session_relationships(session_id)
        assert len(stored) == 2
        assert stored[0]["source_crumb"] == "00_repo_genome.crumb"
        assert stored[0]["relationship_type"] == "refs"
        assert stored[1]["relationship_type"] == "handoff"


def test_record_relationships_empty(temp_db, sample_report):
    """record_relationships with no edges is a no-op."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        session_id = db.record_session(report=sample_report)
        db.record_relationships(session_id, [])
        assert db.get_session_relationships(session_id) == []


def test_get_hot_files(temp_db, sample_report):
    """get_hot_files returns files seen across multiple sessions."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        db.record_session(report=sample_report, session_name="s1")
        db.record_session(report=sample_report, session_name="s2")

        # min_sessions=2: all three files in sample_report appear in both sessions
        hot = db.get_hot_files(min_sessions=2)
        assert len(hot) == 3
        paths = {f["path"] for f in hot}
        assert "src/app.py" in paths

        # min_sessions=3: no file has been in 3 sessions
        assert db.get_hot_files(min_sessions=3) == []


def test_get_recurring_risks(temp_db, sample_report):
    """get_recurring_risks returns risks seen across multiple sessions."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        db.record_session(report=sample_report, session_name="s1")
        db.record_session(report=sample_report, session_name="s2")

        recurring = db.get_recurring_risks(min_sessions=2)
        assert len(recurring) == 2
        descriptions = {r["description"] for r in recurring}
        assert "Missing error handling" in descriptions

        assert db.get_recurring_risks(min_sessions=3) == []


def test_get_command_frequency(temp_db, sample_report):
    """get_command_frequency returns commands ordered by total mentions."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()
        db.record_session(report=sample_report, session_name="s1")
        db.record_session(report=sample_report, session_name="s2")

        commands = db.get_command_frequency()
        assert len(commands) >= 2
        # Should be ordered by total_mentions desc
        mentions = [c["total_mentions"] for c in commands]
        assert mentions == sorted(mentions, reverse=True)


def test_get_stats(temp_db, sample_report):
    """get_stats returns correct aggregate counts."""
    with MemoryDatabase(temp_db) as db:
        db.init_database()

        stats = db.get_stats()
        assert stats["session_count"] == 0

        db.record_session(report=sample_report, session_name="s1")
        db.record_session(report=sample_report, session_name="s2")

        stats = db.get_stats()
        assert stats["session_count"] == 2
        assert stats["unique_files"] == 3   # deduped across both sessions
        assert stats["open_risks"] == 4     # 2 risks × 2 sessions (not deduped)
        assert stats["unique_commands"] == 2


def test_record_pack_to_db_auto_init(tmp_path):
    """record_pack_to_db auto-inits schema without a prior init-db call."""
    db_path = tmp_path / "auto.db"
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()

    report_path = pack_dir.parent / "bob-report.md"
    report_path.write_text("# Auto Init Test\n\n- pytest\n- src/app.py\n")

    proof = {
        "schema": "crumdbob.proof-chain.v1",
        "timestamp_utc": "2024-01-01T00:00:00Z",
        "crumdbob_version": "0.2.0",
        "source_report": {"path": str(report_path), "sha256": "x", "bytes": 10},
        "generated_files": [],
    }
    (pack_dir / "08_proof_chain.json").write_text(json.dumps(proof))

    # No init-db call — record_pack_to_db should auto-initialize.
    session_id = record_pack_to_db(pack_dir=pack_dir, db_path=db_path)
    assert session_id > 0
    assert db_path.exists()

    with MemoryDatabase(db_path) as db:
        session = db.get_session(session_id)
        assert session is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
