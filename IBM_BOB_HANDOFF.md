# IBM Bob Handoff: CrumbBob v0.3.1 Release Hardening

**Date:** 2026-05-15
**Repo:** `/Users/slavaz/Crumb-Bob`
**Branch:** `main`
**State:** enterprise hardening pass tuned, verified, and ready for final review/push.

## Current Status

CrumbBob v0.3.1 is in release-candidate shape.

Fixed/tuned in the final Codex pass:

- Removed a real CLI blocker: dead `cmd_llm` code referenced undefined `error_count`.
- Completed `crumdbob config list` return handling and implemented `config reset`.
- Brought Mypy to green across `crumdbob` and `web`.
- Brought Ruff to green by fixing real findings and scoping intentional CLI lazy imports/return shape.
- Hardened retry jitter so Bandit no longer flags non-crypto randomness.
- Tightened typed handling for proof-chain count diffs, LLM responses, watcher paths, API query params, and prediction sorting.
- Reconciled version drift: `pyproject.toml`, `crumdbob.__version__`, and checked-in proof chain now report `0.3.1`.
- Regenerated the checked-in example pack so proof-chain metadata and generated CRUMB output are current.

## Verification Evidence

Commands run from `/Users/slavaz/Crumb-Bob`:

```bash
pytest -q --tb=short
# 278 passed, 12 skipped

python3 -m compileall -q crumdbob web tests
# passed

/tmp/crumdbob-audit-venv/bin/python -m mypy crumdbob web
# Success: no issues found in 26 source files

/tmp/crumdbob-audit-venv/bin/python -m ruff check .
# All checks passed

git diff --check
# clean

/tmp/crumdbob-audit-venv/bin/python -m bandit -r crumdbob web -f txt
# No issues identified

/tmp/crumdbob-audit-venv/bin/python -m pip_audit
# No known vulnerabilities found
```

Additional smoke checks:

- `python3 -m crumdbob.cli --help` renders all commands.
- `python3 -m crumdbob.cli config list` returns defaults cleanly.
- `python3 -m crumdbob.cli pack examples/compliance-ai --out examples/compliance-ai/generated` regenerates 9 files.
- `examples/compliance-ai/generated/08_proof_chain.json` reports `"crumdbob_version": "0.3.1"`.

## Remaining Non-Blocking Work

- `pip-audit` skips the local `crumdbob` package because it is not on PyPI; third-party dependencies report clean.
- Watcher tests are skipped in the base environment when `watchdog` is not installed.
- The web API remains local-demo oriented unless auth is enabled/configured.
- Large CLI/web functions remain, but current complexity is intentional for command dispatch and API routing.

## Suggested Final Bob Check

Ask IBM Bob to do a final blocker-only pass:

```text
Review CrumbBob v0.3.1 final diff only for release blockers. Do not propose broad refactors.

Known green checks:
- pytest -q --tb=short: 278 passed, 12 skipped
- compileall: passed
- mypy crumdbob web: clean
- ruff check .: clean
- git diff --check: clean
- bandit -r crumdbob web: no issues
- pip-audit: no known vulnerable third-party dependencies

Focus on:
- Version consistency for 0.3.1
- CLI config/LLM command behavior
- New audit/logging/migrations/pagination/retry/middleware/metrics files
- Docker/CI/pre-commit packaging sanity
- Whether all untracked files should be included in the release commit

Output only:
1. BLOCKERS
2. SAFE TO PUSH? YES/NO
3. MINIMAL PATCHES REQUIRED
4. POST-RELEASE FOLLOW-UP
```

## Do Not Redo

- Do not rework the proof-chain schema.
- Do not change CRUMB v1.4 grammar.
- Do not convert optional `web`/`llm`/`watch` dependencies into required dependencies.
- Do not add new feature scope before pushing v0.3.1.
