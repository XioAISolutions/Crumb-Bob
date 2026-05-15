# CrumbBob Web Dashboard

Interactive web dashboard for visualizing and querying CrumbBob intelligence data.

## Overview

The CrumbBob Web Dashboard provides a modern, user-friendly interface for exploring your development session history, insights, patterns, and risks. It's built with FastAPI for the backend and vanilla JavaScript for the frontend, making it lightweight and easy to deploy.

## Features

### 📊 Dashboard Overview
- Real-time statistics (sessions, files, risks, tasks)
- Session timeline chart
- Risk distribution visualization
- Recent activity feed

### 📝 Sessions View
- Browse all recorded sessions
- Filter and search sessions
- View detailed session information
- See files, commands, risks, and tasks per session

### 💡 Insights View
- AI-generated insights from your data
- Filter by severity (critical, high, medium, low)
- Actionable recommendations
- Confidence scores

### 🔍 Patterns View
- Detected patterns across sessions
- Recurring risks and issues
- File relationship patterns
- Command usage patterns

### ⚠️ Risks View
- All identified risks
- Filter by status (open, mitigated, accepted)
- Risk predictions
- Historical risk data

### 📈 Trends View
- Activity trends over time
- Customizable time periods (7, 30, 90 days)
- Multi-metric visualization
- Session, risk, and file trends

### 🔎 Query View
- Natural language queries
- Example queries for quick access
- SQL-like results display
- Query history

## Installation

### Requirements

```bash
pip install fastapi uvicorn[standard]
```

Or install with CrumbBob:

```bash
pip install crumdbob[web]
```

### Dependencies

- **FastAPI**: Modern web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI
- **Chart.js**: JavaScript charting library (loaded via CDN)

## Usage

### Starting the Server

```bash
# Start with default settings (localhost:8000)
crumdbob serve

# Specify custom host and port
crumdbob serve --host 127.0.0.1 --port 8080

# Use custom database
crumdbob serve --db /path/to/custom.db

# Don't open browser automatically
crumdbob serve --no-browser
```

Bind to `0.0.0.0` only on trusted networks. The dashboard API is intended for local development and does not provide authentication.

### Accessing the Dashboard

Once started, the dashboard is available at:
- **Main Dashboard**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## API Endpoints

