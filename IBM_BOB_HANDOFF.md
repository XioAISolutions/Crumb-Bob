# IBM Bob Handoff: CrumbBob v0.3.0 Release Hardening

**Date:** 2026-05-15
**Repo:** `/Users/slavaz/Crumb-Bob`
**Branch:** `main`
**State:** release-blocker fixes applied; working tree is intentionally dirty for review/commit.

## Current Status

CrumbBob v0.3.0 is now in release-candidate shape.

Fixed since the final audit:

- FastAPI/TestClient SQLite failures: `MemoryDatabase` now opens SQLite with `check_same_thread=False`.
- Dashboard first-load crash: loading state now uses a non-destructive overlay instead of replacing the view DOM.
- Version drift: package metadata, `crumdbob.__version__`, API metadata, dashboard label, and proof chains now report `0.3.0`.
- Packaging: `web` is now a package, `web/api/server.py` and `web/static/*` are included in the wheel, and `ui`/`web`/`watch`/`llm`/`all`/`dev` extras are real.
- Query UX: `crumdbob query natural "show me all sessions"` now returns recorded sessions.
- Rich UI real-data bug: session file display now works with actual `FileRecord.path` records.
- Security scan cleanup: Bandit now reports no issues; controlled dynamic SQL and git subprocess calls are explicitly documented/suppressed.
- Dependency scan: `pip-audit` reports no known vulnerable dependencies.
- `.gitignore` now covers env files, coverage output, local DBs, caches, and `.DS_Store`.

## Verification Evidence

Commands run from `/Users/slavaz/Crumb-Bob`:

```bash
pytest -q --tb=short
# 195 passed, 12 skipped

/tmp/crumdbob-audit-venv/bin/python -m bandit -r crumdbob web -f txt
# No issues identified

/tmp/crumdbob-audit-venv/bin/python -m pip_audit
# No known vulnerabilities found

/tmp/crumdbob-audit-venv/bin/python -m pylint crumdbob/ui.py crumdbob/llm.py web/api/server.py
# 9.48/10
```

Additional checks already completed:

- Browser smoke test against `crumdbob serve`: dashboard renders v0.3.0 stats with no console errors.
- Wheel check: `crumdbob-0.3.0-py3-none-any.whl` includes `web/__init__.py`, `web/api/server.py`, and all `web/static/*` assets.
- Minimal editable install without extras works; `crumdbob serve` fails gracefully with the `[web]` install hint.
- Pack workflow: `pack -> validate -> record -> query -> doctor` passes, and proof chain emits `"crumdbob_version": "0.3.0"`.

## Remaining Non-Blocking Work

Pylint still reports style/architecture findings:

- Long lines in `crumdbob/ui.py` and `crumdbob/llm.py`.
- Large functions in `crumdbob/ui.py` and `web/api/server.py`.
- `HTTPException(..., detail=str(e))` should eventually use `raise ... from e` or sanitized error helpers.
- FastAPI LLM imports are intentionally local so core/web install paths do not require LLM SDKs.

Security debt that is not blocking local/hackathon release:

- Frontend still renders API data through `innerHTML`; before public hosting, replace with DOM/text rendering or a sanitizer.
- Web API is local-development oriented and unauthenticated. Keep `--host 127.0.0.1` for demos unless the network is trusted.

## Suggested Next Steps

1. Review the diff.
2. Regenerate the committed example pack if you want checked-in examples to carry v0.3.0 proof-chain metadata:
   ```bash
   crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
   crumdbob doctor examples/compliance-ai/generated
   ```
3. Commit the release-hardening changes.
4. Optional post-release cleanup: split `web/api/server.py`, split large Rich UI display functions, and remove frontend `innerHTML`.

## Do Not Redo

- Do not rework the proof-chain schema.
- Do not change CRUMB v1.4 grammar.
- Do not add new feature scope before the v0.3.0 release.
- Do not convert optional `web`/`llm` dependencies into required dependencies.

