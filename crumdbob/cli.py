from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

from .collector import auto_collect
from .config import (
    DEFAULT_CONFIG,
    get_config_value,
    get_database_path,
    load_config,
    save_config,
    set_config_value,
    should_auto_record,
)
from .differ import compare_packs, format_detailed, format_json, format_summary
from .insights import create_insights_engine
from .llm import create_llm_analyzer
from .logging_config import configure_logging
from .memory import (
    MemoryDatabase,
    get_default_db_path,
    init_database,
    record_pack_to_db,
)
from .packer import read_pr_summary, read_replay_prompt, write_pack, write_pack_from_directory
from .parser import parse_bob_report
from .patterns import create_pattern_detector
from .predict import create_prediction_engine
from .query import create_query_engine
from .ui import (
    display_insights,
    display_pack_summary,
    display_patterns,
    display_query_results,
    display_sessions_table,
    display_trends,
    display_validation_results,
)
from .validator import dependency_edges, validate_target
from .watcher import watch_directory

EXPECTED_PACK_FILES = [
    "00_repo_genome.crumb",
    "01_session_flight_recorder.crumb",
    "02_next_task.crumb",
    "03_test_plan.crumb",
    "04_risk_register.crumb",
    "05_agent_passport.crumb",
    "06_replay_prompt.md",
    "07_pr_summary.md",
    "08_proof_chain.json",
]


def cmd_import(args: argparse.Namespace) -> int:
    written = write_pack(args.report, args.out)
    for path in written:
        print(path)
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    written = write_pack_from_directory(args.input_dir, args.out)

    # Auto-record to database if requested or configured
    session_id = None
    should_record = (hasattr(args, "record") and args.record) or should_auto_record()
    if should_record:
        db_path = Path(args.db) if hasattr(args, "db") and args.db else get_database_path()
        try:
            session_id = record_pack_to_db(
                pack_dir=args.out,
                db_path=db_path,
            )
        except Exception as exc:
            print(f"Warning: Failed to record to database: {exc}", file=sys.stderr)

    # Display beautiful pack summary
    display_pack_summary(args.out, written, session_id)

    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    report = parse_bob_report(args.report)
    verbose = getattr(args, "verbose", False)
    print(f"title: {report.title}")
    print(f"summary: {report.summary}")
    print(f"files: {len(report.files)}")
    print(f"commands: {len(report.commands)}")
    print(f"risks: {len(report.risks)}")
    print(f"tests: {len(report.tests)}")
    print(f"next_steps: {len(report.next_steps)}")
    if verbose:

        def _show(label: str, items: list[str]) -> None:
            if items:
                print(f"\n{label}:")
                for item in items:
                    print(f"  - {item}")

        _show("Files", report.files)
        _show("Commands", report.commands)
        _show("Risks", report.risks)
        _show("Tests", report.tests)
        _show("Next steps", report.next_steps)
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    sys.stdout.write(read_replay_prompt(args.pack_dir))
    return 0


def cmd_pr(args: argparse.Namespace) -> int:
    sys.stdout.write(read_pr_summary(args.pack_dir))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    report = validate_target(args.target)

    # Display beautiful validation results
    display_validation_results(report)

    return 0 if report.ok else 1


def _proof_source_present(pack_dir: Path) -> bool:
    proof_path = pack_dir / "08_proof_chain.json"
    if proof_path.exists():
        try:
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        source_report = proof.get("source_report", {}).get("path")
        if source_report and Path(source_report).exists():
            return True
    return (pack_dir.parent / "bob-report.md").exists()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _proof_hashes_current(pack_dir: Path) -> bool:
    proof_path = pack_dir / "08_proof_chain.json"
    if not proof_path.exists():
        return False
    try:
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    for item in proof.get("generated_files", []):
        path = pack_dir / item.get("path", "")
        if not path.is_file() or not item.get("sha256"):
            return False
        if _sha256_file(path) != item["sha256"]:
            return False

    source_report = proof.get("source_report", {})
    source_path = Path(source_report.get("path", ""))
    if not source_path.is_file() or not source_report.get("sha256"):
        return False
    return _sha256_file(source_path) == source_report["sha256"]


def cmd_doctor(args: argparse.Namespace) -> int:
    pack_dir = Path(args.pack_dir)
    validation = validate_target(pack_dir)
    present = [name for name in EXPECTED_PACK_FILES if (pack_dir / name).exists()]
    missing = [name for name in EXPECTED_PACK_FILES if name not in present]
    replay_present = (pack_dir / "06_replay_prompt.md").exists()
    pr_present = (pack_dir / "07_pr_summary.md").exists()
    proof_present = (pack_dir / "08_proof_chain.json").exists()
    source_present = _proof_source_present(pack_dir)
    proof_current = _proof_hashes_current(pack_dir)
    healthy = (
        not missing
        and validation.ok
        and replay_present
        and pr_present
        and proof_present
        and source_present
        and proof_current
    )

    print("CrumbBob Doctor")
    print(f"pack: {pack_dir}")
    print(f"files present: {len(present)}/{len(EXPECTED_PACK_FILES)}")
    print(f"CRUMBs valid: {'yes' if validation.ok else 'no'}")
    print(f"replay prompt present: {'yes' if replay_present else 'no'}")
    print(f"PR summary present: {'yes' if pr_present else 'no'}")
    print(f"proof chain present: {'yes' if proof_present else 'no'}")
    print(f"proof hashes current: {'yes' if proof_current else 'no'}")
    print(f"source report present: {'yes' if source_present else 'no'}")
    if missing:
        print("missing files:")
        for name in missing:
            print(f"- {name}")
    if validation.errors:
        print("validation errors:")
        for error in validation.errors:
            print(f"- {error.format()}")
    print(f"verdict: {'ready for judge walkthrough' if healthy else 'needs attention'}")
    return 0 if healthy else 1


def cmd_graph(args: argparse.Namespace) -> int:
    edges, report = dependency_edges(args.pack_dir)
    if report.errors:
        for error in report.errors:
            print(error.format(), file=sys.stderr)
        return 1
    if not edges:
        print("No dependency edges found.")
        return 0
    print("CrumbBob Dependency Graph")
    for source, target, kind in edges:
        print(f"{source} -> {target} [{kind}]")
    return 0


