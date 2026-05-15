from pathlib import Path

from crumdbob.parser import parse_bob_report
from crumdbob.packer import generate_pack, write_pack, read_pr_summary, read_replay_prompt

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
    pack = generate_pack(report)
    names = {item.path for item in pack}
    assert "00_repo_genome.crumb" in names
    assert "01_session_flight_recorder.crumb" in names
    assert "06_replay_prompt.md" in names
    assert "07_pr_summary.md" in names
    assert len(pack) == 8

def test_write_pack_roundtrip(tmp_path):
    written = write_pack(FIXTURE, tmp_path)
    assert len(written) == 8
    replay = read_replay_prompt(tmp_path)
    pr = read_pr_summary(tmp_path)
    assert "Replay this IBM Bob session" in replay
    assert "PR: Add CrumbBob replay pack" in pr
    assert (tmp_path / "00_repo_genome.crumb").read_text().startswith("BEGIN CRUMB")
