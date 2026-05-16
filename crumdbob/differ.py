from __future__ import annotations

import contextlib
import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ANSI color codes
COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"
COLOR_BLUE = "\033[34m"
COLOR_RESET = "\033[0m"


@dataclass
class CrumbSection:
    """Represents a section in a CRUMB file."""

    name: str
    content: str


@dataclass
class CrumbFile:
    """Parsed CRUMB file structure."""

    path: str
    headers: dict[str, str]
    sections: dict[str, str]

    @property
    def kind(self) -> str:
        return self.headers.get("kind", "unknown")

    @property
    def title(self) -> str:
        return self.headers.get("title", "")

    @property
    def id(self) -> str:
        return self.headers.get("id", "")


@dataclass
class FileDiff:
    """Difference for a single file."""

    path: str
    status: str  # "added", "removed", "modified", "unchanged"
    old_size: int = 0
    new_size: int = 0
    details: str = ""


@dataclass
class CrumbDiff:
    """Difference for a CRUMB file."""

    path: str
    status: str  # "added", "removed", "modified", "unchanged"
    header_changes: dict[str, tuple[str | None, str | None]] = field(default_factory=dict)
    section_changes: dict[str, tuple[str | None, str | None]] = field(default_factory=dict)
    added_sections: list[str] = field(default_factory=list)
    removed_sections: list[str] = field(default_factory=list)
    modified_sections: list[str] = field(default_factory=list)


@dataclass
class ProofChainDiff:
    """Difference in proof chain."""

    status: str  # "added", "removed", "modified", "unchanged"
    source_hash_changed: bool = False
    old_source_hash: str | None = None
    new_source_hash: str | None = None
    count_changes: dict[str, tuple[int, int]] = field(default_factory=dict)
    file_hash_changes: dict[str, tuple[str | None, str | None]] = field(default_factory=dict)
    added_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)


@dataclass
class PackDiff:
    """Complete pack comparison result."""

    pack1_dir: str
    pack2_dir: str
    identical: bool = False
    crumb_diffs: list[CrumbDiff] = field(default_factory=list)
    file_diffs: list[FileDiff] = field(default_factory=list)
    proof_chain_diff: ProofChainDiff | None = None
    added_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return not self.identical


def parse_crumb_file(path: Path) -> CrumbFile | None:
    """Parse a CRUMB file into structured format."""
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    lines = content.splitlines()
    if not lines or lines[0] != "BEGIN CRUMB":
        return None

    # Parse headers
    headers: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i] != "---":
        line = lines[i].strip()
        if "=" in line:
            key, value = line.split("=", 1)
            headers[key] = value
        i += 1

    # Parse sections
    sections: dict[str, str] = {}
    current_section: str | None = None
    section_lines: list[str] = []

    i += 1  # Skip "---"
    while i < len(lines):
        line = lines[i]
        if line == "END CRUMB":
            if current_section:
                sections[current_section] = "\n".join(section_lines).strip()
            break

        # Check for section header
        section_match = re.match(r"^\[([^\]]+)\]$", line)
        if section_match:
            if current_section:
                sections[current_section] = "\n".join(section_lines).strip()
            current_section = section_match.group(1)
            section_lines = []
        else:
            section_lines.append(line)
        i += 1

    return CrumbFile(path=str(path), headers=headers, sections=sections)


