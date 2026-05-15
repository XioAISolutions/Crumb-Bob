# CrumbBob

> **The flight recorder for IBM Bob development sessions.**

IBM Bob gives software a temporary brain. CrumbBob gives that brain memory.

CrumbBob converts an exported Bob report plus optional repo artifacts into a replayable memory pack:

```text
Bob report + repo metadata + test output + git diff
  -> Repo Genome + Flight Recorder + Next Task + Test Plan + Risk Register
  -> Agent Passport + Replay Prompt + PR Summary + Proof Chain
```

## ✨ Features

- 🎨 **Beautiful Rich Terminal UI** - Professional, color-coded output with tables, panels, and progress bars
- 🌐 **Interactive Web Dashboard** - Modern web UI for visualizing sessions, insights, patterns, and trends
- 🤖 **AI-Powered Analysis** - LLM integration for intelligent insights, risk categorization, and recommendations
- 📦 **Smart Pack Generation** - Auto-collect artifacts from Git repos with visual feedback
- 🔍 **Multi-Session Memory** - SQLite database tracks patterns across development sessions
- 🧠 **Intelligence Engine** - Insights, predictions, pattern detection, and natural language queries
- 👁️ **Watch Mode** - Real-time monitoring of Bob reports with live updates
- ✅ **Validation & Verification** - Comprehensive pack validation with detailed error reporting
- 📊 **Trend Analysis** - Visualize hot files, recurring risks, and command patterns

## Quickstart

### Installation

**Recommended: Use a virtual environment**

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install CrumbBob with all features (includes rich terminal UI)
pip install -e .[dev]

# Verify installation
crumdbob --help
```

**Optional: Install watch mode support**

```bash
pip install -e .[watch]
```

**Optional: Install web dashboard**

```bash
pip install fastapi uvicorn[standard]
# Or install with CrumbBob extras
pip install -e .[web]
```

**Optional: Install AI-powered analysis (LLM)**

```bash
# Install LLM support (OpenAI, Anthropic)
pip install -e .[llm]

# Or install all features
pip install -e .[all]

# Configure LLM provider
export OPENAI_API_KEY="sk-..."
crumdbob llm setup openai --model gpt-4

# Verify LLM status
crumdbob llm status
```

See [LLM Integration Guide](docs/llm-integration.md) for detailed setup instructions.

### Quick Test

```bash
# Run test suite (200+ tests)
pytest -q

# Generate example pack
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated

# Verify pack integrity
crumdbob doctor examples/compliance-ai/generated

# Generate replay prompt
crumdbob replay examples/compliance-ai/generated
```

**Quick Win: Auto-collect artifacts from your Git repo:**

```bash
crumdbob auto-collect --out ./generated
```

**Quick Win: Watch mode for active development:**

```bash
crumdbob watch ./crumdbob-input --out ./generated
```

**Quick Win: Launch web dashboard:**

```bash
# Initialize database (first time only)
crumdbob init-db

# Record some sessions
crumdbob record ./generated

# Start web dashboard
crumdbob serve
# Opens browser at http://localhost:8000
```

**Quick Win: AI-powered analysis:**

```bash
# Analyze a session with AI
crumdbob llm analyze 1

# Get AI recommendations
crumdbob llm recommend 1

# Explain a pattern
crumdbob llm explain "Recurring SQL injection risks"

