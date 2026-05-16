import hashlib
import json
import subprocess
import sys
from pathlib import Path

from crumdbob.cli import main
from crumdbob.packer import generate_pack, read_pr_summary, read_replay_prompt, write_pack
from crumdbob.parser import parse_bob_report
from crumdbob.validator import validate_target

FIXTURE = Path("examples/compliance-ai/bob-report.md")


def test_parser_extracts_useful_signal():
    report = parse_bob_report(FIXTURE)
    assert report.title == "IBM Bob Report: XIO Compliance Brain"
    assert "Canadian" in report.summary and "legal workbench" in report.summary
    assert "packages/agents" in report.files
    assert any("pnpm test" in command for command in report.commands)
    assert report.risks
    assert report.tests
    assert report.next_steps


def test_generate_pack_contains_expected_files():
    report = parse_bob_report(FIXTURE)
    pack = generate_pack(report, timestamp="2026-05-15T00:00:00Z")
    names = {item.path for item in pack}
    assert "00_repo_genome.crumb" in names
    assert "01_session_flight_recorder.crumb" in names
    assert "06_replay_prompt.md" in names
    assert "07_pr_summary.md" in names
    assert "08_proof_chain.json" in names
    assert len(pack) == 9
    repo_genome = next(item.content for item in pack if item.path == "00_repo_genome.crumb")
    assert (
        "refs=session-flight-recorder,next-task,test-plan,risk-register,agent-passport"
        in repo_genome
    )
    assert "[workflow]" in repo_genome
    assert "[guardrails]" in repo_genome
    assert "[capabilities]" in repo_genome


def test_write_pack_roundtrip_and_validates(tmp_path):
    written = write_pack(FIXTURE, tmp_path, timestamp="2026-05-15T00:00:00Z")
    assert len(written) == 9
    replay = read_replay_prompt(tmp_path)
    pr = read_pr_summary(tmp_path)
    assert "Replay this IBM Bob session" in replay
    assert "PR: Add CrumbBob replay pack" in pr
    assert (tmp_path / "00_repo_genome.crumb").read_text().startswith("BEGIN CRUMB")
    assert validate_target(tmp_path).ok


def test_proof_chain_contains_hashes(tmp_path):
    write_pack(FIXTURE, tmp_path, timestamp="2026-05-15T00:00:00Z")
    proof = json.loads((tmp_path / "08_proof_chain.json").read_text(encoding="utf-8"))
    assert proof["source_report"]["sha256"]
    assert proof["timestamp_utc"] == "2026-05-15T00:00:00Z"
    assert proof["extracted_counts"]["files"] > 0
    hashed = {item["path"]: item["sha256"] for item in proof["generated_files"]}
    for relpath, expected_hash in hashed.items():
        data = (tmp_path / relpath).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected_hash


def test_validation_failure_for_malformed_crumb(tmp_path):
    bad = tmp_path / "bad.crumb"
    bad.write_text(
        """BEGIN CRUMB
v=1.4
kind=task
title=Broken
source=ibm-bob
---
[goal]
Ship it.

[context]
Missing useful context.

[constraints]
- None.

[checks]
bad check line

END CRUMB
""",
        encoding="utf-8",
    )
    report = validate_target(bad)
    assert not report.ok
    assert any("invalid [checks] line" in error.message for error in report.errors)


def test_validation_failure_for_unknown_refs(tmp_path):
    (tmp_path / "map.crumb").write_text(
        """BEGIN CRUMB
v=1.4
kind=map
title=Map
source=ibm-bob
id=repo-genome
refs=missing-target
---
[project]
Captured.

[modules]
- crumdbob

END CRUMB
""",
        encoding="utf-8",
    )
    (tmp_path / "agent.crumb").write_text(
        """BEGIN CRUMB
v=1.4
kind=agent
title=Agent
source=ibm-bob
id=agent-passport
---
[identity]
role=continuation agent

END CRUMB
""",
        encoding="utf-8",
    )
    report = validate_target(tmp_path)
    assert not report.ok
    assert any("unknown refs target: missing-target" in error.message for error in report.errors)


def test_doctor_command_output(tmp_path, capsys):
    write_pack(FIXTURE, tmp_path, timestamp="2026-05-15T00:00:00Z")
    assert main(["doctor", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "CrumbBob Doctor" in output
    assert "CRUMBs valid: yes" in output
    assert "proof hashes current: yes" in output
    assert "verdict: ready for judge walkthrough" in output


def test_doctor_detects_stale_proof_chain(tmp_path, capsys):
    write_pack(FIXTURE, tmp_path, timestamp="2026-05-15T00:00:00Z")
    target = tmp_path / "00_repo_genome.crumb"
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert main(["doctor", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "proof hashes current: no" in output
    assert "verdict: needs attention" in output


def test_pack_command_directory_with_optional_artifacts(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "generated"
    input_dir.mkdir()
    (input_dir / "bob-report.md").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    (input_dir / "test-output.txt").write_text("pytest -q\n12 passed\n", encoding="utf-8")
    (input_dir / "repo-notes.md").write_text("- Add docs/quickstart.md next\n", encoding="utf-8")
    assert main(["pack", str(input_dir), "--out", str(output_dir)]) == 0
    proof = json.loads((output_dir / "08_proof_chain.json").read_text(encoding="utf-8"))
    assert {item["kind"] for item in proof["source_artifacts"]} == {"test-output", "repo-notes"}
    assert validate_target(output_dir).ok


def test_cli_validate_smoke(tmp_path):
    write_pack(FIXTURE, tmp_path, timestamp="2026-05-15T00:00:00Z")
    result = subprocess.run(
        [sys.executable, "-m", "crumdbob.cli", "validate", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Accept either the legacy plain output ("OK: 6 CRUMB file(s) valid") or
    # the Rich-styled panel ("All 6 CRUMB file(s) are valid"). Both formats
    # mean the same thing — which one runs depends on whether the optional
    # `rich` dependency is installed.
    assert (
        "OK: 6 CRUMB file(s) valid" in result.stdout
        or "All 6 CRUMB file(s) are valid" in result.stdout
    )