def cmd_init_bob_skill(args: argparse.Namespace) -> int:
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        """# CrumbBob

Use CrumbBob when an IBM Bob report needs to become replayable repository memory.

## Workflow

1. Place `bob-report.md` in a working directory.
2. Add optional `git-diff.patch`, `test-output.txt`, and `repo-notes.md`.
3. Run `crumdbob pack <input-dir> --out <pack-dir>`.
4. Run `crumdbob validate <pack-dir>` and `crumdbob doctor <pack-dir>`.
5. Load generated files in lexical order, then continue from `02_next_task.crumb`.
6. Check `08_proof_chain.json` before trusting or sharing generated output.

## IBM Bob CLI

When the local Bob CLI is available, hand the replay prompt back to Bob:

```bash
bob --chat-mode ask --hide-intermediary-output "$(crumdbob replay <pack-dir>)"
```

Use `--chat-mode code` only when the user explicitly wants Bob to edit the repo.

## Guardrails

- Treat the Bob report as evidence, not as a substitute for current repo verification.
- Run captured tests before marking the continuation complete.
- Regenerate the pack after changing source context or generated CRUMBs.
""",
        encoding="utf-8",
    )
    print(target)
    return 0


def cmd_auto_collect(args: argparse.Namespace) -> int:
    """Auto-collect artifacts and generate pack."""
    bob_report = args.report if hasattr(args, "report") and args.report else None
    input_dir = args.input_dir if hasattr(args, "input_dir") and args.input_dir else None
    output_dir = args.out

    # Auto-collect artifacts
    try:
        created_dir, selected = auto_collect(
            bob_report_path=bob_report,
            input_dir=input_dir,
            interactive=not args.no_interactive,
        )
    except Exception as exc:
        print(f"Error during artifact collection: {exc}", file=sys.stderr)
        return 1

    print(f"\nCreated input directory: {created_dir}")
    print(f"Collected {len(selected)} artifact(s)")

    # Generate pack
    print(f"\nGenerating pack to: {output_dir}")
    try:
        written = write_pack_from_directory(created_dir, output_dir)
        print(f"\nGenerated {len(written)} files:")
        for path in written:
            print(f"  - {path}")

        # Auto-record to database if requested or configured
        should_record = (hasattr(args, "record") and args.record) or should_auto_record()
        if should_record:
            db_path = Path(args.db) if hasattr(args, "db") and args.db else get_database_path()
            try:
                session_id = record_pack_to_db(
                    pack_dir=output_dir,
                    db_path=db_path,
                )
                print(f"✓ Recorded to database: Session #{session_id}")
            except Exception as exc:
                print(f"Warning: Failed to record to database: {exc}", file=sys.stderr)

        return 0
    except Exception as exc:
        print(f"Error generating pack: {exc}", file=sys.stderr)
        return 1


def cmd_watch(args: argparse.Namespace) -> int:
    """Watch input directory and regenerate pack on changes."""
    input_dir = Path(args.input_dir)
    output_dir = Path(args.out)
    debounce = args.debounce

    return watch_directory(
        input_dir,
        output_dir,
        write_pack_from_directory,
        debounce_seconds=debounce,
    )


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare two pack directories and show differences."""
    try:
        diff = compare_packs(args.pack_dir_1, args.pack_dir_2)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error comparing packs: {exc}", file=sys.stderr)
        return 1

    # Determine output format
    format_type = args.format if hasattr(args, "format") else "summary"
    use_color = not args.no_color if hasattr(args, "no_color") else True

    if format_type == "json":
        output = format_json(diff)
    elif format_type == "detailed":
        output = format_detailed(diff, use_color=use_color)
    else:  # summary
        output = format_summary(diff, use_color=use_color)

    sys.stdout.write(output)

    # Exit code: 0 if identical, 1 if different
    return 0 if diff.identical else 1


def cmd_init_db(args: argparse.Namespace) -> int:
    """Initialize memory database."""
    db_path = Path(args.path) if args.path else get_default_db_path()

    try:
        db = init_database(db_path)
        db.close()
        print(f"✓ Database initialized: {db_path}")
        print("✓ Schema version: 1")
        print("✓ Ready to record sessions")
        return 0
    except Exception as exc:
        print(f"Error initializing database: {exc}", file=sys.stderr)
        return 1


def cmd_record(args: argparse.Namespace) -> int:
    """Record a pack directory to the database."""
    pack_dir = Path(args.pack_dir)
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not pack_dir.exists():
        print(f"Error: Pack directory not found: {pack_dir}", file=sys.stderr)
        return 1

    try:
        session_id = record_pack_to_db(
            pack_dir=pack_dir,
            db_path=db_path,
            session_name=args.session_name,
        )

        # Get session details
        with MemoryDatabase(db_path) as db:
            session = db.get_session(session_id)
            if session:
                print(f"✓ Session recorded: #{session_id}")
                print(f"  Timestamp: {session.timestamp}")
                if session.session_name:
                    print(f"  Name: {session.session_name}")
                if session.git_branch:
                    print(f"  Branch: {session.git_branch}")
                if session.git_commit:
                    print(f"  Commit: {session.git_commit}")
                print(f"  Files: {session.file_count}")
                print(f"  Commands: {session.command_count}")
                print(f"  Risks: {session.risk_count}")
                print(f"  Tasks: {session.task_count}")

        return 0
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error recording session: {exc}", file=sys.stderr)
        return 1


def cmd_list_sessions(args: argparse.Namespace) -> int:
    """List all recorded sessions."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        print("Run 'crumdbob init-db' to create the database.", file=sys.stderr)
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            sessions = db.list_sessions(
                limit=args.limit if hasattr(args, "limit") else 100,
                git_branch=args.branch if hasattr(args, "branch") else None,
                git_author=args.author if hasattr(args, "author") else None,
            )

            if not sessions:
                print("No sessions found.")
                return 0

            # Determine output format
            format_type = args.format if hasattr(args, "format") else "table"

            if format_type == "json":
                # JSON output
                output = []
                for session in sessions:
                    output.append(
                        {
                            "id": session.id,
                            "timestamp": session.timestamp,
                            "session_name": session.session_name,
                            "git_branch": session.git_branch,
                            "git_commit": session.git_commit,
                            "git_author": session.git_author,
                            "file_count": session.file_count,
                            "command_count": session.command_count,
                            "risk_count": session.risk_count,
                            "task_count": session.task_count,
                        }
                    )
                print(json.dumps(output, indent=2))
            else:
                # Display beautiful sessions table
                display_sessions_table(sessions)

        return 0
    except Exception as exc:
        print(f"Error listing sessions: {exc}", file=sys.stderr)
        return 1


