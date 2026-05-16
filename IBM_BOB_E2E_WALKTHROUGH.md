# IBM Bob — End-to-End Walkthrough of CrumdBob v0.3.1

**Use this prompt verbatim.** Paste the whole document into IBM Bob
(`bob --chat-mode ask --hide-intermediary-output "$(cat IBM_BOB_E2E_WALKTHROUGH.md)"`)
or into a fresh agent session. The goal is an independent, end-to-end
audit confirming that the v0.3.1 enterprise-hardening pass is production-ready.

---

## Your job

You are conducting a **release-gate audit** of CrumdBob v0.3.1. The
codebase has just received a substantial enterprise-grade hardening
pass: structured logging, observability middleware, rate limiting,
audit logging, migration framework, API versioning, Docker support,
and ~80 new tests. **Verify everything actually works** rather than
trusting the documentation.

You have **full read access** to the repo at `/Users/slavaz/Crumb-Bob`.
You may **run any verification command** but **do not modify code**
unless you find a clear bug that needs a one-line fix. If you find
something deeper, **flag it for human review** rather than fixing it.

Output a single audit report at the end. Do not stop until you've
completed every section below.

---

## Repository layout (orient yourself first)

```
/Users/slavaz/Crumb-Bob/
├── crumdbob/              # Python package (CLI + library)
│   ├── audit.py           # NEW v0.3.1 — audit log persistence
│   ├── cli.py             # argparse entry point
│   ├── collector.py       # auto-discover artifacts
│   ├── config.py          # user preferences
│   ├── differ.py          # diff two CRUMB packs
│   ├── insights.py        # AI-generated insights (heuristic)
│   ├── llm.py             # optional LLM SDK adapter
│   ├── logging_config.py  # NEW v0.3.1 — structured JSON logging
│   ├── memory.py          # SQLite persistence
│   ├── migrations.py      # NEW v0.3.1 — forward-only migration runner
│   ├── pagination.py      # NEW v0.3.1 — HAL-style pagination helper
│   ├── parser.py          # Bob report → BobReport
│   ├── patterns.py        # cross-session pattern detection
│   ├── predict.py         # impact/risk/complexity prediction
│   ├── py.typed           # NEW v0.3.1 — PEP 561 marker
│   ├── query.py           # NL → SQL translator
│   ├── retry.py           # NEW v0.3.1 — exponential backoff decorator
│   ├── ui.py              # Rich terminal UI
│   ├── validator.py       # CRUMB v1.4 grammar validator
│   └── watcher.py         # filesystem watch loop
├── web/                   # FastAPI + static SPA
│   ├── api/
│   │   ├── server.py      # MODIFIED v0.3.1 — wires middleware/metrics/audit
│   │   ├── middleware.py  # NEW v0.3.1 — request-id, security headers, rate limit
│   │   └── metrics.py     # NEW v0.3.1 — Prometheus exposition
│   └── static/
│       ├── index.html
│       ├── app.js         # MODIFIED v0.3.1 — XSS hardening via DOM API
│       └── styles.css
├── tests/                 # 290 tests, ~65% coverage
├── examples/compliance-ai/  # demo IBM Bob report + generated pack
├── .github/workflows/ci.yml      # NEW v0.3.1 — matrix CI
├── .pre-commit-config.yaml       # NEW v0.3.1
├── Dockerfile                     # NEW v0.3.1 — multi-stage
├── docker-compose.yml             # NEW v0.3.1
├── .dockerignore                  # NEW v0.3.1
├── pyproject.toml                 # REWRITTEN v0.3.1 — strict tooling config
├── CHANGELOG.md                   # UPDATED v0.3.1
├── SECURITY.md                    # NEW v0.3.1
├── CONTRIBUTING.md                # NEW v0.3.1
└── ARCHITECTURE.md                # NEW v0.3.1
```

---

## Section 1 — Environment & install verification

Run these in order. Stop and flag if any step fails unexpectedly.

