"""Rich Terminal UI for CrumbBob.

This module provides beautiful, professional terminal output using the rich library.
All functions gracefully fallback to plain text if rich is not available.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

# Try to import rich, but gracefully fallback if not available
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.tree import Tree
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class CrumbBobUI:
    """Rich terminal UI for CrumbBob with graceful fallback."""

    def __init__(self, use_rich: bool = True):
        """Initialize UI.

        Args:
            use_rich: Whether to use rich library (if available)
        """
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
            self.error_console = Console(stderr=True)
        else:
            self.console = None
            self.error_console = None

    def print(self, *args, **kwargs):
        """Print with rich or fallback to standard print."""
        if self.use_rich and self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args, **kwargs)

    def print_error(self, message: str):
        """Print error message."""
        if self.use_rich and self.error_console:
            self.error_console.print(f"[red]✗ {message}[/red]")
        else:
            print(f"✗ {message}", file=sys.stderr)

    def print_success(self, message: str):
        """Print success message."""
        if self.use_rich and self.console:
            self.console.print(f"[green]✓ {message}[/green]")
        else:
            print(f"✓ {message}")

    def print_warning(self, message: str):
        """Print warning message."""
        if self.use_rich and self.console:
            self.console.print(f"[yellow]⚠ {message}[/yellow]")
        else:
            print(f"⚠ {message}")

    def print_info(self, message: str):
        """Print info message."""
        if self.use_rich and self.console:
            self.console.print(f"[blue]ℹ {message}[/blue]")
        else:
            print(f"ℹ {message}")


def display_pack_summary(pack_dir: Path, files: list[Path], session_id: Optional[int] = None):
    """Display beautiful pack generation summary.

    Args:
        pack_dir: Path to pack directory
        files: List of generated files
        session_id: Optional database session ID
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        # Create a panel with pack info
        content = f"[cyan]Pack Directory:[/cyan] {pack_dir}\n"
        content += f"[cyan]Files Generated:[/cyan] {len(files)}\n"
        if session_id:
            content += f"[cyan]Session ID:[/cyan] {session_id}\n"

        panel = Panel(
            content,
            title="[bold green]✓ Pack Generated Successfully[/bold green]",
            border_style="green",
            box=box.ROUNDED
        )
        ui.console.print(panel)

        # Create a tree of files
        tree = Tree(f"📦 [bold]{pack_dir.name}[/bold]", guide_style="bold bright_blue")
        for file in sorted(files):
            if file.suffix == ".crumb":
                tree.add(f"📄 [cyan]{file.name}[/cyan]")
            elif file.suffix == ".md":
                tree.add(f"📝 [yellow]{file.name}[/yellow]")
            elif file.suffix == ".json":
                tree.add(f"📊 [magenta]{file.name}[/magenta]")
            else:
                tree.add(f"📁 {file.name}")

        ui.console.print(tree)
    else:
        # Fallback to plain text
        print("\n✓ Pack Generated Successfully")
        print(f"Pack Directory: {pack_dir}")
        print(f"Files Generated: {len(files)}")
        if session_id:
            print(f"Session ID: {session_id}")
        print("\nGenerated files:")
        for file in sorted(files):
            print(f"  - {file.name}")


