# CrumbBob Architecture

This document describes the high-level structure of CrumbBob, the
contracts between modules, and the rationale behind the major design
decisions. It is intentionally a working document — when the design
shifts, this file gets updated in the same PR.

## C4 Level 1 — System context

```
                       ┌────────────────────┐
                       │   IBM Bob report   │
                       │  (markdown export) │
                       └─────────┬──────────┘
                                 │
                                 ▼
   ┌───────────────┐      ┌─────────────────┐      ┌──────────────────┐
   │   Developer   │◀────▶│    CrumbBob     │◀────▶│  SQLite memory   │
   │     (CLI)     │      │   (this repo)   │      │     database     │
   └───────────────┘      └────────┬────────┘      └──────────────────┘
                                   │
                          ┌────────┴────────┐
                          ▼                 ▼
                  ┌────────────────┐ ┌──────────────────┐
                  │ CRUMB v1.4 pack│ │  Web dashboard   │
                  │ (9 files on FS)│ │ (FastAPI + static│
                  │                │ │   single-page)   │
                  └────────────────┘ └──────────────────┘
```

CrumbBob is a single Python package with three user-facing surfaces:

1. **CLI** (`crumdbob …`) — primary interface for pack generation,
   validation, and database operations.
2. **Web dashboard** (`crumdbob serve`) — read-mostly visualization
   of session history, insights, patterns, and risks.
3. **Library API** (`import crumdbob`) — for embedding in other tools.

## C4 Level 2 — Container view