```bash
# 1.1 Confirm the working tree compiles
cd /Users/slavaz/Crumb-Bob
python3 -m py_compile crumdbob/*.py web/api/*.py
echo "exit=$?  (must be 0)"

# 1.2 Set up an isolated venv (verify-venv may already exist)
test -d /tmp/crumdbob-verify-venv || python3 -m venv /tmp/crumdbob-verify-venv
source /tmp/crumdbob-verify-venv/bin/activate
pip install -e ".[dev]" -q

# 1.3 Confirm the version pin
python3 -c "from crumdbob import __version__; print(__version__)"
# Expected: 0.3.1 (CHANGELOG says 0.3.1; if it says 0.3.0 this is a bug — flag it)

# 1.4 Confirm py.typed marker is in the wheel
python3 -c "import importlib.resources, crumdbob; print(list(importlib.resources.files(crumdbob).iterdir()))" \
  | tr ',' '\n' | grep py.typed
# Expected: a line containing PosixPath('.../crumdbob/py.typed')
```

**Report:** Did all four steps succeed? List any version mismatch
(`crumdbob.__version__` should be `0.3.1`).

---

## Section 2 — Test suite

```bash
source /tmp/crumdbob-verify-venv/bin/activate
cd /Users/slavaz/Crumb-Bob
python3 -m pytest tests/ -v 2>&1 | tail -40
```

**Expected:** 290 tests pass, 0 fail, 0 skip. If anything skips or
fails, list which and which file.

Then run with coverage:

```bash
python3 -m pytest --cov=crumdbob --cov=web --cov-report=term -q 2>&1 | tail -30
```

**Expected:** TOTAL coverage ≥ 60% (currently ~65%). New modules
should be at 86–100%:

- `crumdbob/audit.py` — 100%
- `crumdbob/logging_config.py` — 100%
- `crumdbob/migrations.py` — 86%
- `crumdbob/pagination.py` — 100%
- `crumdbob/retry.py` — 100%
- `web/api/middleware.py` — 100%
- `web/api/metrics.py` — 86%

**Report:** Test count, coverage %, any modules below their target.

---

## Section 3 — Static analysis

```bash
source /tmp/crumdbob-verify-venv/bin/activate
cd /Users/slavaz/Crumb-Bob

# 3.1 Ruff (lint)
ruff check . --statistics 2>&1 | tail -30

# 3.2 Ruff (format check — should be clean since ruff format was applied)
ruff format --check . 2>&1 | tail -5

# 3.3 Bandit (security)
bandit -c pyproject.toml -r crumdbob web 2>&1 | tail -15

# 3.4 pip-audit (vulnerable deps)
pip-audit --disable-pip 2>&1 | tail -10
```

**Expected:**

- Ruff: ≤ 200 issues remaining (most are pre-existing in legacy modules).
  The NEW v0.3.1 modules (`audit.py`, `logging_config.py`, `migrations.py`,
  `pagination.py`, `retry.py`, `middleware.py`, `metrics.py`) must have
  **zero** ruff errors. Verify this:
  ```bash
  ruff check crumdbob/audit.py crumdbob/logging_config.py \
              crumdbob/migrations.py crumdbob/pagination.py \
              crumdbob/retry.py web/api/middleware.py web/api/metrics.py
  ```
- Bandit: ≤ 5 issues, all Low severity, all in legacy modules.
- pip-audit: 0 known vulnerabilities.

**Report:** Counts for each. List any HIGH-severity bandit finding
(should be zero — flag immediately if not).

---

## Section 4 — End-to-end CLI workflow

This exercises the core happy path that judges will see.

```bash
source /tmp/crumdbob-verify-venv/bin/activate
cd /Users/slavaz/Crumb-Bob

# 4.1 Generate a fresh pack from the demo report
rm -rf /tmp/cb-walkthrough && mkdir -p /tmp/cb-walkthrough
cp examples/compliance-ai/bob-report.md /tmp/cb-walkthrough/
crumdbob pack /tmp/cb-walkthrough --out /tmp/cb-walkthrough/generated 2>&1 | tail -15

# 4.2 Confirm all 9 pack files exist
ls /tmp/cb-walkthrough/generated/ | wc -l   # expect 9
ls /tmp/cb-walkthrough/generated/

# 4.3 Validate the pack
crumdbob validate /tmp/cb-walkthrough/generated 2>&1 | tail -10
# Expect "All 6 CRUMB file(s) are valid" (Rich-styled) or "OK: 6 CRUMB file(s) valid"

# 4.4 Verify proof chain
crumdbob doctor /tmp/cb-walkthrough/generated 2>&1 | tail -15
# Expect "verdict: ready for judge walkthrough"

# 4.5 Confirm version stamp in proof chain
python3 -c "import json; print(json.load(open('/tmp/cb-walkthrough/generated/08_proof_chain.json'))['crumdbob_version'])"
# Expect: 0.3.1 (if 0.3.0, the version-bump was incomplete — flag it)

# 4.6 Record the session and verify audit_log was written
rm -f /tmp/cb-walkthrough/memory.db
crumdbob init-db --path /tmp/cb-walkthrough/memory.db 2>&1 | tail -3
crumdbob record /tmp/cb-walkthrough/generated --db /tmp/cb-walkthrough/memory.db 2>&1 | tail -5

# 4.7 Inspect the database schema — confirm audit_log is present (schema v2)
python3 -c "
import sqlite3
c = sqlite3.connect('/tmp/cb-walkthrough/memory.db')
tables = [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\")]
print('TABLES:', tables)
print('schema_version:', c.execute(\"SELECT value FROM metadata WHERE key='schema_version'\").fetchone())
"
# Expect: audit_log in TABLES, schema_version == ('2',)
```

