"""Tests for the watcher module."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crumdbob.watcher import (
    WATCHDOG_AVAILABLE,
    PackRegenerationHandler,
    watch_directory,
)


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
class TestPackRegenerationHandler:
    """Tests for PackRegenerationHandler."""

    def test_init(self):
        """Test handler initialization."""
        input_dir = Path("/tmp/input")
        output_dir = Path("/tmp/output")
        callback = MagicMock()

        handler = PackRegenerationHandler(
            input_dir,
            output_dir,
            callback,
            debounce_seconds=1.0,
        )

        assert handler.input_dir == input_dir
        assert handler.output_dir == output_dir
        assert handler.regenerate_callback == callback
        assert handler.debounce_seconds == 1.0
        assert handler.last_change_time is None
        assert not handler.pending_regeneration

    def test_should_process_event_bob_report(self):
        """Test that bob-report.md changes are processed."""
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            MagicMock(),
        )

        # Mock event
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/input/bob-report.md"

        assert handler._should_process_event(event)

    def test_should_process_event_git_diff(self):
        """Test that git-diff.patch changes are processed."""
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            MagicMock(),
        )

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/input/git-diff.patch"

        assert handler._should_process_event(event)

    def test_should_process_event_ignore_directory(self):
        """Test that directory events are ignored."""
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            MagicMock(),
        )

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/tmp/input/subdir"

        assert not handler._should_process_event(event)

    def test_should_process_event_ignore_unrelated_file(self):
        """Test that unrelated files are ignored."""
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            MagicMock(),
        )

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/tmp/input/random-file.txt"

        assert not handler._should_process_event(event)

    def test_schedule_regeneration(self):
        """Test that regeneration is scheduled on file change."""
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            MagicMock(),
        )

        handler._schedule_regeneration("/tmp/input/bob-report.md", "modified")

        assert handler.pending_regeneration
        assert handler.last_change_time is not None

    def test_check_and_regenerate_no_pending(self):
        """Test that regeneration doesn't happen when not pending."""
        callback = MagicMock()
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            callback,
        )

        result = handler.check_and_regenerate()

        assert not result
        callback.assert_not_called()

    def test_check_and_regenerate_debounce_not_elapsed(self):
        """Test that regeneration waits for debounce period."""
        callback = MagicMock()
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            callback,
            debounce_seconds=10.0,  # Long debounce
        )

        handler._schedule_regeneration("/tmp/input/bob-report.md", "modified")
        result = handler.check_and_regenerate()

        assert not result
        callback.assert_not_called()

    def test_check_and_regenerate_success(self):
        """Test successful regeneration after debounce."""
        callback = MagicMock(return_value=[Path("/tmp/output/file1.crumb")])
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            callback,
            debounce_seconds=0.1,  # Short debounce
        )

        handler._schedule_regeneration("/tmp/input/bob-report.md", "modified")
        time.sleep(0.2)  # Wait for debounce
        result = handler.check_and_regenerate()

        assert result
        callback.assert_called_once_with(Path("/tmp/input"), Path("/tmp/output"))
        assert not handler.pending_regeneration

    def test_check_and_regenerate_error_handling(self):
        """Test that errors during regeneration are handled."""
        callback = MagicMock(side_effect=Exception("Test error"))
        handler = PackRegenerationHandler(
            Path("/tmp/input"),
            Path("/tmp/output"),
            callback,
            debounce_seconds=0.1,
        )

        handler._schedule_regeneration("/tmp/input/bob-report.md", "modified")
        time.sleep(0.2)
        result = handler.check_and_regenerate()

        assert not result
        callback.assert_called_once()


def test_watch_directory_no_watchdog():
    """Test watch_directory when watchdog is not available."""
    with patch("crumdbob.watcher.WATCHDOG_AVAILABLE", False):
        result = watch_directory(
            Path("/tmp/input"),
            Path("/tmp/output"),
            MagicMock(),
        )

        assert result == 1


def test_watch_directory_missing_input():
    """Test watch_directory with missing input directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / "nonexistent"
        output_dir = Path(tmpdir) / "output"

        result = watch_directory(input_dir, output_dir, MagicMock())

        assert result == 1


def test_watch_directory_missing_bob_report():
    """Test watch_directory with missing bob-report.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / "input"
        input_dir.mkdir()
        output_dir = Path(tmpdir) / "output"

        result = watch_directory(input_dir, output_dir, MagicMock())

        assert result == 1


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_watch_directory_initial_generation_error():
    """Test watch_directory when initial generation fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / "input"
        input_dir.mkdir()
        (input_dir / "bob-report.md").write_text("# Test", encoding="utf-8")
        output_dir = Path(tmpdir) / "output"

        callback = MagicMock(side_effect=Exception("Generation failed"))

        result = watch_directory(input_dir, output_dir, callback)

        assert result == 1


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
@patch("crumdbob.watcher.Observer")
def test_watch_directory_success(mock_observer_class):
    """Test successful watch_directory setup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / "input"
        input_dir.mkdir()
        (input_dir / "bob-report.md").write_text("# Test", encoding="utf-8")
        output_dir = Path(tmpdir) / "output"

        callback = MagicMock(return_value=[Path(output_dir / "file.crumb")])

        # Mock observer
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        # Simulate KeyboardInterrupt on the first watch-loop iteration.
        # We patch the watcher's bound `time.sleep` (not the global
        # `time.sleep`) so the side_effect itself doesn't recurse.
        def side_effect(*args, **kwargs):
            raise KeyboardInterrupt()

        with patch("crumdbob.watcher.time.sleep", side_effect=side_effect):
            result = watch_directory(input_dir, output_dir, callback, debounce_seconds=0.5)

        assert result == 0
        mock_observer.start.assert_called_once()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()


def test_format_time():
    """Test time formatting."""
    handler = PackRegenerationHandler(
        Path("/tmp/input"),
        Path("/tmp/output"),
        MagicMock(),
    )

    formatted = handler._format_time()

    # Should be in HH:MM:SS format
    assert len(formatted) == 8
    assert formatted.count(":") == 2


# Made with Bob
