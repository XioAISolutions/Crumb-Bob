# Source Adoption Map

CrumbBob should borrow the strongest proven ideas from the XIO repo family without becoming messy or unfocused.

## 1. From `XioAISolutions/crumb-format`

Borrow first. This is the foundation.

Adopt:

- CRUMB v1.4 grammar and validation rules
- `refs=` cross-crumb references
- foldable summary/full sections
- `[handoff]` dependency lines with `id=` and `after=`
- `[workflow]` numbered orchestration blocks
- `[checks]` validation results
- `[guardrails]`, `[capabilities]`, and `[script]` sections
- `kind=agent`, `kind=audit`, `kind=todo`, `kind=map`, `kind=task`
- `crumb it` trigger language
- native Claude Code and Cursor integration language
- MCP and AgentAuth roadmap hooks
- Palace/wake/reflect ideas as future CrumbBob memory modes

Do not copy every command. CrumbBob only needs the parts that make Bob reports replayable.

## 2. From `XioAISolutions/compliance-AI`

Borrow the trust model.

Adopt:

- proof-chain framing
- source-locker style metadata for report evidence
- hash-bound output identity
- approval-gated export language
- audit trail from input report to generated pack
- smoke-demo habit and judge-first walkthrough

CrumbBob equivalent:

```text
Bob report -> extracted evidence -> generated CRUMBs -> replay prompt -> PR summary
```

## 3. From `XioAISolutions/penguinwalkos`

Borrow the product packaging discipline.

Adopt:

- simple public buckets layered over deeper runtime
- deterministic-first runtime language
- trust/approval/workflow/memory package layout
- demo workspace mindset
- health/ready/version/checks command surface as future CLI polish

CrumbBob public buckets:

- Capture
- Compress
- Replay
- Prove

## 4. From `slavazeph-coder/the-brain`

Borrow the demo drama, not the neuroscience.

Adopt:

- visual live system feel
- knowledge graph / second brain language
- MCP bridge to agents
- risk scoring and red-team panel idea
- replay/consolidation metaphor

CrumbBob equivalent:

- Repo Genome graph
- Session Flight Recorder timeline
- Risk Register panel
- Replay Pack viewer

## 5. From `slavazeph-coder/openclaw-workspace`

Borrow the local bridge pattern.

Adopt:

- localhost service wrapper concept
- skill file that teaches another agent how to use the tool
- safe local-only defaults

CrumbBob equivalent:

- `skills/crumdbob/SKILL.md`
- optional local service exposing `/health`, `/pack`, `/replay`, `/pr`

## Priority order

1. Make generated CRUMBs fully validate against CRUMB v1.4 expectations.
2. Add `validate`, `doctor`, `pack`, and `graph` CLI commands.
3. Add real source/evidence metadata and content hashes.
4. Add a polished web/demo surface.
5. Add MCP/Claude/Cursor/Bob integration docs.
6. Add local bridge or skill mode only after the core pack is solid.