**Report:** Confirm 9 pack files, doctor verdict, proof-chain version,
audit_log table presence, schema version = 2.

---

## Section 5 — Web dashboard & API smoke tests

```bash
source /tmp/crumdbob-verify-venv/bin/activate
cd /Users/slavaz/Crumb-Bob

# 5.1 Start the API in the background
export CRUMDBOB_DATA_DIR=/tmp/cb-walkthrough
crumdbob serve --host 127.0.0.1 --port 8765 &
SERVE_PID=$!
sleep 2

# 5.2 Health + readiness
curl -s http://127.0.0.1:8765/api/health | python3 -m json.tool
curl -s http://127.0.0.1:8765/api/ready | python3 -m json.tool

# 5.3 V1 alias works
curl -s http://127.0.0.1:8765/api/v1/health | python3 -m json.tool

# 5.4 Security headers are present (this proves SecurityHeadersMiddleware is wired)
curl -sI http://127.0.0.1:8765/api/health | grep -iE "x-frame-options|content-security-policy|x-content-type-options|x-request-id"
# Expect 4 headers

# 5.5 Request ID is echoed
curl -sI http://127.0.0.1:8765/api/health -H "X-Request-ID: bob-test-id-42" | grep -i x-request-id
# Expect: x-request-id: bob-test-id-42

# 5.6 Prometheus metrics endpoint exposes the right shape
curl -s http://127.0.0.1:8765/metrics | head -30
# Expect HELP/TYPE markers and crumdbob_* counter names

# 5.7 Sanitised 500: cause an error and confirm no SQL leaks in the response
curl -s "http://127.0.0.1:8765/api/sessions/99999" -w "\nHTTP %{http_code}\n"
# Expect 404 (proper not-found, not 500). If 500, check the body has no SQL.

# 5.8 Rate limit enforcement — hammer the API and watch for 429s
for i in $(seq 1 50); do
  curl -s -o /dev/null -w "%{http_code} " http://127.0.0.1:8765/api/stats
done
echo
# Expect: a mix of 200s and 429s (after the burst is exhausted at the default 30)

# 5.9 Auth gate (opt-in) — set the env, restart, confirm 401
kill $SERVE_PID
sleep 1
export CRUMDBOB_API_KEY="walkthrough-test-key"
crumdbob serve --host 127.0.0.1 --port 8765 &
SERVE_PID=$!
sleep 2

curl -s -o /dev/null -w "no-key: %{http_code}\n"  http://127.0.0.1:8765/api/stats
curl -s -o /dev/null -w "wrong:  %{http_code}\n"  http://127.0.0.1:8765/api/stats -H "X-API-Key: wrong"
curl -s -o /dev/null -w "right:  %{http_code}\n"  http://127.0.0.1:8765/api/stats -H "X-API-Key: walkthrough-test-key"
# Expect: 401, 401, 200

# 5.10 Confirm the audit log captured the failures
unset CRUMDBOB_API_KEY
kill $SERVE_PID
python3 -c "
from crumdbob.audit import AuditLogger
log = AuditLogger('/tmp/cb-walkthrough/memory.db')
for e in log.recent(20):
    print(e.ts, e.event, e.actor, e.payload)
"
# Expect: at least 2 auth.failure entries from the failed curl calls
```

**Report:** For each numbered step above (5.1–5.10), say "OK" or
describe what was unexpected. **Specifically confirm:**

