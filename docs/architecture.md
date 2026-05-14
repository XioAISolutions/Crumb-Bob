# Architecture

CrumbBob is intentionally small. The goal is to make IBM Bob session output portable, not to create another heavyweight platform.

## Flow

```text
Bob report markdown
  -> crumdbob.parser.parse_bob_report
  -> BobReport structured extraction
  -> crumdbob.packer.generate_pack
  -> generated CRUMB memory pack
```

## Components

- `crumdbob/parser.py` extracts headings, bullets, file paths, commands, risks, tests, and next steps from a markdown Bob report.
- `crumdbob/packer.py` renders the standard CrumbBob pack files.
- `crumdbob/cli.py` provides `import`, `inspect`, `replay`, and `pr` commands.
- `examples/compliance-ai/` contains a demo Bob report and generated output.

## Pack files

- `00_repo_genome.crumb` maps product purpose, modules, and command surface.
- `01_session_flight_recorder.crumb` captures the session goal, actions, verdict, and evidence.
- `02_next_task.crumb` turns Bob's findings into an implementation task.
- `03_test_plan.crumb` captures the test checklist.
- `04_risk_register.crumb` preserves unresolved risks and assumptions.
- `05_agent_passport.crumb` defines the continuation agent persona.
- `06_replay_prompt.md` is the paste-ready prompt for the next Bob/dev session.
- `07_pr_summary.md` is the review-ready GitHub PR description.

## Design rules

1. The pack must be useful even without the original chat.
2. Every file should be readable by a human and pasteable into an AI tool.
3. The source Bob report should remain the audit source.
4. The output should be small enough for hackathon demo review.