def cmd_show_session(args: argparse.Namespace) -> int:
    """Show detailed session information."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            session = db.get_session(args.session_id)

            if not session:
                print(f"Error: Session #{args.session_id} not found", file=sys.stderr)
                return 1

            # Print session details
            print(f"Session #{session.id}")
            print("=" * 60)
            print(f"Timestamp: {session.timestamp}")
            if session.session_name:
                print(f"Name: {session.session_name}")
            print(f"Pack Version: {session.pack_version}")

            if session.git_branch or session.git_commit or session.git_author:
                print("\nGit Context:")
                if session.git_branch:
                    print(f"  Branch: {session.git_branch}")
                if session.git_commit:
                    print(f"  Commit: {session.git_commit}")
                if session.git_author:
                    print(f"  Author: {session.git_author}")

            print(f"\nSource Report: {session.source_report_path}")
            if session.pack_directory:
                print(f"Pack Directory: {session.pack_directory}")

            print("\nEntity Counts:")
            print(f"  Files: {session.file_count}")
            print(f"  Commands: {session.command_count}")
            print(f"  Risks: {session.risk_count}")
            print(f"  Tasks: {session.task_count}")

            # Show files
            if session.file_count > 0:
                files = db.get_session_files(session.id)
                print(f"\nFiles ({len(files)}):")
                for file in files[:20]:  # Show first 20
                    print(f"  - {file.path}")
                if len(files) > 20:
                    print(f"  ... and {len(files) - 20} more")

            # Show commands
            if session.command_count > 0:
                commands = db.get_session_commands(session.id)
                print(f"\nCommands ({len(commands)}):")
                for cmd in commands[:10]:  # Show first 10
                    print(f"  - {cmd.command}")
                if len(commands) > 10:
                    print(f"  ... and {len(commands) - 10} more")

            # Show risks
            if session.risk_count > 0:
                risks = db.get_session_risks(session.id)
                print(f"\nRisks ({len(risks)}):")
                for risk in risks[:10]:  # Show first 10
                    print(f"  - [{risk.status}] {risk.description}")
                if len(risks) > 10:
                    print(f"  ... and {len(risks) - 10} more")

            # Show tasks
            if session.task_count > 0:
                tasks = db.get_session_tasks(session.id)
                print(f"\nTasks ({len(tasks)}):")
                for task in tasks[:10]:  # Show first 10
                    print(f"  - [{task.status}] {task.description}")
                if len(tasks) > 10:
                    print(f"  ... and {len(tasks) - 10} more")

        return 0
    except Exception as exc:
        print(f"Error showing session: {exc}", file=sys.stderr)
        return 1


def cmd_trends(args: argparse.Namespace) -> int:
    """Show cross-session patterns surfaced from memory database."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"No database found at {db_path}.", file=sys.stderr)
        print(
            "Run 'crumdbob init-db' then 'crumdbob record <pack>' to start building memory.",
            file=sys.stderr,
        )
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            stats = db.get_stats()
            min_sessions = getattr(args, "min_sessions", 1)
            hot = db.get_hot_files(min_sessions=min_sessions)
            recurring = db.get_recurring_risks(min_sessions=min_sessions)
            commands = db.get_command_frequency()

            # Display beautiful trends
            display_trends(stats, hot, recurring, commands)

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_migrate_to_db(args: argparse.Namespace) -> int:
    """Migrate existing pack directories to database."""
    db_path = Path(args.db) if args.db else get_default_db_path()
    pack_dirs = [Path(p) for p in args.pack_dirs]

    # Initialize database if needed
    if not db_path.exists():
        print(f"Initializing database: {db_path}")
        try:
            db = init_database(db_path)
            db.close()
        except Exception as exc:
            print(f"Error initializing database: {exc}", file=sys.stderr)
            return 1

    # Migrate each pack
    success_count = 0
    error_count = 0

    print(f"Migrating {len(pack_dirs)} pack(s) to database...\n")

    for pack_dir in pack_dirs:
        if not pack_dir.exists():
            print(f"✗ {pack_dir}: Not found")
            error_count += 1
            continue

        try:
            session_id = record_pack_to_db(
                pack_dir=pack_dir,
                db_path=db_path,
            )
            print(f"✓ {pack_dir}: Session #{session_id}")
            success_count += 1
        except Exception as exc:
            print(f"✗ {pack_dir}: {exc}")
            error_count += 1

    print("\nMigration complete:")
    print(f"  Success: {success_count}")
    print(f"  Errors:  {error_count}")
    return 1 if error_count else 0


