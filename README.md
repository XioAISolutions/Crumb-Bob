# CrumbBob

> **The flight recorder for IBM Bob development sessions.**

CrumbBob turns exported IBM Bob repo sessions into replayable software memory: repo genomes, session logs, risk registers, test plans, PR summaries, and paste-ready handoffs for the next developer or AI agent.

**Bob gives software a temporary brain. CrumbBob gives that brain memory.**

## What it does

IBM Bob can understand a repository, explain architecture, generate docs/tests, and reduce repetitive developer work. CrumbBob preserves that work as a portable memory pack.

CrumbBob imports a Bob report and produces:

- **Repo Genome** — compressed architecture map of the codebase
- **Session Flight Recorder** — audit trail of what Bob understood, changed, and left behind
- **Next Task** — implementation-ready task brief
- **Test Plan** — validation checklist for the next developer or AI agent
- **Risk Register** — unresolved risk zones and hidden assumptions
- **Agent Passport** — reusable Bob persona for this repo
- **Replay Prompt** — paste-ready prompt to continue in Bob, Claude, Cursor, Codex, or another agent
- **PR Summary** — clean pull request description generated from the session

## Demo

```bash
python -m crumdbob.cli import examples/compliance-ai/bob-report.md --out examples/compliance-ai/generated
python -m crumdbob.cli replay examples/compliance-ai/generated
python -m crumdbob.cli pr examples/compliance-ai/generated
```

After installing locally:

```bash
pip install -e .
crumdbob import examples/compliance-ai/bob-report.md --out examples/compliance-ai/generated
crumdbob replay examples/compliance-ai/generated
crumdbob pr examples/compliance-ai/generated
```

## Repository layout

```text
crumdbob/                  Python package and CLI
examples/compliance-ai/    Example Bob report and generated memory pack
docs/                      Architecture and judge walkthrough
tests/                     Pack generation tests
```

## Built on CRUMB

CrumbBob specializes the CRUMB handoff format for IBM Bob sessions. CRUMB provides the portable handoff grammar; CrumbBob gives it a Bob-native workflow.

## Hackathon thesis

Most teams use Bob to build an app. CrumbBob builds the missing memory layer around Bob.

The product loop is simple:

```text
IBM Bob report -> CrumbBob pack -> replayable repo memory -> faster next session
```
