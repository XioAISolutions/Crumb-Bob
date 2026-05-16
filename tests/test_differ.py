from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from crumdbob.differ import (
    compare_crumb_files,
    compare_packs,
    compare_proof_chains,
    format_detailed,
    format_json,
    format_summary,
    parse_crumb_file,
)


@pytest.fixture
def temp_pack_dir(tmp_path: Path) -> Path:
    """Create a temporary pack directory with sample files."""
    pack_dir = tmp_path / "pack1"
    pack_dir.mkdir()

    # Create a sample CRUMB file
    crumb_content = (
        dedent("""
        BEGIN CRUMB
        v=1.4
        kind=map
        title=Test Repo Genome
        source=ibm-bob
        id=repo-genome
        refs=session-flight-recorder,next-task
        ---
        [project]
        This is a test project.

        [modules]
        - src/app.ts
        - src/utils.ts

        [commands]
        - npm test
        - npm build

        END CRUMB
    """).strip()
        + "\n"
    )

    (pack_dir / "00_repo_genome.crumb").write_text(crumb_content, encoding="utf-8")

    # Create a sample proof chain
    proof_chain = {
        "schema": "crumdbob.proof-chain.v1",
        "timestamp_utc": "2026-05-15T15:00:00Z",
        "crumdbob_version": "0.2.0",
        "source_report": {
            "path": "bob-report.md",
            "sha256": "abc123",
            "bytes": 1000,
        },
        "source_artifacts": [],
        "generated_files": [
            {
                "path": "00_repo_genome.crumb",
                "sha256": "def456",
                "bytes": 500,
            }
        ],
        "extracted_counts": {
            "files": 2,
            "commands": 2,
            "risks": 1,
            "tests": 1,
            "next_steps": 1,
        },
        "notes": ["Test note"],
    }

    (pack_dir / "08_proof_chain.json").write_text(
        json.dumps(proof_chain, indent=2), encoding="utf-8"
    )

    # Create a sample markdown file
    (pack_dir / "06_replay_prompt.md").write_text(
        "# Replay Prompt\n\nTest content\n", encoding="utf-8"
    )

    return pack_dir


def test_parse_crumb_file(temp_pack_dir: Path):
    """Test parsing a CRUMB file."""
    crumb_path = temp_pack_dir / "00_repo_genome.crumb"
    crumb = parse_crumb_file(crumb_path)

    assert crumb is not None
    assert crumb.kind == "map"
    assert crumb.title == "Test Repo Genome"
    assert crumb.id == "repo-genome"
    assert "project" in crumb.sections
    assert "modules" in crumb.sections
    assert "commands" in crumb.sections
    assert "This is a test project." in crumb.sections["project"]


def test_parse_crumb_file_missing(tmp_path: Path):
    """Test parsing a missing CRUMB file."""
    crumb = parse_crumb_file(tmp_path / "missing.crumb")
    assert crumb is None


def test_compare_crumb_files_identical(temp_pack_dir: Path, tmp_path: Path):
    """Test comparing identical CRUMB files."""
    crumb_path = temp_pack_dir / "00_repo_genome.crumb"

    # Copy to another location
    pack2 = tmp_path / "pack2"
    pack2.mkdir()
    crumb_path2 = pack2 / "00_repo_genome.crumb"
    crumb_path2.write_text(crumb_path.read_text(), encoding="utf-8")

    diff = compare_crumb_files(crumb_path, crumb_path2)

    assert diff.status == "unchanged"
    assert not diff.header_changes
    assert not diff.section_changes
    assert not diff.added_sections
    assert not diff.removed_sections
    assert not diff.modified_sections