```
┌──────────────────────────────────────────────────────────────────────┐
│                          crumdbob (package)                          │
│                                                                      │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   CLI   │  │ Parser  │  │  Packer  │  │ Validator│  │ Watcher  │  │
│  │ cli.py  │  │parser.py│  │packer.py │  │valid.py  │  │watcher.py│  │
│  └────┬────┘  └────┬────┘  └────┬─────┘  └────┬─────┘  └─────┬────┘  │
│       │            │            │             │              │       │
│       └────────────┴────────────┴─────────────┴──────────────┘       │
│                                 │                                    │
│            ┌────────────────────┴────────────────────┐               │
│            ▼                                         ▼               │
│  ┌──────────────────┐                      ┌──────────────────┐      │
│  │   memory.py      │                      │  Intelligence    │      │
│  │  (SQLite I/O)    │◀────────────────────▶│  insights.py     │      │
│  │  migrations.py   │                      │  patterns.py     │      │
│  │  pagination.py   │                      │  predict.py      │      │
│  │  audit.py        │                      │  query.py        │      │
│  └──────────────────┘                      └──────────────────┘      │
│            │                                                         │
└────────────┼─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          web (package)                               │
│  ┌──────────────────┐  ┌──────────────────────────────────────────┐  │
│  │  api/server.py   │  │            api/middleware.py             │  │
│  │   (FastAPI)      │◀─┤  RequestID │ SecurityHeaders │ RateLimit │  │
│  └────────┬─────────┘  └──────────────────────────────────────────┘  │
│           │                ┌────────────────────────┐                │
│           ├──────────────▶ │  api/metrics.py        │                │
│           │                │  (Prometheus)          │                │
│           │                └────────────────────────┘                │
│           ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ static/index.html + app.js + styles.css                         │ │
│  │ (vanilla JS SPA, no build step)                                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

## Module map

| Module                    | Purpose                                                    | Key types                                           | Stability                       |
| ------------------------- | ---------------------------------------------------------- | --------------------------------------------------- | ------------------------------- |
| `crumdbob.cli`            | Argparse entry point; orchestrates everything.             | (functions only)                                    | Stable — public CLI             |
| `crumdbob.parser`         | Parse an IBM Bob markdown report into `BobReport`.         | `BobReport`, `SourceArtifact`                       | Stable                          |
| `crumdbob.packer`         | Generate CRUMB v1.4 pack files from a `BobReport`.         | (functions)                                         | Stable                          |
| `crumdbob.validator`      | Validate CRUMB files against the v1.4 grammar.             | `CrumbDocument`, `ValidationReport`                 | Stable                          |
| `crumdbob.collector`      | Auto-discover git diffs, test output, CI logs.             | `Artifact`                                          | Stable                          |
| `crumdbob.watcher`        | File-system watch loop driving pack regeneration.          | `PackRegenerationHandler`                           | Stable (optional dep: watchdog) |
| `crumdbob.differ`         | Diff two CRUMB packs.                                      | (functions)                                         | Stable                          |
| `crumdbob.memory`         | SQLite persistence for session history.                    | `MemoryDatabase`, `Session`, `FileRecord`, …        | Stable                          |
| `crumdbob.migrations`     | Forward-only schema migrations.                            | (decorator + runner)                                | Stable (v0.3.1+)                |
| `crumdbob.config`         | User preferences (JSON file at `~/.crumdbob/config.json`). | (functions)                                         | Stable                          |
| `crumdbob.audit`          | Tamper-evident security event log.                         | `AuditLogger`, `AuditEvent`                         | New (v0.3.1)                    |
| `crumdbob.logging_config` | Structured (JSON or human) logging setup.                  | `JsonFormatter`, `PlainFormatter`, `request_id_ctx` | New (v0.3.1)                    |
| `crumdbob.pagination`     | HAL-style pagination helper.                               | `Page`, `paginate()`                                | New (v0.3.1)                    |
| `crumdbob.retry`          | Exponential-backoff retry decorator.                       | `retry()`                                           | New (v0.3.1)                    |
| `crumdbob.insights`       | Generate actionable insights from history.                 | `Insight`, `InsightsEngine`                         | Beta                            |
| `crumdbob.patterns`       | Detect cross-session patterns.                             | `Pattern`, `PatternDetector`                        | Beta                            |
| `crumdbob.predict`        | Predict impact / risks / complexity / tests.               | `Prediction`, `PredictionEngine`                    | Beta                            |
| `crumdbob.query`          | Natural-language → SQL translator.                         | `QueryEngine`                                       | Beta                            |
| `crumdbob.ui`             | Rich-terminal output (optional dep: rich).                 | `CrumbBobUI`                                        | Stable                          |
| `crumdbob.llm`            | LLM integration (optional dep: openai, anthropic).         | `LLMConfig`, `LLMAnalyzer`                          | Beta                            |
| `web.api.server`          | FastAPI app factory (`create_app()`).                      | (functions)                                         | Stable (optional dep: fastapi)  |
| `web.api.middleware`      | Request ID / security headers / rate limit.                | 3 middleware classes                                | New (v0.3.1)                    |
| `web.api.metrics`         | Prometheus text-format exposition.                         | `MetricsMiddleware`, counters                       | New (v0.3.1)                    |

## Data flow

### Pack generation (`crumdbob pack`)

```
bob-report.md ──▶ parser.parse_bob_report() ──▶ BobReport
                                                    │
artifacts ────▶ parser.enrich_report_with_artifact()
   (git diff,                                       │
    tests, etc.)                                    ▼
                                          packer.write_pack()
                                                    │
                                                    ▼
                          9 files in <out>/  (00..08_*.crumb / .md / .json)
                                                    │
                                                    ▼
                                          validator.validate_target()
                                                    │
                                                    └─▶ exit 0 / non-zero
```

### Session recording (`crumdbob record`)

```
<pack-dir>  ──▶ packer reads 08_proof_chain.json (single read since v0.3.1)
                       │
                       ▼
              parser.parse_bob_report(source_report_path)
                       │  (path-traversal-guarded since v0.3.1)
                       ▼
              memory.MemoryDatabase.record_session()
                       │
                       ▼
                ┌──────┴───────┐
                ▼              ▼
          sessions table   audit_log table
                ▼              ▼
          files/cmds/        ts, event=pack.recorded,
          risks/tasks        actor, request_id, payload
