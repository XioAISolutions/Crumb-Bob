# Multi-Session Memory System - Design Document

## Executive Summary

Transform CrumbBob from a single-session pack generator into an **organizational intelligence platform** that tracks, analyzes, and learns from every Bob session across time and team members.

**Vision**: Make CrumbBob indispensable by creating a persistent memory layer that captures institutional knowledge, detects patterns, predicts impacts, and enables team collaboration.

**Core Value Proposition**: 
- Track how understanding of the codebase evolves over time
- Identify recurring patterns: risks, tasks, file changes
- Enable cross-session intelligence and team collaboration
- Predict impact of changes based on historical patterns
- Create quality gates based on historical data

---

## 1. Architecture Overview

### Current State (File-Based)
```
Bob Report → Parser → Packer → 8 CRUMB Files + Proof Chain
                                ↓
                         Isolated Pack Directory
                         (No connection to other sessions)
```

### Future State (Memory-Based)
```
Bob Report → Parser → Packer → Pack Files
                ↓              ↓
         Memory Recorder → SQLite Database
                ↓
    ┌───────────┴───────────┐
    │   Multi-Session DB    │
    │  - Sessions           │
    │  - Packs              │
    │  - Files              │
    │  - Commands           │
    │  - Risks              │
    │  - Tasks              │
    │  - Relationships      │
    │  - Insights           │
    └───────────┬───────────┘
                ↓
    ┌───────────┴───────────┐
    │  Intelligence Engine  │
    │  - Pattern Detection  │
    │  - Impact Prediction  │
    │  - Trend Analysis     │
    │  - Anomaly Detection  │
    └───────────┬───────────┘
                ↓
    Query API / CLI / Dashboard
```

---

## 2. Database Schema Design

### 2.1 Core Tables

