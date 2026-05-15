# Multi-Session Memory System - Implementation Examples

This document provides concrete code examples and usage scenarios for the Multi-Session Memory System.

---

## 1. Database Implementation Examples

### 1.1 Database Initialization

```python
# crumdbob/memory/database.py
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

class MemoryDatabase:
    """SQLite database for multi-session memory"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self):
        """Create database schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        self._create_sessions_table()
        self._create_packs_table()
        self._create_files_table()
        self._create_commands_table()
        self._create_risks_table()
        self._create_tasks_table()
        self._create_relationships_table()
        self._create_insights_table()
        
        # Create indexes
        self._create_indexes()
        
        # Create views
        self._create_views()
        
        self.conn.commit()
    
    def _create_sessions_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                bob_report_path TEXT NOT NULL,
                bob_report_hash TEXT NOT NULL,
                pack_dir TEXT NOT NULL,
                parent_session_id TEXT,
                branch_name TEXT,
                commit_hash TEXT,
                author TEXT,
                crumdbob_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
            )
        """)
    
    # ... other table creation methods
```

### 1.2 Recording a Session

```python
# crumdbob/memory/recorder.py
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from ..parser import parse_bob_report
from .database import MemoryDatabase

class SessionRecorder:
    """Records Bob sessions to memory database"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def record_pack(
        self,
        pack_dir: Path,
        parent_session_id: Optional[str] = None
    ) -> str:
        """Record a pack to the database"""
        
        # Parse the pack
        pack_data = self._parse_pack(pack_dir)
        
        # Get Git context
        git_context = self._get_git_context(pack_dir)
        
        # Create session record
        session_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        self.db.conn.execute("""
            INSERT INTO sessions (
                id, timestamp, title, summary,
                bob_report_path, bob_report_hash, pack_dir,
                parent_session_id, branch_name, commit_hash,
                author, crumdbob_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            timestamp,
            pack_data['title'],
            pack_data['summary'],
            pack_data['bob_report_path'],
            pack_data['bob_report_hash'],
            str(pack_dir),
            parent_session_id,
            git_context.get('branch'),
            git_context.get('commit'),
            git_context.get('author'),
            pack_data['crumdbob_version'],
            timestamp
        ))
        
        # Record pack metadata
        self._record_pack_metadata(session_id, pack_data)
        
        # Record files
        self._record_files(session_id, pack_data['files'])
        
        # Record commands
        self._record_commands(session_id, pack_data['commands'])
        
        # Record risks
        self._record_risks(session_id, pack_data['risks'])
        
        # Record tasks
        self._record_tasks(session_id, pack_data['tasks'])
        
        # Update relationships
        self._update_relationships(session_id, pack_data['files'])
        
        self.db.conn.commit()
        
        return session_id
    
    def _record_files(self, session_id: str, files: list[str]):
        """Record files mentioned in session"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        for file_path in files:
            # Check if file exists
            cursor = self.db.conn.execute(
                "SELECT id FROM files WHERE file_path = ?",
                (file_path,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update existing file
                file_id = row['id']
                self.db.conn.execute("""
                    UPDATE files 
                    SET last_seen_session = ?,
                        mention_count = mention_count + 1,
                        updated_at = ?
                    WHERE id = ?
                """, (session_id, timestamp, file_id))
            else:
                # Insert new file
                cursor = self.db.conn.execute("""
                    INSERT INTO files (
                        file_path, first_seen_session, last_seen_session,
                        mention_count, file_type, created_at, updated_at
                    ) VALUES (?, ?, ?, 1, ?, ?, ?)
                """, (
                    file_path,
                    session_id,
                    session_id,
                    Path(file_path).suffix,
                    timestamp,
                    timestamp
                ))
                file_id = cursor.lastrowid
            
            # Link to session
            self.db.conn.execute("""
                INSERT INTO session_files (session_id, file_id, created_at)
                VALUES (?, ?, ?)
            """, (session_id, file_id, timestamp))
```

---

## 2. Query API Examples

### 2.1 High-Level Query Interface

