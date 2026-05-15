# CrumbBob — lablab.ai submission copy

## About
CrumbBob is the flight recorder for IBM Bob development sessions. It converts an exported IBM Bob session plus repository artifacts (git-diff, test output, CI logs) into a replayable, hash‑bound memory pack containing: Repo Genome, Session Flight Recorder, Next Task, Test Plan, Risk Register, Agent Passport, Replay Prompt, PR Summary, and Proof Chain. Designed for judges: fast validation, transparent proof chain, and a small local static demo (web/index.html).

## Short description
Flight recorder for IBM Bob sessions — capture, compress, replay, and prove session intelligence.

## Demo (commands)
1. pip install -e . pytest
2. pytest -q
3. crumdbob auto-collect --out examples/compliance-ai/generated
4. crumdbob validate examples/compliance-ai/generated
5. crumdbob doctor examples/compliance-ai/generated
6. crumdbob replay examples/compliance-ai/generated

Or open `web/index.html`, paste a Bob report, and click **Generate Demo Pack**.

## Judge checklist
- Install & test: `pip install -e . pytest` && `pytest -q`
- Validate pack: `crumdbob validate examples/compliance-ai/generated` (no errors)
- Health: `crumdbob doctor examples/compliance-ai/generated`
- Proof chain: inspect `08_proof_chain.json` for source and generated file hashes
- Web demo: open `web/index.html` and generate a pack

## Why it matters
Preserves session context so the next developer or AI agent can continue without rediscovery; improves auditability, reproducibility, and PR handoffs.

## Links
- Repository: https://github.com/XioAISolutions/Crumb-Bob
- Local demo: `web/index.html`
- Issues: https://github.com/XioAISolutions/Crumb-Bob/issues

## Tags
IBM Bob, memory, reproducibility, AI tooling, devtools, hackathon

## Contact
File an issue on GitHub or contact the maintainers via the repository.

## Notes for lablab.ai fields
- Use the Short description for the one-line field.
- Use the About paragraph for the main description.
- Paste demo commands into "How to reproduce" or "How to run".
- Add repository link and proof-chain note in "Additional links".
- Attach a screenshot of `web/index.html` and a short demo GIF if available.