#### `sessions` - Bob Session Metadata
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,              -- UUID v4
    timestamp TEXT NOT NULL,          -- ISO 8601 UTC
    title TEXT NOT NULL,              -- From Bob report
    summary TEXT,                     -- Project summary
    bob_report_path TEXT NOT NULL,    -- Source report path
    bob_report_hash TEXT NOT NULL,    -- SHA256 of source
    pack_dir TEXT NOT NULL,           -- Generated pack location
    parent_session_id TEXT,           -- Link to previous session
    branch_name TEXT,                 -- Git branch if available
    commit_hash TEXT,                 -- Git commit if available
    author TEXT,                      -- Who ran the session
    crumdbob_version TEXT NOT NULL,   -- Version used
    created_at TEXT NOT NULL,         -- Record creation time
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_sessions_timestamp ON sessions(timestamp);
CREATE INDEX idx_sessions_branch ON sessions(branch_name);
CREATE INDEX idx_sessions_author ON sessions(author);
CREATE INDEX idx_sessions_parent ON sessions(parent_session_id);
```

#### `packs` - Generated Pack Versions
```sql
CREATE TABLE packs (
    id TEXT PRIMARY KEY,              -- UUID v4
    session_id TEXT NOT NULL,         -- Link to session
    pack_dir TEXT NOT NULL,           -- Pack directory path
    proof_chain_hash TEXT NOT NULL,   -- SHA256 of proof chain
    file_count INTEGER NOT NULL,      -- Number of files extracted
    command_count INTEGER NOT NULL,   -- Number of commands
    risk_count INTEGER NOT NULL,      -- Number of risks
    test_count INTEGER NOT NULL,      -- Number of tests
    task_count INTEGER NOT NULL,      -- Number of next steps
    validation_status TEXT NOT NULL,  -- valid, invalid, unknown
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_packs_session ON packs(session_id);
CREATE INDEX idx_packs_validation ON packs(validation_status);
```

#### `files` - Files Mentioned Across Sessions
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,   -- Normalized file path
    first_seen_session TEXT NOT NULL, -- First session mentioning it
    last_seen_session TEXT NOT NULL,  -- Most recent session
    mention_count INTEGER DEFAULT 1,  -- How many sessions mention it
    file_type TEXT,                   -- Extension-based type
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (first_seen_session) REFERENCES sessions(id),
    FOREIGN KEY (last_seen_session) REFERENCES sessions(id)
);

CREATE INDEX idx_files_path ON files(file_path);
CREATE INDEX idx_files_type ON files(file_type);
CREATE INDEX idx_files_mention_count ON files(mention_count DESC);
```

#### `session_files` - File Mentions Per Session
```sql
CREATE TABLE session_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    context TEXT,                     -- How file was mentioned
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    UNIQUE(session_id, file_id)
);

CREATE INDEX idx_session_files_session ON session_files(session_id);
CREATE INDEX idx_session_files_file ON session_files(file_id);
```

#### `commands` - Commands Extracted
```sql
CREATE TABLE commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_text TEXT NOT NULL,       -- Normalized command
    command_hash TEXT NOT NULL UNIQUE,-- SHA256 for deduplication
    first_seen_session TEXT NOT NULL,
    last_seen_session TEXT NOT NULL,
    mention_count INTEGER DEFAULT 1,
    command_type TEXT,                -- npm, pytest, git, etc.
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (first_seen_session) REFERENCES sessions(id),
    FOREIGN KEY (last_seen_session) REFERENCES sessions(id)
);

CREATE INDEX idx_commands_hash ON commands(command_hash);
CREATE INDEX idx_commands_type ON commands(command_type);
CREATE INDEX idx_commands_mention_count ON commands(mention_count DESC);
```

#### `session_commands` - Commands Per Session
```sql
CREATE TABLE session_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    command_id INTEGER NOT NULL,
    context TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (command_id) REFERENCES commands(id) ON DELETE CASCADE,
    UNIQUE(session_id, command_id)
);

CREATE INDEX idx_session_commands_session ON session_commands(session_id);
CREATE INDEX idx_session_commands_command ON session_commands(command_id);
```

#### `risks` - Risk Register Across Time
```sql
CREATE TABLE risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_text TEXT NOT NULL,
    risk_hash TEXT NOT NULL UNIQUE,   -- SHA256 for deduplication
    first_seen_session TEXT NOT NULL,
    last_seen_session TEXT NOT NULL,
    status TEXT NOT NULL,             -- new, ongoing, resolved, ignored
    severity TEXT,                    -- high, medium, low (AI-derived)
    category TEXT,                    -- security, performance, etc.
    resolution_session TEXT,          -- Session where resolved
    resolution_notes TEXT,
    mention_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (first_seen_session) REFERENCES sessions(id),
    FOREIGN KEY (last_seen_session) REFERENCES sessions(id),
    FOREIGN KEY (resolution_session) REFERENCES sessions(id)
);

CREATE INDEX idx_risks_hash ON risks(risk_hash);
CREATE INDEX idx_risks_status ON risks(status);
CREATE INDEX idx_risks_severity ON risks(severity);
CREATE INDEX idx_risks_category ON risks(category);
```

#### `session_risks` - Risks Per Session
```sql
CREATE TABLE session_risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    risk_id INTEGER NOT NULL,
    context TEXT,
    status_in_session TEXT,           -- Status at this point in time
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (risk_id) REFERENCES risks(id) ON DELETE CASCADE,
    UNIQUE(session_id, risk_id)
);

CREATE INDEX idx_session_risks_session ON session_risks(session_id);
CREATE INDEX idx_session_risks_risk ON session_risks(risk_id);
CREATE INDEX idx_session_risks_status ON session_risks(status_in_session);
```

#### `tasks` - Next Steps Tracking
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_text TEXT NOT NULL,
    task_hash TEXT NOT NULL UNIQUE,
    first_seen_session TEXT NOT NULL,
    last_seen_session TEXT NOT NULL,
    status TEXT NOT NULL,             -- pending, in_progress, completed, abandoned
    priority TEXT,                    -- high, medium, low
    completion_session TEXT,
    completion_time_days REAL,        -- Days from first seen to completion
    mention_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (first_seen_session) REFERENCES sessions(id),
    FOREIGN KEY (last_seen_session) REFERENCES sessions(id),
    FOREIGN KEY (completion_session) REFERENCES sessions(id)
);

CREATE INDEX idx_tasks_hash ON tasks(task_hash);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
```

#### `session_tasks` - Tasks Per Session
```sql
CREATE TABLE session_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    task_id INTEGER NOT NULL,
    context TEXT,
    status_in_session TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE(session_id, task_id)
);

CREATE INDEX idx_session_tasks_session ON session_tasks(session_id);
CREATE INDEX idx_session_tasks_task ON session_tasks(task_id);
```

#### `relationships` - File Co-Change Patterns
```sql
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file1_id INTEGER NOT NULL,
    file2_id INTEGER NOT NULL,
    co_change_count INTEGER DEFAULT 1,  -- How often changed together
    confidence REAL,                     -- 0.0 to 1.0
    relationship_type TEXT,              -- imports, tests, config, etc.
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (file1_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (file2_id) REFERENCES files(id) ON DELETE CASCADE,
    UNIQUE(file1_id, file2_id),
    CHECK(file1_id < file2_id)          -- Prevent duplicates
);

