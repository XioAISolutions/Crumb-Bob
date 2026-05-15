# Multi-Session Memory: Getting Started Guide

This guide will help you get started with CrumbBob's multi-session memory system, which enables persistent storage and querying of pack sessions across time.

## Quick Start

### 1. Initialize the Database

First, initialize the memory database:

```bash
crumdbob init-db
```

This creates `~/.crumdbob/memory.db` with the complete schema.

### 2. Record Your First Session

Generate a pack and record it to the database:

```bash
# Generate and record in one command
crumdbob pack ./input-dir --out ./pack-dir --record

# Or record an existing pack
crumdbob record ./pack-dir
```

### 3. List Your Sessions

View all recorded sessions:

```bash
# Table format (default)
crumdbob list-sessions

# JSON format
crumdbob list-sessions --format json

# Filter by branch
crumdbob list-sessions --branch main

# Filter by author
crumdbob list-sessions --author "Alice"
```

### 4. View Session Details

Get detailed information about a specific session:

```bash
crumdbob show-session 1
```

This displays:
- Session metadata (timestamp, Git context)
- Entity counts (files, commands, risks, tasks)
- First 20 files
- First 10 commands, risks, and tasks

## Configuration

### Enable Auto-Recording

Configure CrumbBob to automatically record all packs:

```bash
# Enable auto-recording
crumdbob config set auto_record true

# Now all pack commands automatically record
crumdbob pack ./input-dir --out ./pack-dir
# ✓ Recorded to database: Session #2
```

### View Configuration

```bash
# List all settings
crumdbob config list

# Get a specific value
crumdbob config get database_path

# Reset to defaults
crumdbob config reset
```

### Available Settings

- `database_path`: Database location (default: `~/.crumdbob/memory.db`)
- `auto_record`: Auto-record packs (default: `false`)
- `git_integration`: Enable Git context extraction (default: `true`)
- `team_mode`: Enable team collaboration features (default: `false`)

## Migrating Existing Packs

If you have existing file-based packs, migrate them to the database:

```bash
# Migrate single pack
crumdbob migrate-to-db ./pack-dir

# Migrate multiple packs
crumdbob migrate-to-db ./pack1 ./pack2 ./pack3

# Use custom database
crumdbob migrate-to-db ./pack-dir --db ./custom.db
```

## Common Workflows

### Workflow 1: Development Session

```bash
# 1. Auto-collect and record
crumdbob auto-collect --out ./pack --record

# 2. View what was recorded
crumdbob show-session $(crumdbob list-sessions --format json | jq -r '.[0].id')

# 3. Continue working...

# 4. Generate new pack and record
crumdbob pack ./input --out ./pack-v2 --record
```

### Workflow 2: Team Collaboration

```bash
# Alice records her session
crumdbob pack ./input --out ./pack-alice --record

# Bob records his session
crumdbob pack ./input --out ./pack-bob --record

# View all team sessions
crumdbob list-sessions

# Compare sessions (future feature)
crumdbob diff ./pack-alice ./pack-bob
```

### Workflow 3: Historical Analysis

```bash
# List all sessions
crumdbob list-sessions --limit 50

# Find sessions by branch
crumdbob list-sessions --branch feature/new-api

# View session timeline
crumdbob list-sessions --format json | jq '.[] | {id, timestamp, branch, files: .file_count}'
```

## Advanced Usage

### Custom Database Location

Use a project-specific database:

```bash
# Set custom database path
crumdbob config set database_path ./project-memory.db

# Or use --db flag
crumdbob record ./pack --db ./project-memory.db
```

### Session Naming

Give sessions meaningful names:

```bash
crumdbob record ./pack --session-name "API v2 implementation"
```

### Querying with Python

```python
from crumdbob.memory import MemoryDatabase

with MemoryDatabase("~/.crumdbob/memory.db") as db:
    # Get recent sessions
    sessions = db.list_sessions(limit=10)
    
    # Search for files
    py_files = db.search_files("%.py")
    
    # Find open risks
    risks = db.search_risks(status="open")
    
    # Get session timeline
    timeline = db.get_session_timeline(limit=20)
```

## Database Schema

The memory database includes:

### Core Tables
- `sessions` - Pack sessions with metadata
- `packs` - Pack version history
- `files` - Files mentioned in sessions
- `commands` - Commands captured
- `risks` - Identified risks
- `tasks` - Next steps/tasks
- `relationships` - CRUMB dependencies
- `insights` - AI-generated insights (future)

### Views
- `session_summary` - Session overview with counts
- `file_history` - File mention history
- `risk_summary` - Risk aggregation
- `command_frequency` - Command usage stats

### Indexes
12+ indexes for fast queries on:
- Timestamps
- Git context (branch, author)
- File paths
- Risk status
- Task status

## Troubleshooting

### Database Not Found

```bash
# Initialize if missing
crumdbob init-db

# Or specify path
crumdbob init-db --path ./my-db.db
```

### Migration Errors

```bash
# Check pack structure
crumdbob doctor ./pack-dir

# Validate before migrating
crumdbob validate ./pack-dir
```

### Performance

For large databases:
- Use filters (`--branch`, `--author`, `--limit`)
- Query specific date ranges
- Use JSON format for programmatic access

## Next Steps

- **Phase 2**: Intelligent queries across sessions
- **Phase 3**: Pattern detection and insights
- **Phase 4**: Predictive suggestions
- **Phase 5**: Team collaboration features

See [Multi-Session Memory Design](./multi-session-memory-design.md) for the complete roadmap.

## Examples

See [Multi-Session Memory Examples](./multi-session-memory-examples.md) for detailed usage examples and query patterns.