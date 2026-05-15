# Integrations

CrumbBob is local-first. It does not call IBM, OpenAI, Anthropic, GitHub, or any external service during pack generation.

## IBM Bob

1. Use Bob to inspect a repository.
2. Export or paste the session report into `bob-report.md`.
3. Add optional `git-diff.patch`, `test-output.txt`, or `repo-notes.md`.
4. Run `crumdbob pack <input-dir> --out <pack-dir>`.
5. Paste `06_replay_prompt.md` into the next Bob session with the generated pack files.

## Local Bob CLI

If the IBM Bob CLI is installed, CrumbBob can hand the replay prompt back to Bob directly:

```bash
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
crumdbob doctor examples/compliance-ai/generated
bob --chat-mode ask --hide-intermediary-output "$(crumdbob replay examples/compliance-ai/generated)"
```

For a repo review loop, ask Bob to inspect the generated pack without editing:

```bash
bob --chat-mode ask --hide-intermediary-output \
  "Review examples/compliance-ai/generated as a CrumbBob replay pack. Do not edit files. Report missing context, proof-chain risks, and next Bob actions."
```

Use `--chat-mode code` only when you intentionally want Bob to modify the repo.

## Claude, Cursor, Codex, And Other Agents

Load files in lexical order:

```text
00_repo_genome.crumb
01_session_flight_recorder.crumb
02_next_task.crumb
03_test_plan.crumb
04_risk_register.crumb
05_agent_passport.crumb
08_proof_chain.json
```

Then continue from `02_next_task.crumb` and run the test plan before claiming completion.

## Agent Skill

Generate a local skill file:

```bash
crumdbob init-bob-skill --out skills/crumdbob/SKILL.md
```

That file teaches another agent the local CrumbBob workflow and proof-chain guardrails.

## MCP And AgentAuth Roadmap

The current product is intentionally dependency-free. The future integration shape is:

- localhost service with `/health`, `/pack`, `/replay`, and `/pr`
- AgentAuth-aware approval before exporting generated packs
- MCP resource endpoints for pack files and proof-chain metadata
- watcher mode that refreshes a pack when a Bob report or test output changes

The current CLI already models the stable contract those integrations would wrap.