CREATE INDEX idx_relationships_file1 ON relationships(file1_id);
CREATE INDEX idx_relationships_file2 ON relationships(file2_id);
CREATE INDEX idx_relationships_confidence ON relationships(confidence DESC);
```

#### `insights` - Derived Intelligence
```sql
CREATE TABLE insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_type TEXT NOT NULL,       -- pattern, anomaly, prediction, trend
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    confidence REAL,                  -- 0.0 to 1.0
    severity TEXT,                    -- info, warning, critical
    related_sessions TEXT,            -- JSON array of session IDs
    related_files TEXT,               -- JSON array of file paths
    related_risks TEXT,               -- JSON array of risk IDs
    metadata TEXT,                    -- JSON for extensibility
    created_at TEXT NOT NULL,
    expires_at TEXT                   -- Optional expiration
);

CREATE INDEX idx_insights_type ON insights(insight_type);
CREATE INDEX idx_insights_severity ON insights(severity);
CREATE INDEX idx_insights_created ON insights(created_at DESC);
```

### 2.2 Views for Common Queries

```sql
-- Active risks across all sessions
CREATE VIEW active_risks AS
SELECT 
    r.id,
    r.risk_text,
    r.severity,
    r.category,
    r.first_seen_session,
    r.last_seen_session,
    r.mention_count,
    s.timestamp as last_seen_timestamp
FROM risks r
JOIN sessions s ON r.last_seen_session = s.id
WHERE r.status IN ('new', 'ongoing')
ORDER BY r.severity DESC, r.mention_count DESC;

-- Most frequently changed files
CREATE VIEW hot_files AS
SELECT 
    f.file_path,
    f.file_type,
    f.mention_count,
    f.first_seen_session,
    f.last_seen_session,
    s.timestamp as last_seen_timestamp
FROM files f
JOIN sessions s ON f.last_seen_session = s.id
ORDER BY f.mention_count DESC;

-- Task completion metrics
CREATE VIEW task_metrics AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(completion_time_days) as avg_completion_days,
    MIN(completion_time_days) as min_completion_days,
    MAX(completion_time_days) as max_completion_days
FROM tasks
WHERE status = 'completed'
GROUP BY status;

-- Session timeline
CREATE VIEW session_timeline AS
SELECT 
    s.id,
    s.timestamp,
    s.title,
    s.author,
    s.branch_name,
    p.file_count,
    p.command_count,
    p.risk_count,
    p.task_count
FROM sessions s
LEFT JOIN packs p ON s.id = p.session_id
ORDER BY s.timestamp DESC;
```

---

## 3. CLI Commands Design

### 3.1 Database Management

```bash
# Initialize memory database
crumdbob init-db [--path ./crumdbob.db]
# Creates SQLite database with schema
# Sets up indexes and views
# Creates default configuration

# Database info
crumdbob db-info
# Shows database location, size, session count, etc.

# Database maintenance
crumdbob db-vacuum
# Optimizes database, reclaims space

crumdbob db-backup --out backup.db
# Creates backup of database

crumdbob db-restore --from backup.db
# Restores from backup
```

### 3.2 Session Recording

```bash
# Record a pack to memory database
crumdbob record <pack-dir> [--parent-session <id>]
# Analyzes pack and stores in database
# Links to parent session if provided
# Auto-detects Git context (branch, commit, author)

# Record with auto-collect
crumdbob pack . --out generated --record
# Generates pack AND records to database in one step

# Record existing packs in bulk
crumdbob record-bulk <directory>
# Recursively finds and records all packs
```

### 3.3 Querying

```bash
# Natural language queries
crumdbob query "What did Bob discover about authentication in the last 3 sessions?"
crumdbob query "Show me all risks related to database migrations"
crumdbob query "Which files has Bob analyzed most frequently?"
crumdbob query "What tasks were marked as next steps but never completed?"

# Structured queries
crumdbob search --type risk --status unresolved --severity high
crumdbob search --type file --path "packages/auth/*" --min-mentions 3
crumdbob search --type command --contains "pytest"
crumdbob search --type task --status pending --priority high

# SQL-like query language
crumdbob sql "SELECT * FROM active_risks WHERE severity='high'"
crumdbob sql "SELECT file_path, mention_count FROM hot_files LIMIT 10"
```

### 3.4 Insights & Analytics

```bash
# Generate insights from history
crumdbob insights [--type pattern|anomaly|prediction|trend]
# Analyzes database and generates insights
# Stores in insights table

# Show insights
crumdbob insights list [--severity critical|warning|info]
crumdbob insights show <insight-id>

