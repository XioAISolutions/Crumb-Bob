# Final Submission Checklist

## Judge Run

- [ ] `pip install -e . pytest`
- [ ] `pytest -q`
- [ ] `crumdbob doctor examples/compliance-ai/generated`
- [ ] `crumdbob validate examples/compliance-ai/generated`
- [ ] `crumdbob graph examples/compliance-ai/generated`
- [ ] `crumdbob replay examples/compliance-ai/generated`
- [ ] Open `web/index.html` and generate the demo pack preview.

## Files To Inspect

- [ ] `examples/compliance-ai/bob-report.md`
- [ ] `examples/compliance-ai/generated/00_repo_genome.crumb`
- [ ] `examples/compliance-ai/generated/01_session_flight_recorder.crumb`
- [ ] `examples/compliance-ai/generated/02_next_task.crumb`
- [ ] `examples/compliance-ai/generated/04_risk_register.crumb`
- [ ] `examples/compliance-ai/generated/08_proof_chain.json`
- [ ] `docs/proof-chain.md`
- [ ] `docs/crumdbob-cli.md`

## Demo Beats

- [ ] Bob creates temporary repo intelligence.
- [ ] CrumbBob captures that intelligence as CRUMB v1.4 memory.
- [ ] Proof Chain binds generated files back to the source report.
- [ ] Replay Prompt lets Bob or another agent continue without rediscovery.
- [ ] Doctor output gives judges a fast trust check.

## Product Claim

CrumbBob is the missing memory layer around IBM Bob: capture, compress, replay, prove.
