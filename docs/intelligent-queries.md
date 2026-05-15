# Intelligent Queries Guide

CrumbBob's query engine allows you to ask questions about your development history using natural language, templates, or direct SQL.

## Natural Language Queries

Ask questions in plain English and CrumbBob will translate them to SQL:

```bash
# Find authentication-related risks
crumdbob query natural "Show me all authentication risks"

# Find frequently changed files
crumdbob query natural "What files changed most in the last month?"

# Find incomplete tasks
crumdbob query natural "Which tasks were never completed?"

# Find most used commands
crumdbob query natural "What commands are used most frequently?"

# Find recent sessions
crumdbob query natural "Show me recent sessions"
```

### Supported Query Patterns

**Risk Queries:**
- "Show me all [type] risks" (e.g., authentication, security)
- "Show me all open/unresolved risks"
- "List all risks"

**File Queries:**
- "What files changed most [in the last X]?"
- "Show me files matching [pattern]"
- "Show me hot files"

**Task Queries:**
- "Which tasks were never completed?"
- "Show me pending/incomplete tasks"
- "Show me completed tasks"
- "Show me in-progress tasks"

**Command Queries:**
- "What commands are used most?"
- "Show me all commands"

**Session Queries:**
- "Show me recent sessions"
- "Show me sessions by [author]"
- "Show me sessions on branch [name]"

## Template Queries

Use predefined templates with parameters for common queries:

```bash
# List available templates
crumdbob query list-templates

# Query with template
crumdbob query template risks-by-severity --params status=open limit=20
crumdbob query template files-by-frequency --params limit=10
crumdbob query template tasks-by-status --params status=pending
crumdbob query template hot-files --params min_sessions=3 limit=15
```

### Available Templates

- **risks-by-severity**: Filter risks by status
  - Parameters: `status` (open/mitigated/accepted), `limit`

- **files-by-frequency**: Most frequently changed files
  - Parameters: `limit`

- **tasks-by-status**: Filter tasks by status
  - Parameters: `status` (pending/in_progress/completed), `limit`

- **commands-by-frequency**: Most used commands
  - Parameters: `limit`

- **sessions-by-author**: Sessions by Git author
  - Parameters: `author`, `limit`

- **sessions-by-branch**: Sessions by Git branch
  - Parameters: `branch`, `limit`

- **recent-sessions**: Most recent sessions
  - Parameters: `limit`

- **hot-files**: Files changed across multiple sessions
  - Parameters: `min_sessions`, `limit`

- **recurring-risks**: Risks appearing in multiple sessions
  - Parameters: `min_sessions`

## Direct SQL Queries

For power users, execute SQL directly:

```bash
# Custom SQL query
crumdbob query sql "SELECT * FROM risks WHERE description LIKE '%auth%' LIMIT 10"

# Complex aggregation
crumdbob query sql "SELECT git_branch, COUNT(*) as count FROM sessions GROUP BY git_branch"

# Join queries
crumdbob query sql "SELECT s.timestamp, r.description FROM sessions s JOIN risks r ON s.id = r.session_id WHERE s.git_author = 'john'"
```

### Database Schema

Key tables:
- `sessions`: Recorded pack sessions
- `files`: Files mentioned in sessions
- `commands`: Commands captured in sessions
- `risks`: Identified risks
- `tasks`: Next steps/tasks
- `insights`: Generated insights

Views:
- `session_summary`: Session overview with counts
- `file_history`: File change history
- `risk_summary`: Risk occurrence summary
- `command_frequency`: Command usage frequency

## Output Formats

### Table Format (Default)

```bash
crumdbob query natural "Show me all risks"
```

Output:
```
Query: Found 15 risks matching pattern '%auth%'
Results: 15 row(s)

id | session_id | description | status | first_seen | last_seen
-------------------------------------------------------------------
1  | 5          | Auth token... | open   | 2024-01-15 | 2024-01-20
2  | 3          | Session sec... | open   | 2024-01-10 | 2024-01-18
...
```

### JSON Format

```bash
crumdbob query natural "Show me all risks" --format json
```

Output:
```json
[
  {
    "id": 1,
    "session_id": 5,
    "description": "Authentication token expiration not handled",
    "status": "open",
    "first_seen": "2024-01-15T10:30:00Z",
    "last_seen": "2024-01-20T14:22:00Z"
  }
]
```

## Query Performance

- All queries are optimized with database indexes
- Typical query time: <100ms
- Large result sets are automatically limited
- Use `--limit` parameter to control result size

## Examples

### Find Security Issues

```bash
# Natural language
crumdbob query natural "Show me all security risks"

# Template
crumdbob query template risks-by-severity --params status=open

# SQL
crumdbob query sql "SELECT * FROM risks WHERE description LIKE '%security%' OR description LIKE '%vulnerability%'"
```

### Analyze File Changes

```bash
# Most changed files
crumdbob query natural "What files changed most?"

# Files in specific directory
crumdbob query sql "SELECT * FROM files WHERE path LIKE 'src/auth/%'"

# Hot files (changed across sessions)
crumdbob query template hot-files --params min_sessions=3
```

### Track Task Progress

```bash
# Incomplete tasks
crumdbob query natural "Which tasks were never completed?"

# All pending tasks
crumdbob query template tasks-by-status --params status=pending

# Tasks by session
crumdbob query sql "SELECT s.timestamp, t.description FROM tasks t JOIN sessions s ON t.session_id = s.id WHERE t.status = 'pending'"
```

### Command Analysis

```bash
# Most used commands
crumdbob query natural "What commands are used most?"

# Test commands
crumdbob query sql "SELECT * FROM commands WHERE command LIKE '%test%'"

# Command frequency
crumdbob query template commands-by-frequency --params limit=20
```

## Tips

1. **Start with natural language** - Try natural language first, it's the easiest
2. **Use templates for common queries** - Templates are faster and more reliable
3. **Use SQL for complex analysis** - SQL gives you full power when needed
4. **Combine with other commands** - Use with `insights` and `patterns` for deeper analysis
5. **Export to JSON** - Use `--format json` for programmatic processing

## Integration

Query results can be piped to other tools:

```bash
# Export to file
crumdbob query natural "Show me all risks" --format json > risks.json

# Count results
crumdbob query natural "Show me all risks" | wc -l

# Filter with grep
crumdbob query natural "Show me all commands" | grep test
```

## Next Steps

- Learn about [Pattern Detection](pattern-detection.md)
- Explore [Insights System](insights.md)
- Try [Predictions](predictions.md)
- View the [Dashboard](../README.md#dashboard)