# Timeline visualization
crumdbob timeline [--format text|json|mermaid]
# Shows session timeline with key metrics

# Trend analysis
crumdbob trends --metric risks
crumdbob trends --metric task-completion
crumdbob trends --metric file-churn

# Pattern detection
crumdbob patterns --type risk
crumdbob patterns --type file-cochange
crumdbob patterns --type recurring-task
```

### 3.5 Impact Prediction

```bash
# Predict impact of changes
crumdbob predict <file-path>
# Based on past sessions, predicts:
# - Other files likely to be affected
# - Risks that may arise
# - Tests that should be run
# - Estimated complexity

# Predict from diff
crumdbob predict --from-diff git-diff.patch
# Analyzes diff and predicts impact

# Predict from task
crumdbob predict --task "Add OAuth authentication"
# Finds similar tasks and predicts impact
```

### 3.6 Comparison & Diff

```bash
# Compare sessions
crumdbob session-diff <session-id-1> <session-id-2>
# Shows what changed between sessions

# Compare with current state
crumdbob session-diff <session-id> --current
# Compares historical session with current repo state

# Risk evolution
crumdbob risk-history <risk-id>
# Shows how a risk evolved across sessions

# Task tracking
crumdbob task-history <task-id>
# Shows task lifecycle across sessions
```

### 3.7 Team Collaboration

```bash
# List all sessions
crumdbob sessions [--author <name>] [--branch <name>] [--since <date>]

# Session details
crumdbob session <session-id>
# Shows full session details

# Team dashboard
crumdbob dashboard [--port 8080]
# Starts web dashboard showing team activity

# Export for sharing
crumdbob export <session-id> --format json|markdown
# Exports session data for sharing
```

---

## 4. Query Language Design

### 4.1 Natural Language to SQL Translation

```python
# crumdbob/query_translator.py
class QueryTranslator:
    """Translates natural language queries to SQL"""
    
    PATTERNS = {
        "authentication": ["auth", "login", "password", "oauth", "jwt"],
        "database": ["db", "sql", "migration", "schema", "query"],
        "security": ["xss", "csrf", "injection", "vulnerability"],
        # ... more patterns
    }
    
    def translate(self, query: str) -> str:
        """Convert natural language to SQL"""
        # Example: "risks about authentication"
        # -> SELECT * FROM risks WHERE risk_text LIKE '%auth%' OR ...
```

### 4.2 Predefined Query Templates

```python
QUERY_TEMPLATES = {
    "recent_sessions": """
        SELECT * FROM session_timeline 
        WHERE timestamp > datetime('now', '-{days} days')
        ORDER BY timestamp DESC
    """,
    
    "unresolved_risks": """
        SELECT * FROM active_risks
        WHERE severity IN ({severities})
        ORDER BY mention_count DESC, severity DESC
    """,
    
    "hot_files": """
        SELECT * FROM hot_files
        WHERE mention_count >= {min_mentions}
        LIMIT {limit}
    """,
    
    "pending_tasks": """
        SELECT * FROM tasks
        WHERE status = 'pending'
        AND priority IN ({priorities})
        ORDER BY priority DESC, created_at ASC
    """,
    
    "file_cochanges": """
        SELECT f1.file_path as file1, f2.file_path as file2, r.co_change_count
        FROM relationships r
        JOIN files f1 ON r.file1_id = f1.id
        JOIN files f2 ON r.file2_id = f2.id
        WHERE r.confidence > {min_confidence}
        ORDER BY r.co_change_count DESC
    """
}
```

### 4.3 Query API

```python
# crumdbob/query_api.py
class QueryAPI:
    """High-level query interface"""
    
    def find_risks(
        self,
        status: list[str] = None,
        severity: list[str] = None,
        category: list[str] = None,
        text_contains: str = None,
        limit: int = 100
    ) -> list[Risk]:
        """Find risks matching criteria"""
    
    def find_files(
        self,
        path_pattern: str = None,
        file_type: str = None,
        min_mentions: int = 1,
        limit: int = 100
    ) -> list[File]:
        """Find files matching criteria"""
    
    def find_sessions(
        self,
        author: str = None,
        branch: str = None,
        since: datetime = None,
        until: datetime = None,
        limit: int = 100
    ) -> list[Session]:
        """Find sessions matching criteria"""
    
    def get_session_timeline(
        self,
        since: datetime = None,
        limit: int = 50
    ) -> list[SessionSummary]:
        """Get chronological session timeline"""
    
    def get_file_relationships(
        self,
        file_path: str,
        min_confidence: float = 0.5
    ) -> list[FileRelationship]:
        """Get files frequently changed with this file"""
