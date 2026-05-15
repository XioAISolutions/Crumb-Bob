# Proof Chain

CrumbBob writes `08_proof_chain.json` so a judge or reviewer can verify that the generated pack is tied to the source Bob report.

## What It Contains

- `source_report.path`
- `source_report.sha256`
- `generated_files[].path`
- `generated_files[].sha256`
- `timestamp_utc`
- `crumdbob_version`
- `extracted_counts.files`
- `extracted_counts.commands`
- `extracted_counts.risks`
- `extracted_counts.tests`
- `extracted_counts.next_steps`
- optional `source_artifacts` for `git-diff.patch`, `test-output.txt`, and `repo-notes.md`

`generated_files` excludes `08_proof_chain.json` itself to avoid recursive self-hashing.

## Verify Locally

```bash
crumdbob validate examples/compliance-ai/generated
crumdbob doctor examples/compliance-ai/generated
python -m json.tool examples/compliance-ai/generated/08_proof_chain.json
```

`doctor` also recomputes source and generated file hashes. If a pack file changes after `08_proof_chain.json` was written, the report prints `proof hashes current: no` and exits non-zero.

For a manual hash check:

```bash
shasum -a 256 examples/compliance-ai/bob-report.md
shasum -a 256 examples/compliance-ai/generated/00_repo_genome.crumb
```

The values should match the corresponding entries in `08_proof_chain.json`.

## Why It Matters

CrumbBob is not only a markdown converter. It preserves source identity, extracted evidence counts, generated output hashes, and replay instructions in one reviewable artifact. That gives the memory pack a clear audit trail from Bob report to CRUMBs to replay prompt.