```

### HTTP request lifecycle (`crumdbob serve`)

```
   HTTP Request
       │
       ▼
┌──────────────────────────────┐
│  RequestIDMiddleware         │  Mint or echo X-Request-ID, bind ContextVar
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  SecurityHeadersMiddleware   │  Will attach CSP/X-Frame/etc. on the way out
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  RateLimitMiddleware         │  Token-bucket per IP; 429 if empty
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  MetricsMiddleware           │  Time the request, count it
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  CORSMiddleware              │  Reject cross-origin if regex doesn't match
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  @app.middleware api_key     │  Check X-API-Key if CRUMDBOB_API_KEY set
└──────────────────────────────┘
       │  (on failure → audit.record(EVENT_AUTH_FAILURE))
       ▼
┌──────────────────────────────┐
│  @app.exception_handler      │  Catches anything that escapes the route
└──────────────────────────────┘
       │
       ▼
   Route handler ───▶ _server_error(exc) if raised
                            │
                            ▼
                  Sanitized JSON {error, error_id}
```

## Storage layout

```
~/.crumdbob/
├── config.json       # CLI preferences (auto_record, default_db, …)
└── memory.db         # SQLite database (default location)

memory.db schema (v2)
├── metadata          # key/value, includes schema_version
├── sessions          # one row per recorded pack session
├── packs             # version history per session
├── files             # files mentioned in each session
├── commands          # commands captured per session
├── risks             # risks per session
├── tasks             # next-step tasks per session
├── relationships     # CRUMB cross-references
├── insights          # AI-generated insights (deduped since v0.3.1)
├── audit_log         # NEW v0.3.1 — security/audit events
├── llm_config        # LLM provider config
└── llm_cache         # LLM response cache (TTL'd)
```

### SQLite tuning

Set on every connection in `MemoryDatabase.__init__`:

- `PRAGMA journal_mode=WAL` — readers don't block writers, single writer
  doesn't block readers. Big throughput win at zero correctness cost.
- `PRAGMA foreign_keys=ON` — enforce cascade deletes on `ON DELETE CASCADE`.
  Off by default in SQLite for legacy reasons; we always want it.
- `PRAGMA synchronous=NORMAL` — safe with WAL; trades a 0.5% durability
  window for a 5–10× write speedup.

## Configuration surface

CrumbBob reads configuration from three places, in this precedence:

1. **Environment variables** (highest priority).
   See the table below.
2. **`~/.crumdbob/config.json`** — managed via `crumdbob config set …`.
3. **Hard-coded defaults** — sensible for local development.

| Env var                          | Purpose                                         | Default                                       |
| -------------------------------- | ----------------------------------------------- | --------------------------------------------- |
| `CRUMDBOB_API_KEY`               | If set, require `X-API-Key` header on `/api/*`. | (unset — open)                                |
| `CRUMDBOB_CORS_ORIGIN_REGEX`     | Regex of allowed CORS origins.                  | `^https?://(localhost\|127\.0\.0\.1)(:\d+)?$` |
| `CRUMDBOB_RATE_LIMIT_PER_SECOND` | Sustained rate per IP.                          | `10`                                          |
| `CRUMDBOB_RATE_LIMIT_BURST`      | Bucket capacity per IP.                         | `30`                                          |
| `CRUMDBOB_ENABLE_HSTS`           | Send HSTS header (set behind TLS proxy).        | (unset — off)                                 |
| `CRUMDBOB_LOG_FORMAT`            | `json` or `plain`.                              | auto (TTY → plain)                            |
| `CRUMDBOB_DATA_DIR`              | Where the SQLite DB lives.                      | `~/.crumdbob`                                 |

## Why these choices

### Why SQLite, not Postgres?

CrumbBob is built around the assumption that session memory is **local
per developer or per team**. The data volume is small (tens of MB even
after years of use), the access pattern is read-heavy, and zero-ops
deployment beats every other consideration. WAL mode + indices get us
adequate concurrency for the expected single-digit writer count.

If you hit SQLite's ceilings, the schema and queries port cleanly to
PostgreSQL; `MemoryDatabase` is the only module that needs a backend
swap.

### Why hand-rolled migrations, not Alembic?

Alembic pulls in SQLAlchemy (~60 MB transitive deps). CrumbBob's
schema is small and we never need to downgrade. The 50-line
`migrations.py` covers our needs with zero new dependencies.

### Why zero JS framework?

The dashboard is read-heavy with simple interactions. Vanilla JS with
DOM APIs (the `el()` helper) renders in <50ms per view and ships
~50 KB instead of the ~150 KB minimum for React + bundler. The cost is
that some patterns (state synchronization across views) are slightly
more code, but the surface area is small enough that it doesn't matter.

### Why CRUMB v1.4 as the on-disk format?

CRUMB (Compact Replayable Universal Memory Block) is a deliberately
text-first format so it diffs cleanly in git and humans can read it
without a viewer. v1.4 is the contract we ship — we will not break it
without a major-version bump and a migration tool.

## Deployment topologies

### Single-user CLI

```
   developer machine
   ────────────────
   crumdbob … ──▶ ~/.crumdbob/memory.db
```

### Single-node dashboard

```
   developer machine            developer browser
   ────────────────             ─────────────────
   crumdbob serve  ───────────▶ http://127.0.0.1:8000
        │
        └──▶ ~/.crumdbob/memory.db
```

### Team deployment (recommended)

```
   ┌───────────┐    HTTPS    ┌─────────────────────────────┐
   │  Browser  │ ──────────▶ │  TLS proxy (nginx/Caddy)    │
   └───────────┘             │  • adds X-API-Key from vault│
                             └──────────────┬──────────────┘
                                            │ plain HTTP
                                            ▼
                             ┌─────────────────────────────┐
                             │  Docker container           │
                             │  • crumdbob serve --host    │
                             │    0.0.0.0 --port 8000      │
                             │  • CRUMDBOB_API_KEY=...     │
                             │  • CRUMDBOB_ENABLE_HSTS=1   │
                             │  • read-only root FS        │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │ persistent       │
                                  │ volume: /data    │
                                  └──────────────────┘
```

## Open architectural questions

These are tracked as issues; named here so reviewers know the
known unknowns:

- **Async DB I/O.** Routes are `async def` but the SQLite handle is
  synchronous, so we serialize writes on a single thread. For our
  current throughput this is fine; eventually we'll either move to
  `aiosqlite` or migrate to PostgreSQL with `asyncpg`.
- **Multi-replica deployment.** In-process rate limiting doesn't
  scale horizontally. Pluggable bucket store (Redis) tracked for v0.4.
- **CSRF in cookie-auth mode.** We currently have no cookie auth, so
  no CSRF surface. If/when we add cookie SSO, we need CSRF tokens.
- **Connection pooling.** The FastAPI app holds one `MemoryDatabase`
  per app instance; the audit logger opens short-lived connections.
  This is fine for single-node, but a connection-pool wrapper would
  let us scale writes more cleanly.

## Glossary

- **CRUMB** — Compact Replayable Universal Memory Block. The on-disk
  format for a single piece of memory. Grammar version v1.4.
- **Pack** — a directory of 9 CRUMB files plus `06_replay_prompt.md`,
  `07_pr_summary.md`, and `08_proof_chain.json` that together capture
  one IBM Bob session.
- **Proof chain** — `08_proof_chain.json`. Records SHA-256 hashes of
  the source `bob-report.md` and every generated file. The `doctor`
  command verifies these are current.
- **Session** — one recorded `pack` in the memory database. A
  session can have many pack versions (e.g., regenerated as the
  source report evolves).
- **Replay** — using a stored pack to bootstrap a new IBM Bob (or
  human) session with full prior context.