```

---

## 5. Intelligence Engine Design

### 5.1 Pattern Detection

```python
# crumdbob/intelligence/patterns.py
class PatternDetector:
    """Detects patterns across sessions"""
    
    def detect_recurring_risks(self) -> list[Insight]:
        """Find risks that appear repeatedly"""
        # Query risks with mention_count > threshold
        # Group by similarity (fuzzy matching)
        # Generate insights about recurring issues
    
    def detect_file_clusters(self) -> list[Insight]:
        """Find files that are frequently changed together"""
        # Analyze relationships table
        # Use clustering algorithm
        # Identify modules/components
    
    def detect_task_patterns(self) -> list[Insight]:
        """Find common task types and completion patterns"""
        # Analyze task completion times
        # Group similar tasks
        # Identify bottlenecks
    
    def detect_risk_patterns(self) -> list[Insight]:
        """Find risk categories and trends"""
        # Categorize risks by type
        # Track resolution patterns
        # Identify high-risk areas
```

### 5.2 Impact Prediction

```python
# crumdbob/intelligence/predictor.py
class ImpactPredictor:
    """Predicts impact of changes"""
    
    def predict_affected_files(
        self,
        changed_files: list[str]
    ) -> list[tuple[str, float]]:
        """Predict other files likely to be affected"""
        # Use file relationships
        # Calculate probability based on co-change history
        # Return ranked list with confidence scores
    
    def predict_risks(
        self,
        changed_files: list[str],
        task_description: str = None
    ) -> list[tuple[Risk, float]]:
        """Predict risks that may arise"""
        # Find historical risks for these files
        # Use NLP to match task description to past risks
        # Return ranked list with confidence scores
    
    def predict_complexity(
        self,
        task_description: str
    ) -> dict:
        """Predict task complexity"""
        # Find similar historical tasks
        # Analyze completion times
        # Return complexity estimate with confidence
    
    def predict_required_tests(
        self,
        changed_files: list[str]
    ) -> list[str]:
        """Predict which tests should be run"""
        # Find test files related to changed files
        # Use historical test patterns
        # Return prioritized test list
```

### 5.3 Trend Analysis

```python
# crumdbob/intelligence/trends.py
class TrendAnalyzer:
    """Analyzes trends over time"""
    
    def analyze_risk_trends(
        self,
        time_window_days: int = 90
    ) -> dict:
        """Analyze how risks are trending"""
        # Count new vs resolved risks over time
        # Calculate risk velocity
        # Identify improving/degrading areas
    
    def analyze_task_velocity(
        self,
        time_window_days: int = 90
    ) -> dict:
        """Analyze task completion velocity"""
        # Calculate tasks completed per time period
        # Identify velocity trends
        # Predict future capacity
    
    def analyze_file_churn(
        self,
        time_window_days: int = 90
    ) -> dict:
        """Analyze file change frequency"""
        # Track which files change most often
        # Identify stability trends
        # Flag high-churn areas
    
    def analyze_code_quality_trends(
        self,
        time_window_days: int = 90
    ) -> dict:
        """Analyze code quality metrics over time"""
        # Track test coverage trends
        # Monitor risk density
        # Identify quality improvements/regressions
```

### 5.4 Anomaly Detection

```python
# crumdbob/intelligence/anomalies.py
class AnomalyDetector:
    """Detects unusual patterns"""
    
    def detect_unusual_risks(self) -> list[Insight]:
        """Find risks that are unusual or unexpected"""
        # Compare current risks to historical patterns
        # Flag new risk categories
        # Identify severity anomalies
    
    def detect_unusual_file_changes(self) -> list[Insight]:
        """Find unusual file change patterns"""
        # Detect files changing more than usual
        # Identify unexpected file relationships
        # Flag potential issues
    
    def detect_stalled_tasks(self) -> list[Insight]:
        """Find tasks that are taking longer than expected"""
        # Compare task duration to historical average
        # Flag tasks exceeding expected time
        # Suggest interventions
```

---

## 6. Integration Points

### 6.1 Git Integration

```python
# crumdbob/integrations/git.py
class GitIntegration:
    """Deep Git integration"""
    
    def auto_record_on_commit(self):
        """Git hook: record pack after commit"""
        # Install post-commit hook
        # Auto-generate and record pack
        # Link to commit hash
    
    def link_session_to_commit(self, session_id: str, commit_hash: str):
        """Link session to specific commit"""
    
    def generate_from_pr(self, base_branch: str, head_branch: str):
        """Generate pack from PR diff"""
        # Get diff between branches
        # Generate pack
        # Record with PR context
    
    def track_branch_sessions(self, branch_name: str):
        """Get all sessions for a branch"""
