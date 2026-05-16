"""FastAPI server for CrumbBob web dashboard."""

from __future__ import annotations

import logging
import os
import secrets
import sqlite3
import threading
import time
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from crumdbob import __version__
from crumdbob.audit import (
    EVENT_AUTH_FAILURE,
    AuditLogger,
)
from crumdbob.insights import create_insights_engine
from crumdbob.llm import create_llm_analyzer, is_llm_available
from crumdbob.memory import MemoryDatabase, get_default_db_path
from crumdbob.patterns import create_pattern_detector
from crumdbob.predict import create_prediction_engine
from crumdbob.query import create_query_engine

from .metrics import MetricsMiddleware, metrics_response
from .middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

logger = logging.getLogger(__name__)


def _server_error(exc: BaseException) -> HTTPException:
    """Build a sanitized 500 HTTPException and log the underlying cause.

    We never leak raw exception text to clients — it can contain SQL fragments,
    file paths, or stack frames. Each error gets a short correlation ID so the
    server log (which has the full traceback) can be matched back to the
    user-visible response.
    """
    error_id = uuid.uuid4().hex[:8]
    logger.exception("[%s] API error: %s", error_id, exc)
    return HTTPException(
        status_code=500,
        detail={"error": "Internal server error", "error_id": error_id},
    )


# Request/Response Models
class QueryRequest(BaseModel):
    """Natural language query request."""

    question: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)


class StatsResponse(BaseModel):
    """Dashboard statistics response."""

    total_sessions: int
    total_files: int
    total_commands: int
    total_risks: int
    total_tasks: int
    open_risks: int
    pending_tasks: int
    recent_sessions: int