def test_compare_crumb_files_modified(temp_pack_dir: Path, tmp_path: Path):
    """Test comparing modified CRUMB files."""
    crumb_path = temp_pack_dir / "00_repo_genome.crumb"

    # Create modified version
    pack2 = tmp_path / "pack2"
    pack2.mkdir()
    crumb_path2 = pack2 / "00_repo_genome.crumb"

    modified_content = (
        dedent("""
        BEGIN CRUMB
        v=1.4
        kind=map
        title=Modified Repo Genome
        source=ibm-bob
        id=repo-genome-v2
        refs=session-flight-recorder,next-task
        ---
        [project]
        This is a modified test project.

        [modules]
        - src/app.ts
        - src/utils.ts
        - src/new.ts

        [commands]
        - npm test
        - npm build

        [new_section]
        This is a new section.

        END CRUMB
    """).strip()
        + "\n"
    )

    crumb_path2.write_text(modified_content, encoding="utf-8")

    diff = compare_crumb_files(crumb_path, crumb_path2)

    assert diff.status == "modified"
    assert "title" in diff.header_changes
    assert "id" in diff.header_changes
    assert diff.header_changes["title"] == ("Test Repo Genome", "Modified Repo Genome")
    assert "project" in diff.modified_sections
    assert "modules" in diff.modified_sections
    assert "new_section" in diff.added_sections


def test_compare_crumb_files_added(tmp_path: Path):
    """Test comparing when second file is added."""
    pack1 = tmp_path / "pack1"
    pack1.mkdir()

    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    crumb_path1 = pack1 / "test.crumb"
    crumb_path2 = pack2 / "test.crumb"

    crumb_content = (
        dedent("""
        BEGIN CRUMB
        v=1.4
        kind=map
        title=Test
        source=ibm-bob
        ---
        [section]
        Content

        END CRUMB
    """).strip()
        + "\n"
    )

    crumb_path2.write_text(crumb_content, encoding="utf-8")

    diff = compare_crumb_files(crumb_path1, crumb_path2)
    assert diff.status == "added"


def test_compare_crumb_files_removed(tmp_path: Path):
    """Test comparing when first file is removed."""
    pack1 = tmp_path / "pack1"
    pack1.mkdir()

    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    crumb_path1 = pack1 / "test.crumb"
    crumb_path2 = pack2 / "test.crumb"

    crumb_content = (
        dedent("""
        BEGIN CRUMB
        v=1.4
        kind=map
        title=Test
        source=ibm-bob
        ---
        [section]
        Content

        END CRUMB
    """).strip()
        + "\n"
    )

    crumb_path1.write_text(crumb_content, encoding="utf-8")

    diff = compare_crumb_files(crumb_path1, crumb_path2)
    assert diff.status == "removed"


def test_compare_proof_chains_identical(temp_pack_dir: Path, tmp_path: Path):
    """Test comparing identical proof chains."""
    proof_path1 = temp_pack_dir / "08_proof_chain.json"

    pack2 = tmp_path / "pack2"
    pack2.mkdir()
    proof_path2 = pack2 / "08_proof_chain.json"
    proof_path2.write_text(proof_path1.read_text(), encoding="utf-8")

    diff = compare_proof_chains(proof_path1, proof_path2)

    assert diff.status == "unchanged"
    assert not diff.source_hash_changed
    assert not diff.count_changes
    assert not diff.file_hash_changes


def test_compare_proof_chains_modified(temp_pack_dir: Path, tmp_path: Path):
    """Test comparing modified proof chains."""
    proof_path1 = temp_pack_dir / "08_proof_chain.json"

    pack2 = tmp_path / "pack2"
    pack2.mkdir()
    proof_path2 = pack2 / "08_proof_chain.json"

    # Modify proof chain
    proof = json.loads(proof_path1.read_text())
    proof["source_report"]["sha256"] = "xyz789"
    proof["extracted_counts"]["files"] = 5
    proof["extracted_counts"]["commands"] = 3
    proof["generated_files"][0]["sha256"] = "newHash"

    proof_path2.write_text(json.dumps(proof, indent=2), encoding="utf-8")

    diff = compare_proof_chains(proof_path1, proof_path2)

    assert diff.status == "modified"
    assert diff.source_hash_changed
    assert diff.old_source_hash == "abc123"
    assert diff.new_source_hash == "xyz789"
    assert "files" in diff.count_changes
    assert diff.count_changes["files"] == (2, 5)
    assert "commands" in diff.count_changes
    assert diff.count_changes["commands"] == (2, 3)
    assert "00_repo_genome.crumb" in diff.file_hash_changes


