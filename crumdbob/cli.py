from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .packer import read_pr_summary, read_replay_prompt, write_pack
from .parser import parse_bob_report

def cmd_import(args: argparse.Namespace) -> int:
    written = write_pack(args.report, args.out)
    for path in written:
        print(path)
    return 0

def cmd_inspect(args: argparse.Namespace) -> int:
    report = parse_bob_report(args.report)
    print(f"title: {report.title}")
    print(f"summary: {report.summary}")
    print(f"files: {len(report.files)}")
    print(f"commands: {len(report.commands)}")
    print(f"risks: {len(report.risks)}")
    print(f"tests: {len(report.tests)}")
    print(f"next_steps: {len(report.next_steps)}")
    return 0

def cmd_replay(args: argparse.Namespace) -> int:
    sys.stdout.write(read_replay_prompt(args.pack_dir))
    return 0

def cmd_pr(args: argparse.Namespace) -> int:
    sys.stdout.write(read_pr_summary(args.pack_dir))
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crumdbob", description="Generate replayable software memory packs from IBM Bob reports.")
    sub = parser.add_subparsers(dest="command", required=True)

    import_cmd = sub.add_parser("import", help="Generate a CrumbBob pack from a Bob markdown report.")
    import_cmd.add_argument("report", type=Path)
    import_cmd.add_argument("--out", type=Path, required=True)
    import_cmd.set_defaults(func=cmd_import)

    inspect_cmd = sub.add_parser("inspect", help="Inspect what CrumbBob can extract from a Bob report.")
    inspect_cmd.add_argument("report", type=Path)
    inspect_cmd.set_defaults(func=cmd_inspect)

    replay_cmd = sub.add_parser("replay", help="Print the replay prompt from a generated pack.")
    replay_cmd.add_argument("pack_dir", type=Path)
    replay_cmd.set_defaults(func=cmd_replay)

    pr_cmd = sub.add_parser("pr", help="Print the PR summary from a generated pack.")
    pr_cmd.add_argument("pack_dir", type=Path)
    pr_cmd.set_defaults(func=cmd_pr)
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