def cmd_query(args: argparse.Namespace) -> int:
    """Execute natural language or template queries."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        print("Run 'crumdbob init-db' to create the database.", file=sys.stderr)
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            query_engine = create_query_engine(db)

            if args.query_type == "natural":
                # Natural language query
                result = query_engine.query_natural(args.question)
            elif args.query_type == "template":
                # Template query
                params = {}
                if hasattr(args, "params") and args.params:
                    for param in args.params:
                        key, value = param.split("=", 1)
                        # Try to convert to int if possible
                        try:
                            params[key] = int(value)
                        except ValueError:
                            params[key] = value
                result = query_engine.query_template(args.template, **params)
            elif args.query_type == "sql":
                # Direct SQL query
                result = query_engine.query_sql(args.sql)
            elif args.query_type == "list-templates":
                # List available templates
                templates = query_engine.list_templates()
                print("Available query templates:")
                for template in templates:
                    print(f"  - {template}")
                return 0
            else:
                print("Error: Unknown query type", file=sys.stderr)
                return 1

            # Determine output format
            format_type = args.format if hasattr(args, "format") else "table"

            if format_type == "json":
                print(json.dumps(result.results, indent=2))
            else:
                # Display beautiful query results
                display_query_results(result)

            return 0
    except Exception as exc:
        print(f"Error executing query: {exc}", file=sys.stderr)
        return 1


def cmd_insights(args: argparse.Namespace) -> int:
    """Generate and view insights."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            insights_engine = create_insights_engine(db)

            if args.insights_command == "generate":
                # Generate insights
                print("Generating insights from database...")
                insights = insights_engine.generate_insights()
                print(f"✓ Generated {len(insights)} insights")

                # Display top insights with beautiful UI
                if insights:
                    display_insights(insights[:5])

                return 0

            if args.insights_command == "list":
                # List insights
                category = args.category if hasattr(args, "category") else None
                insights = insights_engine.get_insights(category=category, limit=args.limit)

                if not insights:
                    print("No insights found.")
                    return 0

                # Display beautiful insights
                display_insights(insights)

                return 0

            if args.insights_command == "top":
                # Get top insights
                insights = insights_engine.get_top_insights(n=args.n)

                if not insights:
                    print("No insights found.")
                    return 0

                # Display beautiful insights
                display_insights(insights)

                return 0

            if args.insights_command == "actionable":
                # Get actionable insights
                insights = insights_engine.get_actionable_insights()

                if not insights:
                    print("No actionable insights found.")
                    return 0

                # Display beautiful insights
                display_insights(insights)

                return 0

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_predict(args: argparse.Namespace) -> int:
    """Make predictions based on historical data."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            prediction_engine = create_prediction_engine(db)

            if args.predict_type == "impact":
                # Predict impact of file change
                prediction = prediction_engine.predict_impact(args.file_path)

                print(f"Impact Prediction for: {args.file_path}")
                print(f"Confidence: {prediction.confidence:.0%}")
                print(f"Reasoning: {prediction.reasoning}\n")

                if prediction.predictions:
                    print("Likely to be affected:")
                    for pred in prediction.predictions[:10]:
                        print(
                            f"  • {pred['file']} (confidence: {pred['confidence']:.0%}, {pred['co_changes']} co-changes)"
                        )
                else:
                    print("No related files found in history.")

                return 0

            if args.predict_type == "risks":
                # Predict risks for planned change
                prediction = prediction_engine.predict_risks(args.description)

                print(f"Risk Prediction for: {args.description}")
                print(f"Confidence: {prediction.confidence:.0%}")
                print(f"Reasoning: {prediction.reasoning}\n")

                if prediction.predictions:
                    print("Potential risks based on similar past changes:")
                    for pred in prediction.predictions[:10]:
                        print(f"  • [{pred['status']}] {pred['risk'][:80]}")
                        print(f"    Occurred {pred['frequency']}x in history")
                else:
                    print("No similar risks found in history.")

                return 0

            if args.predict_type == "complexity":
                # Predict task complexity
                prediction = prediction_engine.predict_complexity(args.description)

                print(f"Complexity Prediction for: {args.description}")
                print(f"Confidence: {prediction.confidence:.0%}")
                print(f"Reasoning: {prediction.reasoning}\n")

                if prediction.predictions:
                    for pred in prediction.predictions:
                        print(f"Estimated duration: {pred.get('estimate_days', 'Unknown')} days")
                        if "average_days" in pred:
                            print(f"Based on average: {pred['average_days']} days")
                            print(f"Range: {pred['min_days']}-{pred['max_days']} days")
                        if "note" in pred:
                            print(f"Note: {pred['note']}")

                return 0

            if args.predict_type == "tests":
                # Recommend tests
                file_paths = args.file_paths
                prediction = prediction_engine.recommend_tests(file_paths)

                print(f"Test Recommendations for: {', '.join(file_paths)}")
                print(f"Confidence: {prediction.confidence:.0%}")
                print(f"Reasoning: {prediction.reasoning}\n")

                if prediction.predictions:
                    print("Recommended tests:")
                    for pred in prediction.predictions:
                        print(f"  • {pred['test_file']}")
                        print(f"    Reason: {pred['reason']}")
                else:
                    print("No test recommendations available.")

                return 0

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_patterns(args: argparse.Namespace) -> int:
    """Detect and analyze patterns."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            pattern_detector = create_pattern_detector(db)

            if args.patterns_command == "detect":
                # Detect patterns
                pattern_type = args.type if hasattr(args, "type") else "all"

                print(f"Detecting {pattern_type} patterns...")

                if pattern_type == "all":
                    patterns = pattern_detector.detect_all()
                elif pattern_type == "risks":
                    patterns = pattern_detector.detect_recurring_risks()
                elif pattern_type == "files":
                    patterns = pattern_detector.detect_file_relationships()
                elif pattern_type == "tasks":
                    patterns = pattern_detector.detect_task_patterns()
                elif pattern_type == "commands":
                    patterns = pattern_detector.detect_command_patterns()
                elif pattern_type == "anomalies":
                    patterns = pattern_detector.detect_anomalies()
                else:
                    print(f"Error: Unknown pattern type: {pattern_type}", file=sys.stderr)
                    return 1

                # Display beautiful patterns
                display_patterns(patterns)

                return 0

            if args.patterns_command == "analyze":
                # Analyze specific file
                analysis = pattern_detector.analyze_file(args.file)

                if not analysis["found"]:
                    print(analysis["message"])
                    return 1

                print(f"Pattern Analysis for: {analysis['file_path']}\n")
                print(f"Session count: {analysis['session_count']}")
                print(f"Total mentions: {analysis['total_mentions']}")
                print(f"First seen: {analysis['first_seen']}")
                print(f"Last seen: {analysis['last_seen']}")

                if analysis["related_files"]:
                    print("\nRelated files (change together):")
                    for rel in analysis["related_files"][:10]:
                        print(f"  • {rel['file']}")
                        print(
                            f"    Co-changes: {rel['co_changes']}, Confidence: {rel['confidence']:.0%}"
                        )

                return 0

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Display intelligence dashboard."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        with MemoryDatabase(db_path) as db:
            insights_engine = create_insights_engine(db)
            pattern_detector = create_pattern_detector(db)

            print("=" * 70)
            print("CrumbBob Intelligence Dashboard".center(70))
            print("=" * 70)

            # Database stats
            stats = db.get_stats()
            print("\n📊 Database Statistics:")
            print(f"   Sessions: {stats['session_count']}")
            print(f"   Unique files: {stats['unique_files']}")
            print(f"   Open risks: {stats['open_risks']}")
            print(f"   Unique commands: {stats['unique_commands']}")

            # Recent sessions
            timeline = db.get_session_timeline(limit=7)
            if timeline:
                print("\n📅 Recent Sessions (last 7):")
                for session in timeline:
                    name = session.get("session_name") or f"Session #{session['id']}"
                    branch = session.get("git_branch") or "-"
                    print(
                        f"   {session['timestamp'][:10]} | {name[:30]:<30} | {branch[:15]:<15} | {session['risk_count']} risks"
                    )

            # Top insights
            insights = insights_engine.get_top_insights(n=5)
            if insights:
                print("\n💡 Top Insights:")
                for insight in insights:
                    severity_icon = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                    }.get(insight.severity, "⚪")
                    print(f"   {severity_icon} {insight.title[:60]}")

            # Critical patterns
            patterns = pattern_detector.detect_all()
            critical_patterns = [p for p in patterns if p.severity in ("critical", "high")]
            if critical_patterns:
                print(f"\n⚠️  Critical Patterns ({len(critical_patterns)}):")
                for pattern in critical_patterns[:5]:
                    print(f"   • {pattern.description[:60]}")

            # Hot files
            hot_files = db.get_hot_files(min_sessions=2, limit=5)
            if hot_files:
                print("\n🔥 Hot Files (frequently changed):")
                for file in hot_files:
                    print(f"   {file['session_count']:>2}x | {file['path'][:55]}")

            # Recurring risks
            recurring = db.get_recurring_risks(min_sessions=2)
            if recurring:
                print(f"\n🔄 Recurring Risks ({len(recurring)}):")
                for risk in recurring[:5]:
                    print(f"   {risk['session_count']:>2}x | {risk['description'][:55]}")

            print("\n" + "=" * 70)
            print("Use 'crumdbob insights', 'crumdbob patterns', or 'crumdbob query' for details")
            print("=" * 70)

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the web dashboard server."""
    try:
        # Import here to avoid requiring FastAPI for other commands
        from web.api.server import run_server
    except ImportError:
        print(
            "Error: FastAPI not installed. Install with: pip install 'crumdbob[web]'",
            file=sys.stderr,
        )
        print("Or: pip install fastapi uvicorn[standard]", file=sys.stderr)
        return 1

    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists():
        print(f"Warning: Database not found: {db_path}")
        print("The server will start, but you may need to create the database first.")
        print(f"Run: crumdbob init-db --db {db_path}")
        print()

    host = args.host
    port = args.port
    no_browser = args.no_browser

    print("🧠 CrumbBob Web Dashboard")
    print(f"   Database: {db_path}")
    print(f"   Server: http://{host}:{port}")
    print()

    try:
        run_server(
            host=host,
            port=port,
            db_path=db_path,
            open_browser=not no_browser,
        )
        return 0
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        return 0
    except Exception as exc:
        print(f"Error starting server: {exc}", file=sys.stderr)
        return 1


def cmd_llm(args: argparse.Namespace) -> int:
    """LLM-powered analysis commands."""
    db_path = Path(args.db) if args.db else get_default_db_path()

    if not db_path.exists() and args.llm_command != "setup":
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        if args.llm_command == "setup":
            # Setup LLM configuration

            provider = args.provider
            model = args.model

            # Determine API key environment variable
            if provider == "openai":
                api_key_env = "OPENAI_API_KEY"
                default_model = "gpt-4"
            elif provider == "anthropic":
                api_key_env = "ANTHROPIC_API_KEY"
                default_model = "claude-3-sonnet-20240229"
            else:
                print(f"Error: Unsupported provider: {provider}", file=sys.stderr)
                return 1

            if not model:
                model = default_model

            if not os.getenv(api_key_env):
                print(f"⚠️  Warning: {api_key_env} environment variable not set", file=sys.stderr)
                print(f"   Set it with: export {api_key_env}=your-api-key", file=sys.stderr)

            # Save configuration to database
            with MemoryDatabase(db_path) as db:
                db.init_database()  # Ensure tables exist
                config_id = db.save_llm_config(
                    provider=provider,
                    model=model,
                    api_key_env=api_key_env,
                    temperature=args.temperature if hasattr(args, "temperature") else 0.7,
                    max_tokens=args.max_tokens if hasattr(args, "max_tokens") else 2000,
                )

            print(f"✓ LLM configured: {provider}/{model}")
            print(f"  Configuration ID: {config_id}")
            print(f"  API Key: ${api_key_env}")
            print("\nTo use LLM features, ensure your API key is set:")
            print(f"  export {api_key_env}=your-api-key")

            return 0

        if args.llm_command == "status":
            # Show LLM status and configuration
            with MemoryDatabase(db_path) as db:
                config = db.get_llm_config()

                if not config:
                    print("❌ LLM not configured")
                    print("\nRun 'crumdbob llm setup' to configure LLM integration.")
                    return 1

                print("🤖 LLM Configuration")
                print("=" * 60)
                print(f"Provider: {config['provider']}")
                print(f"Model: {config['model']}")
                print(f"API Key: ${config['api_key_env']}")
                print(f"Temperature: {config['temperature']}")
                print(f"Max Tokens: {config['max_tokens']}")

                api_key = os.getenv(config["api_key_env"])
                if api_key:
                    print("Status: ✓ API key is set")
                else:
                    print("Status: ❌ API key not set")
                    print(f"\nSet it with: export {config['api_key_env']}=your-api-key")

                # Show cache stats
                cache_stats = db.get_llm_cache_stats()
                print("\n📊 Cache Statistics")
                print(f"Cached responses: {cache_stats['total_cached']}")
                print(f"Tokens saved: {cache_stats['total_tokens_saved']:,}")

                if cache_stats["by_provider"]:
                    print("\nBy provider:")
                    for provider, count in cache_stats["by_provider"].items():
                        print(f"  {provider}: {count}")

            return 0

        if args.llm_command == "analyze":
            # Analyze a session with LLM
            with MemoryDatabase(db_path) as db:
                analyzer = create_llm_analyzer(db)

                if not analyzer:
                    print("❌ LLM not configured or API key not set", file=sys.stderr)
                    print("Run 'crumdbob llm setup' first.", file=sys.stderr)
                    return 1

                # Get session data
                session = db.get_session(args.session_id)
                if not session:
                    print(f"Error: Session #{args.session_id} not found", file=sys.stderr)
                    return 1

                # Gather session data
                files = db.get_session_files(args.session_id)
                commands = db.get_session_commands(args.session_id)
                risks = db.get_session_risks(args.session_id)
                tasks = db.get_session_tasks(args.session_id)

                session_data = {
                    "session_name": session.session_name,
                    "git_branch": session.git_branch,
                    "git_author": session.git_author,
                    "file_count": session.file_count,
                    "command_count": session.command_count,
                    "risk_count": session.risk_count,
                    "task_count": session.task_count,
                    "files": [f.path for f in files],
                    "commands": [c.command for c in commands],
                    "risks": [r.description for r in risks],
                    "tasks": [t.description for t in tasks],
                }

                print(f"🤖 Analyzing Session #{args.session_id}...")
                print()

                response = analyzer.analyze_session(session_data)

                if response.cached:
                    print("📦 [Cached Response]")
                    print()

                print(response.content)
                print()
                print(f"Provider: {response.provider}/{response.model}")
                if response.tokens_used:
                    print(f"Tokens: {response.tokens_used}")

            return 0

        if args.llm_command == "explain":
            # Explain a pattern with LLM
            with MemoryDatabase(db_path) as db:
                analyzer = create_llm_analyzer(db)

                if not analyzer:
                    print("❌ LLM not configured or API key not set", file=sys.stderr)
                    return 1

                # For now, use pattern description from command line
                pattern_data = {
                    "pattern_type": args.pattern_type
                    if hasattr(args, "pattern_type")
                    else "general",
                    "description": args.description,
                    "frequency": args.frequency if hasattr(args, "frequency") else 1,
                    "evidence": [],
                }

                print("🤖 Explaining pattern...")
                print()

                response = analyzer.explain_pattern(pattern_data)

                if response.cached:
                    print("📦 [Cached Response]")
                    print()

                print(response.content)
                print()
                print(f"Provider: {response.provider}/{response.model}")
                if response.tokens_used:
                    print(f"Tokens: {response.tokens_used}")

            return 0

        if args.llm_command == "recommend":
            # Get recommendations for a session
            with MemoryDatabase(db_path) as db:
                analyzer = create_llm_analyzer(db)

                if not analyzer:
                    print("❌ LLM not configured or API key not set", file=sys.stderr)
                    return 1

                # Get session data
                session = db.get_session(args.session_id)
                if not session:
                    print(f"Error: Session #{args.session_id} not found", file=sys.stderr)
                    return 1

                files = db.get_session_files(args.session_id)
                risks = db.get_session_risks(args.session_id)
                tasks = db.get_session_tasks(args.session_id)

                session_data = {
                    "session_name": session.session_name,
                    "files": [f.path for f in files],
                    "risks": [r.description for r in risks],
                    "tasks": [t.description for t in tasks],
                }

                print(f"🤖 Generating recommendations for Session #{args.session_id}...")
                print()

                response = analyzer.recommend_actions(session_data)

                if response.cached:
                    print("📦 [Cached Response]")
                    print()

                print(response.content)
                print()
                print(f"Provider: {response.provider}/{response.model}")
                if response.tokens_used:
                    print(f"Tokens: {response.tokens_used}")

            return 0

        if args.llm_command == "clear-cache":
            # Clear LLM cache
            with MemoryDatabase(db_path) as db:
                older_than = args.older_than if hasattr(args, "older_than") else None
                deleted = db.clear_llm_cache(older_than_days=older_than)

                if older_than:
                    print(f"✓ Cleared {deleted} cached responses older than {older_than} days")
                else:
                    print(f"✓ Cleared {deleted} cached responses")

            return 0

        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


def cmd_config(args: argparse.Namespace) -> int:
    """Manage CrumbBob configuration."""
    if args.config_command == "get":
        # Get a config value
        try:
            value = get_config_value(args.key)
            print(f"{args.key} = {value}")
            return 0
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    elif args.config_command == "set":
        # Set a config value
        try:
            set_config_value(args.key, args.value)
            print(f"✓ Set {args.key} = {args.value}")
            return 0
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    elif args.config_command == "list":
        # List all config values
        config = load_config()
        print("Current configuration:")
        for key, value in sorted(config.items()):
            print(f"  {key} = {value}")
        return 0

    if args.config_command == "reset":
        try:
            save_config(DEFAULT_CONFIG.copy())
            print("✓ Reset configuration to defaults")
            return 0
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    print(f"Error: Unknown config command: {args.config_command}", file=sys.stderr)
    return 1


def _register_llm_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register LLM-powered analysis commands."""
    llm_cmd = sub.add_parser("llm", help="LLM-powered intelligent analysis.")
    llm_sub = llm_cmd.add_subparsers(dest="llm_command", required=True)

    # Setup command
    llm_setup = llm_sub.add_parser("setup", help="Configure LLM provider and API key")
    llm_setup.add_argument("provider", choices=["openai", "anthropic"], help="LLM provider")
    llm_setup.add_argument("--model", type=str, help="Model name (default: provider default)")
    llm_setup.add_argument(
        "--temperature", type=float, default=0.7, help="Temperature (default: 0.7)"
    )
    llm_setup.add_argument(
        "--max-tokens", type=int, default=2000, help="Max tokens (default: 2000)"
    )
    _add_db_argument(llm_setup)

    # Status command
    llm_status = llm_sub.add_parser("status", help="Show LLM configuration and usage stats")
    _add_db_argument(llm_status)

    # Analyze command
    llm_analyze = llm_sub.add_parser("analyze", help="Analyze a session with LLM")
    llm_analyze.add_argument("session_id", type=int, help="Session ID to analyze")
    _add_db_argument(llm_analyze)

    # Explain command
    llm_explain = llm_sub.add_parser("explain", help="Get LLM explanation of a pattern")
    llm_explain.add_argument("description", type=str, help="Pattern description")
    llm_explain.add_argument("--pattern-type", type=str, help="Pattern type")
    llm_explain.add_argument("--frequency", type=int, help="Pattern frequency")
    _add_db_argument(llm_explain)

    # Recommend command
    llm_recommend = llm_sub.add_parser("recommend", help="Get LLM recommendations for a session")
    llm_recommend.add_argument("session_id", type=int, help="Session ID")
    _add_db_argument(llm_recommend)

    # Clear cache command
    llm_clear = llm_sub.add_parser("clear-cache", help="Clear LLM response cache")
    llm_clear.add_argument("--older-than", type=int, help="Clear entries older than N days")
    _add_db_argument(llm_clear)

    llm_cmd.set_defaults(func=cmd_llm)