def test_compare_packs_identical(temp_pack_dir: Path, tmp_path: Path):
    """Test comparing identical packs."""
    # Create identical pack2
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    for file in temp_pack_dir.iterdir():
        if file.is_file():
            (pack2 / file.name).write_text(file.read_text(), encoding="utf-8")

    diff = compare_packs(temp_pack_dir, pack2)

    assert diff.identical
    assert not diff.added_files
    assert not diff.removed_files
    assert all(d.status == "unchanged" for d in diff.crumb_diffs)


def test_compare_packs_with_changes(temp_pack_dir: Path, tmp_path: Path):
    """Test comparing packs with various changes."""
    # Create modified pack2
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    # Copy and modify CRUMB file
    crumb_content = (temp_pack_dir / "00_repo_genome.crumb").read_text()
    modified_crumb = crumb_content.replace("Test Repo Genome", "Modified Genome")
    (pack2 / "00_repo_genome.crumb").write_text(modified_crumb, encoding="utf-8")

    # Copy proof chain with modifications
    proof = json.loads((temp_pack_dir / "08_proof_chain.json").read_text())
    proof["extracted_counts"]["files"] = 10
    (pack2 / "08_proof_chain.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")

    # Copy markdown file unchanged
    (pack2 / "06_replay_prompt.md").write_text(
        (temp_pack_dir / "06_replay_prompt.md").read_text(), encoding="utf-8"
    )

    # Add a new file
    (pack2 / "new_file.txt").write_text("New content", encoding="utf-8")

    diff = compare_packs(temp_pack_dir, pack2)

    assert not diff.identical
    assert "new_file.txt" in diff.added_files
    assert len(diff.crumb_diffs) > 0

    # Find the modified CRUMB
    crumb_diff = next(d for d in diff.crumb_diffs if d.path == "00_repo_genome.crumb")
    assert crumb_diff.status == "modified"

    # Check proof chain changes
    assert diff.proof_chain_diff is not None
    assert diff.proof_chain_diff.status == "modified"
    assert "files" in diff.proof_chain_diff.count_changes


def test_compare_packs_missing_directory(tmp_path: Path):
    """Test comparing when one directory doesn't exist."""
    pack1 = tmp_path / "pack1"
    pack1.mkdir()
    pack2 = tmp_path / "pack2"

    with pytest.raises(FileNotFoundError):
        compare_packs(pack1, pack2)


def test_format_summary_identical(temp_pack_dir: Path, tmp_path: Path):
    """Test formatting summary for identical packs."""
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    for file in temp_pack_dir.iterdir():
        if file.is_file():
            (pack2 / file.name).write_text(file.read_text(), encoding="utf-8")

    diff = compare_packs(temp_pack_dir, pack2)
    output = format_summary(diff, use_color=False)

    assert "identical" in output.lower()
    assert str(temp_pack_dir) in output
    assert str(pack2) in output


def test_format_summary_with_changes(temp_pack_dir: Path, tmp_path: Path):
    """Test formatting summary with changes."""
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    # Copy with modifications
    crumb_content = (temp_pack_dir / "00_repo_genome.crumb").read_text()
    modified_crumb = crumb_content.replace("Test Repo Genome", "Modified Genome")
    (pack2 / "00_repo_genome.crumb").write_text(modified_crumb, encoding="utf-8")

    # Add proof chain with changes
    proof = json.loads((temp_pack_dir / "08_proof_chain.json").read_text())
    proof["extracted_counts"]["files"] = 10
    (pack2 / "08_proof_chain.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")

    # Add new file
    (pack2 / "new_file.txt").write_text("New", encoding="utf-8")

    diff = compare_packs(temp_pack_dir, pack2)
    output = format_summary(diff, use_color=False)

    assert "differ" in output.lower()
    assert "1 file(s) added" in output
    assert "modified" in output.lower()


def test_format_detailed(temp_pack_dir: Path, tmp_path: Path):
    """Test detailed format output."""
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    # Create changes
    crumb_content = (temp_pack_dir / "00_repo_genome.crumb").read_text()
    modified_crumb = crumb_content.replace("This is a test project.", "This is a modified project.")
    (pack2 / "00_repo_genome.crumb").write_text(modified_crumb, encoding="utf-8")

    proof = json.loads((temp_pack_dir / "08_proof_chain.json").read_text())
    (pack2 / "08_proof_chain.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")

    diff = compare_packs(temp_pack_dir, pack2)
    output = format_detailed(diff, use_color=False)

    assert "Detailed" in output
    assert "00_repo_genome.crumb" in output
    assert "Modified CRUMB Files" in output or "modified" in output.lower()


