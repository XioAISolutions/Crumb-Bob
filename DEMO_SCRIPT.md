# Demo Script

## 0:00 - Problem

"AI coding tools are strong inside a session, but the best context disappears when the session ends. The next developer or AI agent has to rediscover the repo, the risks, the setup commands, and the reason behind the work."

## 0:20 - Bob

"IBM Bob gives us repo-aware intelligence. It can inspect a real codebase and produce useful development findings."

## 0:40 - CrumbBob

"CrumbBob turns that exported Bob report into a replayable memory pack."

Run:

```bash
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
```

## 1:10 - Show generated pack

Open:

```text
00_repo_genome.crumb
01_session_flight_recorder.crumb
02_next_task.crumb
03_test_plan.crumb
04_risk_register.crumb
05_agent_passport.crumb
06_replay_prompt.md
07_pr_summary.md
08_proof_chain.json
```

## 1:40 - Trust check

Run:

```bash
crumdbob validate examples/compliance-ai/generated
crumdbob doctor examples/compliance-ai/generated
crumdbob graph examples/compliance-ai/generated
```

Show that the output is validated, dependency-linked, and hash-bound to the source Bob report.

## 2:05 - Replay moment

Run:

```bash
crumdbob replay examples/compliance-ai/generated
```

Show that the replay prompt tells the next Bob session exactly what to load and how to continue.

## 2:30 - PR handoff

Run:

```bash
crumdbob pr examples/compliance-ai/generated
```

Show that the Bob session becomes a clean review artifact.

## 2:50 - Web demo

Run `crumdbob serve --no-browser`, open `http://localhost:8000`, and show the dashboard reading the recorded pack data.

## 3:20 - Close

"Bob gives software a temporary brain. CrumbBob gives that brain memory."
