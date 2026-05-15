# IBM Bob Handoff: Crumb-Bob Repo, Post-Audit

**Date:** 2026-05-15
**Repo:** `/Users/slavaz/Crumb-Bob` (XioAISolutions/Crumb-Bob, branch `main`, working tree dirty)
**State:** 24 fixes applied across 9 source files; 101 tests passing, 12 skipped (watchdog optional dep). Working tree NOT committed yet — you decide which fixes to land first.

---

## What this is

Crumb-Bob is a Python 3.10+ CLI (`crumdbob`) that:

1. Parses IBM Bob markdown reports into structured signals (files, commands, risks, next steps).
2. Generates 9-file CRUMB v1.4 memory packs (`00_repo_genome.crumb` ... `08_proof_chain.json`).
3. Stores session history in SQLite at `~/.crumdbob/memory.db` for cross-session pattern detection and prediction.
4. Validates pack integrity via a `doctor` command that recomputes proof-chain hashes.

The codebase has ~6,300 LOC of Python across `crumdbob/`, with 101 passing tests and a static-site demo in `web/`. Bob shipped this initial implementation; this handoff lists what Bob missed and what's left to harden it for production.

---

## What I already fixed (DO NOT redo)

The following 24 issues are **already fixed in the working tree**. Treat this as completed scope:

### High-severity correctness bugs (8)

1. **[cli.py:615]** `cmd_migrate_to_db()` was truncated — only printed `Success: N`, never reported error count, never set exit code. Fixed: prints both, returns `1` if any errors.
2. **[memory.py:888]** `record_pack_to_db` opened and parsed `08_proof_chain.json` twice. Fixed: single read, reuse parsed dict.
3. **[memory.py:109]** `MemoryDatabase.close()` discarded uncommitted writes silently. Fixed: `__exit__` rolls back on exception, commits on clean exit.
4. **[validator.py:89]** Validator silently merged duplicate `[section]` blocks. Fixed: emits `duplicate section: [name]` error.
5. **[insights.py:275]** `ZeroDivisionError` in trend calc when `older_avg == 0`. Fixed: explicit guard `older_avg > 0 and ...` before any division.
6. **[query.py:161]** `query_natural()` crashed with `TypeError` when a lambda took `match` but the optional capture group didn't match. Fixed: every handler now has uniform `(match)` signature; unused arg named `_m`.
7. **[query.py:104]** Risk queries didn't match `"Show me all risks"` because the regex required `(show|find|get|list)` immediately followed by `(all|risks)`. Fixed: added optional filler tokens (`me`, `the`).
8. **[memory.py:891]** Path traversal: malicious `proof_chain.json` could set `source_report.path` to `/etc/passwd`. Fixed: candidates resolved + `_is_within()` guard against pack/cwd ancestor tree.

### Performance & resource issues (6)

9. **[memory.py:107]** SQLite opened without `WAL` / `foreign_keys` / `synchronous=NORMAL`. Fixed: pragmas set in `__init__`.
10. **[memory.py:283]** Missing indexes for `patterns.detect_recurring_risks` (filters on `risks.description`) and `detect_task_patterns` (filters on `tasks.status, tasks.description`). Fixed: added `idx_risks_description`, `idx_tasks_status_description`, `idx_commands_command`.
11. **[predict.py:104]** N+1 query in `predict_risks()` — fired one `LIKE` query per keyword. Fixed: single query with OR'd LIKE clauses, dedup via dict insertion order.
12. **[predict.py:170]** Same N+1 pattern in `predict_complexity()`. Fixed: single OR'd query, set-based dedup.
13. **[predict.py:275]** N+1 in `recommend_tests()` — one query per file_path. Fixed: single `WHERE f1.path IN (?, ?, ...)` query.
14. **[patterns.py:117]** O(n²) co-change computation duplicated verbatim in `detect_file_relationships` and `get_file_relationships`. Fixed: extracted shared `_compute_co_changes()` helper.

### Data-quality / API issues (8)

