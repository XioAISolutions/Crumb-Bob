# CrumbBob Hackathon Brief

## Project

**CrumbBob** — the flight recorder for IBM Bob development sessions.

## One-liner

CrumbBob converts exported IBM Bob repository sessions into replayable software memory: repo genomes, session logs, risk registers, test plans, PR summaries, and paste-ready handoffs.

## Problem

AI coding sessions create valuable repository understanding, but that context often dies when the session ends. Teams lose time re-explaining architecture, rediscovering setup steps, repeating risk analysis, and reconstructing why a change happened.

## Solution

CrumbBob imports a Bob report and generates a portable memory pack:

1. Repo Genome
2. Session Flight Recorder
3. Next Task
4. Test Plan
5. Risk Register
6. Agent Passport
7. Replay Prompt
8. PR Summary

The next developer or AI agent can continue from the prior Bob session without rereading the whole repo or chat history.

## Why IBM Bob

CrumbBob is built around Bob's strength: repo-aware development. Bob understands the codebase; CrumbBob preserves that understanding as structured handoffs.

## Business value

- Faster onboarding to complex repos
- Less repeated AI context setup
- Cleaner PRs and handoffs
- Better auditability for AI-assisted software work
- Reusable memory for multi-agent development workflows

## Demo target

The example pack uses XIO Compliance Brain, a Canadian AI-assisted legal workbench with document intake, task-specific reviewers, citation verification, approval gating, and DOCX export.

## Judging hook

Most teams use Bob to build an app. CrumbBob builds the missing memory layer around Bob.
