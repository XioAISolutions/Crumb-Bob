"""Tests for the web API."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Skip tests if FastAPI is not installed
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from crumdbob.memory import MemoryDatabase, init_database
from crumdbob.parser import BobReport
from web.api.server import create_app


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Initialize database
    db = init_database(db_path)
    db.close()

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
        files=["/test/file1.py", "/test/file2.py"],
        commands=["pytest", "git commit"],
        risks=["Security vulnerability in auth", "Performance issue"],
        tests=["Run pytest", "Check coverage"],
        next_steps=["Fix authentication", "Update tests"],
        raw_text="# Test Report\n\nThis is a test.",
    )


@pytest.fixture
def populated_db(temp_db, sample_report):
    """Create a database with test data."""
    db = MemoryDatabase(temp_db)
    db.init_database()

    # Add test session using the correct API
    db.record_session(
        report=sample_report,
        session_name="Test Session",
        git_context={
            "branch": "main",
            "commit": "abc123",
            "author": "test@example.com",
        },
    )

    db.conn.commit()
    db.conn.close()

    return temp_db


@pytest.fixture
def client(populated_db):
    """Create test client with populated database."""
    app = create_app(populated_db)
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    """Liveness endpoint returns status, timestamp, and version.

    The legacy v0.3.0 response exposed the database path on disk — that
    was reverted in v0.3.1 because exposing internal filesystem paths to
    unauthenticated callers is an info-leak.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    # Path must NOT be leaked
    assert "database" not in data
    assert "/" not in data["version"]


def test_health_check_v1_alias(client):
    """The /api/v1/health route is an alias for /api/health."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_check(client):
    """Readiness probe returns 200 when the database is reachable."""
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_metrics_endpoint(client):
    """Prometheus metrics endpoint exposes the standard text format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    # Expected counters
    assert "crumdbob_http_requests_total" in body
    assert "crumdbob_process_start_time_seconds" in body
    # Format-spec markers
    assert "# HELP" in body
    assert "# TYPE" in body


def test_request_id_header_in_response(client):
    """Every response carries the X-Request-ID header for log correlation."""
    response = client.get("/api/health")
    assert "x-request-id" in {k.lower() for k in response.headers}


def test_request_id_is_echoed(client):
    """Caller-supplied X-Request-ID is honored (for cross-service tracing)."""
    response = client.get("/api/health", headers={"X-Request-ID": "test-12345"})
    assert response.headers.get("x-request-id") == "test-12345"


def test_security_headers_present(client):
    """OWASP-recommended response headers are attached to every response."""
    response = client.get("/api/health")
    h = {k.lower(): v for k, v in response.headers.items()}
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "default-src 'self'" in h["content-security-policy"]
    assert "referrer-policy" in h


def test_get_stats(client):
    """Test stats endpoint."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()

    assert "total_sessions" in data
    assert "total_files" in data
    assert "total_commands" in data
    assert "total_risks" in data
    assert "total_tasks" in data
    assert "open_risks" in data
    assert "pending_tasks" in data

    assert data["total_sessions"] >= 1
    assert data["total_files"] >= 2
    assert data["open_risks"] >= 2


def test_list_sessions(client):
    """Test sessions list endpoint."""
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()

    assert "sessions" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    assert len(data["sessions"]) >= 1
    session = data["sessions"][0]
    assert "id" in session
    assert "timestamp" in session
    assert "session_name" in session
    assert session["session_name"] == "Test Session"


def test_list_sessions_pagination(client):
    """Test sessions pagination."""
    response = client.get("/api/sessions?limit=1&offset=0")
    assert response.status_code == 200
    data = response.json()

    assert data["limit"] == 1
    assert data["offset"] == 0
    assert len(data["sessions"]) <= 1


def test_get_session_detail(client):
    """Test session detail endpoint."""
    # First get a session ID
    response = client.get("/api/sessions")
    sessions = response.json()["sessions"]
    session_id = sessions[0]["id"]

    # Get session detail
    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()

    assert "session" in data
    assert "files" in data
    assert "commands" in data
    assert "risks" in data
    assert "tasks" in data

    assert data["session"]["id"] == session_id
    assert len(data["files"]) >= 2
    assert len(data["commands"]) >= 2
    assert len(data["risks"]) >= 2
    assert len(data["tasks"]) >= 2


def test_get_session_not_found(client):
    """Test session detail with invalid ID."""
    response = client.get("/api/sessions/99999")
    assert response.status_code == 404


def test_list_insights(client):
    """Test insights endpoint."""
    response = client.get("/api/insights")
    assert response.status_code == 200
    data = response.json()

    assert "insights" in data
    assert "total" in data


def test_list_insights_with_filter(client):
    """Test insights with severity filter."""
    response = client.get("/api/insights?severity=high")
    assert response.status_code == 200
    data = response.json()

    assert "insights" in data


def test_get_trends(client):
    """Test trends endpoint."""
    response = client.get("/api/trends")
    assert response.status_code == 200
    data = response.json()

    assert "sessions" in data
    assert "risks" in data
    assert "files" in data
    assert "days" in data

    assert isinstance(data["sessions"], list)
    assert isinstance(data["risks"], list)
    assert isinstance(data["files"], list)


def test_get_trends_custom_period(client):
    """Test trends with custom period."""
    response = client.get("/api/trends?days=7")
    assert response.status_code == 200
    data = response.json()

    assert data["days"] == 7


def test_get_patterns(client):
    """Test patterns endpoint."""
    response = client.get("/api/patterns")
    assert response.status_code == 200
    data = response.json()

    assert "patterns" in data
    assert "total" in data
    assert isinstance(data["patterns"], list)


def test_list_risks(client):
    """Test risks endpoint."""
    response = client.get("/api/risks")
    assert response.status_code == 200
    data = response.json()

    assert "risks" in data
    assert "predictions" in data
    assert "total" in data

    assert len(data["risks"]) >= 2


def test_list_risks_with_filter(client):
    """Test risks with status filter."""
    response = client.get("/api/risks?status=open")
    assert response.status_code == 200
    data = response.json()

    assert "risks" in data
    # All returned risks should be open
    for risk in data["risks"]:
        assert risk["status"] == "open"


def test_execute_query(client):
    """Test query endpoint."""
    response = client.post("/api/query", json={"question": "Show me all sessions", "limit": 10})
    assert response.status_code == 200
    data = response.json()

    assert "query" in data
    assert "results" in data
    assert "row_count" in data
    assert "explanation" in data
    assert data["row_count"] >= 1


def test_execute_query_invalid(client):
    """Test query with invalid input."""
    response = client.post("/api/query", json={"question": "", "limit": 10})
    assert response.status_code == 422  # Validation error


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200


def test_api_docs(client):
    """Test API documentation is available."""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_empty_database():
    """Test API with empty database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db = init_database(db_path)
    db.close()
    try:
        app = create_app(db_path)
        with TestClient(app) as client:
            # Should still work with empty database
            response = client.get("/api/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total_sessions"] == 0

            response = client.get("/api/sessions")
            assert response.status_code == 200
            data = response.json()
            assert len(data["sessions"]) == 0
    finally:
        if db_path.exists():
            db_path.unlink()


def test_error_handling(client):
    """Test error handling for invalid requests."""
    # Invalid session ID type
    response = client.get("/api/sessions/invalid")
    assert response.status_code == 422

    # Invalid query parameters
    response = client.get("/api/sessions?limit=-1")
    assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
