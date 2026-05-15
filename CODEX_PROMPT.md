# Codex Prompt — Blow Out CrumbBob

You are Codex working inside `XioAISolutions/Crumb-Bob`.

## Mission

Turn CrumbBob from a simple Bob-report-to-pack generator into a hackathon-grade IBM Bob companion product.

CrumbBob is the flight recorder for IBM Bob development sessions. IBM Bob understands a repo during a session. CrumbBob preserves that understanding as replayable software memory.

## Product thesis

Bob gives software a temporary brain. CrumbBob gives that brain memory.

The product converts:

```text
IBM Bob report + repo metadata + test output + git diff
```

into:

```text
Repo Genome + Session Flight Recorder + Next Task + Test Plan + Risk Register + Agent Passport + Replay Prompt + PR Summary + Proof Chain
```

## Repos to borrow from conceptually

Read `docs/source-adoption-map.md` first.

Borrow ideas from:

1. `XioAISolutions/crumb-format`
   - CRUMB v1.4 grammar
   - refs, folds, handoff dependencies, workflow, checks, guardrails, capabilities, script
   - kind=map/task/todo/agent/audit
   - validate/lint/doctor style CLI commands
   - native Claude/Cursor/MCP integration language

2. `XioAISolutions/compliance-AI`
   - proof-chain framing
   - source-locker/evidence metadata
   - hash-bound signoff language
   - auditability and judge-first demo discipline

3. `XioAISolutions/penguinwalkos`
   - public product buckets over deeper runtime
   - deterministic-first runtime language
   - workspace/trust/memory packaging

4. `slavazeph-coder/the-brain`
   - visual live intelligence demo feel
   - graph/timeline/panel metaphors
   - MCP bridge and second-brain language

5. `slavazeph-coder/openclaw-workspace`
   - local bridge/skill pattern
   - safe localhost defaults

Do not blindly copy unrelated code. Borrow the useful patterns and adapt them cleanly.

## Required implementation

### 1. Make generated CRUMBs stronger

Update `crumdbob/packer.py` so generated CRUMBs include richer v1.4 sections where appropriate:

- `refs=` headers linking pack files together
- `[checks]` sections using `name :: status` format
- `[workflow]` numbered continuation steps
- `[guardrails]` for safe AI-assisted dev behavior
- `[capabilities]` for what the continuation agent can/cannot do
- `[evidence]` with source snippets and file/command/risk extraction
- `[handoff]` with valid `id=` and `after=` dependencies

Each generated file must remain human-readable and pasteable.

### 2. Add validation

Create `crumdbob/validator.py`.

It should validate the CrumbBob-generated subset of CRUMB v1.4:

- starts with `BEGIN CRUMB`
- ends with `END CRUMB`
- has `v=1.4`, `kind=`, `title=`, and `source=` headers
- has required sections for each kind:
  - map: `[project]`, `[modules]`
  - task: `[goal]`, `[context]`, `[constraints]`
  - todo: `[tasks]`
  - agent: `[identity]`
  - audit: `[goal]`, `[actions]`, `[verdict]`
- validates `[checks]` lines use `name :: status`
- validates `[handoff]` dependency references are known
- validates `[workflow]` step dependencies are known

Add tests.

### 3. Add CLI commands

Update `crumdbob/cli.py` with:

```bash
crumdbob validate <pack-dir-or-file>
crumdbob doctor <pack-dir>
crumdbob graph <pack-dir>
crumdbob pack <input-dir> --out <output-dir>
crumdbob init-bob-skill --out skills/crumdbob/SKILL.md
```

Expected behavior:

- `validate` checks every `.crumb` file and exits non-zero on errors.
- `doctor` prints a judge-friendly health report: files present, CRUMBs valid, replay prompt present, PR summary present, source report present.
- `graph` prints a simple dependency graph from refs/handoff/workflow.
- `pack` accepts a directory containing `bob-report.md`, optional `git-diff.patch`, optional `test-output.txt`, optional `repo-notes.md`, then generates the pack.
- `init-bob-skill` writes a small skill/instructions file explaining how another agent should use CrumbBob.

### 4. Add proof chain

Add a new generated output:

```text
08_proof_chain.json
```

It should include:

- source report path
- sha256 hash of source report
- generated files with sha256 hashes
- timestamp in UTC
- CrumbBob version
- extracted counts: files, commands, risks, tests, next_steps

Add tests verifying the hashes exist.

### 5. Add optional web demo

Create a minimal static web demo in `web/` using plain HTML/CSS/JS or a tiny Vite app. Keep it simple and dependency-light.

Required UI sections:

- hero: `Your AI built it. CrumbBob remembers why.`
- text area for Bob report paste
- Generate Demo Pack button
- panels for Repo Genome, Flight Recorder, Risk Register, Replay Prompt
- copy buttons

It does not need server-side generation. It can use a small browser-side sample transform or load the example generated files.

### 6. Add docs

Create/update:

- `docs/crumdbob-cli.md`
- `docs/proof-chain.md`
- `docs/integrations.md`
- `docs/final-submission-checklist.md`
- `docs/source-adoption-map.md` if needed

Add final README sections:

- Quickstart
- Why IBM Bob
- What judges should inspect
- Demo flow
- CLI command reference
- Final submission checklist

### 7. Add tests and CI

Expand tests to cover:

- parser extraction
- pack generation
- validation success
- validation failure for malformed crumb
- doctor command output
- proof chain hashes
- CLI smoke via subprocess if practical

Run:

```bash
python -m pip install -e . pytest
pytest -q
```

All tests must pass.

## Style rules

- Keep code small and understandable.
- No fake external API calls.
- No network dependency.
- Do not require IBM credentials for local demo.
- Do not remove existing files unless replacing with a strictly better version.
- Prefer deterministic output so tests are stable. If timestamps are needed, allow injection or only validate shape.
- Keep the README judge-readable in under 90 seconds.

## Definition of done

The repo should let a judge run:

```bash
git clone https://github.com/XioAISolutions/Crumb-Bob
cd Crumb-Bob
pip install -e . pytest
pytest -q
crumdbob doctor examples/compliance-ai/generated
crumdbob replay examples/compliance-ai/generated
```

And immediately understand that CrumbBob is the missing memory layer around IBM Bob.