```python
# crumdbob/memory/query.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Risk:
    id: int
    text: str
    severity: str
    category: str
    status: str
    first_seen: datetime
    last_seen: datetime
    mention_count: int

@dataclass
class Session:
    id: str
    timestamp: datetime
    title: str
    author: str
    branch: str
    file_count: int
    risk_count: int
    task_count: int

class QueryAPI:
    """High-level query interface for memory database"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def find_risks(
        self,
        status: Optional[List[str]] = None,
        severity: Optional[List[str]] = None,
        text_contains: Optional[str] = None,
        limit: int = 100
    ) -> List[Risk]:
        """Find risks matching criteria"""
        
        query = """
            SELECT 
                r.id, r.risk_text, r.severity, r.category,
                r.status, r.first_seen_session, r.last_seen_session,
                r.mention_count
            FROM risks r
            WHERE 1=1
        """
        params = []
        
        if status:
            placeholders = ','.join('?' * len(status))
            query += f" AND r.status IN ({placeholders})"
            params.extend(status)
        
        if severity:
            placeholders = ','.join('?' * len(severity))
            query += f" AND r.severity IN ({placeholders})"
            params.extend(severity)
        
        if text_contains:
            query += " AND r.risk_text LIKE ?"
            params.append(f"%{text_contains}%")
        
        query += " ORDER BY r.severity DESC, r.mention_count DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.db.conn.execute(query, params)
        
        return [
            Risk(
                id=row['id'],
                text=row['risk_text'],
                severity=row['severity'],
                category=row['category'],
                status=row['status'],
                first_seen=datetime.fromisoformat(row['first_seen_session']),
                last_seen=datetime.fromisoformat(row['last_seen_session']),
                mention_count=row['mention_count']
            )
            for row in cursor.fetchall()
        ]
    
    def get_session_timeline(
        self,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Session]:
        """Get chronological session timeline"""
        
        query = """
            SELECT 
                s.id, s.timestamp, s.title, s.author, s.branch_name,
                p.file_count, p.risk_count, p.task_count
            FROM sessions s
            LEFT JOIN packs p ON s.id = p.session_id
            WHERE 1=1
        """
        params = []
        
        if since:
            query += " AND s.timestamp >= ?"
            params.append(since.isoformat())
        
        query += " ORDER BY s.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.db.conn.execute(query, params)
        
        return [
            Session(
                id=row['id'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                title=row['title'],
                author=row['author'] or 'unknown',
                branch=row['branch_name'] or 'unknown',
                file_count=row['file_count'] or 0,
                risk_count=row['risk_count'] or 0,
                task_count=row['task_count'] or 0
            )
            for row in cursor.fetchall()
        ]
    
    def get_file_relationships(
        self,
        file_path: str,
        min_confidence: float = 0.5
    ) -> List[tuple[str, float]]:
        """Get files frequently changed with this file"""
        
        # Get file ID
        cursor = self.db.conn.execute(
            "SELECT id FROM files WHERE file_path = ?",
            (file_path,)
        )
        row = cursor.fetchone()
        if not row:
            return []
        
        file_id = row['id']
        
        # Get relationships
        query = """
            SELECT 
                f.file_path,
                r.confidence
            FROM relationships r
            JOIN files f ON (
                CASE 
                    WHEN r.file1_id = ? THEN r.file2_id
                    ELSE r.file1_id
                END = f.id
            )
            WHERE (r.file1_id = ? OR r.file2_id = ?)
            AND r.confidence >= ?
            ORDER BY r.confidence DESC
        """
        
        cursor = self.db.conn.execute(
            query,
            (file_id, file_id, file_id, min_confidence)
        )
        
        return [
            (row['file_path'], row['confidence'])
            for row in cursor.fetchall()
        ]
```

### 2.2 Natural Language Query Translation