- Health response has `version` but NOT `database` (info-leak fix).
- All 4 security headers present.
- X-Request-ID is echoed verbatim.
- Metrics body contains `# HELP` and `# TYPE`.
- /api/sessions/99999 returns 404 with no SQL fragment.
- At least one 429 appears in the rate-limit burst test.
- Auth gate returns 401/401/200.
- Audit log has the failure entries.

---

## Section 6 — XSS hardening proof

This proves the dashboard cannot execute injected scripts. Read
`web/static/app.js` and verify:

```bash
cd /Users/slavaz/Crumb-Bob

# 6.1 Count innerHTML assignments — expect ZERO outside the comment line
grep -n "innerHTML" web/static/app.js
# Expected: exactly ONE match — line ~70-something containing a comment.
# Anything else is an XSS regression.

# 6.2 Confirm el() helper is used
grep -c "replaceChildrenWith\|el(" web/static/app.js
# Expected: > 50 — the helpers are now the rendering primitive.
```

**Report:** Number of innerHTML occurrences (must be 1, the comment).
Number of `el()` usages.

---

## Section 7 — Docker build verification (optional but recommended)

If Docker is available on the audit machine:

```bash
cd /Users/slavaz/Crumb-Bob

# 7.1 Build the image
docker build -t crumdbob:walkthrough . 2>&1 | tail -20

# 7.2 Confirm image size (should be ~110 MB)
docker images crumdbob:walkthrough --format "{{.Size}}"

# 7.3 Confirm non-root user
docker run --rm crumdbob:walkthrough id
# Expect: uid=10001(crumdbob)

# 7.4 Health check
docker run -d --name cb-walkthrough -p 18765:8000 crumdbob:walkthrough
sleep 5
docker inspect cb-walkthrough --format '{{.State.Health.Status}}'
# Expect: "healthy" (may show "starting" first — wait 30s and re-check)

# 7.5 Clean up
docker stop cb-walkthrough && docker rm cb-walkthrough
```

**Report:** Image size, user ID, health status. Skip cleanly if Docker
isn't available.

---

## Section 8 — Architecture review

Read `ARCHITECTURE.md` end-to-end. Then verify these claims against
the code:

| Claim in ARCHITECTURE.md                                                     | How to verify                                                                                                       |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| "Middleware order: RequestID → SecurityHeaders → RateLimit → Metrics → CORS" | Read `web/api/server.py` around the middleware registrations                                                        |
| "WAL mode + foreign_keys=ON on every connection"                             | Read `crumdbob/memory.py` `__init__`, look for the PRAGMA calls                                                     |
| "\_server_error() sanitizes 500s"                                            | Read `web/api/server.py`, count uses of `_server_error()`; should be 12                                             |
| "Audit log table is indexed on ts, event, actor"                             | Read `crumdbob/migrations.py` `_add_audit_log`, count `CREATE INDEX` lines (3)                                      |
| "ContextVar-based request_id propagates across async"                        | Read `crumdbob/logging_config.py`, find `request_id_ctx = contextvars.ContextVar(...)`                              |
| "Rate limiter uses token-bucket per IP"                                      | Read `web/api/middleware.py` `_Bucket` + `_take_token`                                                              |
| "el() builds DOM nodes, never parses HTML strings"                           | Read `web/static/app.js`, find `el(tag, attrs, ...children)` and confirm it uses `createElement` + `createTextNode` |

**Report:** Any claim that doesn't match the code (most damning kind
of bug — documentation drift).

---

## Section 9 — Adversarial probes

Try to break things that should not break:

```bash
source /tmp/crumdbob-verify-venv/bin/activate
cd /Users/slavaz/Crumb-Bob

# 9.1 Try to read /etc/passwd via a crafted proof chain (path traversal)
mkdir -p /tmp/cb-evil/generated
cat > /tmp/cb-evil/generated/08_proof_chain.json <<'JSON'
{
  "crumdbob_version": "0.3.1",
  "source_report": {"path": "/etc/passwd", "sha256": "0"},
  "generated_files": []
}
JSON
crumdbob record /tmp/cb-evil/generated --db /tmp/cb-walkthrough/memory.db 2>&1 | tail -5
# Expect: FileNotFoundError saying it can't find bob-report.md. The crafted
# path must NOT be opened. If you see /etc/passwd content in the output,
# the path-traversal guard regressed.

# 9.2 Try destructive SQL via query_sql
crumdbob query sql --db /tmp/cb-walkthrough/memory.db "DROP TABLE sessions" 2>&1 | tail -3
# Expect: "'drop' is not permitted (read-only mode)"

# 9.3 Sanitized error: try a query that triggers a server-side exception
#     (the response must not contain SQL fragments or stack frames)
crumdbob query sql --db /tmp/cb-walkthrough/memory.db "SELECT * FROM nonexistent_table" 2>&1 | tail -3

# 9.4 Schema downgrade: pretend the DB is at a newer schema version
python3 -c "
import sqlite3
c = sqlite3.connect('/tmp/cb-evil-down.db')
c.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
c.execute(\"INSERT INTO metadata VALUES ('schema_version', '99')\")
c.commit()
from crumdbob.memory import MemoryDatabase
try:
    db = MemoryDatabase('/tmp/cb-evil-down.db')
    db.init_database()
    print('REGRESSION: opened a v99 DB without error')
except RuntimeError as e:
    print('OK:', e)
"
# Expect: OK: <error message saying schema is newer than this code>
```