15. **[parser.py:12]** `RISK_WORDS` matched as substrings — "contestant" matched "test", "attestation" matched "test". Fixed: precompiled `\b...\b` regexes `_RISK_RE`, `_TEST_RE`, `_NEXT_RE`.
16. **[insights.py:449]** `_store_insight` had no dedup; running `insights generate` 10× inserted 10 copies of each insight. Fixed: pre-insert SELECT with type+title match.
17. **[insights.py:454]** My initial dedup used unescaped LIKE pattern — backslash/percent/underscore in titles caused false matches. Fixed: explicit escape with `ESCAPE '\\'`.
18. **[predict.py:386]** `_extract_keywords` returned only original tokens — `"authentication"` didn't match historical risks containing `"auth"`. Fixed: appends stem variants by stripping common suffixes (`tion`, `ment`, `ing`, etc.).
19. **[parser.py:97]** `enrich_report_with_artifact` mutated in-place AND returned the report — confusing contract. Fixed: return type now `None`, mutation contract explicit.
20. **[query.py:205]** `query_sql` accepted arbitrary SQL — a power user (or untrusted caller) could `DROP TABLE sessions`. Fixed: keyword denylist (`drop`, `delete`, `update`, `insert`, `create`, `alter`, `truncate`, `replace`, `pragma`, `vacuum`, `attach`, `detach`), multi-statement detection, narrowed exception to `sqlite3.Error`.

### Code hygiene (5)

21. **[memory.py:826]** `hashlib` imported inline in method. Fixed: moved to module imports.
22. **[insights.py:9]** `import json` appeared inline in two methods. Fixed: top-level import.
23. **[watcher.py:210]** Dead `watch_with_status()` stub that just delegated to `watch_directory`. Fixed: removed.
24. **[collector.py:23]** Hardcoded 10s subprocess timeout in `_run_git_command`. Fixed: module-level `GIT_TIMEOUT_SECONDS = 30` constant with `timeout` parameter on the helper.
25. **[memory.py:120]** Schema-version check added — refuses to open a database with a newer schema than this CrumbBob supports.

**Smoke-test evidence:**

- `crumdbob init-db --path /tmp/x.db` → schema initialized, WAL mode active.
- `crumdbob record examples/compliance-ai/generated --db /tmp/x.db` → session 1 recorded (12 files, 7 risks, 7 tasks).
- `crumdbob query sql --db /tmp/x.db "DROP TABLE sessions"` → rejected: `'drop' is not permitted (read-only mode)`.
- `crumdbob query sql --db /tmp/x.db "SELECT COUNT(*) FROM sessions"` → returns 0 row(s).
- `pytest -q` → 101 passed, 12 skipped.

---

## What's still open — pick from this list

These are **real, recurring issues** identified by parallel security/perf/API/test audits. They were too large for a single editing pass; each is a focused chunk Bob can take.

### Priority 1 — Production safety

**P1.1 Narrow exception handling (26 sites)**