# Check LLM status and cache stats
crumdbob llm status
```

Single-file compatibility path:

```bash
crumdbob import examples/compliance-ai/bob-report.md --out examples/compliance-ai/generated
```

## Why IBM Bob

Bob is strongest while it is repo-aware inside a session. CrumbBob preserves that understanding after the session ends so the next developer, Bob session, Claude, Cursor, Codex, or local agent can continue without rediscovering architecture, commands, risks, and test plans.

## What Judges Should Inspect

- `examples/compliance-ai/bob-report.md` — source Bob report
- `examples/compliance-ai/generated/00_repo_genome.crumb` — architecture memory
- `examples/compliance-ai/generated/01_session_flight_recorder.crumb` — audit trail
- `examples/compliance-ai/generated/02_next_task.crumb` — continuation task
- `examples/compliance-ai/generated/04_risk_register.crumb` — unresolved risks
- `examples/compliance-ai/generated/08_proof_chain.json` — source and generated file hashes
- `web/index.html` — local static demo

## Demo Flow

```bash
crumdbob inspect examples/compliance-ai/bob-report.md
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
crumdbob validate examples/compliance-ai/generated
crumdbob graph examples/compliance-ai/generated
crumdbob doctor examples/compliance-ai/generated
crumdbob replay examples/compliance-ai/generated
crumdbob pr examples/compliance-ai/generated
```

Then open `web/index.html`, paste a Bob report, and click **Generate Demo Pack**.

To hand the pack back to a local IBM Bob CLI:

```bash
bob --chat-mode ask --hide-intermediary-output "$(crumdbob replay examples/compliance-ai/generated)"
```

## Quick Wins Implemented 🚀

CrumbBob goes beyond basic pack generation with three powerful workflow enhancements:

### 1. Auto-Collect: Intelligent Artifact Discovery

**Problem**: Manual artifact gathering is tedious (5-10 minutes per pack)
**Solution**: Automatic discovery and collection in 30 seconds

```bash
crumdbob auto-collect --out ./generated
```

**What it does**:
- 🔍 Scans Git repository for relevant artifacts
- 📊 Detects git diffs, test outputs, CI logs
- 🎯 Interactive selection interface
- ⚡ Generates pack in one command

**Time Saved**: 95% reduction in manual work

[📖 Full Auto-Collect Workflow Guide](examples/workflows/01-auto-collect-workflow.md)

### 2. Watch Mode: Continuous Pack Updates

**Problem**: Packs become stale during active development
**Solution**: Real-time monitoring and auto-regeneration

```bash
crumdbob watch ./crumdbob-input --out ./generated
```

**What it does**:
- 👀 Monitors input directory for changes
- 🔄 Auto-regenerates pack within seconds
- ⏱️ Intelligent debouncing (configurable)
- 💻 Maintains development flow

**Benefit**: Zero manual regeneration needed

[📖 Full Watch Mode Workflow Guide](examples/workflows/02-watch-mode-workflow.md)

### 3. Pack Diff: Change Visualization

**Problem**: No way to see what changed between pack versions
**Solution**: Comprehensive pack comparison tool

```bash
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed
```

**What it does**:
- 📊 Compares extracted counts (files, commands, risks)
- 🔍 Shows CRUMB content changes
- 📈 Multiple output formats (summary, detailed, json)
- ✅ Exit codes for CI/CD integration

**Use Cases**: PR reviews, regression detection, team collaboration

[📖 Full Diff Workflow Guide](examples/workflows/03-diff-workflow.md)

### Complete Workflow Example

```bash
# 1. Auto-collect artifacts (30 seconds)
crumdbob auto-collect --out ./generated

# 2. Start watch mode for active development
crumdbob watch ./crumdbob-input --out ./generated

# 3. Work normally - pack stays current automatically
vim src/auth.py
pytest
git commit

# 4. Compare versions for PR review
crumdbob diff ./pack-before ./pack-after --format=summary
```

**Result**: From 5-10 minutes of manual work to 30 seconds of automated workflow.

See [ENHANCEMENTS.md](ENHANCEMENTS.md) for detailed feature documentation and before/after comparisons.

### 4. Multi-Session Memory: Persistent Intelligence 🧠

**NEW**: CrumbBob now includes a persistent memory database that tracks sessions across time, enabling intelligent queries and insights.

```bash
# Initialize database
crumdbob init-db

# Generate and record in one command
crumdbob pack ./input --out ./pack --record

# List all sessions
crumdbob list-sessions

# View session details
crumdbob show-session 1
```

**What it enables**:
- 📊 **Session History**: Track all pack generations over time
- 🔍 **Cross-Session Queries**: Find files, risks, and patterns across sessions
- 🌳 **Git Integration**: Automatic branch, commit, and author tracking
- 📈 **Timeline Analysis**: Understand how your project evolves
- 🤝 **Team Collaboration**: Share and query team sessions (future)

**Key Features**:
- SQLite-based for portability and zero config
- 8 core tables with 12+ indexes for fast queries
- 4 views for common query patterns
- Proof chain integration for verification
- Auto-recording support with configuration

**Example Workflow**:
```bash
# Enable auto-recording
crumdbob config set auto_record true

# Work normally - sessions auto-record
crumdbob pack ./input --out ./pack-v1
crumdbob pack ./input --out ./pack-v2

# Query your history
crumdbob list-sessions --branch main
crumdbob show-session 2