```python
# crumdbob/memory/nl_query.py
import re
from typing import Dict, List, Tuple

class NaturalLanguageQueryTranslator:
    """Translates natural language queries to SQL"""
    
    PATTERNS = {
        'authentication': ['auth', 'login', 'password', 'oauth', 'jwt', 'token'],
        'database': ['db', 'sql', 'migration', 'schema', 'query', 'postgres', 'mysql'],
        'security': ['xss', 'csrf', 'injection', 'vulnerability', 'exploit', 'attack'],
        'performance': ['slow', 'performance', 'optimization', 'cache', 'speed'],
        'testing': ['test', 'coverage', 'pytest', 'jest', 'unit', 'integration'],
    }
    
    def translate(self, query: str) -> Tuple[str, List]:
        """Convert natural language to SQL"""
        query_lower = query.lower()
        
        # Detect query type
        if 'risk' in query_lower:
            return self._translate_risk_query(query_lower)
        elif 'file' in query_lower:
            return self._translate_file_query(query_lower)
        elif 'task' in query_lower:
            return self._translate_task_query(query_lower)
        elif 'session' in query_lower:
            return self._translate_session_query(query_lower)
        else:
            # Default to general search
            return self._translate_general_query(query_lower)
    
    def _translate_risk_query(self, query: str) -> Tuple[str, List]:
        """Translate risk-related queries"""
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        # Build SQL
        sql = """
            SELECT 
                r.id, r.risk_text, r.severity, r.category,
                r.status, r.mention_count
            FROM risks r
            WHERE 1=1
        """
        params = []
        
        # Add keyword filters
        if keywords:
            conditions = []
            for keyword in keywords:
                conditions.append("r.risk_text LIKE ?")
                params.append(f"%{keyword}%")
            sql += " AND (" + " OR ".join(conditions) + ")"
        
        # Check for status filters
        if 'unresolved' in query or 'active' in query:
            sql += " AND r.status IN ('new', 'ongoing')"
        elif 'resolved' in query:
            sql += " AND r.status = 'resolved'"
        
        # Check for severity filters
        if 'critical' in query or 'high' in query:
            sql += " AND r.severity IN ('critical', 'high')"
        
        sql += " ORDER BY r.severity DESC, r.mention_count DESC LIMIT 50"
        
        return sql, params
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract relevant keywords from query"""
        keywords = []
        
        for category, terms in self.PATTERNS.items():
            for term in terms:
                if term in query:
                    keywords.append(term)
        
        # Also extract quoted phrases
        quoted = re.findall(r'"([^"]+)"', query)
        keywords.extend(quoted)
        
        return list(set(keywords))
```

---

## 3. Intelligence Engine Examples

### 3.1 Pattern Detection

```python
# crumdbob/intelligence/patterns.py
from dataclasses import dataclass
from typing import List
from collections import defaultdict

@dataclass
class Pattern:
    type: str
    title: str
    description: str
    confidence: float
    evidence: List[str]

class PatternDetector:
    """Detects patterns across sessions"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def detect_recurring_risks(self, threshold: int = 3) -> List[Pattern]:
        """Find risks that appear repeatedly"""
        
        cursor = self.db.conn.execute("""
            SELECT 
                r.risk_text,
                r.mention_count,
                r.category,
                GROUP_CONCAT(s.timestamp) as timestamps
            FROM risks r
            JOIN session_risks sr ON r.id = sr.risk_id
            JOIN sessions s ON sr.session_id = s.id
            WHERE r.mention_count >= ?
            GROUP BY r.id
            ORDER BY r.mention_count DESC
        """, (threshold,))
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append(Pattern(
                type='recurring_risk',
                title=f"Recurring Risk: {row['risk_text'][:50]}...",
                description=f"This risk has appeared in {row['mention_count']} sessions",
                confidence=min(row['mention_count'] / 10.0, 1.0),
                evidence=[
                    f"Category: {row['category']}",
                    f"Mentions: {row['mention_count']}",
                    f"Sessions: {row['timestamps']}"
                ]
            ))
        
        return patterns
    
    def detect_file_clusters(self, min_cochange: int = 3) -> List[Pattern]:
        """Find files that are frequently changed together"""
        
        cursor = self.db.conn.execute("""
            SELECT 
                f1.file_path as file1,
                f2.file_path as file2,
                r.co_change_count,
                r.confidence
            FROM relationships r
            JOIN files f1 ON r.file1_id = f1.id
            JOIN files f2 ON r.file2_id = f2.id
            WHERE r.co_change_count >= ?
            ORDER BY r.co_change_count DESC
            LIMIT 20
        """, (min_cochange,))
        
        # Group by clusters
        clusters = defaultdict(list)
        for row in cursor.fetchall():
            key = row['file1']
            clusters[key].append((row['file2'], row['co_change_count']))
        
        patterns = []
        for main_file, related_files in clusters.items():
            if len(related_files) >= 2:
                patterns.append(Pattern(
                    type='file_cluster',
                    title=f"File Cluster: {main_file}",
                    description=f"This file is frequently changed with {len(related_files)} other files",
                    confidence=0.8,
                    evidence=[
                        f"Main file: {main_file}",
                        *[f"  - {f} (co-changed {count}x)" for f, count in related_files[:5]]
                    ]
                ))
        
        return patterns
```

