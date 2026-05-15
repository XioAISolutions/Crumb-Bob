# Changelog

All notable changes to CrumbBob will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-15

### Added

#### Core Features
- **Multi-Session Memory System**: SQLite database with 8 tables for persistent session storage
  - Session recording and querying across development history
  - Git context integration (branch, commit, author)
  - Auto-recording support via configuration
  - Migration from file-based packs to database
- **Intelligent Query Engine**: Natural language queries with 15+ patterns
  - Template-based queries for common questions
  - Direct SQL access for power users
  - Query result formatting (table, JSON)
- **Pattern Detection**: Automatic identification of recurring issues
  - Recurring risk detection with frequency analysis
  - File relationship mapping (co-change patterns)
  - Task completion pattern analysis
  - Command usage pattern detection
  - Anomaly detection for unusual patterns
- **Insights Generation**: Actionable insights from detected patterns
  - 7 insight types (risks, files, tasks, commands, trends, health, anomalies)
  - Severity scoring (critical, high, medium, low)
  - Confidence levels (0-100%)
  - Automatic deduplication
- **Predictive Analytics**: Future issue prediction
  - Impact prediction (affected files)
  - Risk prediction for planned changes
  - Task complexity estimation
  - Test recommendation engine

#### Quick Wins
- **Auto-Collect**: Intelligent artifact discovery and collection (95% time savings)
  - Git diff detection (staged/unstaged)
  - Test output discovery
  - CI log collection
  - Interactive selection interface
- **Watch Mode**: Real-time pack regeneration during development
  - File system monitoring with debouncing
  - Automatic regeneration on changes
  - Auto-recording integration
  - Live status indicators
- **Pack Diff**: Visual comparison of pack versions
  - Summary view with color coding
  - Detailed section-by-section comparison
  - JSON output for CI/CD integration
  - Exit codes for automation

#### CLI Commands (30+ new)
- Memory: `init-db`, `record`, `list-sessions`, `show-session`, `migrate-to-db`
- Query: `query natural`, `query template`, `query sql`, `query list-templates`
- Patterns: `patterns detect`, `patterns analyze`
- Insights: `insights generate`, `insights list`, `insights top`, `insights actionable`
- Predictions: `predict impact`, `predict risks`, `predict complexity`, `predict tests`
- Dashboard: `dashboard` (real-time intelligence overview)
- Config: `config get`, `config set`, `config list`, `config reset`
- Workflow: `auto-collect`, `watch`, `diff`

#### Documentation
- Multi-session memory system (4 comprehensive guides)
- Intelligence features (queries, patterns, insights, predictions)
- Workflow guides (auto-collect, watch mode, diff)
- Configuration management guide
- Enhancement roadmap with 18 planned features

#### Testing
- 130+ tests (up from 8)
- Comprehensive config.py test coverage (29 tests)
- Intelligence engine tests (40+ tests)
- Memory system tests (15 tests)
- Workflow tests (collector, watcher, differ)

### Changed
- Enhanced `packer.py` with full CRUMB v1.4 sections
- Enhanced `parser.py` with artifact enrichment
- Improved `cli.py` with 38+ commands (up from 8)
- Updated `pyproject.toml` with dev dependencies and Python 3.12 classifier
- Improved README.md with detailed installation instructions

### Fixed
- **High-severity correctness bugs (8)**:
  - `cmd_migrate_to_db()` now reports error count and sets exit code
  - `record_pack_to_db` no longer parses proof chain twice
  - `MemoryDatabase.close()` properly commits/rolls back transactions
  - Validator now detects duplicate CRUMB sections
  - `ZeroDivisionError` in trend calculation fixed
  - `TypeError` in natural language query handlers fixed
  - Risk queries now match "Show me all risks" pattern
  - Path traversal vulnerability in proof chain parsing fixed

- **Performance & resource issues (6)**:
  - SQLite now uses WAL mode, foreign keys, and optimized synchronous mode
  - Added missing indexes for pattern detection queries
  - Fixed N+1 queries in `predict_risks()`, `predict_complexity()`, `recommend_tests()`
  - Extracted shared co-change computation helper

- **Data-quality / API issues (8)**:
  - `RISK_WORDS` now uses word boundaries to avoid false matches
  - Insight generation now deduplicates properly
  - LIKE pattern escaping fixed in insight deduplication
  - `_extract_keywords` now includes stem variants
  - `enrich_report_with_artifact` contract clarified (mutation only)
  - `query_sql` now has read-only protection against destructive operations

- **Code hygiene (5)**:
  - Moved inline imports to module level
  - Removed dead `watch_with_status()` stub
  - Made Git timeout configurable
  - Added schema version check for database compatibility

### Security
- Added read-only SQL query protection (blocks DROP, DELETE, UPDATE, etc.)
- Fixed path traversal vulnerability in proof chain source report resolution
- Added input validation for configuration keys

## [0.1.0] - 2026-05-14

### Added
- Initial CrumbBob implementation
- CRUMB v1.4 format support
- Basic pack generation (9 files)
- Proof chain with SHA256 hashes
- Validation and health checking
- Web demo for visual presentation
- 8 initial tests

[0.2.0]: https://github.com/XioAISolutions/Crumb-Bob/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/XioAISolutions/Crumb-Bob/releases/tag/v0.1.0