def compare_crumb_files(path1: Path, path2: Path) -> CrumbDiff:
    """Compare two CRUMB files."""
    crumb1 = parse_crumb_file(path1)
    crumb2 = parse_crumb_file(path2)

    filename = path1.name if path1.exists() else path2.name

    if crumb1 is None and crumb2 is None:
        return CrumbDiff(path=filename, status="unchanged")

    if crumb1 is None:
        return CrumbDiff(path=filename, status="added")

    if crumb2 is None:
        return CrumbDiff(path=filename, status="removed")

    # Compare headers
    header_changes: dict[str, tuple[str | None, str | None]] = {}
    all_header_keys = set(crumb1.headers.keys()) | set(crumb2.headers.keys())
    for key in all_header_keys:
        old_val = crumb1.headers.get(key)
        new_val = crumb2.headers.get(key)
        if old_val != new_val:
            header_changes[key] = (old_val, new_val)

    # Compare sections
    section_changes: dict[str, tuple[str | None, str | None]] = {}
    added_sections: list[str] = []
    removed_sections: list[str] = []
    modified_sections: list[str] = []

    all_section_keys = set(crumb1.sections.keys()) | set(crumb2.sections.keys())
    for key in all_section_keys:
        old_content = crumb1.sections.get(key)
        new_content = crumb2.sections.get(key)

        if old_content is None and new_content is not None:
            added_sections.append(key)
            section_changes[key] = (None, new_content)
        elif old_content is not None and new_content is None:
            removed_sections.append(key)
            section_changes[key] = (old_content, None)
        elif old_content != new_content:
            modified_sections.append(key)
            section_changes[key] = (old_content, new_content)

    status = "unchanged"
    if header_changes or section_changes:
        status = "modified"

    return CrumbDiff(
        path=filename,
        status=status,
        header_changes=header_changes,
        section_changes=section_changes,
        added_sections=added_sections,
        removed_sections=removed_sections,
        modified_sections=modified_sections,
    )


def compare_proof_chains(path1: Path, path2: Path) -> ProofChainDiff:
    """Compare two proof chain JSON files."""
    proof1: dict[str, Any] | None = None
    proof2: dict[str, Any] | None = None

    if path1.exists():
        with contextlib.suppress(OSError, UnicodeDecodeError, json.JSONDecodeError):
            proof1 = json.loads(path1.read_text(encoding="utf-8"))

    if path2.exists():
        with contextlib.suppress(OSError, UnicodeDecodeError, json.JSONDecodeError):
            proof2 = json.loads(path2.read_text(encoding="utf-8"))

    if proof1 is None and proof2 is None:
        return ProofChainDiff(status="unchanged")

    if proof1 is None:
        return ProofChainDiff(status="added")

    if proof2 is None:
        return ProofChainDiff(status="removed")

    # Compare source hash
    source1 = proof1.get("source_report", {})
    source2 = proof2.get("source_report", {})
    old_source_hash = source1.get("sha256")
    new_source_hash = source2.get("sha256")
    source_hash_changed = old_source_hash != new_source_hash

    # Compare extracted counts
    counts1 = proof1.get("extracted_counts", {})
    counts2 = proof2.get("extracted_counts", {})
    count_changes: dict[str, tuple[int, int]] = {}
    all_count_keys = set(counts1.keys()) | set(counts2.keys())
    for key in all_count_keys:
        old_count = counts1.get(key, 0)
        new_count = counts2.get(key, 0)
        if old_count != new_count:
            count_changes[key] = (old_count, new_count)

    # Compare file hashes
    files1 = {f["path"]: f["sha256"] for f in proof1.get("generated_files", [])}
    files2 = {f["path"]: f["sha256"] for f in proof2.get("generated_files", [])}

    file_hash_changes: dict[str, tuple[str | None, str | None]] = {}
    added_files: list[str] = []
    removed_files: list[str] = []

    all_file_paths = set(files1.keys()) | set(files2.keys())
    for path in all_file_paths:
        old_hash = files1.get(path)
        new_hash = files2.get(path)

        if old_hash is None and new_hash is not None:
            added_files.append(path)
        elif old_hash is not None and new_hash is None:
            removed_files.append(path)
        elif old_hash != new_hash:
            file_hash_changes[path] = (old_hash, new_hash)

    status = "unchanged"
    if source_hash_changed or count_changes or file_hash_changes or added_files or removed_files:
        status = "modified"

    return ProofChainDiff(
        status=status,
        source_hash_changed=source_hash_changed,
        old_source_hash=old_source_hash,
        new_source_hash=new_source_hash,
        count_changes=count_changes,
        file_hash_changes=file_hash_changes,
        added_files=added_files,
        removed_files=removed_files,
    )