def display_validation_results(report: Any):
    """Display color-coded validation results.

    Args:
        report: Validation report object
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        if report.ok:
            panel = Panel(
                f"[green]All {len(report.documents)} CRUMB file(s) are valid[/green]",
                title="[bold green]✓ Validation Passed[/bold green]",
                border_style="green",
                box=box.ROUNDED
            )
            ui.console.print(panel)
        else:
            # Create error table
            table = Table(title="Validation Errors", box=box.ROUNDED, border_style="red")
            table.add_column("File", style="cyan")
            table.add_column("Error", style="red")

            for error in report.errors:
                error_str = error.format()
                parts = error_str.split(":", 1)
                if len(parts) == 2:
                    table.add_row(parts[0], parts[1].strip())
                else:
                    table.add_row("", error_str)

            ui.console.print(table)
            ui.print_error(f"Validation failed: {len(report.errors)} error(s)")
    else:
        # Fallback to plain text
        if report.ok:
            print(f"✓ OK: {len(report.documents)} CRUMB file(s) valid")
        else:
            for error in report.errors:
                print(error.format(), file=sys.stderr)
            print(f"✗ FAILED: {len(report.errors)} validation error(s)", file=sys.stderr)


def display_session_info(session: Any, files: list[Any], risks: list[Any], tasks: list[Any]):
    """Display rich session information.

    Args:
        session: Session object
        files: List of session files
        risks: List of session risks
        tasks: List of session tasks
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        # Session header panel
        header = f"[cyan]ID:[/cyan] {session.id}\n"
        header += f"[cyan]Name:[/cyan] {session.session_name or '(unnamed)'}\n"
        header += f"[cyan]Timestamp:[/cyan] {session.timestamp}\n"
        if session.git_branch:
            header += f"[cyan]Branch:[/cyan] {session.git_branch}\n"
        if session.git_commit:
            header += f"[cyan]Commit:[/cyan] {session.git_commit[:8]}\n"
        if session.git_author:
            header += f"[cyan]Author:[/cyan] {session.git_author}\n"

        panel = Panel(header, title="[bold]Session Details[/bold]", border_style="blue", box=box.ROUNDED)
        ui.console.print(panel)

        # Statistics table
        stats_table = Table(title="Statistics", box=box.SIMPLE)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Count", justify="right", style="yellow")
        stats_table.add_row("Files", str(len(files)))
        stats_table.add_row("Commands", str(session.command_count))
        stats_table.add_row("Risks", str(len(risks)))
        stats_table.add_row("Tasks", str(len(tasks)))
        ui.console.print(stats_table)

        # Files table
        if files:
            files_table = Table(title="Files", box=box.ROUNDED, show_lines=False)
            files_table.add_column("Path", style="cyan")
            files_table.add_column("Details", justify="right", style="yellow")
            for file in files[:10]:
                path = getattr(file, "file_path", getattr(file, "path", ""))
                size_bytes = getattr(file, "size_bytes", None)
                detail = f"{size_bytes:,} bytes" if size_bytes is not None else f"{getattr(file, 'mention_count', 1)}x"
                files_table.add_row(path, detail)
            if len(files) > 10:
                files_table.add_row(f"... and {len(files) - 10} more", "")
            ui.console.print(files_table)

        # Risks table
        if risks:
            risks_table = Table(title="Risks", box=box.ROUNDED)
            risks_table.add_column("Status", style="cyan")
            risks_table.add_column("Description", style="yellow")
            for risk in risks[:5]:
                status_color = "red" if risk.status == "open" else "green"
                risks_table.add_row(
                    f"[{status_color}]{risk.status}[/{status_color}]",
                    risk.description[:60]
                )
            if len(risks) > 5:
                risks_table.add_row("", f"... and {len(risks) - 5} more")
            ui.console.print(risks_table)
    else:
        # Fallback to plain text
        print(f"\nSession #{session.id}")
        print(f"Name: {session.session_name or '(unnamed)'}")
        print(f"Timestamp: {session.timestamp}")
        if session.git_branch:
            print(f"Branch: {session.git_branch}")
        if session.git_commit:
            print(f"Commit: {session.git_commit[:8]}")

        print("\nStatistics:")
        print(f"  Files: {len(files)}")
        print(f"  Commands: {session.command_count}")
        print(f"  Risks: {len(risks)}")
        print(f"  Tasks: {len(tasks)}")

        if files:
            print(f"\nFiles ({len(files)}):")
            for file in files[:10]:
                path = getattr(file, "file_path", getattr(file, "path", ""))
                print(f"  - {path}")
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more")


