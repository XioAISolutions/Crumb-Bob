"""FastAPI server for CrumbBob web dashboard."""
from __future__ import annotations

import os
import webbrowser
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from crumdbob import __version__
from crumdbob.memory import MemoryDatabase, get_default_db_path
from crumdbob.query import create_query_engine
from crumdbob.insights import create_insights_engine
from crumdbob.patterns import create_pattern_detector
from crumdbob.predict import create_prediction_engine


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

    # Enable CORS for local development dashboards without credentialed wildcard access.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize database connection
    if db_path is None:
        db_path = get_default_db_path()

    db = MemoryDatabase(db_path)
    query_engine = create_query_engine(db)
    insights_engine = create_insights_engine(db)
    pattern_detector = create_pattern_detector(db)
    prediction_engine = create_prediction_engine(db)

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
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": str(db_path),
        }

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/trends")
    async def get_trends(
        days: int = Query(default=30, ge=1, le=365),
    ):
        """Get trend data over time."""
        try:
            cursor = db.conn.cursor()

            # Sessions over time
            cursor.execute("""
                SELECT date(timestamp) as date, COUNT(*) as count
                FROM sessions
                WHERE datetime(timestamp) >= datetime('now', ? || ' days')
                GROUP BY date(timestamp)
                ORDER BY date
            """, (f"-{days}",))
            sessions_trend = [
                {"date": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]

            # Risks over time
            cursor.execute("""
                SELECT date(r.first_seen) as date, COUNT(*) as count
                FROM risks r
                WHERE datetime(r.first_seen) >= datetime('now', ? || ' days')
                GROUP BY date(r.first_seen)
                ORDER BY date
            """, (f"-{days}",))
            risks_trend = [
                {"date": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]

            # Files over time
            cursor.execute("""
                SELECT date(f.first_seen) as date, COUNT(DISTINCT f.path) as count
                FROM files f
                WHERE datetime(f.first_seen) >= datetime('now', ? || ' days')
                GROUP BY date(f.first_seen)
                ORDER BY date
            """, (f"-{days}",))
            files_trend = [
                {"date": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]

            return {
                "sessions": sessions_trend,
                "risks": risks_trend,
                "files": files_trend,
                "days": days,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
            params = []

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
                predictions = pred.predictions if hasattr(pred, 'predictions') else []
            except (ValueError, RuntimeError, AttributeError):
                # If prediction fails, return empty list.
                predictions = []

            return {
                "risks": risks,
                "predictions": predictions,
                "total": len(risks),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/llm/status")
    async def llm_status():
        """Get LLM configuration and status."""
        try:
            from crumdbob.llm import is_llm_available

            config = db.get_llm_config()
            available = is_llm_available()
            cache_stats = db.get_llm_cache_stats()

            return {
                "configured": config is not None,
                "available": available,
                "config": config,
                "cache_stats": cache_stats,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/llm/analyze/{session_id}")
    async def llm_analyze_session(session_id: int):
        """Analyze a session with LLM."""
        try:
            from crumdbob.llm import create_llm_analyzer

            analyzer = create_llm_analyzer(db)
            if not analyzer:
                raise HTTPException(
                    status_code=503,
                    detail="LLM not configured or unavailable"
                )

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/llm/explain")
    async def llm_explain_pattern(pattern_data: dict):
        """Get LLM explanation of a pattern."""
        try:
            from crumdbob.llm import create_llm_analyzer

            analyzer = create_llm_analyzer(db)
            if not analyzer:
                raise HTTPException(
                    status_code=503,
                    detail="LLM not configured or unavailable"
                )

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/llm/recommend/{session_id}")
    async def llm_recommend_actions(session_id: int):
        """Get LLM recommendations for a session."""
        try:
            from crumdbob.llm import create_llm_analyzer

            analyzer = create_llm_analyzer(db)
            if not analyzer:
                raise HTTPException(
                    status_code=503,
                    detail="LLM not configured or unavailable"
                )

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
    import uvicorn

    app = create_app(db_path)

    # Open browser after a short delay
    if open_browser:
        import threading
        import time

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