def compare_packs(pack_dir1: str | Path, pack_dir2: str | Path) -> PackDiff:
    """Compare two pack directories."""
    dir1 = Path(pack_dir1)
    dir2 = Path(pack_dir2)

    if not dir1.exists():
        raise FileNotFoundError(f"Pack directory not found: {dir1}")
    if not dir2.exists():
        raise FileNotFoundError(f"Pack directory not found: {dir2}")

    # Get all files in both directories
    files1 = {f.name for f in dir1.iterdir() if f.is_file()}
    files2 = {f.name for f in dir2.iterdir() if f.is_file()}

    added_files = sorted(files2 - files1)
    removed_files = sorted(files1 - files2)
    common_files = sorted(files1 & files2)

    crumb_diffs: list[CrumbDiff] = []
    file_diffs: list[FileDiff] = []
    proof_chain_diff: ProofChainDiff | None = None

    # Compare CRUMB files
    for filename in common_files:
        if filename.endswith(".crumb"):
            diff = compare_crumb_files(dir1 / filename, dir2 / filename)
            crumb_diffs.append(diff)
        elif filename == "08_proof_chain.json":
            proof_chain_diff = compare_proof_chains(dir1 / filename, dir2 / filename)
        else:
            # Compare other files (MD files)
            path1 = dir1 / filename
            path2 = dir2 / filename
            content1 = path1.read_text(encoding="utf-8")
            content2 = path2.read_text(encoding="utf-8")

            status = "unchanged" if content1 == content2 else "modified"
            file_diffs.append(
                FileDiff(
                    path=filename,
                    status=status,
                    old_size=len(content1),
                    new_size=len(content2),
                )
            )

    # Handle added/removed CRUMB files
    for filename in added_files:
        if filename.endswith(".crumb"):
            crumb_diffs.append(CrumbDiff(path=filename, status="added"))
        elif filename == "08_proof_chain.json":
            proof_chain_diff = compare_proof_chains(dir1 / filename, dir2 / filename)

    for filename in removed_files:
        if filename.endswith(".crumb"):
            crumb_diffs.append(CrumbDiff(path=filename, status="removed"))
        elif filename == "08_proof_chain.json":
            proof_chain_diff = compare_proof_chains(dir1 / filename, dir2 / filename)

    # Check if packs are identical
    identical = (
        not added_files
        and not removed_files
        and all(d.status == "unchanged" for d in crumb_diffs)
        and all(d.status == "unchanged" for d in file_diffs)
        and (proof_chain_diff is None or proof_chain_diff.status == "unchanged")
    )

    return PackDiff(
        pack1_dir=str(dir1),
        pack2_dir=str(dir2),
        identical=identical,
        crumb_diffs=crumb_diffs,
        file_diffs=file_diffs,
        proof_chain_diff=proof_chain_diff,
        added_files=added_files,
        removed_files=removed_files,
    )


def format_summary(diff: PackDiff, use_color: bool = True) -> str:
    """Format diff as high-level summary."""
    lines: list[str] = []

    def color(text: str, code: str) -> str:
        return f"{code}{text}{COLOR_RESET}" if use_color else text

    lines.append(f"Pack Diff: {diff.pack1_dir} -> {diff.pack2_dir}")
    lines.append("")

    if diff.identical:
        lines.append(color("✓ Packs are identical", COLOR_GREEN))
        return "\n".join(lines)

    lines.append(color("✗ Packs differ", COLOR_RED))
    lines.append("")

    # Summary counts
    added_count = len(diff.added_files)
    removed_count = len(diff.removed_files)
    modified_crumbs = sum(1 for d in diff.crumb_diffs if d.status == "modified")
    modified_files = sum(1 for d in diff.file_diffs if d.status == "modified")

    if added_count:
        lines.append(color(f"+ {added_count} file(s) added", COLOR_GREEN))
    if removed_count:
        lines.append(color(f"- {removed_count} file(s) removed", COLOR_RED))
    if modified_crumbs:
        lines.append(color(f"~ {modified_crumbs} CRUMB file(s) modified", COLOR_YELLOW))
    if modified_files:
        lines.append(color(f"~ {modified_files} other file(s) modified", COLOR_YELLOW))

    # Proof chain changes
    if diff.proof_chain_diff and diff.proof_chain_diff.status != "unchanged":
        lines.append("")
        lines.append(color("Proof Chain Changes:", COLOR_BLUE))
        pc = diff.proof_chain_diff

        if pc.source_hash_changed:
            lines.append(color("  • Source report hash changed", COLOR_YELLOW))

        if pc.count_changes:
            lines.append("  • Extracted counts changed:")
            for key, (old, new) in pc.count_changes.items():
                delta = new - old
                sign = "+" if delta > 0 else ""
                lines.append(f"    - {key}: {old} -> {new} ({sign}{delta})")

        if pc.file_hash_changes:
            lines.append(
                color(f"  • {len(pc.file_hash_changes)} file hash(es) changed", COLOR_YELLOW)
            )

    return "\n".join(lines)