- `cli.py` has 19 instances of `except Exception as exc:` — most should be `OSError`, `json.JSONDecodeError`, `sqlite3.Error`, or `FileNotFoundError`.
- `differ.py:105, 218, 224` — distinguish JSON parse failures from file I/O errors so the UI can show actionable error messages.
- `watcher.py:123, 177` — distinguish watchdog event errors from regeneration errors.
- **Acceptance:** zero bare `except Exception` outside `_get_git_context` (where it's intentional for graceful Git-unavailable fallback).

**P1.2 Logging migration (50+ `print()` sites)**

- `watcher.py` has 22 `print()` calls — this is a background service; switch to `logging.getLogger("crumdbob.watcher")` with INFO/WARNING levels.
- `collector.py` has 7 print() calls mixing UI prompts with diagnostic output. Keep `input()` prompts as `print()`, move diagnostics to `logging.info()`.
- `cli.py` `print()` calls that go to stdout for user display are correct — only convert the ones that are diagnostic (line 588, 611, 691, 794, etc.).
- **Acceptance:** `logging.basicConfig(level=INFO)` at CLI entry; library modules use `logger = logging.getLogger(__name__)`.

**P1.3 CLI test coverage (22 untested `cmd_*` functions)**

- Tested today: only `cmd_pack` and `cmd_doctor` (via `test_pack_generation.py`).
- Untested: `cmd_import`, `cmd_inspect`, `cmd_replay`, `cmd_pr`, `cmd_validate`, `cmd_graph`, `cmd_init_bob_skill`, `cmd_auto_collect`, `cmd_watch`, `cmd_diff`, `cmd_init_db`, `cmd_record`, `cmd_list_sessions`, `cmd_show_session`, `cmd_trends`, `cmd_migrate_to_db`, `cmd_query`, `cmd_insights`, `cmd_predict`, `cmd_patterns`, `cmd_dashboard`, `cmd_config`.
- **Approach:** add `tests/test_cli.py` using `pytest`'s `capsys` and a `tmp_path` fixture. Test exit codes, stdout content, and one error case per command.
- **Acceptance:** 90%+ of `cmd_*` functions covered by at least one happy-path test.

**P1.4 `config.py` has zero tests**

- 102 LOC of config loading, type coercion, defaults handling — entirely untested.
- Add `tests/test_config.py` covering: load missing file (returns defaults), load malformed JSON (raises or returns defaults — document which), `set_config_value` type coercion, `get_database_path` expansion.

### Priority 2 — Architecture

**P2.1 Decompose `build_parser()` (207 lines)**

- `cli.py:1092-1299` is a wall of `add_parser()` calls. Extract one function per subcommand group: `_register_pack_subcommands(sub)`, `_register_db_subcommands(sub)`, `_register_query_subcommands(sub)`.
- Adds testability and lets you share `--db` argument definition (currently duplicated 17 times verbatim).

**P2.2 Web demo divergence (web/demo.js vs Python CLI)**

- `web/demo.js` generates only **4 of 9** pack files (genome, recorder, risks, replay) — missing `02_next_task`, `03_test_plan`, `05_agent_passport`, `07_pr_summary`, `08_proof_chain`.
- Regex patterns in JS differ from `parser.py` (e.g., JS only matches `pnpm|npm|python|pytest|git|node` for commands).
- **Options:**
  - (a) Bring JS up to parity with Python (faithful demo).
  - (b) Document the JS demo as "structural preview only" in README and rename it (`/preview/` instead of `/web/`).
  - (c) Compile Python to WebAssembly via Pyodide and serve the real `crumdbob` (best fidelity, more complex deploy).
- **Recommendation:** option (b) for the hackathon submission, option (a) post-submission.

**P2.3 Stale example pack**

- `examples/compliance-ai/generated/00_repo_genome.crumb` was generated **before** the parser/validator fixes in this audit. Regenerate and commit so judges see current behavior:
  ```bash
  crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
  crumdbob doctor examples/compliance-ai/generated
  ```

**P2.4 Helper duplication in `cli.py` argument registration**

- The string `"Database path (default: ~/.crumdbob/memory.db)"` appears 13 times.
- `"Run 'crumdbob init-db' to create the database."` appears 4 times.
- `--db DB` argument registration appears 17 times with identical help text.
- Extract `_add_db_argument(parser)` and `DB_HELP = "..."` module constants.

### Priority 3 — Performance polish

**P3.1 `_compute_co_changes` loads all files into memory**

- `patterns.py:117` builds a dict of `session_id → set[str]` for every session, then computes pairs. At 10K files this is 50M+ tuples.
- **Fix:** add `LIMIT 1000` to the SELECT, document a max-sessions parameter, or stream session-by-session.

**P3.2 Subprocess timeout in `_get_git_context` is 5s × 3 commands**

- `memory.py:947, 958, 969` — three sequential `git` calls, each with 5s timeout. On a hung git the user waits 15s before pack record completes.
- **Fix:** run them in a single `git for-each-ref` or one shell-wrapped command; failing that, parallelize.

**P3.3 Hardcoded thresholds in pattern detection**

- `patterns.py` uses `min_occurrences=2`, `min_co_changes=2`, `min_sessions=2` as defaults. These produce noise at low session counts. Surface as `--min-occurrences` CLI flags.

### Priority 4 — Documentation & packaging

**P4.1 `pyproject.toml`**

- Add `[project.optional-dependencies]dev = ["pytest>=7.0", "mypy>=1.0"]` so `pip install -e .[dev]` works.
- Add Python 3.12 classifier (codebase uses modern syntax that supports 3.12).

**P4.2 `CHANGELOG.md`**

- No release history. Start one now with v0.2.0 / v0.3.0 cutover (this audit's fixes warrant a minor version bump).

**P4.3 `config.py` is not documented**

- `docs/` has 10+ files but nothing about config management. Add `docs/configuration.md`.

**P4.4 README.md `pip install` instructions**

- README says "use a virtualenv on Homebrew-managed Python" — too vague. Give the exact commands: `python3 -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`.

---

## Suggested execution order for Bob

If you only have one session:

1. P2.3 (regen examples) — 2 min, no code.
2. P1.4 (config.py tests) — 30 min, no refactoring risk.
3. P4.1 (pyproject.toml deps) — 5 min.

If you have a full afternoon: 4. P1.1 (narrow exceptions) — 1-2 hours, can be done file-by-file. 5. P1.3 (CLI test coverage) — 2-3 hours.

If you have a multi-day arc: 6. P1.2 (logging migration) — 1 day, touches many files but mechanical. 7. P2.1 (decompose `build_parser`) — 0.5 day. 8. P2.2 (web demo strategy) — depends on choice.

---

## How to verify your work

```bash
# Create a clean test environment (PEP 668 blocks system Python on this Mac)
python3 -m venv /tmp/crumdbob-verify-venv
source /tmp/crumdbob-verify-venv/bin/activate
pip install -e /Users/slavaz/Crumb-Bob

# Run the full test suite (should be 101 passed, 12 skipped today)
cd /Users/slavaz/Crumb-Bob
python3 -m pytest tests/ -q

# Run the example flow end-to-end
crumdbob pack examples/compliance-ai --out /tmp/test-pack
crumdbob doctor /tmp/test-pack
crumdbob validate /tmp/test-pack

# Exercise the memory database
crumdbob init-db --path /tmp/test.db
crumdbob record /tmp/test-pack --db /tmp/test.db
crumdbob list-sessions --db /tmp/test.db
crumdbob query sql --db /tmp/test.db "SELECT COUNT(*) FROM sessions"
```

---

## Files to read first (in this order)

1. `crumdbob/cli.py` — 1,313 LOC, the entry point for everything.
2. `crumdbob/memory.py` — schema, persistence, the hottest module.
3. `crumdbob/parser.py` — 149 LOC, the IBM-Bob → signals translator.
4. `crumdbob/packer.py` — 558 LOC, generates the 9-file pack.
5. `crumdbob/validator.py` — 221 LOC, CRUMB format validation.
6. `crumdbob/{insights,patterns,predict,query}.py` — the AI/intel layer; collectively ~1,800 LOC. Most complex but most independently testable.

---

## Out of scope / explicitly NOT for Bob

- **Don't touch the proof-chain format.** Existing packs must validate after Bob's pass.
- **Don't change CRUMB v1.4 grammar.** Validator behavior must remain backward-compatible.
- **Don't introduce new runtime dependencies** beyond what's already in `pyproject.toml`. `watchdog` stays optional.
- **Don't add new CLI subcommands.** This is a stabilization pass, not feature work.

---

## Bonus context (memory you have)

- The local IBM Bob CLI is at `/opt/homebrew/bin/bob` v1.0.3.
- Sample report lives at `examples/compliance-ai/bob-report.md`.
- Working test venv: `/tmp/crumdbob-verify-venv` (already has crumdbob installed editable).
- Hackathon framing: this repo is the demo for "flight-recorder for IBM Bob sessions". The example pack in `examples/compliance-ai/generated/` is what judges will replay.

**Ship it. Don't perfect it.**