### 3.2 Impact Prediction

```python
# crumdbob/intelligence/predictor.py
from typing import List, Tuple
from collections import Counter

class ImpactPredictor:
    """Predicts impact of changes"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def predict_affected_files(
        self,
        changed_files: List[str]
    ) -> List[Tuple[str, float]]:
        """Predict other files likely to be affected"""
        
        affected = Counter()
        
        for file_path in changed_files:
            # Get file ID
            cursor = self.db.conn.execute(
                "SELECT id FROM files WHERE file_path = ?",
                (file_path,)
            )
            row = cursor.fetchone()
            if not row:
                continue
            
            file_id = row['id']
            
            # Get related files
            cursor = self.db.conn.execute("""
                SELECT 
                    f.file_path,
                    r.confidence,
                    r.co_change_count
                FROM relationships r
                JOIN files f ON (
                    CASE 
                        WHEN r.file1_id = ? THEN r.file2_id
                        ELSE r.file1_id
                    END = f.id
                )
                WHERE (r.file1_id = ? OR r.file2_id = ?)
                AND r.confidence > 0.3
            """, (file_id, file_id, file_id))
            
            for row in cursor.fetchall():
                # Weight by confidence and co-change count
                score = row['confidence'] * (1 + row['co_change_count'] / 10.0)
                affected[row['file_path']] += score
        
        # Normalize scores
        max_score = max(affected.values()) if affected else 1.0
        normalized = [
            (file, score / max_score)
            for file, score in affected.most_common(10)
        ]
        
        return normalized
    
    def predict_risks(
        self,
        changed_files: List[str],
        task_description: str = None
    ) -> List[Tuple[Risk, float]]:
        """Predict risks that may arise"""
        
        risk_scores = Counter()
        
        # Find historical risks for these files
        for file_path in changed_files:
            cursor = self.db.conn.execute("""
                SELECT DISTINCT
                    r.id, r.risk_text, r.severity, r.category,
                    r.status, r.mention_count
                FROM risks r
                JOIN session_risks sr ON r.id = sr.risk_id
                JOIN session_files sf ON sr.session_id = sf.session_id
                JOIN files f ON sf.file_id = f.id
                WHERE f.file_path = ?
            """, (file_path,))
            
            for row in cursor.fetchall():
                # Score based on mention count and severity
                severity_weight = {
                    'critical': 1.0,
                    'high': 0.8,
                    'medium': 0.5,
                    'low': 0.3
                }.get(row['severity'], 0.5)
                
                score = severity_weight * (1 + row['mention_count'] / 5.0)
                risk_scores[row['id']] = max(risk_scores[row['id']], score)
        
        # If task description provided, boost matching risks
        if task_description:
            keywords = task_description.lower().split()
            for risk_id, score in list(risk_scores.items()):
                cursor = self.db.conn.execute(
                    "SELECT risk_text FROM risks WHERE id = ?",
                    (risk_id,)
                )
                row = cursor.fetchone()
                if row:
                    risk_text = row['risk_text'].lower()
                    matches = sum(1 for kw in keywords if kw in risk_text)
                    if matches > 0:
                        risk_scores[risk_id] *= (1 + matches * 0.2)
        
        # Get top risks
        top_risk_ids = [rid for rid, _ in risk_scores.most_common(10)]
        
        # Fetch full risk objects
        risks = []
        for risk_id in top_risk_ids:
            cursor = self.db.conn.execute("""
                SELECT 
                    id, risk_text, severity, category,
                    status, first_seen_session, last_seen_session,
                    mention_count
                FROM risks
                WHERE id = ?
            """, (risk_id,))
            
            row = cursor.fetchone()
            if row:
                risk = Risk(
                    id=row['id'],
                    text=row['risk_text'],
                    severity=row['severity'],
                    category=row['category'],
                    status=row['status'],
                    first_seen=datetime.fromisoformat(row['first_seen_session']),
                    last_seen=datetime.fromisoformat(row['last_seen_session']),
                    mention_count=row['mention_count']
                )
                confidence = min(risk_scores[risk_id] / 2.0, 1.0)
                risks.append((risk, confidence))
        
        return risks
```

