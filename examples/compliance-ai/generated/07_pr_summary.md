# PR: Add CrumbBob replay pack

## Summary

This PR adds a CrumbBob memory pack generated from an IBM Bob repository session.

## What changed

- Added Repo Genome for the target repository
- Added Session Flight Recorder capturing the Bob session
- Added Next Task, Test Plan, Risk Register, Agent Passport, and Replay Prompt
- Added a reusable PR summary for review handoff

## Why

IBM Bob can understand a repository during a session. CrumbBob makes that understanding portable so the next developer or AI agent can continue without re-reading the full session.

## Validation

- [ ] pnpm test
- [ ] pnpm -r typecheck
- [ ] pnpm --filter @compliance-ai/web build
- [ ] pnpm smoke:demo
- [ ] Validate that generated citations include source-locker metadata
- [ ] Validate that export is blocked without a matching hash-bound approval
