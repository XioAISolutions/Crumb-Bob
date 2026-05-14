from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from .parser import BobReport, parse_bob_report

@dataclass(frozen=True)
class PackFile:
    path: str
    content: str

def _bullet(items: list[str], fallback: str) -> str:
    return "\n".join(f"- {x}" for x in (items or [fallback]))

def _checkbox(items: list[str], fallback: str) -> str:
    return "\n".join(f"- [ ] {x}" for x in (items or [fallback]))

def _crumb(kind: str, title: str, sections: dict[str, str], extra: dict[str, str] | None = None) -> str:
    headers = {"v": "1.4", "kind": kind, "title": title, "source": "ibm-bob"}
    if extra:
        headers.update(extra)
    lines = ["BEGIN CRUMB", *[f"{k}={v}" for k, v in headers.items()], "---"]
    for name, body in sections.items():
        lines += [f"[{name}]", body.strip() or "- Not captured in source report.", ""]
    lines.append("END CRUMB")
    return "\n".join(lines) + "\n"

def generate_pack(report: BobReport) -> list[PackFile]:
    files = _bullet(report.files[:16], "No specific files were named in the Bob report.")
    commands = _bullet(report.commands[:12], "Run the repository's documented install, test, and build commands.")
    risks = _checkbox(report.risks[:12], "Validate assumptions Bob could not prove from static repo context.")
    tests = _checkbox(report.tests[:12], "Run lint, typecheck, tests, build, and smoke checks before merging.")
    next_steps = _checkbox(report.next_steps[:12], "Pick the smallest high-value improvement Bob identified and ship it with tests.")

    repo_genome = _crumb("map", f"Repo Genome: {report.title}", {
        "project": report.summary,
        "modules": files,
        "commands": commands,
        "handoff": "- Load this Repo Genome first id=load_genome\n- Read the Session Flight Recorder id=read_session after=load_genome\n- Execute the Next Task id=execute_task after=read_session",
    })

    session = _crumb("audit", "Session Flight Recorder", {
        "goal": "Preserve IBM Bob's repository understanding as a replayable development memory pack.",
        "actions": _bullet([f"Parsed source report: {report.source_path}", "Extracted repo summary, files, commands, risks, tests, and next steps.", "Generated CRUMB handoffs for replay, PR review, and future AI sessions."], "Captured Bob session."),
        "verdict": "CrumbBob pack generated. A future developer or AI agent can continue without re-reading the full Bob report.",
        "evidence": _bullet(report.bullets[:14], "Source report is included beside the generated pack."),
    })

    next_task = _crumb("task", "Next Task from Bob Session", {
        "goal": report.next_steps[0] if report.next_steps else "Implement the highest-value improvement identified by Bob.",
        "context": f"{report.summary}\n\nFiles mentioned:\n{files}",
        "constraints": "- Preserve existing behavior unless Bob explicitly says otherwise.\n- Keep changes reviewable inside one pull request.\n- Update the replay pack after implementation.",
        "checks": "lint :: required\ntypecheck :: required\ntests :: required\nbuild :: required when applicable",
    })

    test_plan = _crumb("todo", "Bob-Derived Test Plan", {"tasks": tests, "checks": "unit-tests :: pending\nintegration-smoke :: pending\ndocs-review :: pending"})
    risk_register = _crumb("todo", "Risk Register", {"tasks": risks, "handoff": "- Resolve highest risk first id=resolve_risk\n- Add or update tests id=add_tests after=resolve_risk\n- Refresh CrumbBob pack id=refresh_pack after=add_tests"})
    agent = _crumb("agent", "CrumbBob Repo Agent Passport", {
        "identity": "role=IBM Bob continuation agent\nmission=Continue from the CrumbBob memory pack without re-discovering solved context.",
        "rules": "- Load Repo Genome before code changes.\n- Treat Session Flight Recorder as prior session state.\n- Start with the Next Task unless the user overrides priority.\n- Run or update the Test Plan before declaring complete.\n- Update the Risk Register when new assumptions appear.",
        "knowledge": f"{report.summary}\n\nKnown files:\n{files}\n\nKnown commands:\n{commands}",
    }, {"id": "crumdbob-repo-agent"})

    replay = dedent(f"""
    # Replay this IBM Bob session

    You are IBM Bob continuing from a previous repo-aware development session.

    Load the attached files in order: Repo Genome, Session Flight Recorder, Next Task, Test Plan, Risk Register, and Agent Passport.

    Continue from the previous Bob findings. Do not re-discover captured context. Validate the current repo state, implement the next task, run the test plan, and update the flight recorder.

    Project summary: {report.summary}
    """).strip() + "\n"

    pr = dedent(f"""
    # PR: Add CrumbBob replay pack

    ## Summary
    This PR adds a CrumbBob memory pack generated from an IBM Bob repository session.

    ## What changed
    - Added Repo Genome, Session Flight Recorder, Next Task, Test Plan, Risk Register, Agent Passport, Replay Prompt, and PR Summary.

    ## Why
    IBM Bob can understand a repository during a session. CrumbBob makes that understanding portable.

    ## Validation
    {tests}
    """).strip() + "\n"

    return [PackFile("00_repo_genome.crumb", repo_genome), PackFile("01_session_flight_recorder.crumb", session), PackFile("02_next_task.crumb", next_task), PackFile("03_test_plan.crumb", test_plan), PackFile("04_risk_register.crumb", risk_register), PackFile("05_agent_passport.crumb", agent), PackFile("06_replay_prompt.md", replay), PackFile("07_pr_summary.md", pr)]

def write_pack(report_path: str | Path, out_dir: str | Path) -> list[Path]:
    report = parse_bob_report(report_path)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    written = []
    for item in generate_pack(report):
        target = output / item.path
        target.write_text(item.content, encoding="utf-8")
        written.append(target)
    return written

def read_replay_prompt(pack_dir: str | Path) -> str:
    return (Path(pack_dir) / "06_replay_prompt.md").read_text(encoding="utf-8")

def read_pr_summary(pack_dir: str | Path) -> str:
    return (Path(pack_dir) / "07_pr_summary.md").read_text(encoding="utf-8")