def display_sessions_table(sessions: list[Any]):
    """Display sessions in a beautiful table.

    Args:
        sessions: List of session objects
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        table = Table(title="CrumbBob Sessions", box=box.ROUNDED, show_lines=False)
        table.add_column("ID", style="cyan", no_wrap=True, justify="right")
        table.add_column("Timestamp", style="blue")
        table.add_column("Name", style="magenta")
        table.add_column("Branch", style="green")
        table.add_column("Files", justify="right", style="yellow")
        table.add_column("Risks", justify="right", style="red")

        for session in sessions:
            table.add_row(
                str(session.id),
                session.timestamp[:19],
                session.session_name or "—",
                session.git_branch or "—",
                str(session.file_count),
                str(session.risk_count)
            )

        ui.console.print(table)
        ui.print_info(f"Found {len(sessions)} session(s)")
    else:
        # Fallback to plain text
        print(f"Found {len(sessions)} session(s):\n")
        print(f"{'ID':<6} {'Timestamp':<20} {'Name':<25} {'Branch':<20} {'Files':<6} {'Risks':<6}")
        print("-" * 100)
        for session in sessions:
            name = session.session_name or "(unnamed)"
            branch = session.git_branch or "-"
            print(f"{session.id:<6} {session.timestamp[:19]:<20} {name[:24]:<25} {branch[:19]:<20} {session.file_count:<6} {session.risk_count:<6}")


def display_insights(insights: list[Any]):
    """Display insights with icons and colors.

    Args:
        insights: List of insight objects
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        for insight in insights:
            severity_colors = {
                'low': 'blue',
                'medium': 'yellow',
                'high': 'orange3',
                'critical': 'red'
            }
            severity_icons = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴'
            }

            color = severity_colors.get(insight.severity, 'white')
            icon = severity_icons.get(insight.severity, '⚪')

            content = f"{insight.description}\n\n"
            content += f"[cyan]Type:[/cyan] {insight.insight_type}\n"
            content += f"[cyan]Confidence:[/cyan] {insight.confidence:.0%}\n"

            if hasattr(insight, 'recommendations') and insight.recommendations:
                content += "\n[bold]Recommendations:[/bold]\n"
                for rec in insight.recommendations[:3]:
                    content += f"  • {rec}\n"

            panel = Panel(
                content,
                title=f"{icon} [{color}]{insight.title}[/{color}]",
                subtitle=f"Created: {insight.created_at[:19]}",
                border_style=color,
                box=box.ROUNDED
            )
            ui.console.print(panel)
    else:
        # Fallback to plain text
        for insight in insights:
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(insight.severity, "⚪")
            print(f"{severity_icon} [{insight.severity.upper()}] {insight.title}")
            print(f"   Type: {insight.insight_type}")
            print(f"   Confidence: {insight.confidence:.0%}")
            print(f"   Created: {insight.created_at[:19]}")
            if hasattr(insight, 'recommendations') and insight.recommendations:
                print("   Recommendations:")
                for rec in insight.recommendations[:3]:
                    print(f"     • {rec}")
            print()


