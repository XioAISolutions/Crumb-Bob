# IBM Bob Shell Integration

CrumbBob works with Bob Shell as a local handoff loop. It does not require a Bob API integration.

## Review Current Pack With Bob

```bash
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
crumdbob doctor examples/compliance-ai/generated
bob --chat-mode ask --hide-intermediary-output \
  "Review examples/compliance-ai/generated as a CrumbBob replay pack. Do not edit files. Report missing context, proof-chain risks, and next Bob actions."
```

## Continue From Replay Prompt

```bash
bob --chat-mode ask --hide-intermediary-output "$(crumdbob replay examples/compliance-ai/generated)"
```

Use `ask` mode for analysis and `code` mode only when the user wants Bob to edit the repo.

## Bob Instructions

When Bob receives a CrumbBob pack:

1. Read `08_proof_chain.json` first and check the source report hash.
2. Load `.crumb` files in lexical order.
3. Continue from `02_next_task.crumb`.
4. Run or update `03_test_plan.crumb`.
5. Regenerate the pack after changing source context or generated files.
6. Run `crumdbob doctor <pack-dir>` before handoff.