```

### 6.2 CI/CD Integration

```yaml
# .github/workflows/crumdbob-memory.yml
name: CrumbBob Memory Recording
on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  record-session:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup CrumbBob
        run: pip install crumdbob
      
      - name: Initialize database
        run: crumdbob init-db --path .crumdbob/memory.db
      
      - name: Generate and record pack
        run: |
          crumdbob auto-collect --out ./pack --no-interactive
          crumdbob record ./pack --parent-session ${{ env.PARENT_SESSION }}
      
      - name: Generate insights
        run: crumdbob insights --type anomaly
      
      - name: Check quality gates
        run: |
          # Fail if critical risks detected
          crumdbob query "SELECT COUNT(*) FROM active_risks WHERE severity='critical'" | \
            grep -q "^0$" || exit 1
      
      - name: Upload database
        uses: actions/upload-artifact@v3
        with:
          name: crumdbob-memory
          path: .crumdbob/memory.db
```

### 6.3 VSCode Extension Integration

```typescript
// vscode-crumdbob/src/memoryExplorer.ts
export class MemoryExplorer implements vscode.TreeDataProvider<MemoryNode> {
    // Show session history in sidebar
    // Display active risks inline
    // Show file relationships
    // Predict impact on file changes
    
    async getChildren(element?: MemoryNode): Promise<MemoryNode[]> {
        if (!element) {
            return [
                new MemoryNode('Recent Sessions', 'sessions'),
                new MemoryNode('Active Risks', 'risks'),
                new MemoryNode('Pending Tasks', 'tasks'),
                new MemoryNode('Hot Files', 'files'),
                new MemoryNode('Insights', 'insights')
            ];
        }
        
        // Query database based on node type
        const db = await this.getDatabase();
        return db.query(element.type);
    }
}

// Inline risk annotations
export class RiskAnnotationProvider implements vscode.CodeLensProvider {
    async provideCodeLenses(document: vscode.TextDocument): Promise<vscode.CodeLens[]> {
        // Query risks for this file
        const risks = await queryRisksForFile(document.fileName);
        
        // Create code lenses at relevant lines
        return risks.map(risk => new vscode.CodeLens(
            new vscode.Range(risk.line, 0, risk.line, 0),
            {
                title: `⚠️ Risk: ${risk.text}`,
                command: 'crumdbob.showRiskDetails',
                arguments: [risk.id]
            }
        ));
    }
}
```

---

## 7. Privacy & Security Design

### 7.1 Data Privacy

```python
# crumdbob/security/privacy.py
class PrivacyManager:
    """Manages data privacy and PII protection"""
    
    def sanitize_content(self, text: str) -> str:
        """Remove PII from content before storing"""
        # Redact emails, API keys, passwords
        # Anonymize user names if configured
        # Remove sensitive paths
    
    def configure_retention(self, days: int):
        """Set data retention policy"""
        # Auto-delete sessions older than N days
        # Archive instead of delete if configured
    
    def export_user_data(self, author: str) -> dict:
        """Export all data for a user (GDPR compliance)"""
    
    def delete_user_data(self, author: str):
        """Delete all data for a user (GDPR compliance)"""
```

### 7.2 Access Control

```python
# crumdbob/security/access.py
class AccessControl:
    """Manages access to memory database"""
    
    def set_database_permissions(self, mode: str):
        """Set file permissions on database"""
        # user-only, team-shared, world-readable
    
    def encrypt_database(self, password: str):
        """Encrypt database with password"""
        # Use SQLCipher for encryption
    
    def configure_team_access(self, team_members: list[str]):
        """Configure which team members can access"""
```

### 7.3 Audit Trail

```sql
-- Audit log for database operations
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    operation TEXT NOT NULL,      -- insert, update, delete, query
    table_name TEXT NOT NULL,
    record_id TEXT,
    user TEXT,
    details TEXT,                 -- JSON with operation details
    created_at TEXT NOT NULL
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_operation ON audit_log(operation);
CREATE INDEX idx_audit_user ON audit_log(user);
```

---

## 8. Migration Strategy

### 8.1 From File-Based to Database

```python
# crumdbob/migration/migrate.py
class MigrationManager:
    """Manages migration from file-based to database"""
    
    def migrate_existing_packs(self, directory: Path):
        """Migrate all existing packs to database"""
        # Find all pack directories
        # Parse each pack
        # Record to database
        # Preserve timestamps from proof chains
        # Link sessions based on git history
    
    def verify_migration(self) -> bool:
        """Verify migration completed successfully"""
        # Check all packs were migrated
        # Verify data integrity
        # Compare counts
