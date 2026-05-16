# Contributing to CrumbBob

Thanks for considering a contribution! This guide covers the
mechanics; if anything is unclear, open a Discussion before opening
a PR.

## Quick start

```bash
# 1. Fork + clone
git clone git@github.com:<your-user>/Crumb-Bob.git
cd Crumb-Bob

# 2. Install with dev extras (uses an isolated venv to keep your system clean)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Wire up pre-commit hooks so you can't ship lint or type errors
pre-commit install --install-hooks

# 4. Verify the dev environment works
pytest -q
ruff check .
mypy
```

If `pytest -q` reports anything other than `207 passed` (or higher),
something in your environment is off — open an issue rather than
spending hours debugging.

## Development workflow

### Branching

- Base branches off `main`.
- Name them `feat/<short-description>`, `fix/<short-description>`,
  or `docs/<short-description>`.
- One topic per branch — small focused PRs are reviewed and merged
  faster than mega-PRs.

### Commits

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(api): add /api/v1/predictions endpoint
fix(parser): handle empty bob-report.md without crashing
docs(security): document hardening for team deployments
refactor(memory): extract migration runner into separate module
test(retry): cover jitter behavior under deterministic seed
chore(deps): bump uvicorn from 0.27 to 0.28
```

Why: this lets us auto-generate the CHANGELOG entry and decide
semver bumps mechanically.

### Code style

Enforced by pre-commit. Locally:

```bash
ruff format .   # apply formatting
ruff check . --fix   # auto-fix lint issues
mypy           # type-check
bandit -c pyproject.toml -r crumdbob web   # security scan
```

Rules of thumb:

- **Lines ≤ 100 characters.** Wrap long signatures across multiple
  lines. Wrap long f-strings into parenthesised string concatenation.
- **Type hint every public function.** Use `from __future__ import
annotations` so you can use `X | None` syntax on Python 3.10.
- **Docstrings on every public function and class.** Google or
  NumPy style, your call — match the surrounding file.
- **No bare `except Exception`** in library code unless you're
  catching at a daemon-loop boundary and have a comment explaining
  why. CI's ruff config will flag bare excepts.
- **`raise X from exc`** when re-raising with context. Don't lose
  the cause chain.
- **No `print()` in library modules.** Use `logging`. CLI entry
  points and the Rich UI module are exempt (see `[tool.ruff.lint.per-file-ignores]`).

### Testing

- Add a test for every behaviour change. Bug fixes get a regression
  test that fails before your fix and passes after.
- Tests live in `tests/` and follow the `test_<module>.py` naming
  pattern. Use fixtures (`tmp_path`, `populated_db`) — see
  `tests/conftest.py`.
- We have three markers — apply them where appropriate:
  - `@pytest.mark.unit` — pure functions, no I/O.
  - `@pytest.mark.integration` — file system, subprocess, or network.
  - `@pytest.mark.slow` — > 1 second. Excluded from `pytest -m "not slow"`.
- Coverage floor is enforced at 60% globally (`fail_under=60` in
  `pyproject.toml`). New modules should land closer to 90%.

### Database changes

CrumbBob uses a forward-only migration framework
(`crumdbob/migrations.py`):

1. Bump `SCHEMA_VERSION` to the next integer.
2. Append a function decorated with `@migration(N)` to `migrations.py`.
3. Write the DDL/DML using `IF NOT EXISTS` clauses where possible
   so the migration is idempotent.
4. Add a test that creates a v(N-1) database, runs `run_migrations()`,
   and verifies the new objects exist.

Never edit an already-shipped migration; add a new one to fix it.

## Pull request process

1. Make sure CI is green (`ruff`, `mypy`, `bandit`, `pip-audit`,
   tests across the full Python matrix).
2. Update `CHANGELOG.md` under the `[Unreleased]` section.
3. If you're touching public API or behaviour, update `README.md`
   and any relevant `docs/*.md` file.
4. Open the PR with a description that answers:
   - **What** does it change?
   - **Why** is the change needed?
   - **How** was it tested?
5. Mark draft PRs with the `WIP` label so reviewers don't pile in
   on incomplete work.

## Release process (maintainers)

1. Decide the semver bump:
   - `MAJOR` for breaking changes (rare; pre-1.0 only for severe
     compatibility breaks).
   - `MINOR` for new features (most common).
   - `PATCH` for bug fixes and internal refactors with no API change.
2. Move `[Unreleased]` entries in `CHANGELOG.md` under a new
   `[X.Y.Z] - YYYY-MM-DD` heading.
3. Bump `version` in `pyproject.toml`.
4. Commit: `chore(release): v0.X.Y`.
5. Tag: `git tag v0.X.Y && git push --tags`.
6. CI builds the wheel and uploads to GitHub Releases.
7. PyPI publish is **manual** for now (no trusted publishing yet):
   ```bash
   python -m build
   twine upload dist/*
   ```
8. Announce in the repo Discussions and on any relevant chat
   channels.

## Reviewing

If you're reviewing a PR:

- **Test the worst case first.** Empty inputs, huge inputs, malformed
  inputs, concurrent access. Most bugs hide in these edges.
- **Read the diff bottom-up.** New code at the bottom tells you the
  shape of the contribution; context at the top is rarely the most
  important review surface.
- **Ask "what happens if...".** Don't just confirm the happy path —
  walk through failure modes.
- **Approve fast, ship slow.** If the change is correct and tested,
  approve. Don't gate on style nits that the formatter will fix.

## Code of conduct

We follow the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Be kind, assume good intent, and remember that the person on the
other end of the PR is trying to make CrumbBob better.

Report violations to **conduct@xioaisolutions.com**.

## Licence

By contributing, you agree that your contributions are licensed
under the MIT licence (same as the rest of the project).