def create_app(db_path: str | Path | None = None) -> FastAPI:
    """Create FastAPI application.

    Args:
        db_path: Path to database file (uses default if None)

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="CrumbBob Dashboard",
        description="Interactive web dashboard for CrumbBob intelligence data",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    cors_origin_regex = os.getenv(
        "CRUMDBOB_CORS_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    )

    # Middleware stack — order matters. Starlette processes them in reverse
    # of registration order, so the LAST registered is the OUTERMOST. We
    # want this final outer-to-inner order:
    #
    #   RequestID  →  SecurityHeaders  →  RateLimit  →  Metrics  →  CORS  →  app
    #
    # so that:
    #   * every log line (including auth/rate-limit denials) has a request ID,
    #   * every response (including 429s and 401s) carries security headers,
    #   * metrics see the final status code,
    #   * CORS still wraps the actual handlers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        rate_per_second=float(os.getenv("CRUMDBOB_RATE_LIMIT_PER_SECOND", "10")),
        burst=int(os.getenv("CRUMDBOB_RATE_LIMIT_BURST", "30")),
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=os.getenv("CRUMDBOB_ENABLE_HSTS", "").lower() in {"1", "true", "yes"},
    )
    app.add_middleware(RequestIDMiddleware)

    # Defense-in-depth: catch any unhandled exception, log it server-side, and
    # return a sanitized response. The per-route handlers below already do this
    # explicitly; this is the safety net for anything that slips through.
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):
        error_id = uuid.uuid4().hex[:8]
        logger.exception("[%s] Unhandled exception at %s: %s", error_id, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": {"error": "Internal server error", "error_id": error_id}},
        )

    # Optional API-key auth. If CRUMDBOB_API_KEY is set in the environment,
    # every /api/* request must include `X-API-Key: <key>`. If unset, the API
    # behaves as before (open access on localhost). This is opt-in so the
    # hackathon demo UX is unchanged, but operators deploying beyond
    # 127.0.0.1 can enable a basic gate without touching the codebase.
    expected_api_key = os.getenv("CRUMDBOB_API_KEY")

    @app.middleware("http")
    async def api_key_middleware(request, call_next):
        if expected_api_key and request.url.path.startswith("/api/"):
            provided = request.headers.get("x-api-key", "")
            # secrets.compare_digest defends against timing-attack key recovery.
            if not provided or not secrets.compare_digest(provided, expected_api_key):
                # Audit log the failure. Use a closure on `audit` defined
                # below — bound at call time, not registration time.
                client_host = request.client.host if request.client else "unknown"
                try:
                    audit.record(
                        EVENT_AUTH_FAILURE,
                        actor=client_host,
                        payload={"path": request.url.path, "method": request.method},
                    )
                except Exception:  # pragma: no cover — audit must not block
                    logger.exception("audit.write_failed")
                return JSONResponse(
                    status_code=401,
                    content={"detail": {"error": "Missing or invalid X-API-Key header"}},
                )
        return await call_next(request)

    # Initialize database connection
    if db_path is None:
        db_path = get_default_db_path()

    db = MemoryDatabase(db_path)
    # Apply pending migrations (audit_log table etc.) on startup.
    db.init_database()

    query_engine = create_query_engine(db)
    insights_engine = create_insights_engine(db)
    pattern_detector = create_pattern_detector(db)
    prediction_engine = create_prediction_engine(db)

    # Audit logger shares the same SQLite file as session memory.
    audit = AuditLogger(
        db_path,
        actor_resolver=lambda: "api",
    )

    # Store in app state
    app.state.db = db
    app.state.query_engine = query_engine
    app.state.insights_engine = insights_engine
    app.state.pattern_detector = pattern_detector
    app.state.prediction_engine = prediction_engine

    # Serve static files
    web_dir = Path(__file__).parent.parent
    static_dir = web_dir / "static"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Routes
    @app.get("/")
    async def root():
        """Serve the main dashboard page."""
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "CrumbBob Dashboard API", "docs": "/api/docs"}

    @app.get("/api/health")
    @app.get("/api/v1/health")
    async def health_check():
        """Liveness check. Returns 200 if the process is up.

        Use this for load-balancer liveness probes. For readiness (can we
        serve traffic?), use ``/api/ready`` which also verifies the
        database is reachable.
        """
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": __version__,
        }

    @app.get("/api/ready")
    @app.get("/api/v1/ready")
    async def readiness_check():
        """Readiness check. Returns 200 only if the database is reachable.

        Kubernetes/ECS-style readiness probe target. A 503 here pulls the
        instance out of the LB rotation until the dependency recovers.
        """
        try:
            db.conn.execute("SELECT 1").fetchone()
        except sqlite3.Error as exc:
            logger.warning("readiness.db_unreachable", extra={"error": str(exc)})
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "reason": "database_unreachable"},
            )
        return {"status": "ready", "version": __version__}

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus scrape endpoint.

        Exempt from auth and rate limiting (see middleware config) so a
        Prometheus server can scrape without API keys. Locked down by
        network policy in production — exposing /metrics publicly leaks
        traffic patterns.
        """
        return metrics_response()

    @app.get("/api/stats")
    async def get_stats() -> StatsResponse:
        """Get dashboard statistics."""
        try:
            conn = db.conn
            cursor = conn.cursor()

            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            # Recent sessions (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) FROM sessions
                WHERE datetime(timestamp) >= datetime('now', '-7 days')
            """)
            recent_sessions = cursor.fetchone()[0]

            # Total unique files
            cursor.execute("SELECT COUNT(DISTINCT path) FROM files")
            total_files = cursor.fetchone()[0]

            # Total unique commands
            cursor.execute("SELECT COUNT(DISTINCT command) FROM commands")
            total_commands = cursor.fetchone()[0]

            # Total risks
            cursor.execute("SELECT COUNT(*) FROM risks")
            total_risks = cursor.fetchone()[0]

            # Open risks
            cursor.execute("SELECT COUNT(*) FROM risks WHERE status = 'open'")
            open_risks = cursor.fetchone()[0]

            # Total tasks
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]

            # Pending tasks
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            pending_tasks = cursor.fetchone()[0]

            return StatsResponse(
                total_sessions=total_sessions,
                total_files=total_files,
                total_commands=total_commands,
                total_risks=total_risks,
                total_tasks=total_tasks,
                open_risks=open_risks,
                pending_tasks=pending_tasks,
                recent_sessions=recent_sessions,
            )
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.get("/api/sessions")
    async def list_sessions(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ):
        """List all sessions with pagination."""
        try:
            sessions = db.list_sessions(limit=limit, offset=offset)

            # Convert to dict format
            sessions_data = [
                {
                    "id": s.id,
                    "timestamp": s.timestamp,
                    "session_name": s.session_name,
                    "pack_version": s.pack_version,
                    "git_branch": s.git_branch,
                    "git_commit": s.git_commit,
                    "git_author": s.git_author,
                    "file_count": s.file_count,
                    "command_count": s.command_count,
                    "risk_count": s.risk_count,
                    "task_count": s.task_count,
                }
                for s in sessions
            ]

            # Get total count
            cursor = db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total = cursor.fetchone()[0]

            return {
                "sessions": sessions_data,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: int):
        """Get detailed session information."""
        try:
            session = db.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            # Get related data
            files = db.get_session_files(session_id)
            commands = db.get_session_commands(session_id)
            risks = db.get_session_risks(session_id)
            tasks = db.get_session_tasks(session_id)

            return {
                "session": {
                    "id": session.id,
                    "timestamp": session.timestamp,
                    "session_name": session.session_name,
                    "pack_version": session.pack_version,
                    "git_branch": session.git_branch,
                    "git_commit": session.git_commit,
                    "git_author": session.git_author,
                    "source_report_path": session.source_report_path,
                    "pack_directory": session.pack_directory,
                    "file_count": session.file_count,
                    "command_count": session.command_count,
                    "risk_count": session.risk_count,
                    "task_count": session.task_count,
                },
                "files": [
                    {
                        "path": f.path,
                        "mention_count": f.mention_count,
                        "first_seen": f.first_seen,
                        "last_seen": f.last_seen,
                    }
                    for f in files
                ],
                "commands": [
                    {
                        "command": c.command,
                        "mention_count": c.mention_count,
                        "first_seen": c.first_seen,
                        "last_seen": c.last_seen,
                    }
                    for c in commands
                ],
                "risks": [
                    {
                        "description": r.description,
                        "status": r.status,
                        "first_seen": r.first_seen,
                        "last_seen": r.last_seen,
                    }
                    for r in risks
                ],
                "tasks": [
                    {
                        "description": t.description,
                        "status": t.status,
                        "first_seen": t.first_seen,
                        "last_seen": t.last_seen,
                    }
                    for t in tasks
                ],
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.get("/api/insights")
    async def list_insights(
        severity: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        """List insights with optional filtering."""
        try:
            insights = insights_engine.generate_insights()

            # Filter by severity if provided
            if severity:
                insights = [i for i in insights if i.severity == severity]

            # Apply limit
            insights = insights[:limit]

            return {
                "insights": [
                    {
                        "id": i.id,
                        "insight_type": i.insight_type,
                        "title": i.title,
                        "description": i.description,
                        "severity": i.severity,
                        "confidence": i.confidence,
                        "evidence": i.evidence,
                        "recommendations": i.recommendations,
                        "created_at": i.created_at,
                        "session_id": i.session_id,
                    }
                    for i in insights
                ],
                "total": len(insights),
            }
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.get("/api/trends")
    async def get_trends(
        days: int = Query(default=30, ge=1, le=365),
    ):
        """Get trend data over time."""
        try:
            cursor = db.conn.cursor()

            # Sessions over time
            cursor.execute(
                """
                SELECT date(timestamp) as date, COUNT(*) as count
                FROM sessions
                WHERE datetime(timestamp) >= datetime('now', ? || ' days')
                GROUP BY date(timestamp)
                ORDER BY date
            """,
                (f"-{days}",),
            )
            sessions_trend = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]

            # Risks over time
            cursor.execute(
                """
                SELECT date(r.first_seen) as date, COUNT(*) as count
                FROM risks r
                WHERE datetime(r.first_seen) >= datetime('now', ? || ' days')
                GROUP BY date(r.first_seen)
                ORDER BY date
            """,
                (f"-{days}",),
            )
            risks_trend = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]

            # Files over time
            cursor.execute(
                """
                SELECT date(f.first_seen) as date, COUNT(DISTINCT f.path) as count
                FROM files f
                WHERE datetime(f.first_seen) >= datetime('now', ? || ' days')
                GROUP BY date(f.first_seen)
                ORDER BY date
            """,
                (f"-{days}",),
            )
            files_trend = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]

            return {
                "sessions": sessions_trend,
                "risks": risks_trend,
                "files": files_trend,
                "days": days,
            }
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.get("/api/patterns")
    async def get_patterns():
        """Get detected patterns."""
        try:
            patterns = pattern_detector.detect_all()

            return {
                "patterns": [
                    {
                        "id": p.id,
                        "pattern_type": p.pattern_type,
                        "description": p.description,
                        "frequency": p.frequency,
                        "confidence": p.confidence,
                        "first_seen": p.first_seen,
                        "last_seen": p.last_seen,
                        "severity": p.severity,
                        "evidence": p.evidence,
                    }
                    for p in patterns
                ],
                "total": len(patterns),
            }
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.get("/api/risks")
    async def list_risks(
        status: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ):
        """Get risk predictions and current risks."""
        try:
            cursor = db.conn.cursor()

            # Build query
            query = """
                SELECT r.*, s.session_name, s.timestamp, s.git_branch
                FROM risks r
                JOIN sessions s ON r.session_id = s.id
            """
            params: list[Any] = []

            if status:
                query += " WHERE r.status = ?"
                params.append(status)

            query += " ORDER BY r.last_seen DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            risks = [
                {
                    "id": row[0],
                    "session_id": row[1],
                    "description": row[2],
                    "first_seen": row[3],
                    "last_seen": row[4],
                    "status": row[5],
                    "session_name": row[6],
                    "timestamp": row[7],
                    "git_branch": row[8],
                }
                for row in rows
            ]

            # Get predictions (use empty string as placeholder for change description)
            predictions = []
            try:
                pred = prediction_engine.predict_risks("")
                predictions = pred.predictions if hasattr(pred, "predictions") else []
            except (ValueError, RuntimeError, AttributeError):
                # If prediction fails, return empty list.
                predictions = []

            return {
                "risks": risks,
                "predictions": predictions,
                "total": len(risks),
            }
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.post("/api/query")
    async def execute_query(request: QueryRequest):
        """Execute a natural language query."""
        try:
            result = query_engine.query_natural(request.question)

            return {
                "query": result.query,
                "results": result.results,
                "row_count": result.row_count,
                "explanation": result.explanation,
            }
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.get("/api/llm/status")
    async def llm_status():
        """Get LLM configuration and status."""
        try:
            config = db.get_llm_config()
            available = is_llm_available()
            cache_stats = db.get_llm_cache_stats()

            return {
                "configured": config is not None,
                "available": available,
                "config": config,
                "cache_stats": cache_stats,
            }
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.post("/api/llm/analyze/{session_id}")
    async def llm_analyze_session(session_id: int):
        """Analyze a session with LLM."""
        try:
            analyzer = create_llm_analyzer(db)
            if not analyzer:
                raise HTTPException(status_code=503, detail="LLM not configured or unavailable")

            # Get session data
            session = db.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            files = db.get_session_files(session_id)
            commands = db.get_session_commands(session_id)
            risks = db.get_session_risks(session_id)
            tasks = db.get_session_tasks(session_id)

            session_data = {
                "session_name": session.session_name,
                "git_branch": session.git_branch,
                "git_author": session.git_author,
                "file_count": session.file_count,
                "command_count": session.command_count,
                "risk_count": session.risk_count,
                "task_count": session.task_count,
                "files": [f.path for f in files],
                "commands": [c.command for c in commands],
                "risks": [r.description for r in risks],
                "tasks": [t.description for t in tasks],
            }

            response = analyzer.analyze_session(session_data)

            return {
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cached": response.cached,
                "timestamp": response.timestamp,
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.post("/api/llm/explain")
    async def llm_explain_pattern(pattern_data: dict):
        """Get LLM explanation of a pattern."""
        try:
            analyzer = create_llm_analyzer(db)
            if not analyzer:
                raise HTTPException(status_code=503, detail="LLM not configured or unavailable")

            response = analyzer.explain_pattern(pattern_data)

            return {
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cached": response.cached,
                "timestamp": response.timestamp,
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise _server_error(exc) from exc

    @app.post("/api/llm/recommend/{session_id}")
    async def llm_recommend_actions(session_id: int):
        """Get LLM recommendations for a session."""
        try:
            analyzer = create_llm_analyzer(db)
            if not analyzer:
                raise HTTPException(status_code=503, detail="LLM not configured or unavailable")

            # Get session data
            session = db.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            files = db.get_session_files(session_id)
            risks = db.get_session_risks(session_id)
            tasks = db.get_session_tasks(session_id)

            session_data = {
                "session_name": session.session_name,
                "files": [f.path for f in files],
                "risks": [r.description for r in risks],
                "tasks": [t.description for t in tasks],
            }

            response = analyzer.recommend_actions(session_data)

            return {
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cached": response.cached,
                "timestamp": response.timestamp,
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise _server_error(exc) from exc

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    db_path: str | Path | None = None,
    open_browser: bool = True,
) -> None:
    """Run the FastAPI server.

    Args:
        host: Host to bind to
        port: Port to bind to
        db_path: Path to database file
        open_browser: Whether to open browser automatically
    """
    app = create_app(db_path)

    # Open browser after a short delay
    if open_browser:

        def open_browser_delayed():
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    print(f"🚀 Starting CrumbBob Dashboard at http://{host}:{port}")
    print(f"📊 API Documentation: http://{host}:{port}/api/docs")
    print(f"🗄️  Database: {db_path or get_default_db_path()}")
    print("\nPress Ctrl+C to stop the server")

    uvicorn.run(app, host=host, port=port, log_level="info")


# Made with Bob
