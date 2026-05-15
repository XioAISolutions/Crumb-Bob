# PR: Add CrumbBob replay pack

## Summary
This PR adds a CrumbBob memory pack generated from an IBM Bob repository session.

## What changed
- Added Repo Genome, Session Flight Recorder, Next Task, Test Plan, Risk Register, Agent Passport, Replay Prompt, PR Summary, and Proof Chain.
- Captured source evidence, continuation workflow, guardrails, capabilities, and CRUMB dependency links.
- Added hash-bound provenance so reviewers can trace generated files back to the Bob report.

## Why
IBM Bob can understand a repository during a session. CrumbBob makes that understanding portable and replayable.

## Validation
- [ ] pnpm test
- [ ] pnpm -r typecheck
- [ ] pnpm --filter @compliance-ai/web build
- [ ] pnpm smoke:demo
- [ ] Run pnpm test to validate agents, cognition, and web behavior.
- [ ] Run pnpm -r typecheck to validate the monorepo TypeScript surface.
- [ ] Run pnpm --filter @compliance-ai/web build before any hosted demo.
- [ ] Run pnpm smoke:demo against the deployed or local app.
- [ ] Add Risk Register and Test Plan as CRUMB handoffs.
