"""Auto-artifact collection for CrumbBob.

Scans Git repositories and collects relevant artifacts for pack generation.
"""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class Artifact:
    """Represents a collected artifact."""

    kind: Literal["git-diff", "test-output", "repo-notes"]
    filename: str
    content: str
    description: str


GIT_TIMEOUT_SECONDS = 30
GIT_EXECUTABLE = "git"


def _run_git_command(
    args: list[str], cwd: Path | None = None, timeout: int = GIT_TIMEOUT_SECONDS
) -> tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        # Git arguments are fixed by CrumbBob callers; shell execution is disabled.
        result = subprocess.run(  # nosec B603
            [GIT_EXECUTABLE, *args],
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""


def is_git_repository(path: Path | None = None) -> bool:
    """Check if the current directory is a Git repository."""
    success, _ = _run_git_command(["rev-parse", "--git-dir"], cwd=path)
    return success


def collect_git_diff_staged(cwd: Path | None = None) -> Artifact | None:
    """Collect staged changes (git diff --cached)."""
    success, output = _run_git_command(["diff", "--cached"], cwd=cwd)
    if success and output.strip():
        return Artifact(
            kind="git-diff",
            filename="git-diff-staged.patch",
            content=output,
            description="Staged changes (git diff --cached)",
        )
    return None


def collect_git_diff_unstaged(cwd: Path | None = None) -> Artifact | None:
    """Collect unstaged changes (git diff)."""
    success, output = _run_git_command(["diff"], cwd=cwd)
    if success and output.strip():
        return Artifact(
            kind="git-diff",
            filename="git-diff-unstaged.patch",
            content=output,
            description="Unstaged changes (git diff)",
        )
    return None


def collect_git_diff_combined(cwd: Path | None = None) -> Artifact | None:
    """Collect all changes (staged + unstaged)."""
    success, output = _run_git_command(["diff", "HEAD"], cwd=cwd)
    if success and output.strip():
        return Artifact(
            kind="git-diff",
            filename="git-diff.patch",
            content=output,
            description="All changes (git diff HEAD)",
        )
    return None


def collect_recent_test_output(cwd: Path | None = None) -> Artifact | None:
    """Look for recent test output files in common locations."""
    search_dir = cwd or Path.cwd()

    # Common test output file patterns
    patterns = [
        "test-output.txt",
        "test-results.txt",
        "pytest-output.txt",
        ".pytest_cache/v/cache/lastfailed",
        "test_output.log",
    ]

    for pattern in patterns:
        test_file = search_dir / pattern
        if test_file.exists() and test_file.is_file():
            try:
                content = test_file.read_text(encoding="utf-8")
                if content.strip():
                    return Artifact(
                        kind="test-output",
                        filename="test-output.txt",
                        content=content,
                        description=f"Test output from {test_file.name}",
                    )
            except (OSError, UnicodeDecodeError):
                continue

    return None


def collect_ci_logs(cwd: Path | None = None) -> Artifact | None:
    """Look for recent CI logs in common locations."""
    search_dir = cwd or Path.cwd()

    # Common CI log patterns
    patterns = [
        ".github/workflows/*.log",
        "ci-output.txt",
        "build.log",
        ".gitlab-ci.log",
    ]

    for pattern in patterns:
        if "*" in pattern:
            # Handle glob patterns
            parent = search_dir / Path(pattern).parent
            if parent.exists():
                for log_file in parent.glob(Path(pattern).name):
                    if log_file.is_file():
                        try:
                            content = log_file.read_text(encoding="utf-8")
                            if content.strip():
                                return Artifact(
                                    kind="test-output",
                                    filename="ci-output.txt",
                                    content=content,
                                    description=f"CI logs from {log_file.name}",
                                )
                        except (OSError, UnicodeDecodeError):
                            continue
        else:
            log_file = search_dir / pattern
            if log_file.exists() and log_file.is_file():
                try:
                    content = log_file.read_text(encoding="utf-8")
                    if content.strip():
                        return Artifact(
                            kind="test-output",
                            filename="ci-output.txt",
                            content=content,
                            description=f"CI logs from {log_file.name}",
                        )
                except (OSError, UnicodeDecodeError):
                    continue

    return None


def discover_artifacts(cwd: Path | None = None) -> list[Artifact]:
    """Discover all available artifacts in the current directory."""
    artifacts: list[Artifact] = []

    # Check if we're in a Git repository
    if not is_git_repository(cwd):
        print("Warning: Not a Git repository. Git diff collection skipped.", file=sys.stderr)
    else:
        # Collect Git diffs
        if artifact := collect_git_diff_staged(cwd):
            artifacts.append(artifact)
        if artifact := collect_git_diff_unstaged(cwd):
            artifacts.append(artifact)
        if artifact := collect_git_diff_combined(cwd):
            artifacts.append(artifact)

    # Collect test outputs
    if artifact := collect_recent_test_output(cwd):
        artifacts.append(artifact)

    # Collect CI logs
    if artifact := collect_ci_logs(cwd):
        artifacts.append(artifact)

    return artifacts


def prompt_user_selection(artifacts: list[Artifact]) -> list[Artifact]:
    """Prompt user to select which artifacts to include."""
    if not artifacts:
        return []

    print("\nDiscovered artifacts:")
    for i, artifact in enumerate(artifacts, 1):
        lines = len(artifact.content.splitlines())
        print(f"{i}. {artifact.description} ({lines} lines)")

    print("\nEnter artifact numbers to include (comma-separated, or 'all'):")
    print("Example: 1,3 or all")

    try:
        selection = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nSelection cancelled.")
        return []

    if selection == "all":
        return artifacts

    if not selection:
        return []

    try:
        indices = [int(x.strip()) - 1 for x in selection.split(",")]
        return [artifacts[i] for i in indices if 0 <= i < len(artifacts)]
    except (ValueError, IndexError):
        print("Invalid selection. No artifacts selected.")
        return []


def create_input_directory(
    output_dir: Path,
    bob_report_path: Path | None = None,
    artifacts: list[Artifact] | None = None,
) -> Path:
    """Create input directory structure with bob-report.md and artifacts.

    Args:
        output_dir: Directory to create the input structure in
        bob_report_path: Optional path to existing bob-report.md to copy
        artifacts: Optional list of artifacts to write

    Returns:
        Path to the created input directory
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy or create bob-report.md
    bob_report_dest = output_dir / "bob-report.md"
    if bob_report_path and bob_report_path.exists():
        bob_report_dest.write_text(
            bob_report_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    elif not bob_report_dest.exists():
        # Create a placeholder
        bob_report_dest.write_text(
            "# Bob Report\n\nPlease replace this with your actual Bob report.\n",
            encoding="utf-8",
        )

    # Write artifacts
    if artifacts:
        for artifact in artifacts:
            artifact_path = output_dir / artifact.filename
            artifact_path.write_text(artifact.content, encoding="utf-8")

    return output_dir


def auto_collect(
    bob_report_path: Path | None = None,
    input_dir: Path | None = None,
    cwd: Path | None = None,
    interactive: bool = True,
) -> tuple[Path, list[Artifact]]:
    """Auto-collect artifacts and create input directory.

    Args:
        bob_report_path: Optional path to bob-report.md
        input_dir: Optional input directory path (default: ./crumdbob-input)
        cwd: Optional working directory for artifact discovery
        interactive: Whether to prompt user for artifact selection

    Returns:
        Tuple of (input_directory_path, selected_artifacts)
    """
    # Discover artifacts
    artifacts = discover_artifacts(cwd)

    # Select artifacts
    selected = prompt_user_selection(artifacts) if interactive and artifacts else artifacts

    # Create input directory
    if input_dir is None:
        input_dir = Path.cwd() / "crumdbob-input"

    created_dir = create_input_directory(input_dir, bob_report_path, selected)

    return created_dir, selected


# Made with Bob