# Constants for CLI help text
DB_HELP = "Database path (default: ~/.crumdbob/memory.db)"
DB_INIT_HINT = "Run 'crumdbob init-db' to create the database."


def _add_db_argument(parser: argparse.ArgumentParser) -> None:
    """Add standard --db argument to a parser."""
    parser.add_argument("--db", type=Path, help=DB_HELP)


def _add_format_argument(parser: argparse.ArgumentParser, default: str = "table") -> None:
    """Add standard --format argument to a parser."""
    parser.add_argument(
        "--format", choices=["table", "json"], default=default, help="Output format"
    )


def _register_pack_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register pack generation and manipulation commands."""
    import_cmd = sub.add_parser(
        "import", help="Generate a CrumbBob pack from a Bob markdown report."
    )
    import_cmd.add_argument("report", type=Path)
    import_cmd.add_argument("--out", type=Path, required=True)
    import_cmd.set_defaults(func=cmd_import)

    pack_cmd = sub.add_parser(
        "pack",
        help="Generate a pack from a directory containing bob-report.md and optional artifacts.",
    )
    pack_cmd.add_argument("input_dir", type=Path)
    pack_cmd.add_argument("--out", type=Path, required=True)
    pack_cmd.add_argument("--record", action="store_true", help="Record pack to memory database")
    _add_db_argument(pack_cmd)
    pack_cmd.set_defaults(func=cmd_pack)

    auto_collect_cmd = sub.add_parser(
        "auto-collect", help="Auto-collect artifacts from Git repo and generate pack."
    )
    auto_collect_cmd.add_argument("--report", type=Path, help="Path to bob-report.md (optional)")
    auto_collect_cmd.add_argument(
        "--input-dir", type=Path, help="Input directory to create (default: ./crumdbob-input)"
    )
    auto_collect_cmd.add_argument(
        "--out", type=Path, required=True, help="Output directory for generated pack"
    )
    auto_collect_cmd.add_argument(
        "--no-interactive", action="store_true", help="Skip interactive artifact selection"
    )
    auto_collect_cmd.add_argument(
        "--record", action="store_true", help="Record pack to memory database"
    )
    _add_db_argument(auto_collect_cmd)
    auto_collect_cmd.set_defaults(func=cmd_auto_collect)

    watch_cmd = sub.add_parser(
        "watch", help="Watch input directory and auto-regenerate pack on changes."
    )
    watch_cmd.add_argument("input_dir", type=Path, help="Input directory to watch")
    watch_cmd.add_argument(
        "--out", type=Path, required=True, help="Output directory for generated pack"
    )
    watch_cmd.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        help="Seconds to wait after last change (default: 2.0)",
    )
    watch_cmd.set_defaults(func=cmd_watch)

    inspect_cmd = sub.add_parser(
        "inspect", help="Inspect what CrumbBob can extract from a Bob report."
    )
    inspect_cmd.add_argument("report", type=Path)
    inspect_cmd.add_argument(
        "--verbose", "-v", action="store_true", help="Show extracted content, not just counts"
    )
    inspect_cmd.set_defaults(func=cmd_inspect)

    replay_cmd = sub.add_parser("replay", help="Print the replay prompt from a generated pack.")
    replay_cmd.add_argument("pack_dir", type=Path)
    replay_cmd.set_defaults(func=cmd_replay)

    pr_cmd = sub.add_parser("pr", help="Print the PR summary from a generated pack.")
    pr_cmd.add_argument("pack_dir", type=Path)
    pr_cmd.set_defaults(func=cmd_pr)

    validate_cmd = sub.add_parser(
        "validate", help="Validate one CRUMB file or every .crumb file in a pack."
    )
    validate_cmd.add_argument("target", type=Path)
    validate_cmd.set_defaults(func=cmd_validate)

    doctor_cmd = sub.add_parser("doctor", help="Print a judge-friendly pack health report.")
    doctor_cmd.add_argument("pack_dir", type=Path)
    doctor_cmd.set_defaults(func=cmd_doctor)

    graph_cmd = sub.add_parser("graph", help="Print refs, handoff, and workflow dependencies.")
    graph_cmd.add_argument("pack_dir", type=Path)
    graph_cmd.set_defaults(func=cmd_graph)

    diff_cmd = sub.add_parser("diff", help="Compare two pack directories and show differences.")
    diff_cmd.add_argument("pack_dir_1", type=Path, help="First pack directory")
    diff_cmd.add_argument("pack_dir_2", type=Path, help="Second pack directory")
    diff_cmd.add_argument(
        "--format",
        choices=["summary", "detailed", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    diff_cmd.add_argument("--no-color", action="store_true", help="Disable colored output")
    diff_cmd.set_defaults(func=cmd_diff)

    skill_cmd = sub.add_parser(
        "init-bob-skill", help="Write a small skill file for agents using CrumbBob."
    )
    skill_cmd.add_argument("--out", type=Path, required=True)
    skill_cmd.set_defaults(func=cmd_init_bob_skill)


def _register_db_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register memory database commands."""
    init_db_cmd = sub.add_parser("init-db", help="Initialize memory database.")
    init_db_cmd.add_argument("--path", type=Path, help=DB_HELP)
    init_db_cmd.set_defaults(func=cmd_init_db)

    record_cmd = sub.add_parser("record", help="Record a pack directory to the database.")
    record_cmd.add_argument("pack_dir", type=Path, help="Pack directory to record")
    _add_db_argument(record_cmd)
    record_cmd.add_argument("--session-name", type=str, help="Optional session name")
    record_cmd.set_defaults(func=cmd_record)

    list_sessions_cmd = sub.add_parser("list-sessions", help="List all recorded sessions.")
    _add_db_argument(list_sessions_cmd)
    _add_format_argument(list_sessions_cmd)
    list_sessions_cmd.add_argument(
        "--limit", type=int, default=100, help="Maximum sessions to show"
    )
    list_sessions_cmd.add_argument("--branch", type=str, help="Filter by Git branch")
    list_sessions_cmd.add_argument("--author", type=str, help="Filter by Git author")
    list_sessions_cmd.set_defaults(func=cmd_list_sessions)

    show_session_cmd = sub.add_parser("show-session", help="Show detailed session information.")
    show_session_cmd.add_argument("session_id", type=int, help="Session ID to show")
    _add_db_argument(show_session_cmd)
    show_session_cmd.set_defaults(func=cmd_show_session)

    migrate_cmd = sub.add_parser(
        "migrate-to-db", help="Migrate existing pack directories to database."
    )
    migrate_cmd.add_argument("pack_dirs", type=Path, nargs="+", help="Pack directories to migrate")
    _add_db_argument(migrate_cmd)
    migrate_cmd.set_defaults(func=cmd_migrate_to_db)

    trends_cmd = sub.add_parser("trends", help="Show cross-session patterns from memory database.")
    _add_db_argument(trends_cmd)
    trends_cmd.add_argument(
        "--min-sessions",
        type=int,
        default=1,
        dest="min_sessions",
        help="Minimum sessions a file/risk must appear in (default: 1)",
    )
    trends_cmd.set_defaults(func=cmd_trends)