def format_detailed(diff: PackDiff, use_color: bool = True) -> str:
    """Format diff with section-by-section comparison."""
    lines: list[str] = []

    def color(text: str, code: str) -> str:
        return f"{code}{text}{COLOR_RESET}" if use_color else text

    lines.append(f"Pack Diff (Detailed): {diff.pack1_dir} -> {diff.pack2_dir}")
    lines.append("=" * 80)
    lines.append("")

    if diff.identical:
        lines.append(color("✓ Packs are identical", COLOR_GREEN))
        return "\n".join(lines)

    # Added files
    if diff.added_files:
        lines.append(color("Added Files:", COLOR_GREEN))
        for filename in diff.added_files:
            lines.append(color(f"  + {filename}", COLOR_GREEN))
        lines.append("")

    # Removed files
    if diff.removed_files:
        lines.append(color("Removed Files:", COLOR_RED))
        for filename in diff.removed_files:
            lines.append(color(f"  - {filename}", COLOR_RED))
        lines.append("")

    # CRUMB file changes
    modified_crumbs = [d for d in diff.crumb_diffs if d.status == "modified"]
    if modified_crumbs:
        lines.append(color("Modified CRUMB Files:", COLOR_YELLOW))
        for crumb_diff in modified_crumbs:
            lines.append(f"  {crumb_diff.path}:")

            if crumb_diff.header_changes:
                lines.append("    Headers changed:")
                for key, (old, new) in crumb_diff.header_changes.items():
                    lines.append(f"      {key}: {old} -> {new}")

            if crumb_diff.added_sections:
                lines.append(color("    Sections added:", COLOR_GREEN))
                for section in crumb_diff.added_sections:
                    lines.append(color(f"      + [{section}]", COLOR_GREEN))

            if crumb_diff.removed_sections:
                lines.append(color("    Sections removed:", COLOR_RED))
                for section in crumb_diff.removed_sections:
                    lines.append(color(f"      - [{section}]", COLOR_RED))

            if crumb_diff.modified_sections:
                lines.append(color("    Sections modified:", COLOR_YELLOW))
                for section in crumb_diff.modified_sections:
                    lines.append(color(f"      ~ [{section}]", COLOR_YELLOW))
                    old_content, new_content = crumb_diff.section_changes[section]
                    if old_content and new_content:
                        # Show unified diff for modified sections
                        old_lines = old_content.splitlines(keepends=True)
                        new_lines = new_content.splitlines(keepends=True)
                        diff_lines = list(
                            difflib.unified_diff(
                                old_lines,
                                new_lines,
                                lineterm="",
                                n=1,
                            )
                        )
                        if len(diff_lines) > 4:  # Skip if only headers
                            for raw_line in diff_lines[2:]:  # Skip diff headers
                                stripped_line = raw_line.rstrip()
                                if stripped_line.startswith("+"):
                                    lines.append(color(f"        {stripped_line}", COLOR_GREEN))
                                elif stripped_line.startswith("-"):
                                    lines.append(color(f"        {stripped_line}", COLOR_RED))
                                elif not stripped_line.startswith("@@"):
                                    lines.append(f"        {stripped_line}")
            lines.append("")

    # Other file changes
    modified_files = [d for d in diff.file_diffs if d.status == "modified"]
    if modified_files:
        lines.append(color("Modified Files:", COLOR_YELLOW))
        for file_diff in modified_files:
            size_delta = file_diff.new_size - file_diff.old_size
            sign = "+" if size_delta > 0 else ""
            lines.append(f"  ~ {file_diff.path} ({sign}{size_delta} bytes)")
        lines.append("")

    # Proof chain details
    if diff.proof_chain_diff and diff.proof_chain_diff.status != "unchanged":
        lines.append(color("Proof Chain Changes:", COLOR_BLUE))
        pc = diff.proof_chain_diff

        if pc.source_hash_changed:
            lines.append(color("  Source report hash changed:", COLOR_YELLOW))
            lines.append(f"    - {pc.old_source_hash}")
            lines.append(f"    + {pc.new_source_hash}")

        if pc.count_changes:
            lines.append("  Extracted counts changed:")
            for key, (old_count, new_count) in pc.count_changes.items():
                delta = new_count - old_count
                sign = "+" if delta > 0 else ""
                lines.append(f"    {key}: {old_count} -> {new_count} ({sign}{delta})")

        if pc.file_hash_changes:
            lines.append(color("  File hashes changed:", COLOR_YELLOW))
            for path, (old_hash, new_hash) in pc.file_hash_changes.items():
                lines.append(f"    {path}:")
                lines.append(f"      - {old_hash}")
                lines.append(f"      + {new_hash}")

        if pc.added_files:
            lines.append(color("  Files added to proof chain:", COLOR_GREEN))
            for path in pc.added_files:
                lines.append(color(f"    + {path}", COLOR_GREEN))

        if pc.removed_files:
            lines.append(color("  Files removed from proof chain:", COLOR_RED))
            for path in pc.removed_files:
                lines.append(color(f"    - {path}", COLOR_RED))

    return "\n".join(lines)