### Core Endpoints

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": "/path/to/crumdbob.db"
}
```

#### `GET /api/stats`
Get dashboard statistics.

**Response:**
```json
{
  "total_sessions": 42,
  "total_files": 156,
  "total_commands": 89,
  "total_risks": 23,
  "total_tasks": 67,
  "open_risks": 5,
  "pending_tasks": 12,
  "recent_sessions": 8
}
```

#### `GET /api/sessions`
List all sessions with pagination.

**Query Parameters:**
- `limit` (int, default: 20): Number of sessions to return
- `offset` (int, default: 0): Offset for pagination

**Response:**
```json
{
  "sessions": [...],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

#### `GET /api/sessions/{id}`
Get detailed session information.

**Response:**
```json
{
  "session": {...},
  "files": [...],
  "commands": [...],
  "risks": [...],
  "tasks": [...]
}
```

#### `GET /api/insights`
List insights with optional filtering.

**Query Parameters:**
- `severity` (string, optional): Filter by severity (critical, high, medium, low)
- `limit` (int, default: 20): Number of insights to return

#### `GET /api/trends`
Get trend data over time.

**Query Parameters:**
- `days` (int, default: 30): Number of days to include

**Response:**
```json
{
  "sessions": [{"date": "2024-01-15", "count": 3}, ...],
  "risks": [{"date": "2024-01-15", "count": 2}, ...],
  "files": [{"date": "2024-01-15", "count": 15}, ...],
  "days": 30
}
```

#### `GET /api/patterns`
Get detected patterns.

**Response:**
```json
{
  "patterns": [...],
  "total": 15
}
```

#### `GET /api/risks`
Get risks with optional filtering.

**Query Parameters:**
- `status` (string, optional): Filter by status (open, mitigated, accepted)
- `limit` (int, default: 50): Number of risks to return

#### `POST /api/query`
Execute a natural language query.

**Request Body:**
```json
{
  "question": "Show me all authentication risks",
  "limit": 10
}
```

**Response:**
```json
{
  "query": "SELECT ...",
  "results": [...],
  "row_count": 5,
  "explanation": "Found 5 authentication-related risks"
}
```

## Architecture

### Backend (FastAPI)

```
web/api/
├── __init__.py       # Package initialization
└── server.py         # FastAPI application and endpoints
```

**Key Features:**
- Async/await for performance
- CORS enabled for local development
- Automatic OpenAPI documentation
- Request validation with Pydantic
- Database connection pooling

### Frontend (Vanilla JavaScript)

```
web/static/
├── index.html        # Main dashboard page
├── styles.css        # Styling and themes
└── app.js           # Frontend logic and API calls
```

**Key Features:**
- Single-page application (SPA)
- Chart.js for visualizations
- Dark/light theme support
- Responsive design
- Real-time updates (polling)

## Configuration

### Environment Variables

- `CRUMDBOB_DB_PATH`: Default database path
- `CRUMDBOB_WEB_HOST`: Default host (default: 127.0.0.1)
- `CRUMDBOB_WEB_PORT`: Default port (default: 8000)

### Database

The dashboard uses the same SQLite database as the CLI. By default, it looks for:
- `~/.crumdbob/memory.db` (Linux/Mac)
- `%USERPROFILE%\.crumdbob\memory.db` (Windows)

You can specify a custom database with `--db`:

```bash
crumdbob serve --db /path/to/custom.db
```

## Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run with auto-reload
uvicorn web.api.server:app --reload --host 127.0.0.1 --port 8000
```

### Running Tests

```bash
# Run API tests
pytest tests/test_api.py -v

# Run with coverage
pytest tests/test_api.py --cov=web.api --cov-report=html
```

### Adding New Endpoints

1. Add endpoint function to `web/api/server.py`
2. Add route decorator with path and method
3. Add request/response models if needed
4. Update frontend in `web/static/app.js`
5. Add tests in `tests/test_api.py`

Example:

```python
@app.get("/api/custom")
async def custom_endpoint():
    """Custom endpoint description."""
    return {"message": "Hello from custom endpoint"}
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
crumdbob serve --port 8080
```

### Database Not Found

If the database doesn't exist:

```bash
# Initialize database first
crumdbob init-db

# Then start server
crumdbob serve
```

### CORS Issues

If you're accessing the dashboard from a different origin, CORS is already enabled. For production, you may want to restrict allowed origins in `server.py`.

### Performance Issues

For large databases:
- Use pagination (limit/offset parameters)
- Filter data by date ranges
- Consider database indexing
- Use the CLI for bulk operations

## Security Considerations

### Local Development

The dashboard is designed for local development and should only be accessed on localhost (127.0.0.1) by default.

### Production Deployment

If deploying to production:

1. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Apache)
2. **Authentication**: Add authentication middleware
3. **CORS**: Restrict allowed origins
4. **Rate Limiting**: Add rate limiting to prevent abuse
5. **Database**: Use proper database permissions

Example nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name crumdbob.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Browser Support

The dashboard supports modern browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Contributing

Contributions are welcome! Please:

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Test on multiple browsers

## License

Same as CrumbBob main project (MIT License).

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/crumdbob/issues
- Documentation: https://github.com/yourusername/crumdbob/docs

## Roadmap

Future enhancements:
- [ ] Real-time updates via WebSockets
- [ ] Export data to CSV/JSON
- [ ] Custom dashboard widgets
- [ ] User preferences and saved queries
- [ ] Multi-user support with authentication
- [ ] Integration with CI/CD pipelines
- [ ] Mobile app