def _register_query_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register query commands."""
    query_cmd = sub.add_parser(
        "query", help="Query memory database with natural language or templates."
    )
    query_sub = query_cmd.add_subparsers(dest="query_type", required=True)

    query_natural = query_sub.add_parser("natural", help="Natural language query")
    query_natural.add_argument("question", type=str, help="Natural language question")
    _add_db_argument(query_natural)
    _add_format_argument(query_natural)

    query_template = query_sub.add_parser("template", help="Template-based query")
    query_template.add_argument("template", type=str, help="Template name")
    query_template.add_argument("--params", nargs="*", help="Template parameters (key=value)")
    _add_db_argument(query_template)
    _add_format_argument(query_template)

    query_sql = query_sub.add_parser("sql", help="Direct SQL query")
    query_sql.add_argument("sql", type=str, help="SQL query string")
    _add_db_argument(query_sql)
    _add_format_argument(query_sql)

    query_list = query_sub.add_parser("list-templates", help="List available query templates")
    _add_db_argument(query_list)

    query_cmd.set_defaults(func=cmd_query)


def _register_insights_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register insights commands."""
    insights_cmd = sub.add_parser("insights", help="Generate and view actionable insights.")
    insights_sub = insights_cmd.add_subparsers(dest="insights_command", required=True)

    insights_generate = insights_sub.add_parser("generate", help="Generate insights from database")
    _add_db_argument(insights_generate)

    insights_list = insights_sub.add_parser("list", help="List all insights")
    _add_db_argument(insights_list)
    insights_list.add_argument("--category", type=str, help="Filter by insight type")
    insights_list.add_argument("--limit", type=int, default=50, help="Maximum insights to show")

    insights_top = insights_sub.add_parser("top", help="Show top N most important insights")
    insights_top.add_argument(
        "n", type=int, default=10, nargs="?", help="Number of insights (default: 10)"
    )
    _add_db_argument(insights_top)

    insights_actionable = insights_sub.add_parser("actionable", help="Show actionable insights")
    _add_db_argument(insights_actionable)

    insights_cmd.set_defaults(func=cmd_insights)