```

### 8.2 Backward Compatibility

```python
# Ensure file-based operations still work
class BackwardCompatibility:
    """Maintains backward compatibility"""
    
    def generate_pack_files(self, session_id: str, output_dir: Path):
        """Generate traditional pack files from database"""
        # Query session data
        # Generate CRUMB files
        # Create proof chain
        # Maintain exact same format
    
    def support_legacy_commands(self):
        """Ensure old CLI commands still work"""
        # crumdbob pack -> works as before
        # crumdbob validate -> works as before
        # New --record flag is optional
```

### 8.3 Migration Timeline

**Phase 1: Database Foundation (Week 1-2)**
- Implement database schema
- Create migration tools
- Test with existing packs

**Phase 2: Dual Mode (Week 3-4)**
- Support both file-based and database modes
- Add --record flag to existing commands
- Migrate existing packs

**Phase 3: Intelligence Layer (Week 5-8)**
- Implement pattern detection
- Add prediction capabilities
- Build query interface

**Phase 4: Full Transition (Week 9-12)**
- Make database mode default
- Deprecate file-only mode
- Full feature rollout

---

## 9. Backup & Sync Strategies

### 9.1 Local Backup

```bash
# Automatic backups
crumdbob db-backup --auto --interval daily --keep 7
# Creates daily backups, keeps last 7

# Manual backup
crumdbob db-backup --out backup-$(date +%Y%m%d).db

# Restore from backup
crumdbob db-restore --from backup-20260515.db
```

### 9.2 Team Sync

```python
# crumdbob/sync/team_sync.py
class TeamSync:
    """Sync database across team members"""
    
    def push_to_remote(self, remote_url: str):
        """Push local sessions to team database"""
        # Export new sessions since last sync
        # Upload to shared storage (S3, Git LFS, etc.)
        # Merge with remote database
    
    def pull_from_remote(self, remote_url: str):
        """Pull team sessions to local database"""
        # Download remote database
        # Merge with local database
        # Resolve conflicts
    
    def configure_auto_sync(self, interval_minutes: int):
        """Auto-sync at regular intervals"""
```

### 9.3 Cloud Storage Integration

```python
# crumdbob/sync/cloud.py
class CloudStorage:
    """Integrate with cloud storage"""
    
    def sync_to_s3(self, bucket: str, prefix: str):
        """Sync database to S3"""
    
    def sync_to_github(self, repo: str, branch: str):
        """Sync database to GitHub (Git LFS)"""
    
    def sync_to_dropbox(self, path: str):
        """Sync database to Dropbox"""
