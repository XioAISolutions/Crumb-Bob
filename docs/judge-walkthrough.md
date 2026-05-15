# Judge Walkthrough

## What to look at first

1. `README.md` for the product story.
2. `examples/compliance-ai/bob-report.md` for the input Bob report.
3. `examples/compliance-ai/generated/` for the generated CrumbBob pack.
4. `examples/compliance-ai/generated/08_proof_chain.json` for source and generated file hashes.
5. `web/index.html` for the local static demo.
6. `DEMO_SCRIPT.md` for the video flow.

## Run it

```bash
pip install -e .
crumdbob inspect examples/compliance-ai/bob-report.md
crumdbob pack examples/compliance-ai --out /tmp/crumdbob-pack
crumdbob validate /tmp/crumdbob-pack
crumdbob doctor /tmp/crumdbob-pack
crumdbob graph /tmp/crumdbob-pack
crumdbob replay /tmp/crumdbob-pack
crumdbob pr /tmp/crumdbob-pack
```

## Why this matters

CrumbBob turns a one-time Bob report into durable repo memory. The Proof Chain makes the generated pack reviewable by tying source input, generated output hashes, extracted counts, and replay instructions together.

## The key product insight

IBM Bob is strongest when it understands the repository. CrumbBob makes that understanding portable after the session ends.