---

## 4. CLI Command Examples

### 4.1 Recording Sessions

```bash
# Initialize database
$ crumdbob init-db
✓ Created database: /Users/dev/project/.crumdbob/memory.db
✓ Initialized schema with 8 tables
✓ Created 12 indexes
✓ Created 4 views
Database ready!

# Record a pack
$ crumdbob record ./generated
Analyzing pack...
✓ Parsed 8 CRUMB files
✓ Extracted 12 files, 9 commands, 7 risks, 8 tasks
✓ Detected Git context: branch=feature/auth, commit=abc123
✓ Recorded session: 550e8400-e29b-41d4-a716-446655440000

Session recorded successfully!
  Files: 12
  Commands: 9
  Risks: 7
  Tasks: 8
  Author: john@example.com
  Branch: feature/auth

# Record with parent session
$ crumdbob record ./generated --parent-session 550e8400-e29b-41d4-a716-446655440000
✓ Linked to parent session
✓ Detected 3 new risks
✓ Detected 2 resolved risks
✓ Recorded session: 661f9511-f3ac-52e5-b827-557766551111
```

### 4.2 Querying

```bash
# Natural language queries
$ crumdbob query "What did Bob discover about authentication in the last 3 sessions?"

Found 5 results:

1. Risk: Authentication bypass in login endpoint
   Severity: high
   First seen: 2026-05-10
   Last seen: 2026-05-15
   Mentions: 3 sessions

2. Task: Implement OAuth 2.0 authentication
   Status: in_progress
   First seen: 2026-05-12
   
3. File: packages/auth/login.ts
   Mentions: 3 sessions
   Related files: auth/oauth.ts, auth/jwt.ts

# Structured search
$ crumdbob search --type risk --status unresolved --severity high

Active High-Severity Risks:
┌────┬─────────────────────────────────────────┬──────────┬──────────┐
│ ID │ Risk                                    │ Severity │ Mentions │
├────┼─────────────────────────────────────────┼──────────┼──────────┤
│ 42 │ SQL injection in search query           │ high     │ 5        │
│ 38 │ XSS vulnerability in user profile       │ high     │ 3        │
│ 51 │ Authentication bypass in login endpoint │ high     │ 3        │
└────┴─────────────────────────────────────────┴──────────┴──────────┘

# SQL queries
$ crumdbob sql "SELECT file_path, mention_count FROM hot_files LIMIT 5"

Most Frequently Mentioned Files:
┌────────────────────────────────┬──────────┐
│ File                           │ Mentions │
├────────────────────────────────┼──────────┤
│ packages/auth/login.ts         │ 12       │
│ packages/db/migrations/001.sql │ 8        │
│ packages/api/routes.ts         │ 7        │
│ packages/auth/oauth.ts         │ 6        │
│ tests/auth.test.ts             │ 5        │
└────────────────────────────────┴──────────┘
```

### 4.3 Insights & Predictions