**Report:** All three probes must be rejected. Any "success" output
means a real security regression.

---

## Section 10 — Migration safety check

Verify the migration framework handles upgrade from older databases.

```bash
source /tmp/crumdbob-verify-venv/bin/activate
cd /Users/slavaz/Crumb-Bob

# 10.1 Create a pre-v0.3.1 database by copying the example and stripping audit_log
python3 -c "
import sqlite3, shutil
shutil.copy('/tmp/cb-walkthrough/memory.db', '/tmp/cb-old.db')
c = sqlite3.connect('/tmp/cb-old.db')
c.execute('DROP TABLE IF EXISTS audit_log')
c.execute(\"UPDATE metadata SET value='1' WHERE key='schema_version'\")
c.commit()
print('Forced /tmp/cb-old.db back to schema_version=1, removed audit_log')
"

# 10.2 Open it with current code and confirm the migration runs
python3 -c "
from crumdbob.memory import MemoryDatabase
db = MemoryDatabase('/tmp/cb-old.db')
db.init_database()
ver = db.conn.execute(\"SELECT value FROM metadata WHERE key='schema_version'\").fetchone()
tables = [r[0] for r in db.conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")]
print('schema_version after open:', ver)
print('audit_log present:', 'audit_log' in tables)
db.close()
"
# Expect: schema_version=('2',), audit_log present.
```

**Report:** Confirm the legacy DB was upgraded cleanly.

---

## Section 11 — Final report format

Produce a single markdown report with this structure:

```markdown
# CrumdBob v0.3.1 — IBM Bob audit, <date>

## Verdict

[GREEN | YELLOW | RED]

GREEN = ship; YELLOW = ship with documented caveats; RED = block release.

## Section-by-section summary

### S1 Environment : PASS / FAIL — <one line>

### S2 Tests : <count passed/failed/skipped>, coverage <%>

### S3 Static analysis: ruff=<n>, bandit=<n low / n med / n high>, pip-audit=<n>

### S4 CLI E2E : <PASS / details>

### S5 Web/API : <list of any 5.x step that failed>

### S6 XSS : innerHTML count=<n> (must be 1), el()=<n>

### S7 Docker : <SKIPPED if no Docker, else size/uid/health>

### S8 Architecture : <list any doc-drift findings>

### S9 Adversarial : <3/3 rejected | list any that succeeded>

### S10 Migration : <PASS / FAIL>

## Findings

List anything that surprised you, in priority order (P0 → P3).

## Recommendations

What should the maintainer do before tagging v0.3.1 final?
```

---

## Hard rules

- **Do not modify production code** unless you find a clear one-line
  bug. Open issues for anything larger.
- **Do not delete the audit database** at `/tmp/cb-walkthrough/memory.db`
  until the end; some later sections depend on it.
- **Treat documentation drift as a P1 finding** — the C4 diagrams,
  CHANGELOG, and SECURITY.md must match the code.
- **If you see "207 passed"** anywhere in old reports, ignore it.
  Current expected count is 290 passed / 0 skipped (the watchdog
  tests un-skipped when the `[dev]` extras are installed).
- **Trust but verify the version number.** The version pin moves
  from `0.3.0` → `0.3.1` in this pass. If you find `0.3.0` anywhere
  except in the CHANGELOG history, flag it.
- **Be skeptical of "all green" results.** Spot-check at least one
  passing test by reading its source and confirming the assertions
  actually verify what they claim to.

Start with Section 1 and proceed sequentially. End with the formatted
audit report.

— end of prompt —
