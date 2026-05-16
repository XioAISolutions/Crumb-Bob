# 🧠 CrumbBob

<div align="center">

**The Flight Recorder for IBM Bob Development Sessions**

[![Version](https://img.shields.io/badge/version-0.3.1-blue.svg)](https://github.com/XioAISolutions/Crumb-Bob/releases)
[![Tests](https://img.shields.io/badge/tests-290%20passing-brightgreen.svg)](https://github.com/XioAISolutions/Crumb-Bob/actions)
[![Coverage](https://img.shields.io/badge/coverage-65%25-green.svg)](https://github.com/XioAISolutions/Crumb-Bob)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

*IBM Bob gives software a temporary brain. CrumbBob gives that brain **permanent memory**.*

[Quick Start](#-quick-start) • [Features](#-features) • [Documentation](#-documentation) • [Demo](#-demo) • [Architecture](#-architecture)

</div>

---

## 🎯 What is CrumbBob?

CrumbBob transforms ephemeral IBM Bob sessions into **persistent, replayable memory packs** that capture everything Bob learned about your codebase. Think of it as a DVR for AI development sessions—record, replay, and learn from every interaction.

```text
┌─────────────────────────────────────────────────────────────────┐
│  Bob Report + Repo Artifacts + Test Output + Git Diff          │
│                              ↓                                  │
│  🧬 Repo Genome + 📼 Flight Recorder + 📋 Next Task            │
│  🧪 Test Plan + ⚠️  Risk Register + 🎫 Agent Passport          │
│  🔄 Replay Prompt + 📝 PR Summary + 🔗 Proof Chain             │
└─────────────────────────────────────────────────────────────────┘
```

### The Problem CrumbBob Solves

**Before CrumbBob:**
- ❌ Bob's insights vanish when the session ends
- ❌ Next developer starts from scratch
- ❌ No memory of past risks, patterns, or decisions
- ❌ Manual context gathering takes 5-10 minutes per session
- ❌ Knowledge lost between team members

**After CrumbBob:**
- ✅ Every Bob session becomes permanent institutional knowledge
- ✅ Instant context restoration for any developer
- ✅ Cross-session pattern detection and risk tracking
- ✅ 30-second automated artifact collection
- ✅ Team-wide memory database with AI-powered insights

---

## ✨ Features

### 🎨 Beautiful Rich Terminal UI
Professional, color-coded output that makes complex data instantly readable:
- 📊 **Tables** with borders, colors, and proper alignment
- 🎭 **Panels** for organized information display
- 🌈 **Syntax highlighting** for code snippets
- 📈 **Progress bars** for long operations
- ⚡ **Animated spinners** for loading states
- 🔄 **Graceful fallback** to plain text when Rich not available

### 🌐 Interactive Web Dashboard
Modern web UI for visualizing your development intelligence:
- 📊 **Overview Dashboard** - Key metrics and recent activity at a glance
- 🗂️ **Session Browser** - Browse and filter all recorded sessions
- 💡 **Insights View** - AI-generated insights and recommendations
- 📈 **Trend Analysis** - Historical charts and pattern visualization
- ⚠️ **Risk Tracking** - Monitor and manage security/quality risks
- 🔍 **Pattern Detection** - Discover recurring issues automatically
- 🔎 **Query Builder** - Interactive natural language queries

### 🤖 AI-Powered Analysis (LLM Integration)
Intelligent insights powered by OpenAI and Anthropic:
- 🧠 **Session Analysis** - AI summaries of Bob sessions
- 🎯 **Risk Categorization** - Automatic severity assessment
- 💬 **Pattern Explanation** - Natural language insights
- 📋 **Actionable Recommendations** - Next steps based on history
- 📊 **Trend Predictions** - Forecast future issues
- 💾 **Response Caching** - Minimize API costs (cache hits for repeated queries)

### 📦 Smart Pack Generation
Automated artifact collection and pack creation:
- 🔍 **Auto-Collect** - Intelligent discovery of git diffs, test outputs, CI logs
- 👁️ **Watch Mode** - Real-time monitoring with auto-regeneration
- ✅ **Validation** - Comprehensive CRUMB v1.4 format verification
- 🔗 **Proof Chain** - SHA-256 hashes for tamper detection
- 📊 **Pack Diff** - Visual comparison of pack versions

### 🧠 Multi-Session Memory System
SQLite database that tracks patterns across development sessions:
- 💾 **Persistent Storage** - Never lose context between sessions
- 🔍 **Cross-Session Queries** - Find patterns across all history
- 🌳 **Git Integration** - Automatic branch, commit, and author tracking
- 📈 **Timeline Analysis** - Understand how your project evolves
- 🤝 **Team Collaboration** - Share and query team sessions

### 🔮 Intelligence Engine
Transform session history into actionable insights:
- 💬 **Natural Language Queries** - Ask questions in plain English
- 🔄 **Pattern Detection** - Automatically find recurring issues
- 💡 **Actionable Insights** - Get recommendations based on history
- 🎯 **Predictive Analysis** - Forecast impact, risks, and complexity
- 📊 **Intelligence Dashboard** - At-a-glance overview of your codebase

### 🔒 Enterprise Hardening
Production-ready security and reliability:
- 🔐 **Structured JSON Logging** - Request correlation IDs and audit trails
- 🛡️ **Security Headers** - CSP, X-Frame-Options, HSTS support
- ⚡ **Rate Limiting** - Token-bucket per-IP protection
- 📊 **Prometheus Metrics** - Observability without dependencies
- 🔄 **Migration Framework** - Forward-only schema upgrades
- 🐳 **Docker Support** - Multi-stage builds, non-root user, read-only FS

---

## 🚀 Quick Start

### Installation

**Recommended: Use a virtual environment**

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install CrumbBob with all features
pip install -e .[all]

# Or install specific feature sets:
pip install -e .[ui]      # Rich terminal UI
pip install -e .[web]     # Web dashboard
pip install -e .[watch]   # Watch mode
pip install -e .[llm]     # AI-powered analysis
pip install -e .[dev]     # Development tools

# Verify installation
crumdbob --help
```

### 5-Minute Walkthrough

**1. Generate Your First Pack**

```bash
# Auto-collect artifacts from your Git repo (30 seconds)
crumdbob auto-collect --out ./generated

# Or manually from a Bob report
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
```

**2. Initialize Memory Database**

```bash
# One-time setup
crumdbob init-db

# Record your pack
crumdbob record ./generated
```

**3. Explore Your Data**

```bash
# List all sessions
crumdbob list-sessions

# View session details
crumdbob show-session 1

# Generate insights
crumdbob insights generate
crumdbob insights actionable
```

**4. Launch Web Dashboard**

```bash
# Start the server
crumdbob serve
# Opens browser at http://localhost:8000
```

**5. Try AI-Powered Analysis** (Optional)

```bash
# Configure LLM provider
export OPENAI_API_KEY="sk-..."
crumdbob llm setup openai --model gpt-4

# Analyze a session
crumdbob llm analyze 1

# Get recommendations
crumdbob llm recommend 1
```

### Common Use Cases

**Hackathon Demo:**
```bash
crumdbob inspect examples/compliance-ai/bob-report.md
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
crumdbob validate examples/compliance-ai/generated
crumdbob replay examples/compliance-ai/generated
```

**Active Development:**
```bash
# Start watch mode for continuous updates
crumdbob watch ./crumdbob-input --out ./generated

# Work normally - pack stays current automatically
vim src/auth.py
pytest
git commit
```

**Team Collaboration:**
```bash
# Enable auto-recording
crumdbob config set auto_record true

# Work normally - sessions auto-record
crumdbob pack ./input --out ./pack-v1

# Query team history
crumdbob query natural "Show me all authentication risks"
crumdbob patterns detect --type risks
```

**PR Review:**
```bash
# Compare pack versions
crumdbob diff ./pack-before ./pack-after --format=detailed

# Generate PR summary
crumdbob pr ./pack-after
```

---

## 🎬 Demo

### Visual Workflow

```text
┌─────────────────────────────────────────────────────────────────┐
│                    CrumbBob Workflow                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1️⃣  IBM Bob Session                                            │
│      └─→ bob-report.md (exported)                              │
│                                                                 │
│  2️⃣  CrumbBob Auto-Collect                                      │
│      ├─→ Scans Git repo                                        │
│      ├─→ Finds diffs, tests, logs                              │
│      └─→ Interactive selection                                 │
│                                                                 │
│  3️⃣  Pack Generation (30 seconds)                               │
│      ├─→ 00_repo_genome.crumb        (architecture)            │
│      ├─→ 01_session_flight_recorder.crumb (audit trail)        │
│      ├─→ 02_next_task.crumb          (continuation)            │
│      ├─→ 03_test_plan.crumb          (testing strategy)        │
│      ├─→ 04_risk_register.crumb      (unresolved risks)        │
│      ├─→ 05_agent_passport.crumb     (session metadata)        │
│      ├─→ 06_replay_prompt.md         (handoff prompt)          │
│      ├─→ 07_pr_summary.md            (PR description)          │
│      └─→ 08_proof_chain.json         (verification hashes)     │
│                                                                 │
│  4️⃣  Memory Recording                                           │
│      └─→ SQLite database (persistent intelligence)             │
│                                                                 │
│  5️⃣  Intelligence Analysis                                      │
│      ├─→ Pattern detection                                     │
│      ├─→ Risk tracking                                         │
│      ├─→ Predictive insights                                   │
│      └─→ Natural language queries                              │
│                                                                 │
│  6️⃣  Replay & Handoff                                           │
│      └─→ Next Bob session starts with full context             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Example Output

**Pack Generation:**
```bash
$ crumdbob pack examples/compliance-ai --out ./generated

✨ CrumbBob Pack Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 Parsing Bob report...
   ✓ Found 47 files, 23 commands, 8 risks, 5 tasks

📦 Generating CRUMB pack...
   ✓ 00_repo_genome.crumb (2.1 KB)
   ✓ 01_session_flight_recorder.crumb (3.4 KB)
   ✓ 02_next_task.crumb (1.2 KB)
   ✓ 03_test_plan.crumb (2.8 KB)
   ✓ 04_risk_register.crumb (1.9 KB)
   ✓ 05_agent_passport.crumb (0.8 KB)
   ✓ 06_replay_prompt.md (4.2 KB)
   ✓ 07_pr_summary.md (2.1 KB)
   ✓ 08_proof_chain.json (1.5 KB)

✅ Pack generated successfully in ./generated
```

**Intelligence Dashboard:**
```bash
$ crumdbob dashboard

╭─────────────────────── CrumbBob Intelligence ───────────────────────╮
│                                                                      │
│  📊 Sessions: 47        🔥 Hot Files: 12       ⚠️  Active Risks: 8   │
│  📈 Trends: ↑ 15%       🎯 Patterns: 23        💡 Insights: 34      │
│                                                                      │
│  🔝 Top Risks:                                                       │
│  • SQL injection in auth/login.py (HIGH) - seen 3x                  │
│  • Missing input validation in api/users.py (MEDIUM) - seen 2x      │
│  • Hardcoded credentials in config.py (CRITICAL) - seen 1x          │
│                                                                      │
│  🔥 Hot Files (most changed):                                        │
│  • src/auth/login.py (23 sessions)                                  │
│  • src/api/users.py (18 sessions)                                   │
│  • tests/test_auth.py (15 sessions)                                 │
│                                                                      │
│  💡 Latest Insights:                                                 │
│  • Authentication module shows recurring SQL injection risks         │
│  • Consider adding input validation layer                           │
│  • Test coverage for auth module is below 60%                       │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
```

### Web Dashboard Screenshots

The web dashboard provides:
- **Real-time metrics** with auto-refresh
- **Interactive charts** (Chart.js visualizations)
- **Dark/light theme** support
- **Mobile-responsive** design
- **Advanced filtering** and search
- **Natural language queries** via REST API

---

## 🏗️ Architecture

### High-Level System Design

```text
┌─────────────────────────────────────────────────────────────────┐
│                         CrumbBob System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   CLI Tool   │    │ Web Dashboard│    │  Python API  │     │
│  │  (Terminal)  │    │   (Browser)  │    │  (Library)   │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │             │
│         └───────────────────┴───────────────────┘             │
│                             │                                 │
│         ┌───────────────────┴───────────────────┐             │
│         │                                       │             │
│         ▼                                       ▼             │
│  ┌──────────────┐                      ┌──────────────┐       │
│  │   Parser     │                      │   Packer     │       │
│  │  (Bob→Data)  │                      │ (Data→CRUMB) │       │
│  └──────┬───────┘                      └──────┬───────┘       │
│         │                                     │               │
│         └─────────────────┬───────────────────┘               │
│                           │                                   │
│                           ▼                                   │
│         ┌─────────────────────────────────────┐               │
│         │      Memory Database (SQLite)       │               │
│         │  • Sessions  • Files  • Commands    │               │
│         │  • Risks     • Tasks  • Insights    │               │
│         └─────────────────┬───────────────────┘               │
│                           │                                   │
│         ┌─────────────────┴───────────────────┐               │
│         │                                     │               │
│         ▼                                     ▼               │
│  ┌──────────────┐                    ┌──────────────┐         │
│  │ Intelligence │                    │  Integrations│         │
│  │   Engine     │                    │  • Git       │         │
│  │ • Patterns   │                    │  • CI/CD     │         │
│  │ • Insights   │                    │  • LLM APIs  │         │
│  │ • Predictions│                    │  • VSCode    │         │
│  └──────────────┘                    └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Overview

**Core Components:**
- **Parser** (`parser.py`) - Extracts structured data from Bob reports
- **Packer** (`packer.py`) - Generates CRUMB v1.4 format packs
- **Validator** (`validator.py`) - Verifies pack integrity and format
- **Memory** (`memory.py`) - SQLite persistence layer with 8 core tables
- **CLI** (`cli.py`) - 38+ commands for all operations

**Intelligence Components:**
- **Query Engine** (`query.py`) - Natural language → SQL translation
- **Pattern Detector** (`patterns.py`) - Recurring issue identification
- **Insights Generator** (`insights.py`) - Actionable recommendations
- **Prediction Engine** (`predict.py`) - Impact and risk forecasting

**Workflow Components:**
- **Collector** (`collector.py`) - Auto-discovery of Git artifacts
- **Watcher** (`watcher.py`) - Real-time file monitoring
- **Differ** (`differ.py`) - Pack version comparison

**Web Components:**
- **FastAPI Server** (`web/api/server.py`) - REST API with 10+ endpoints
- **Middleware** (`web/api/middleware.py`) - Security, rate limiting, metrics
- **Frontend** (`web/static/`) - Vanilla JS SPA with Chart.js

### Data Flow

```text
Bob Report → Parser → BobReport Object → Packer → CRUMB Files
                                              ↓
                                         Validator
                                              ↓
                                      Memory Database
                                              ↓
                                    Intelligence Engine
                                              ↓
                                    Insights & Predictions
```

### Database Schema

**8 Core Tables:**
- `sessions` - Recorded pack sessions with Git context
- `packs` - Version history per session
- `files` - Files mentioned in each session
- `commands` - Commands captured per session
- `risks` - Security and quality risks
- `tasks` - Next-step tasks
- `relationships` - CRUMB cross-references
- `insights` - AI-generated insights

**Additional Tables:**
- `audit_log` - Security events and audit trail
- `llm_config` - LLM provider configuration
- `llm_cache` - Response caching for cost optimization

---

## 📚 Documentation

### Core Documentation
- [**CLI Reference**](docs/crumdbob-cli.md) - Complete command documentation
- [**Architecture**](ARCHITECTURE.md) - System design and technical decisions
- [**Configuration**](docs/configuration.md) - Setup and customization guide
- [**Security Policy**](SECURITY.md) - Security practices and reporting

### Feature Guides
- [**Multi-Session Memory**](docs/multi-session-memory-getting-started.md) - Getting started with persistent memory
- [**LLM Integration**](docs/llm-integration.md) - AI-powered analysis setup
- [**Intelligent Queries**](docs/intelligent-queries.md) - Natural language queries
- [**Pattern Detection**](docs/pattern-detection.md) - Automatic issue discovery
- [**Predictions**](docs/predictions.md) - Impact and risk forecasting
- [**Insights System**](docs/insights.md) - Actionable recommendations

### Workflow Guides
- [**Auto-Collect Workflow**](examples/workflows/01-auto-collect-workflow.md) - Intelligent artifact collection
- [**Watch Mode Workflow**](examples/workflows/02-watch-mode-workflow.md) - Active development with auto-updates
- [**Diff Workflow**](examples/workflows/03-diff-workflow.md) - Pack comparison for PR reviews

### Advanced Topics
- [**Proof Chain**](docs/proof-chain.md) - Verification and tamper detection
- [**Integrations**](docs/integrations.md) - CI/CD and tool integration
- [**Bob Shell Integration**](docs/bob-shell-integration.md) - IBM Bob CLI integration
- [**Enhancement Roadmap**](docs/enhancement-roadmap.md) - Future features and vision

### For Judges & Stakeholders
- [**Judge Walkthrough**](docs/judge-walkthrough.md) - Evaluation guide
- [**Demo Script**](DEMO_SCRIPT.md) - Live demonstration guide
- [**Hackathon Thesis**](HACKATHON.md) - Project vision and goals

---

## 🎯 Use Cases

### 1. Hackathon Demos
**Perfect for showcasing AI development workflows:**
- Generate impressive memory packs in 30 seconds
- Demonstrate cross-session intelligence
- Show predictive insights and pattern detection
- Prove tamper-evidence with proof chains

### 2. Team Collaboration
**Build shared knowledge across your team:**
- Every developer's Bob sessions become team assets
- Query collective history for patterns and insights
- Avoid duplicate analysis work
- Faster onboarding for new team members

### 3. Production Deployment
**Enterprise-ready with security hardening:**
- Docker deployment with read-only filesystem
- Rate limiting and security headers
- Structured logging with correlation IDs
- Prometheus metrics for observability
- Audit logging for compliance

### 4. Compliance & Auditing
**Track and verify development decisions:**
- Tamper-evident proof chains
- Complete audit trail of all sessions
- Risk tracking across time
- Reproducible analysis results

### 5. Code Quality Improvement
**Data-driven development insights:**
- Identify recurring issues automatically
- Predict impact of changes before making them
- Track code quality trends over time
- Get AI-powered recommendations

---

## 🤝 Contributing

We welcome contributions! CrumbBob is built to be extensible and maintainable.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/XioAISolutions/Crumb-Bob.git
cd Crumb-Bob

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest -q

# Run linting
ruff check .
ruff format .

# Run type checking
mypy crumdbob web
```

### Testing Guidelines

- **290 tests** covering all major functionality
- **65% coverage (60% floor)** (enforced in CI)
- Run `pytest -q` for quick test suite
- Run `pytest --cov` for coverage report
- All tests must pass before merging

### Code Quality Standards

- **Ruff** for linting and formatting (100 char line length)
- **mypy** for type checking (strict mode)
- **Bandit** for security scanning
- **Pre-commit hooks** enforce standards automatically

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the full test suite and linters
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`, etc.)
6. Push to your fork and open a PR
7. Wait for CI to pass and review feedback

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📜 License & Credits

### License

CrumbBob is released under the **MIT License**. See [LICENSE](LICENSE) for details.

### Acknowledgments

- **IBM Bob** - The AI agent that inspired this project
- **CRUMB Format** - Compact Replayable Universal Memory Block specification
- **Rich Library** - Beautiful terminal UI framework
- **FastAPI** - Modern web framework for the dashboard
- **SQLite** - Reliable embedded database

### Related Projects

- [IBM Bob](https://www.ibm.com/products/watsonx-code-assistant) - AI-powered coding assistant
- [CRUMB Specification](https://github.com/XioAISolutions/CRUMB-spec) - Memory format standard

### Built With ❤️ By

**XIO AI Solutions** - Transforming AI development workflows

---

## 🚦 Status & Roadmap

### Current Status: v0.3.1 (Submission Ready)

✅ **Core Features Complete:**
- Pack generation and validation
- Multi-session memory database
- Intelligence engine (queries, patterns, insights, predictions)
- Rich terminal UI
- Web dashboard
- LLM integration
- Enterprise hardening (security, logging, metrics)

✅ **Quality Metrics:**
- 290 tests passing
- 65% coverage (60% floor)
- Type-checked with mypy
- Security-scanned with Bandit
- CI/CD with GitHub Actions

### Upcoming Features (v0.4.0)

🔮 **Planned Enhancements:**
- VSCode extension with inline insights
- Team sync with conflict resolution
- Advanced analytics dashboard
- Custom query templates
- Webhook integrations
- PostgreSQL backend option

See [Enhancement Roadmap](docs/enhancement-roadmap.md) for detailed plans.

---

## 📞 Support & Community

### Getting Help

- 📖 **Documentation**: Start with the [Quick Start](#-quick-start) guide
- 🐛 **Bug Reports**: [Open an issue](https://github.com/XioAISolutions/Crumb-Bob/issues)
- 💡 **Feature Requests**: [Discuss ideas](https://github.com/XioAISolutions/Crumb-Bob/discussions)
- 📧 **Email**: support@xioai.solutions

### Quick Links

- [GitHub Repository](https://github.com/XioAISolutions/Crumb-Bob)
- [Issue Tracker](https://github.com/XioAISolutions/Crumb-Bob/issues)
- [Changelog](CHANGELOG.md)
- [Security Policy](SECURITY.md)

---

## 🎓 Final Submission Checklist

For judges and evaluators:

```bash
# 1. Install and verify
pip install -e .[dev]
pytest -q

# 2. Generate example pack
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated

# 3. Validate pack integrity
crumdbob doctor examples/compliance-ai/generated

# 4. View replay prompt
crumdbob replay examples/compliance-ai/generated

# 5. Inspect proof chain
cat examples/compliance-ai/generated/08_proof_chain.json

# 6. Try web dashboard
crumdbob serve --no-browser
```

**Key Files to Inspect:**
- `examples/compliance-ai/bob-report.md` - Source Bob report
- `examples/compliance-ai/generated/00_repo_genome.crumb` - Architecture memory
- `examples/compliance-ai/generated/01_session_flight_recorder.crumb` - Audit trail
- `examples/compliance-ai/generated/04_risk_register.crumb` - Unresolved risks
- `examples/compliance-ai/generated/08_proof_chain.json` - Verification hashes
- `web/static/index.html` - Dashboard shell served by `crumdbob serve`

---

## 💡 Hackathon Thesis

**Most teams use Bob to build an app. CrumbBob builds the missing memory layer around Bob.**

### The Vision

IBM Bob is incredibly powerful during a session—it understands your codebase, suggests improvements, and helps you build. But when the session ends, that understanding vanishes. The next developer, or even the same developer tomorrow, starts from scratch.

**CrumbBob solves this by:**
1. **Capturing** everything Bob learned in a replayable format
2. **Compressing** it into structured CRUMB memory blocks
3. **Replaying** it to restore full context instantly
4. **Proving** integrity with cryptographic verification
5. **Learning** from patterns across all sessions

### The Impact

- **For Developers**: Less repetitive context gathering
- **For Teams**: Shared knowledge base that grows with every session
- **For Organizations**: Institutional memory that survives turnover
- **For AI Agents**: Persistent memory that makes them truly intelligent

**CrumbBob transforms Bob from a powerful tool into an organizational intelligence platform.**

---

<div align="center">

**⭐ Star us on GitHub if CrumbBob helps your team!**

[GitHub](https://github.com/XioAISolutions/Crumb-Bob) • [Documentation](docs/) • [License](LICENSE)

Made with 🧠 by XIO AI Solutions

</div>