def _register_predict_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register prediction commands."""
    predict_cmd = sub.add_parser("predict", help="Make predictions based on historical data.")
    predict_sub = predict_cmd.add_subparsers(dest="predict_type", required=True)

    predict_impact = predict_sub.add_parser("impact", help="Predict impact of file change")
    predict_impact.add_argument("file_path", type=str, help="File path to analyze")
    _add_db_argument(predict_impact)

    predict_risks = predict_sub.add_parser("risks", help="Predict risks for planned change")
    predict_risks.add_argument("description", type=str, help="Description of planned change")
    _add_db_argument(predict_risks)

    predict_complexity = predict_sub.add_parser("complexity", help="Predict task complexity")
    predict_complexity.add_argument("description", type=str, help="Task description")
    _add_db_argument(predict_complexity)

    predict_tests = predict_sub.add_parser("tests", help="Recommend tests for file changes")
    predict_tests.add_argument("file_paths", type=str, nargs="+", help="File paths being changed")
    _add_db_argument(predict_tests)

    predict_cmd.set_defaults(func=cmd_predict)


def _register_patterns_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register pattern detection commands."""
    patterns_cmd = sub.add_parser("patterns", help="Detect and analyze patterns.")
    patterns_sub = patterns_cmd.add_subparsers(dest="patterns_command", required=True)

    patterns_detect = patterns_sub.add_parser("detect", help="Detect patterns in database")
    patterns_detect.add_argument(
        "--type",
        choices=["all", "risks", "files", "tasks", "commands", "anomalies"],
        default="all",
        help="Pattern type to detect",
    )
    _add_db_argument(patterns_detect)

    patterns_analyze = patterns_sub.add_parser("analyze", help="Analyze patterns for specific file")
    patterns_analyze.add_argument("file", type=str, help="File path to analyze")
    _add_db_argument(patterns_analyze)

    patterns_cmd.set_defaults(func=cmd_patterns)