```bash
# Generate insights
$ crumdbob insights

Generating insights from 15 sessions...
✓ Detected 3 recurring risk patterns
✓ Detected 2 file clusters
✓ Detected 1 anomaly
✓ Generated 6 insights

Recent Insights:
┌────┬──────────────┬─────────────────────────────────────────┬────────────┐
│ ID │ Type         │ Title                                   │ Confidence │
├────┼──────────────┼─────────────────────────────────────────┼────────────┤
│ 1  │ pattern      │ Recurring Risk: SQL injection           │ 0.85       │
│ 2  │ pattern      │ File Cluster: packages/auth/*           │ 0.80       │
│ 3  │ anomaly      │ Unusual spike in risk mentions          │ 0.65       │
│ 4  │ prediction   │ High risk area: database migrations     │ 0.75       │
└────┴──────────────┴─────────────────────────────────────────┴────────────┘

# Predict impact
$ crumdbob predict packages/auth/login.ts

Impact Prediction for: packages/auth/login.ts

Likely Affected Files:
  1. packages/auth/oauth.ts (confidence: 0.92)
  2. packages/auth/jwt.ts (confidence: 0.87)
  3. tests/auth.test.ts (confidence: 0.78)
  4. packages/api/routes.ts (confidence: 0.65)

Potential Risks:
  1. Authentication bypass (confidence: 0.85)
  2. Session management issues (confidence: 0.72)
  3. Token validation errors (confidence: 0.68)

Recommended Tests:
  - tests/auth.test.ts
  - tests/integration/login.test.ts
  - tests/security/auth.test.ts

Estimated Complexity: Medium (based on 3 similar historical tasks)
Average Completion Time: 2.5 days

# Timeline visualization
$ crumdbob timeline --format text

Session Timeline:
═══════════════════════════════════════════════════════════════

2026-05-15 10:30 │ Add OAuth authentication
               │ Author: john@example.com
               │ Branch: feature/auth
               │ Files: 12 | Risks: 7 | Tasks: 8
               │
2026-05-12 14:20 │ Fix SQL injection vulnerabilities
               │ Author: jane@example.com
               │ Branch: fix/sql-injection
               │ Files: 8 | Risks: 5 | Tasks: 3
               │
2026-05-10 09:15 │ Database migration system
               │ Author: john@example.com
               │ Branch: feature/migrations
               │ Files: 15 | Risks: 9 | Tasks: 12
               │
═══════════════════════════════════════════════════════════════
```

---

## 5. Integration Examples

### 5.1 Git Hook Integration

```bash
# Install Git hooks
$ crumdbob git install-hooks

Installing CrumbBob Git hooks...
✓ Created .git/hooks/post-commit
✓ Created .git/hooks/pre-push
✓ Made hooks executable

Git hooks installed! CrumbBob will now:
  - Auto-record packs after commits (if bob-report.md exists)
  - Validate packs before pushing

# .git/hooks/post-commit
#!/bin/bash
# CrumbBob auto-record hook

if [ -f "bob-report.md" ]; then
    echo "CrumbBob: Generating and recording pack..."
    crumdbob pack . --out .crumdbob/pack --record --quiet
    if [ $? -eq 0 ]; then
        echo "✓ Pack recorded to memory database"
    fi
fi
```

### 5.2 GitHub Actions Integration

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
        with:
          fetch-depth: 0  # Full history for parent session detection
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install CrumbBob
        run: pip install crumdbob
      
      - name: Download previous database
        uses: actions/download-artifact@v3
        with:
          name: crumdbob-memory
          path: .crumdbob/
        continue-on-error: true
      
      - name: Initialize database if needed
        run: |
          if [ ! -f ".crumdbob/memory.db" ]; then
            crumdbob init-db --path .crumdbob/memory.db
          fi
      
      - name: Generate and record pack
        run: |
          crumdbob auto-collect --out .crumdbob/pack --no-interactive
          crumdbob record .crumdbob/pack
      
      - name: Generate insights
        run: crumdbob insights --type anomaly,pattern
      
      - name: Check quality gates
        run: |
          # Fail if critical risks detected
          CRITICAL_RISKS=$(crumdbob sql "SELECT COUNT(*) FROM active_risks WHERE severity='critical'" | tail -1)
          if [ "$CRITICAL_RISKS" -gt "0" ]; then
            echo "❌ Found $CRITICAL_RISKS critical risk(s)"
            crumdbob search --type risk --severity critical
            exit 1
          fi
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const insights = require('./.crumdbob/insights.json');
            const body = `## CrumbBob Analysis\n\n${insights.summary}`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
      
      - name: Upload database
        uses: actions/upload-artifact@v3
        with:
          name: crumdbob-memory
          path: .crumdbob/memory.db
          retention-days: 90