def format_json(diff: PackDiff) -> str:
    """Format diff as JSON for machine consumption."""
    result = {
        "pack1": diff.pack1_dir,
        "pack2": diff.pack2_dir,
        "identical": diff.identical,
        "summary": {
            "added_files": len(diff.added_files),
            "removed_files": len(diff.removed_files),
            "modified_crumbs": sum(1 for d in diff.crumb_diffs if d.status == "modified"),
            "modified_files": sum(1 for d in diff.file_diffs if d.status == "modified"),
        },
        "added_files": diff.added_files,
        "removed_files": diff.removed_files,
        "crumb_diffs": [
            {
                "path": d.path,
                "status": d.status,
                "header_changes": {
                    k: {"old": v[0], "new": v[1]} for k, v in d.header_changes.items()
                },
                "added_sections": d.added_sections,
                "removed_sections": d.removed_sections,
                "modified_sections": d.modified_sections,
            }
            for d in diff.crumb_diffs
        ],
        "file_diffs": [
            {
                "path": d.path,
                "status": d.status,
                "old_size": d.old_size,
                "new_size": d.new_size,
                "size_delta": d.new_size - d.old_size,
            }
            for d in diff.file_diffs
        ],
    }

    if diff.proof_chain_diff:
        pc = diff.proof_chain_diff
        result["proof_chain"] = {
            "status": pc.status,
            "source_hash_changed": pc.source_hash_changed,
            "old_source_hash": pc.old_source_hash,
            "new_source_hash": pc.new_source_hash,
            "count_changes": {
                k: {"old": v[0], "new": v[1], "delta": v[1] - v[0]}
                for k, v in pc.count_changes.items()
            },
            "file_hash_changes": {
                k: {"old": v[0], "new": v[1]} for k, v in pc.file_hash_changes.items()
            },
            "added_files": pc.added_files,
            "removed_files": pc.removed_files,
        }

    return json.dumps(result, indent=2) + "\n"


# Made with Bob