def display_trends(stats: dict, hot_files: list[dict], recurring_risks: list[dict], commands: list[dict]):
    """Display trend visualization.

    Args:
        stats: Database statistics
        hot_files: List of hot files
        recurring_risks: List of recurring risks
        commands: List of command frequencies
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        # Stats panel
        stats_content = f"[cyan]Sessions recorded:[/cyan] {stats['session_count']}\n"
        stats_content += f"[cyan]Unique files seen:[/cyan] {stats['unique_files']}\n"
        stats_content += f"[cyan]Open risks:[/cyan] {stats['open_risks']}\n"
        stats_content += f"[cyan]Unique commands:[/cyan] {stats['unique_commands']}"

        panel = Panel(
            stats_content,
            title="[bold]📊 CrumbBob Memory Trends[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )
        ui.console.print(panel)

        # Hot files table
        if hot_files:
            table = Table(title="🔥 Hot Files", box=box.ROUNDED)
            table.add_column("Count", justify="right", style="yellow")
            table.add_column("Path", style="cyan")
            for f in hot_files[:15]:
                table.add_row(f"{f['session_count']}x", f['path'])
            ui.console.print(table)

        # Recurring risks table
        if recurring_risks:
            table = Table(title="⚠️  Recurring Risks", box=box.ROUNDED)
            table.add_column("Count", justify="right", style="yellow")
            table.add_column("Status", style="cyan")
            table.add_column("Description", style="red")
            for r in recurring_risks[:10]:
                status_color = "red" if r['status'] == "open" else "green"
                table.add_row(
                    f"{r['session_count']}x",
                    f"[{status_color}]{r['status']}[/{status_color}]",
                    r['description'][:60]
                )
            ui.console.print(table)

        # Commands table
        if commands:
            table = Table(title="💻 Top Commands", box=box.ROUNDED)
            table.add_column("Count", justify="right", style="yellow")
            table.add_column("Command", style="cyan")
            for c in commands[:10]:
                table.add_row(f"{c['total_mentions']}x", c['command'][:60])
            ui.console.print(table)
    else:
        # Fallback to plain text
        print("CrumbBob Memory Trends")
        print("=" * 50)
        print(f"Sessions recorded : {stats['session_count']}")
        print(f"Unique files seen  : {stats['unique_files']}")
        print(f"Open risks         : {stats['open_risks']}")
        print(f"Unique commands    : {stats['unique_commands']}")

        if hot_files:
            print("\nHot Files:")
            for f in hot_files[:15]:
                print(f"  {f['session_count']:>3}x  {f['path']}")

        if recurring_risks:
            print("\nRecurring Risks:")
            for r in recurring_risks[:10]:
                tag = f"[{r['status']}]"
                print(f"  {r['session_count']:>3}x  {tag:<12} {r['description'][:72]}")

        if commands:
            print("\nTop Commands:")
            for c in commands[:10]:
                print(f"  {c['total_mentions']:>3}x  {c['command'][:72]}")


def display_query_results(result: Any):
    """Display formatted query results in tables.

    Args:
        result: Query result object
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        # Query info panel
        panel = Panel(
            f"[cyan]Query:[/cyan] {result.explanation}\n[cyan]Results:[/cyan] {result.row_count} row(s)",
            title="[bold]🔍 Query Results[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )
        ui.console.print(panel)

        if result.row_count > 0 and result.results:
            # Create results table
            columns = list(result.results[0].keys())
            table = Table(box=box.ROUNDED, show_lines=False)

            for col in columns:
                table.add_column(str(col), style="cyan")

            for row in result.results[:50]:
                values = [str(row.get(col, ""))[:50] for col in columns]
                table.add_row(*values)

            ui.console.print(table)

            if result.row_count > 50:
                ui.print_info(f"... and {result.row_count - 50} more rows")
    else:
        # Fallback to plain text
        print(f"Query: {result.explanation}")
        print(f"Results: {result.row_count} row(s)\n")

        if result.row_count > 0 and result.results:
            columns = list(result.results[0].keys())
            header = " | ".join(str(col)[:20] for col in columns)
            print(header)
            print("-" * len(header))

            for row in result.results[:50]:
                values = [str(row.get(col, ""))[:20] for col in columns]
                print(" | ".join(values))

            if result.row_count > 50:
                print(f"\n... and {result.row_count - 50} more rows")


def display_patterns(patterns: list[Any]):
    """Display pattern detection results with highlighting.

    Args:
        patterns: List of pattern objects
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        # Group by type
        by_type: dict[str, list] = {}
        for pattern in patterns:
            by_type.setdefault(pattern.pattern_type, []).append(pattern)

        ui.print_success(f"Detected {len(patterns)} pattern(s)")

        for ptype, plist in sorted(by_type.items()):
            table = Table(
                title=f"{ptype.replace('_', ' ').title()} ({len(plist)})",
                box=box.ROUNDED
            )
            table.add_column("Severity", style="cyan")
            table.add_column("Description", style="yellow")
            table.add_column("Confidence", justify="right", style="green")
            table.add_column("Frequency", justify="right", style="magenta")

            for pattern in plist[:10]:
                severity_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                icon = severity_icons.get(pattern.severity, "⚪")

                table.add_row(
                    f"{icon} {pattern.severity}",
                    pattern.description[:60],
                    f"{pattern.confidence:.0%}",
                    str(pattern.frequency)
                )

            ui.console.print(table)

            if len(plist) > 10:
                ui.print_info(f"... and {len(plist) - 10} more {ptype} patterns")
    else:
        # Fallback to plain text
        print(f"✓ Detected {len(patterns)} pattern(s)\n")

        by_type: dict[str, list] = {}
        for pattern in patterns:
            by_type.setdefault(pattern.pattern_type, []).append(pattern)

        for ptype, plist in sorted(by_type.items()):
            print(f"\n{ptype.replace('_', ' ').title()} ({len(plist)}):")
            for pattern in plist[:5]:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(pattern.severity, "⚪")
                print(f"  {severity_icon} {pattern.description}")
                print(f"     Confidence: {pattern.confidence:.0%}, Frequency: {pattern.frequency}")
            if len(plist) > 5:
                print(f"  ... and {len(plist) - 5} more")


def display_predictions(prediction: Any, prediction_type: str):
    """Display prediction results with severity colors.

    Args:
        prediction: Prediction object
        prediction_type: Type of prediction (impact, risks, complexity, tests)
    """
    ui = CrumbBobUI()

    if ui.use_rich and ui.console:
        # Prediction header
        title_map = {
            "impact": "📊 Impact Prediction",
            "risks": "⚠️  Risk Prediction",
            "complexity": "🎯 Complexity Prediction",
            "tests": "🧪 Test Recommendations"
        }

        content = f"[cyan]Confidence:[/cyan] {prediction.confidence:.0%}\n"
        content += f"[cyan]Reasoning:[/cyan] {prediction.reasoning}"

        panel = Panel(
            content,
            title=f"[bold]{title_map.get(prediction_type, 'Prediction')}[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )
        ui.console.print(panel)

        # Display predictions based on type
        if prediction.predictions:
            if prediction_type == "impact":
                table = Table(title="Likely Affected Files", box=box.ROUNDED)
                table.add_column("File", style="cyan")
                table.add_column("Confidence", justify="right", style="yellow")
                table.add_column("Co-changes", justify="right", style="magenta")

                for pred in prediction.predictions[:10]:
                    table.add_row(
                        pred['file'],
                        f"{pred['confidence']:.0%}",
                        str(pred['co_changes'])
                    )
                ui.console.print(table)

            elif prediction_type == "risks":
                table = Table(title="Potential Risks", box=box.ROUNDED)
                table.add_column("Status", style="cyan")
                table.add_column("Risk", style="red")
                table.add_column("Frequency", justify="right", style="yellow")

                for pred in prediction.predictions[:10]:
                    status_color = "red" if pred['status'] == "open" else "green"
                    table.add_row(
                        f"[{status_color}]{pred['status']}[/{status_color}]",
                        pred['risk'][:60],
                        f"{pred['frequency']}x"
                    )
                ui.console.print(table)

            elif prediction_type == "tests":
                table = Table(title="Recommended Tests", box=box.ROUNDED)
                table.add_column("Test File", style="cyan")
                table.add_column("Reason", style="yellow")

                for pred in prediction.predictions:
                    table.add_row(pred['test_file'], pred['reason'])
                ui.console.print(table)
        else:
            ui.print_warning("No predictions available")
    else:
        # Fallback to plain text
        print(f"Confidence: {prediction.confidence:.0%}")
        print(f"Reasoning: {prediction.reasoning}\n")

        if prediction.predictions:
            if prediction_type == "impact":
                print("Likely to be affected:")
                for pred in prediction.predictions[:10]:
                    print(f"  • {pred['file']} (confidence: {pred['confidence']:.0%}, {pred['co_changes']} co-changes)")
            elif prediction_type == "risks":
                print("Potential risks based on similar past changes:")
                for pred in prediction.predictions[:10]:
                    print(f"  • [{pred['status']}] {pred['risk'][:80]}")
                    print(f"    Occurred {pred['frequency']}x in history")
            elif prediction_type == "tests":
                print("Recommended tests:")
                for pred in prediction.predictions:
                    print(f"  • {pred['test_file']}")
                    print(f"    Reason: {pred['reason']}")
        else:
            print("No predictions available.")


def create_progress_bar(description: str = "Processing..."):
    """Create a progress bar for long operations.

    Args:
        description: Description of the operation

    Returns:
        Progress context manager or None if rich not available
    """
    if RICH_AVAILABLE:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=Console()
        )
    return None


def show_spinner(description: str = "Working..."):
    """Show a spinner for indeterminate operations.

    Args:
        description: Description of the operation

    Returns:
        Progress context manager or None if rich not available
    """
    if RICH_AVAILABLE:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=Console()
        )
    return None

# Made with Bob
