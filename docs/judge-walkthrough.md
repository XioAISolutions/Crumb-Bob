# Judge Walkthrough

## What to look at first

1. `README.md` for the product story.
2. `examples/compliance-ai/bob-report.md` for the input Bob report.
3. `examples/compliance-ai/generated/` for the generated CrumbBob pack.
4. `DEMO_SCRIPT.md` for the video flow.

## Run it

```bash
pip install -e .
crumdbob inspect examples/compliance-ai/bob-report.md
crumdbob import examples/compliance-ai/bob-report.md --out /tmp/crumdbob-pack
crumdbob replay /tmp/crumdbob-pack
crumdbob pr /tmp/crumdbob-pack
```

## Why this matters

CrumbBob turns a one-time Bob report into durable repo memory. That improves onboarding, PR handoffs, AI session continuity, and auditability.

## The key product insight

IBM Bob is strongest when it understands the repository. CrumbBob makes that understanding portable after the session ends.
