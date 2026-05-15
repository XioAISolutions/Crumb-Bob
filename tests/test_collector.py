"""Tests for the collector module."""
from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from crumdbob.collector import (
    Artifact,
    auto_collect,
    collect_git_diff_combined,
    collect_git_diff_staged,
    collect_git_diff_unstaged,
    create_input_directory,
    discover_artifacts,
    is_git_repository,
)


def test_artifact_dataclass():
    """Test Artifact dataclass creation."""
    artifact = Artifact(
        kind="git-diff",
        filename="test.patch",
        content="diff content",
        description="Test diff",
    )
    assert artifact.kind == "git-diff"
    assert artifact.filename == "test.patch"
    assert artifact.content == "diff content"
    assert artifact.description == "Test diff"


def test_is_git_repository_false():
    """Test is_git_repository returns False for non-git directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert not is_git_repository(Path(tmpdir))


def test_collect_git_diff_no_repo():
    """Test git diff collection returns None when not in a git repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = collect_git_diff_staged(Path(tmpdir))
        assert result is None


@patch("crumdbob.collector._run_git_command")
def test_collect_git_diff_staged_success(mock_run):
    """Test successful staged diff collection."""
    mock_run.return_value = (True, "diff --git a/file.txt b/file.txt\n+new line")
    
    result = collect_git_diff_staged()
    
    assert result is not None
    assert result.kind == "git-diff"
    assert result.filename == "git-diff-staged.patch"
    assert "new line" in result.content
    assert "Staged changes" in result.description


@patch("crumdbob.collector._run_git_command")
def test_collect_git_diff_staged_empty(mock_run):
    """Test staged diff collection returns None when no changes."""
    mock_run.return_value = (True, "")
    
    result = collect_git_diff_staged()
    
    assert result is None


@patch("crumdbob.collector._run_git_command")
def test_collect_git_diff_unstaged_success(mock_run):
    """Test successful unstaged diff collection."""
    mock_run.return_value = (True, "diff --git a/file.txt b/file.txt\n-old line")
    
    result = collect_git_diff_unstaged()
    
    assert result is not None
    assert result.kind == "git-diff"
    assert result.filename == "git-diff-unstaged.patch"
    assert "old line" in result.content
    assert "Unstaged changes" in result.description


@patch("crumdbob.collector._run_git_command")
def test_collect_git_diff_combined_success(mock_run):
    """Test successful combined diff collection."""
    mock_run.return_value = (True, "diff --git a/file.txt b/file.txt\n+combined")
    
    result = collect_git_diff_combined()
    
    assert result is not None
    assert result.kind == "git-diff"
    assert result.filename == "git-diff.patch"
    assert "combined" in result.content
    assert "All changes" in result.description


def test_collect_recent_test_output():
    """Test test output collection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a test output file
        test_file = tmppath / "test-output.txt"
        test_file.write_text("Test passed\nAll tests OK", encoding="utf-8")
        
        result = discover_artifacts(tmppath)
        
        # Should find the test output
        test_artifacts = [a for a in result if a.kind == "test-output"]
        assert len(test_artifacts) > 0
        assert "Test passed" in test_artifacts[0].content


def test_create_input_directory_basic():
    """Test basic input directory creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "input"
        
        result = create_input_directory(output_dir)
        
        assert result == output_dir
        assert output_dir.exists()
        assert (output_dir / "bob-report.md").exists()


def test_create_input_directory_with_report():
    """Test input directory creation with existing bob-report.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a bob report
        bob_report = tmppath / "bob-report.md"
        bob_report.write_text("# My Report\n\nContent here", encoding="utf-8")
        
        output_dir = tmppath / "input"
        result = create_input_directory(output_dir, bob_report_path=bob_report)
        
        assert result == output_dir
        assert (output_dir / "bob-report.md").exists()
        content = (output_dir / "bob-report.md").read_text(encoding="utf-8")
        assert "My Report" in content


def test_create_input_directory_with_artifacts():
    """Test input directory creation with artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "input"
        
        artifacts = [
            Artifact(
                kind="git-diff",
                filename="test.patch",
                content="diff content",
                description="Test",
            ),
        ]
        
        result = create_input_directory(output_dir, artifacts=artifacts)
        
        assert result == output_dir
        assert (output_dir / "test.patch").exists()
        content = (output_dir / "test.patch").read_text(encoding="utf-8")
        assert content == "diff content"


@patch("crumdbob.collector.discover_artifacts")
@patch("crumdbob.collector.prompt_user_selection")
def test_auto_collect_interactive(mock_prompt, mock_discover):
    """Test auto_collect in interactive mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Mock discovered artifacts
        mock_artifacts = [
            Artifact(
                kind="git-diff",
                filename="test.patch",
                content="diff",
                description="Test diff",
            ),
        ]
        mock_discover.return_value = mock_artifacts
        mock_prompt.return_value = mock_artifacts
        
        input_dir = tmppath / "input"
        created_dir, selected = auto_collect(
            input_dir=input_dir,
            interactive=True,
        )
        
        assert created_dir == input_dir
        assert len(selected) == 1
        assert selected[0].filename == "test.patch"
        mock_prompt.assert_called_once()


@patch("crumdbob.collector.discover_artifacts")
def test_auto_collect_non_interactive(mock_discover):
    """Test auto_collect in non-interactive mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Mock discovered artifacts
        mock_artifacts = [
            Artifact(
                kind="git-diff",
                filename="test.patch",
                content="diff",
                description="Test diff",
            ),
        ]
        mock_discover.return_value = mock_artifacts
        
        input_dir = tmppath / "input"
        created_dir, selected = auto_collect(
            input_dir=input_dir,
            interactive=False,
        )
        
        assert created_dir == input_dir
        assert len(selected) == 1
        assert selected[0].filename == "test.patch"


def test_discover_artifacts_empty_directory():
    """Test artifact discovery in empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = discover_artifacts(Path(tmpdir))
        
        # Should return empty list or only non-git artifacts
        assert isinstance(result, list)

# Made with Bob