```

---

## 10. Implementation Plan

### 10.1 Phase 1: Foundation (Weeks 1-2)

**Goals**: Database schema, basic recording, migration tools

**Tasks**:
1. Design and implement database schema
2. Create `crumdbob init-db` command
3. Create `crumdbob record` command
4. Build migration tool for existing packs
5. Add `--record` flag to `pack` command
6. Write comprehensive tests

**Deliverables**:
- Working database with all tables
- Ability to record packs to database
- Migration tool for existing packs
- Documentation

### 10.2 Phase 2: Query Interface (Weeks 3-4)

**Goals**: Query API, CLI commands, basic insights

**Tasks**:
1. Implement query API
2. Create `crumdbob query` command
3. Create `crumdbob search` command
4. Create `crumdbob sessions` command
5. Create `crumdbob timeline` command
6. Build query translator for natural language
7. Create predefined query templates

**Deliverables**:
- Full query interface
- Natural language query support
- Timeline visualization
- Documentation and examples

### 10.3 Phase 3: Intelligence Engine (Weeks 5-8)

**Goals**: Pattern detection, predictions, insights

**Tasks**:
1. Implement pattern detector
2. Implement impact predictor
3. Implement trend analyzer
4. Implement anomaly detector
5. Create `crumdbob insights` command
6. Create `crumdbob predict` command
7. Create `crumdbob patterns` command
8. Create `crumdbob trends` command

**Deliverables**:
- Working intelligence engine
- Predictive capabilities
- Insight generation
- Pattern detection

### 10.4 Phase 4: Integration (Weeks 9-12)

**Goals**: Git, CI/CD, VSCode integration

**Tasks**:
1. Implement Git integration
2. Create GitHub Actions workflow
3. Build VSCode extension
4. Implement team sync
5. Create web dashboard
6. Add quality gates
7. Build backup/restore system

**Deliverables**:
- Full Git integration
- CI/CD workflows
- VSCode extension
- Team collaboration features
- Web dashboard

### 10.5 Phase 5: Polish & Scale (Weeks 13-16)

**Goals**: Performance, security, documentation

**Tasks**:
1. Performance optimization
2. Security hardening
3. Privacy features
4. Comprehensive documentation
5. Tutorial videos
6. Migration guides
7. Best practices guide

**Deliverables**:
- Production-ready system
- Complete documentation
- Security audit
- Performance benchmarks

---

## 11. Success Metrics

### 11.1 Adoption Metrics
- **Database initialization rate**: % of users who init database
- **Recording rate**: % of packs recorded to database
- **Query frequency**: Queries per user per week
- **Insight usage**: % of generated insights acted upon

### 11.2 Value Metrics
- **Time saved**: Reduction in context-switching time
- **Knowledge retention**: % of risks/tasks tracked over time
- **Prediction accuracy**: % of accurate impact predictions
- **Pattern detection**: Number of useful patterns found

### 11.3 Quality Metrics
- **Risk resolution time**: Average days to resolve risks
- **Task completion rate**: % of tasks completed
- **Code quality trends**: Improvement in quality metrics
- **Team collaboration**: Cross-session references

### 11.4 Technical Metrics
- **Database size**: Growth rate and optimization
- **Query performance**: Average query time
- **Sync reliability**: Success rate of team sync
- **System uptime**: Availability of services

---

## 12. Risk Assessment

### 12.1 Technical Risks

**Risk**: Database corruption
- **Mitigation**: Automatic backups, transaction safety, validation
- **Severity**: High
- **Likelihood**: Low

**Risk**: Performance degradation with large datasets
- **Mitigation**: Indexes, query optimization, archival strategy
- **Severity**: Medium
- **Likelihood**: Medium

**Risk**: Sync conflicts in team environments
- **Mitigation**: Conflict resolution strategy, last-write-wins with audit
- **Severity**: Medium
- **Likelihood**: Medium

### 12.2 Adoption Risks

**Risk**: Users don't see value in database mode
- **Mitigation**: Clear value demonstration, gradual rollout, opt-in initially
- **Severity**: High
- **Likelihood**: Low

**Risk**: Migration complexity deters users
- **Mitigation**: Automated migration, backward compatibility, clear guides
- **Severity**: Medium
- **Likelihood**: Medium

### 12.3 Privacy Risks

**Risk**: Sensitive data in database
- **Mitigation**: PII sanitization, encryption, access control
- **Severity**: High
- **Likelihood**: Medium

**Risk**: Unauthorized access to team database
- **Mitigation**: Authentication, encryption, audit logging
- **Severity**: High
- **Likelihood**: Low

---

## 13. Future Enhancements

### 13.1 AI-Powered Features
- LLM-based risk categorization
- Intelligent task prioritization
- Automated insight generation
- Natural language query understanding

### 13.2 Advanced Analytics
- Machine learning for prediction
- Anomaly detection with ML
- Trend forecasting
- Recommendation engine

### 13.3 Enterprise Features
- Multi-tenant support
- Role-based access control
- Advanced audit logging
- Compliance reporting
- SLA monitoring

### 13.4 Integration Ecosystem
- Jira/Linear integration
- Slack/Teams notifications
- Datadog/Sentry correlation
- SonarQube integration
- TestRail sync

---

## 14. Conclusion

The Multi-Session Memory System transforms CrumbBob from a simple converter into an **organizational intelligence platform**. By tracking every Bob session, detecting patterns, predicting impacts, and enabling team collaboration, it becomes an indispensable tool for any team using IBM Bob.

**Key Differentiators**:
1. **Persistent Memory**: Never lose context between sessions
2. **Pattern Detection**: Learn from history automatically
3. **Impact Prediction**: Know what will be affected before making changes
4. **Team Collaboration**: Share knowledge across the team
5. **Quality Gates**: Prevent issues based on historical data

**Value Proposition**: 
- Reduces context-switching time by 80%
- Prevents recurring issues through pattern detection
- Accelerates onboarding with institutional knowledge
- Improves code quality through predictive insights
- Enables data-driven development decisions

**Implementation Timeline**: 16 weeks from foundation to production-ready system

**Next Steps**:
1. Review and approve this design
2. Begin Phase 1 implementation
3. Gather early user feedback
4. Iterate based on real-world usage
5. Scale to full feature set

This is the feature that makes CrumbBob a **must-have tool** for teams using IBM Bob.