def test_format_json(temp_pack_dir: Path, tmp_path: Path):
    """Test JSON format output."""
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    for file in temp_pack_dir.iterdir():
        if file.is_file():
            (pack2 / file.name).write_text(file.read_text(), encoding="utf-8")

    diff = compare_packs(temp_pack_dir, pack2)
    output = format_json(diff)

    # Parse JSON to verify it's valid
    data = json.loads(output)

    assert "pack1" in data
    assert "pack2" in data
    assert "identical" in data
    assert data["identical"] is True
    assert "summary" in data
    assert "crumb_diffs" in data
    assert "file_diffs" in data


def test_format_json_with_changes(temp_pack_dir: Path, tmp_path: Path):
    """Test JSON format with changes."""
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    # Add changes
    (pack2 / "new_file.txt").write_text("New", encoding="utf-8")

    crumb_content = (temp_pack_dir / "00_repo_genome.crumb").read_text()
    (pack2 / "00_repo_genome.crumb").write_text(crumb_content, encoding="utf-8")

    proof = json.loads((temp_pack_dir / "08_proof_chain.json").read_text())
    proof["extracted_counts"]["files"] = 10
    (pack2 / "08_proof_chain.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")

    diff = compare_packs(temp_pack_dir, pack2)
    output = format_json(diff)

    data = json.loads(output)

    assert data["identical"] is False
    assert data["summary"]["added_files"] == 1
    assert "new_file.txt" in data["added_files"]
    assert "proof_chain" in data
    assert "count_changes" in data["proof_chain"]
    assert "files" in data["proof_chain"]["count_changes"]


def test_compare_packs_with_removed_files(temp_pack_dir: Path, tmp_path: Path):
    """Test comparing packs when files are removed."""
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    # Copy only some files (remove replay prompt)
    (pack2 / "00_repo_genome.crumb").write_text(
        (temp_pack_dir / "00_repo_genome.crumb").read_text(), encoding="utf-8"
    )
    (pack2 / "08_proof_chain.json").write_text(
        (temp_pack_dir / "08_proof_chain.json").read_text(), encoding="utf-8"
    )

    diff = compare_packs(temp_pack_dir, pack2)

    assert not diff.identical
    assert "06_replay_prompt.md" in diff.removed_files


def test_proof_chain_with_added_removed_files(tmp_path: Path):
    """Test proof chain comparison with added/removed files."""
    pack1 = tmp_path / "pack1"
    pack1.mkdir()
    pack2 = tmp_path / "pack2"
    pack2.mkdir()

    proof1 = {
        "schema": "crumdbob.proof-chain.v1",
        "source_report": {"sha256": "abc", "bytes": 100, "path": "report.md"},
        "generated_files": [
            {"path": "file1.crumb", "sha256": "hash1", "bytes": 100},
            {"path": "file2.crumb", "sha256": "hash2", "bytes": 200},
        ],
        "extracted_counts": {"files": 1},
    }

    proof2 = {
        "schema": "crumdbob.proof-chain.v1",
        "source_report": {"sha256": "abc", "bytes": 100, "path": "report.md"},
        "generated_files": [
            {"path": "file2.crumb", "sha256": "hash2", "bytes": 200},
            {"path": "file3.crumb", "sha256": "hash3", "bytes": 300},
        ],
        "extracted_counts": {"files": 1},
    }

    (pack1 / "08_proof_chain.json").write_text(json.dumps(proof1), encoding="utf-8")
    (pack2 / "08_proof_chain.json").write_text(json.dumps(proof2), encoding="utf-8")

    diff = compare_proof_chains(pack1 / "08_proof_chain.json", pack2 / "08_proof_chain.json")

    assert diff.status == "modified"
    assert "file1.crumb" in diff.removed_files
    assert "file3.crumb" in diff.added_files
    assert "file2.crumb" not in diff.added_files
    assert "file2.crumb" not in diff.removed_files


# Made with Bob