def _register_dashboard_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register dashboard and serve commands."""
    dashboard_cmd = sub.add_parser("dashboard", help="Display intelligence dashboard.")
    _add_db_argument(dashboard_cmd)
    dashboard_cmd.set_defaults(func=cmd_dashboard)

    serve_cmd = sub.add_parser("serve", help="Start web dashboard server.")
    _add_db_argument(serve_cmd)
    serve_cmd.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    serve_cmd.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    serve_cmd.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )
    serve_cmd.set_defaults(func=cmd_serve)


def _register_config_subcommands(sub: argparse._SubParsersAction) -> None:
    """Register configuration commands."""
    config_cmd = sub.add_parser("config", help="Manage CrumbBob configuration.")
    config_sub = config_cmd.add_subparsers(dest="config_command", required=True)

    config_get = config_sub.add_parser("get", help="Get a configuration value")
    config_get.add_argument("key", type=str, help="Configuration key")

    config_set = config_sub.add_parser("set", help="Set a configuration value")
    config_set.add_argument("key", type=str, help="Configuration key")
    config_set.add_argument("value", type=str, help="Configuration value")

    config_sub.add_parser("list", help="List all configuration values")

    config_sub.add_parser("reset", help="Reset configuration to defaults")

    config_cmd.set_defaults(func=cmd_config)


def build_parser() -> argparse.ArgumentParser:
    """Build the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="crumdbob",
        description="Generate replayable software memory packs from IBM Bob reports.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Register all command groups
    _register_pack_subcommands(sub)
    _register_db_subcommands(sub)
    _register_query_subcommands(sub)
    _register_insights_subcommands(sub)
    _register_predict_subcommands(sub)
    _register_patterns_subcommands(sub)
    _register_dashboard_subcommands(sub)
    _register_config_subcommands(sub)
    _register_llm_subcommands(sub)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Configure structured logging before any subcommand runs.
    # CLI default is plain (human-readable) on TTY, JSON when piped.
    # Override via CRUMDBOB_LOG_FORMAT={json,plain} or CRUMDBOB_LOG_LEVEL.
    configure_logging(level=os.getenv("CRUMDBOB_LOG_LEVEL", "WARNING"))

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
