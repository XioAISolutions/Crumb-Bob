"""Watch mode for CrumbBob.

Monitors input directory for changes and automatically regenerates packs.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore
    FileSystemEvent = None  # type: ignore


class PackRegenerationHandler(FileSystemEventHandler):
    """File system event handler for pack regeneration."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        regenerate_callback: Callable[[Path, Path], list[Path]],
        debounce_seconds: float = 2.0,
    ):
        """Initialize the handler.

        Args:
            input_dir: Directory to watch for changes
            output_dir: Directory where packs are generated
            regenerate_callback: Function to call for regeneration
            debounce_seconds: Seconds to wait after last change before regenerating
        """
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.regenerate_callback = regenerate_callback
        self.debounce_seconds = debounce_seconds
        self.last_change_time: float | None = None
        self.pending_regeneration = False

        # Files to watch
        self.watched_files = {
            "bob-report.md",
            "git-diff.patch",
            "git-diff-staged.patch",
            "git-diff-unstaged.patch",
            "test-output.txt",
            "ci-output.txt",
            "repo-notes.md",
        }

    def _should_process_event(self, event: FileSystemEvent) -> bool:
        """Check if the event should trigger regeneration."""
        if event.is_directory:
            return False

        # Get the relative path from input_dir
        try:
            event_path = Path(os.fsdecode(event.src_path))
            rel_path = event_path.relative_to(self.input_dir)
            filename = rel_path.name
        except (ValueError, AttributeError):
            return False

        # Only watch specific files
        return filename in self.watched_files

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if self._should_process_event(event):
            self._schedule_regeneration(os.fsdecode(event.src_path), "modified")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if self._should_process_event(event):
            self._schedule_regeneration(os.fsdecode(event.src_path), "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if self._should_process_event(event):
            self._schedule_regeneration(os.fsdecode(event.src_path), "deleted")

    def _schedule_regeneration(self, path: str, event_type: str) -> None:
        """Schedule a pack regeneration after debounce period."""
        self.last_change_time = time.time()
        self.pending_regeneration = True

        filename = Path(path).name
        print(f"[{self._format_time()}] Detected: {filename} ({event_type})")

    def check_and_regenerate(self) -> bool:
        """Check if regeneration should happen and execute it.

        Returns:
            True if regeneration was performed, False otherwise
        """
        if not self.pending_regeneration or self.last_change_time is None:
            return False

        # Check if debounce period has elapsed
        elapsed = time.time() - self.last_change_time
        if elapsed < self.debounce_seconds:
            return False

        # Perform regeneration
        self.pending_regeneration = False
        print(f"[{self._format_time()}] Regenerating pack...")

        try:
            written = self.regenerate_callback(self.input_dir, self.output_dir)
            print(f"[{self._format_time()}] ✓ Generated {len(written)} files")
            for path in written:
                print(f"  - {path.name}")
            return True
        except Exception as exc:
            # The watcher is a long-running daemon. If the user-supplied
            # regeneration callback raises ANYTHING (FileNotFoundError,
            # ParseError, even an assertion bug), the right behaviour is to
            # log and keep watching, not to crash the entire watch session.
            print(f"[{self._format_time()}] ✗ Regeneration error: {exc}", file=sys.stderr)
            return False

    @staticmethod
    def _format_time() -> str:
        """Format current time for display."""
        return time.strftime("%H:%M:%S")


def watch_directory(
    input_dir: Path,
    output_dir: Path,
    regenerate_callback: Callable[[Path, Path], list[Path]],
    debounce_seconds: float = 2.0,
) -> int:
    """Watch input directory and regenerate pack on changes.

    Args:
        input_dir: Directory to watch for changes
        output_dir: Directory where packs are generated
        regenerate_callback: Function to call for regeneration
        debounce_seconds: Seconds to wait after last change before regenerating

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not WATCHDOG_AVAILABLE:
        print("Error: watchdog package is required for watch mode.", file=sys.stderr)
        print("Install it with: pip install watchdog", file=sys.stderr)
        return 1

    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}", file=sys.stderr)
        return 1

    if not (input_dir / "bob-report.md").exists():
        print(f"Error: bob-report.md not found in {input_dir}", file=sys.stderr)
        return 1

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initial generation
    print(f"[{time.strftime('%H:%M:%S')}] Starting watch mode...")
    print(f"  Input:  {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Debounce: {debounce_seconds}s")
    print()

    try:
        written = regenerate_callback(input_dir, output_dir)
        print(f"[{time.strftime('%H:%M:%S')}] ✓ Initial generation complete ({len(written)} files)")
        print()
    except Exception as exc:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ Initial generation failed: {exc}", file=sys.stderr)
        return 1

    # Set up file system observer
    event_handler = PackRegenerationHandler(
        input_dir,
        output_dir,
        regenerate_callback,
        debounce_seconds,
    )

    observer = Observer()
    observer.schedule(event_handler, str(input_dir), recursive=False)
    observer.start()

    print(f"[{time.strftime('%H:%M:%S')}] Watching for changes... (Press Ctrl+C to stop)")
    print()

    try:
        while True:
            time.sleep(0.5)
            event_handler.check_and_regenerate()
    except KeyboardInterrupt:
        print()
        print(f"[{time.strftime('%H:%M:%S')}] Stopping watch mode...")
        observer.stop()

    observer.join()
    print(f"[{time.strftime('%H:%M:%S')}] Watch mode stopped.")
    return 0


# Made with Bob