# Migrate existing packs
crumdbob migrate-to-db ./old-packs/*
```

**Intelligence Features** ✨:

CrumbBob now includes a complete intelligence engine that transforms your session history into actionable insights:

```bash
# Natural language queries
crumdbob query natural "Show me all authentication risks"
crumdbob query natural "What files changed most this month?"

# Pattern detection
crumdbob patterns detect --type all
crumdbob patterns analyze src/auth/login.py

# Automatic insights
crumdbob insights generate
crumdbob insights actionable

# Predictive analysis
crumdbob predict impact src/auth/login.py
crumdbob predict risks "Refactor authentication system"
crumdbob predict complexity "Add OAuth support"
crumdbob predict tests src/auth/*.py

# Intelligence dashboard
crumdbob dashboard
```

**What it provides**:
- 🔍 **Natural Language Queries**: Ask questions in plain English
- 🔄 **Pattern Detection**: Automatically find recurring issues and relationships
- 💡 **Actionable Insights**: Get recommendations based on your history
- 🔮 **Predictions**: Forecast impact, risks, and complexity
- 📊 **Dashboard**: At-a-glance intelligence overview

[📖 Multi-Session Memory Getting Started](docs/multi-session-memory-getting-started.md)
[📖 Complete Design Document](docs/multi-session-memory-design.md)
[📖 Usage Examples](docs/multi-session-memory-examples.md)
[📖 Intelligent Queries Guide](docs/intelligent-queries.md)
[📖 Pattern Detection Guide](docs/pattern-detection.md)
[📖 Predictions Guide](docs/predictions.md)
[📖 Insights System Guide](docs/insights.md)

---

## CLI Command Reference

### Core Commands

- `crumdbob pack <input-dir> --out <output-dir>` — generate a full pack from `bob-report.md` plus optional `git-diff.patch`, `test-output.txt`, and `repo-notes.md`
- `crumdbob import <bob-report.md> --out <output-dir>` — generate from one report file

### Quick Win Commands

- `crumdbob auto-collect --out <output-dir>` — auto-discover and collect Git diffs, test outputs, and CI logs; prompts for selection; generates pack in one command
- `crumdbob watch <input-dir> --out <output-dir>` — monitor input directory for changes and auto-regenerate pack (debounces changes, shows live status)
- `crumdbob diff <pack-dir-1> <pack-dir-2>` — compare two pack directories; supports summary, detailed, and json formats

### Validation & Inspection

- `crumdbob validate <pack-dir-or-file>` — validate CRUMB v1.4 subset output
- `crumdbob doctor <pack-dir>` — print judge-friendly health report
- `crumdbob graph <pack-dir>` — print refs, handoff, and workflow edges

### Memory Commands

- `crumdbob init-db [--path <db-path>]` — initialize memory database
- `crumdbob record <pack-dir> [--session-name <name>]` — record pack to database
- `crumdbob list-sessions [--format json|table]` — list all recorded sessions
- `crumdbob show-session <session-id>` — show detailed session information
- `crumdbob trends [--min-sessions N]` — show cross-session patterns and trends
- `crumdbob migrate-to-db <pack-dirs...>` — migrate existing packs to database
- `crumdbob config <get|set|list|reset>` — manage configuration

### Intelligence Commands

- `crumdbob query natural "<question>"` — ask questions in natural language
- `crumdbob query template <name> [--params key=value...]` — use query templates
- `crumdbob query sql "<sql>"` — execute direct SQL queries
- `crumdbob query list-templates` — list available query templates
- `crumdbob patterns detect [--type all|risks|files|tasks|commands|anomalies]` — detect patterns
- `crumdbob patterns analyze <file-path>` — analyze patterns for specific file
- `crumdbob insights generate` — generate insights from database
- `crumdbob insights list [--category <type>]` — list all insights
- `crumdbob insights top [N]` — show top N most important insights
- `crumdbob insights actionable` — show insights requiring action
- `crumdbob predict impact <file-path>` — predict which files will be affected
- `crumdbob predict risks "<description>"` — predict risks for planned change
- `crumdbob predict complexity "<description>"` — estimate task complexity
- `crumdbob predict tests <file-paths...>` — recommend tests for changes
- `crumdbob dashboard` — display intelligence dashboard

### Output Commands

- `crumdbob replay <pack-dir>` — print continuation prompt
- `crumdbob pr <pack-dir>` — print PR summary
- `crumdbob init-bob-skill --out skills/crumdbob/SKILL.md` — write local agent instructions

### Installation

**Basic install**:
```bash
pip install -e .
```

**With watch mode support**:
```bash
pip install -e . watchdog
```

**Full development install**:
```bash
pip install -e . pytest watchdog
```

### Documentation

- [CLI Reference](docs/crumdbob-cli.md) - Complete command documentation
- [Enhancements](ENHANCEMENTS.md) - New features and before/after comparisons
- [Proof Chain](docs/proof-chain.md) - Verification and hashing
- [Integrations](docs/integrations.md) - CI/CD and tool integration
- [IBM Bob Shell Integration](docs/bob-shell-integration.md) - Bob CLI integration
- [Enhancement Roadmap](docs/enhancement-roadmap.md) - Future features and vision

### Workflow Guides

- [Auto-Collect Workflow](examples/workflows/01-auto-collect-workflow.md) - Intelligent artifact collection
- [Watch Mode Workflow](examples/workflows/02-watch-mode-workflow.md) - Active development with auto-updates
- [Diff Workflow](examples/workflows/03-diff-workflow.md) - Pack comparison for PR reviews

## Final Submission Checklist

- [ ] `pip install -e . pytest`
- [ ] `pytest -q`
- [ ] `crumdbob doctor examples/compliance-ai/generated`
- [ ] `crumdbob replay examples/compliance-ai/generated`
- [ ] Inspect `08_proof_chain.json`
- [ ] Open `web/index.html`

## Hackathon Thesis

Most teams use Bob to build an app. CrumbBob builds the missing memory layer around Bob: capture, compress, replay, prove.