```

---

## 6. Team Collaboration Examples

### 6.1 Shared Database Setup

```bash
# Team lead initializes shared database
$ crumdbob init-db --path /shared/team/crumdbob.db
$ crumdbob db-info

Database Information:
  Location: /shared/team/crumdbob.db
  Size: 2.4 MB
  Sessions: 0
  Files: 0
  Risks: 0
  Tasks: 0
  Created: 2026-05-15 10:00:00 UTC

# Team members configure to use shared database
$ export CRUMDBOB_DB=/shared/team/crumdbob.db

# Or in .crumdbobrc
$ cat > .crumdbobrc << EOF
database: /shared/team/crumdbob.db
auto_record: true
sync_interval: 300  # 5 minutes
EOF
```

### 6.2 Team Dashboard

```bash
# Start team dashboard
$ crumdbob dashboard --port 8080

Starting CrumbBob Team Dashboard...
✓ Database: /shared/team/crumdbob.db
✓ Sessions: 47
✓ Team members: 5
✓ Server: http://localhost:8080

Dashboard Features:
  - Session timeline
  - Risk heatmap
  - Task board
  - File activity
  - Team metrics
  - Insight feed

Press Ctrl+C to stop
```

---

## 7. Advanced Usage Examples

### 7.1 Custom Queries

```python
# custom_analysis.py
from crumdbob.memory import MemoryDatabase, QueryAPI

db = MemoryDatabase('.crumdbob/memory.db')
db.connect()
api = QueryAPI(db)

# Find files that are always changed together
cursor = db.conn.execute("""
    SELECT 
        f1.file_path as file1,
        f2.file_path as file2,
        r.co_change_count,
        r.confidence
    FROM relationships r
    JOIN files f1 ON r.file1_id = f1.id
    JOIN files f2 ON r.file2_id = f2.id
    WHERE r.confidence > 0.9
    ORDER BY r.co_change_count DESC
    LIMIT 10
""")

print("Strongly Coupled Files:")
for row in cursor.fetchall():
    print(f"  {row['file1']} <-> {row['file2']}")
    print(f"    Co-changed: {row['co_change_count']}x")
    print(f"    Confidence: {row['confidence']:.2f}")
    print()
```

### 7.2 Export and Reporting

```bash
# Export session data
$ crumdbob export 550e8400-e29b-41d4-a716-446655440000 --format json > session.json

# Generate team report
$ crumdbob report --since 2026-05-01 --format markdown > team-report.md

# Export for external analysis
$ crumdbob sql "SELECT * FROM session_timeline" --format csv > timeline.csv
```

---

## 8. Performance Optimization Examples

### 8.1 Database Maintenance

```bash
# Vacuum database
$ crumdbob db-vacuum
Analyzing database...
✓ Reclaimed 1.2 MB
✓ Optimized indexes
✓ Updated statistics
Database optimized!

# Archive old sessions
$ crumdbob db-archive --older-than 90d --output archive.db
Archiving sessions older than 90 days...
✓ Archived 23 sessions
✓ Archived 156 files
✓ Archived 89 risks
✓ Reduced main database by 45%
Archive saved to: archive.db

# Analyze query performance
$ crumdbob db-analyze
Query Performance Analysis:
  Average query time: 12ms
  Slowest query: 245ms (file relationships)
  Index usage: 94%
  Recommendations:
    - Add index on risks.category
    - Consider partitioning sessions table
```

This comprehensive set of examples demonstrates how the Multi-Session Memory System would work in practice, from basic operations to advanced team collaboration scenarios.