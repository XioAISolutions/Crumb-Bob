from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from textwrap import dedent

from . import __version__
from .parser import BobReport, enrich_report_with_artifact, parse_bob_report

OPTIONAL_INPUTS = (
    ("git-diff.patch", "git-diff"),
    ("test-output.txt", "test-output"),
    ("repo-notes.md", "repo-notes"),
)


@dataclass(frozen=True)
class PackFile:
    path: str
    content: str


def _bullet(items: list[str], fallback: str) -> str:
    return "\n".join(f"- {x}" for x in (items or [fallback]))


def _checkbox(items: list[str], fallback: str) -> str:
    return "\n".join(f"- [ ] {x}" for x in (items or [fallback]))


def _checks(items: list[tuple[str, str]]) -> str:
    return "\n".join(f"{name} :: {status}" for name, status in items)


def _workflow(steps: list[tuple[str, str, str | None]]) -> str:
    lines: list[str] = []
    for index, (label, step_id, after) in enumerate(steps, start=1):
        suffix = f" id={step_id}"
        if after:
            suffix += f" after={after}"
        lines.append(f"{index}. {label}{suffix}")
    return "\n".join(lines)


def _handoff(steps: list[tuple[str, str, str | None]]) -> str:
    lines: list[str] = []
    for label, step_id, after in steps:
        suffix = f" id={step_id}"
        if after:
            suffix += f" after={after}"
        lines.append(f"- {label}{suffix}")
    return "\n".join(lines)


def _refs(*refs: str) -> str:
    return ",".join(refs)


def _source_hash(path: str, fallback_text: str) -> tuple[str, int]:
    source = Path(path)
    if source.exists():
        data = source.read_bytes()
    else:
        data = fallback_text.encode("utf-8")
    return hashlib.sha256(data).hexdigest(), len(data)


def _content_hash(content: str) -> tuple[str, int]:
    data = content.encode("utf-8")
    return hashlib.sha256(data).hexdigest(), len(data)


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _crumb(kind: str, title: str, sections: dict[str, str], extra: dict[str, str] | None = None) -> str:
    headers = [
        ("v", "1.4"),
        ("kind", kind),
        ("title", title),
        ("source", "ibm-bob"),
    ]
    if extra:
        headers.extend(extra.items())
    lines = ["BEGIN CRUMB", *[f"{key}={value}" for key, value in headers], "---"]
    for name, body in sections.items():
        lines += [f"[{name}]", body.strip() or "- Not captured in source report.", ""]
    lines.append("END CRUMB")
    return "\n".join(lines) + "\n"


def _guardrails() -> str:
    return _bullet(
        [
            "Treat the Bob report as evidence, not as permission to skip repo verification.",
            "Keep code changes small, reviewable, and reversible.",
            "Do not invent external API calls or credentials that were not present in the repo.",
            "Run the captured test plan before declaring the continuation complete.",
            "Refresh the proof chain whenever the generated pack changes.",
        ],
        "Verify the repository before changing behavior.",
    )


def _capabilities() -> str:
    return _bullet(
        [
            "Can replay prior Bob context from the generated CRUMB pack.",
            "Can identify files, commands, risks, tests, and next steps from the source report.",
            "Can produce PR-ready and agent-ready continuation prompts.",
            "Cannot prove runtime behavior without running the captured commands.",
            "Cannot replace product, legal, or security approval gates.",
        ],
        "Continue from the generated memory pack.",
    )


def _evidence(report: BobReport) -> str:
    snippets = report.bullets[:8] or [report.summary]
    artifacts = [
        f"- {artifact.kind}: {artifact.path} ({len(artifact.text.splitlines())} lines)"
        for artifact in report.source_artifacts
    ]
    return "\n".join(
        [
            "Source report:",
            f"- {report.source_path}",
            "",
            "Extracted source snippets:",
            _bullet(snippets, "Source report is included beside the generated pack."),
            "",
            "Files:",
            _bullet(report.files[:12], "No specific files were named in the Bob report."),
            "",
            "Commands:",
            _bullet(report.commands[:8], "No command surface was captured."),
            "",
            "Risks:",
            _bullet(report.risks[:8], "No explicit risks were captured."),
            "",
            "Additional source artifacts:",
            "\n".join(artifacts) if artifacts else "- None supplied.",
        ]
    )


def _base_pack(report: BobReport) -> list[PackFile]:
    files = _bullet(report.files[:16], "No specific files were named in the Bob report.")
    commands = _bullet(report.commands[:12], "Run the repository's documented install, test, and build commands.")
    risks = _checkbox(report.risks[:12], "Validate assumptions Bob could not prove from static repo context.")
    tests = _checkbox(report.tests[:12], "Run lint, typecheck, tests, build, and smoke checks before merging.")
    next_steps = _checkbox(report.next_steps[:12], "Pick the smallest high-value improvement Bob identified and ship it with tests.")

    repo_workflow = _workflow(
        [
            ("Load `00_repo_genome.crumb` as the architecture map", "wf_load_genome", None),
            ("Read `01_session_flight_recorder.crumb` for prior state", "wf_read_session", "wf_load_genome"),
            ("Open `02_next_task.crumb` and select the first viable task", "wf_select_task", "wf_read_session"),
            ("Run `03_test_plan.crumb` checks before merge", "wf_run_tests", "wf_select_task"),
            ("Review `08_proof_chain.json` for hash-bound provenance", "wf_verify_proof", "wf_run_tests"),
        ]
    )
    repo_handoff = _handoff(
        [
            ("Load this Repo Genome first", "load_genome", None),
            ("Read the Session Flight Recorder", "read_session", "load_genome"),
            ("Execute the Next Task", "execute_task", "read_session"),
            ("Check proof chain before sharing", "verify_proof", "execute_task"),
        ]
    )
    repo_genome = _crumb(
        "map",
        f"Repo Genome: {report.title}",
        {
            "project": report.summary,
            "modules": files,
            "commands": commands,
            "workflow": repo_workflow,
            "checks": _checks(
                [
                    ("source-report", "captured"),
                    ("files-extracted", str(len(report.files))),
                    ("commands-extracted", str(len(report.commands))),
                    ("proof-chain", "required"),
                ]
            ),
            "guardrails": _guardrails(),
            "capabilities": _capabilities(),
            "evidence": _evidence(report),
            "handoff": repo_handoff,
        },
        {
            "id": "repo-genome",
            "refs": _refs("session-flight-recorder", "next-task", "test-plan", "risk-register", "agent-passport"),
        },
    )

    session_handoff = _handoff(
        [
            ("Confirm Bob source report is present", "confirm_source", None),
            ("Compare current repo state against captured actions", "compare_state", "confirm_source"),
            ("Append new findings to a refreshed flight recorder", "refresh_flight_recorder", "compare_state"),
        ]
    )
    session = _crumb(
        "audit",
        "Session Flight Recorder",
        {
            "goal": "Preserve IBM Bob's repository understanding as a replayable development memory pack.",
            "actions": _bullet(
                [
                    f"Parsed source report: {report.source_path}",
                    "Extracted repo summary, files, commands, risks, tests, and next steps.",
                    "Generated CRUMB handoffs for replay, PR review, future AI sessions, and proof-chain review.",
                ],
                "Captured Bob session.",
            ),
            "verdict": "CrumbBob pack generated. A future developer or AI agent can continue without re-reading the full Bob report.",
            "workflow": _workflow(
                [
                    ("Replay captured summary", "session_replay", None),
                    ("Validate extracted risks and tests", "session_validate", "session_replay"),
                    ("Update pack after continuation work", "session_update", "session_validate"),
                ]
            ),
            "checks": _checks(
                [
                    ("source-report", "hash-bound in proof chain"),
                    ("replay-prompt", "generated"),
                    ("pr-summary", "generated"),
                    ("audit-verdict", "captured"),
                ]
            ),
            "guardrails": _guardrails(),
            "capabilities": _capabilities(),
            "evidence": _evidence(report),
            "handoff": session_handoff,
        },
        {
            "id": "session-flight-recorder",
            "refs": _refs("repo-genome", "next-task", "test-plan", "risk-register", "proof-chain"),
        },
    )

    next_task = _crumb(
        "task",
        "Next Task from Bob Session",
        {
            "goal": report.next_steps[0] if report.next_steps else "Implement the highest-value improvement identified by Bob.",
            "context": f"{report.summary}\n\nFiles mentioned:\n{files}\n\nCommands captured:\n{commands}",
            "constraints": "\n".join(
                [
                    "- Preserve existing behavior unless Bob explicitly says otherwise.",
                    "- Keep changes reviewable inside one pull request.",
                    "- Update the replay pack and proof chain after implementation.",
                    "- Avoid external services or credentials in the continuation path unless the repo already requires them.",
                ]
            ),
            "workflow": _workflow(
                [
                    ("Confirm current repo state", "task_confirm_state", None),
                    ("Implement the smallest useful change", "task_implement", "task_confirm_state"),
                    ("Run captured test plan", "task_test", "task_implement"),
                    ("Regenerate CrumbBob pack", "task_regenerate_pack", "task_test"),
                ]
            ),
            "checks": _checks(
                [
                    ("lint", "required when available"),
                    ("typecheck", "required when available"),
                    ("tests", "required"),
                    ("build", "required when applicable"),
                    ("proof-chain", "refresh after pack changes"),
                ]
            ),
            "guardrails": _guardrails(),
            "capabilities": _capabilities(),
            "evidence": _evidence(report),
            "handoff": _handoff(
                [
                    ("Start from captured next task", "start_next_task", None),
                    ("Run validation before review", "run_validation", "start_next_task"),
                    ("Prepare PR summary", "prepare_pr", "run_validation"),
                ]
            ),
        },
        {
            "id": "next-task",
            "refs": _refs("repo-genome", "session-flight-recorder", "test-plan", "risk-register"),
        },
    )

    test_plan = _crumb(
        "todo",
        "Bob-Derived Test Plan",
        {
            "tasks": tests,
            "workflow": _workflow(
                [
                    ("Run fastest static checks first", "tests_static", None),
                    ("Run unit and integration tests", "tests_runtime", "tests_static"),
                    ("Run demo or smoke command", "tests_smoke", "tests_runtime"),
                ]
            ),
            "checks": _checks(
                [
                    ("unit-tests", "pending"),
                    ("integration-smoke", "pending"),
                    ("docs-review", "pending"),
                    ("proof-chain", "pending"),
                ]
            ),
            "guardrails": _guardrails(),
            "capabilities": _capabilities(),
            "evidence": _evidence(report),
            "handoff": _handoff(
                [
                    ("Run required tests", "run_required_tests", None),
                    ("Record failures in risk register", "record_failures", "run_required_tests"),
                    ("Refresh proof chain", "refresh_proof_after_tests", "record_failures"),
                ]
            ),
        },
        {
            "id": "test-plan",
            "refs": _refs("next-task", "risk-register", "proof-chain"),
        },
    )

    risk_register = _crumb(
        "todo",
        "Risk Register",
        {
            "tasks": risks,
            "workflow": _workflow(
                [
                    ("Resolve highest product risk first", "risk_rank", None),
                    ("Add tests or docs for the risk", "risk_mitigate", "risk_rank"),
                    ("Capture residual risk in PR summary", "risk_document", "risk_mitigate"),
                ]
            ),
            "checks": _checks(
                [
                    ("risks-extracted", str(len(report.risks))),
                    ("approval-gates", "respect existing repo rules"),
                    ("claims-language", "review before demo"),
                ]
            ),
            "guardrails": _guardrails(),
            "capabilities": _capabilities(),
            "evidence": _evidence(report),
            "handoff": _handoff(
                [
                    ("Resolve highest risk first", "resolve_risk", None),
                    ("Add or update tests", "add_tests", "resolve_risk"),
                    ("Refresh CrumbBob pack", "refresh_pack", "add_tests"),
                ]
            ),
        },
        {
            "id": "risk-register",
            "refs": _refs("repo-genome", "session-flight-recorder", "next-task", "test-plan"),
        },
    )

    agent = _crumb(
        "agent",
        "CrumbBob Repo Agent Passport",
        {
            "identity": "role=IBM Bob continuation agent\nmission=Continue from the CrumbBob memory pack without re-discovering solved context.",
            "capabilities": _capabilities(),
            "guardrails": _guardrails(),
            "workflow": _workflow(
                [
                    ("Load Repo Genome before code changes", "agent_load_genome", None),
                    ("Treat Flight Recorder as prior session state", "agent_load_session", "agent_load_genome"),
                    ("Start with Next Task unless user overrides", "agent_start_task", "agent_load_session"),
                    ("Run or update Test Plan", "agent_run_tests", "agent_start_task"),
                    ("Update Risk Register and Proof Chain", "agent_update_memory", "agent_run_tests"),
                ]
            ),
            "script": dedent(
                """
                crumb it:
                1. Read every `.crumb` file in lexical order.
                2. Validate `08_proof_chain.json` hashes before trusting the pack.
                3. Continue from `02_next_task.crumb`.
                4. Run the captured test plan.
                5. Regenerate the pack with `crumdbob pack <input-dir> --out <pack-dir>`.
                """
            ).strip(),
            "evidence": f"{report.summary}\n\nKnown files:\n{files}\n\nKnown commands:\n{commands}",
            "handoff": _handoff(
                [
                    ("Load agent passport", "load_agent_passport", None),
                    ("Follow replay prompt", "follow_replay_prompt", "load_agent_passport"),
                    ("Regenerate proof chain after changes", "agent_refresh_proof", "follow_replay_prompt"),
                ]
            ),
        },
        {
            "id": "agent-passport",
            "refs": _refs("repo-genome", "session-flight-recorder", "next-task", "test-plan", "risk-register"),
        },
    )

    replay = dedent(
        f"""
        # Replay this IBM Bob session

        You are IBM Bob continuing from a previous repo-aware development session.

        Load these files in order:

        1. `00_repo_genome.crumb`
        2. `01_session_flight_recorder.crumb`
        3. `02_next_task.crumb`
        4. `03_test_plan.crumb`
        5. `04_risk_register.crumb`
        6. `05_agent_passport.crumb`
        7. `08_proof_chain.json`

        Continue from the previous Bob findings. Do not re-discover captured context. Validate the current repo state, implement the next task, run the test plan, update the flight recorder, and regenerate the proof chain.

        Project summary: {report.summary}

        Suggested commands:

        ```bash
        crumdbob validate .
        crumdbob graph .
        crumdbob doctor .
        ```
        """
    ).strip() + "\n"

    pr = "\n".join(
        [
            "# PR: Add CrumbBob replay pack",
            "",
            "## Summary",
            "This PR adds a CrumbBob memory pack generated from an IBM Bob repository session.",
            "",
            "## What changed",
            "- Added Repo Genome, Session Flight Recorder, Next Task, Test Plan, Risk Register, Agent Passport, Replay Prompt, PR Summary, and Proof Chain.",
            "- Captured source evidence, continuation workflow, guardrails, capabilities, and CRUMB dependency links.",
            "- Added hash-bound provenance so reviewers can trace generated files back to the Bob report.",
            "",
            "## Why",
            "IBM Bob can understand a repository during a session. CrumbBob makes that understanding portable and replayable.",
            "",
            "## Validation",
            tests,
        ]
    ).strip() + "\n"

    return [
        PackFile("00_repo_genome.crumb", repo_genome),
        PackFile("01_session_flight_recorder.crumb", session),
        PackFile("02_next_task.crumb", next_task),
        PackFile("03_test_plan.crumb", test_plan),
        PackFile("04_risk_register.crumb", risk_register),
        PackFile("05_agent_passport.crumb", agent),
        PackFile("06_replay_prompt.md", replay),
        PackFile("07_pr_summary.md", pr),
    ]


def _proof_chain(report: BobReport, generated: list[PackFile], timestamp: str) -> str:
    source_hash, source_bytes = _source_hash(report.source_path, report.raw_text)
    generated_files = []
    for item in generated:
        sha256, size = _content_hash(item.content)
        generated_files.append({"path": item.path, "sha256": sha256, "bytes": size})

    source_artifacts = []
    for artifact in report.source_artifacts:
        sha256, size = _content_hash(artifact.text)
        source_artifacts.append(
            {
                "path": artifact.path,
                "kind": artifact.kind,
                "sha256": sha256,
                "bytes": size,
                "lines": len(artifact.text.splitlines()),
            }
        )

    proof = {
        "schema": "crumdbob.proof-chain.v1",
        "timestamp_utc": timestamp,
        "crumdbob_version": __version__,
        "source_report": {
            "path": report.source_path,
            "sha256": source_hash,
            "bytes": source_bytes,
        },
        "source_artifacts": source_artifacts,
        "generated_files": generated_files,
        "extracted_counts": {
            "files": len(report.files),
            "commands": len(report.commands),
            "risks": len(report.risks),
            "tests": len(report.tests),
            "next_steps": len(report.next_steps),
        },
        "notes": [
            "generated_files excludes 08_proof_chain.json to avoid recursive self-hashing.",
            "Re-run CrumbBob after source report or pack changes to refresh this proof chain.",
        ],
    }
    return json.dumps(proof, indent=2, sort_keys=True) + "\n"


def generate_pack(report: BobReport, timestamp: str | None = None) -> list[PackFile]:
    generated = _base_pack(report)
    proof = _proof_chain(report, generated, timestamp or _timestamp())
    return [*generated, PackFile("08_proof_chain.json", proof)]


def write_report_pack(report: BobReport, out_dir: str | Path, timestamp: str | None = None) -> list[Path]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    written = []
    for item in generate_pack(report, timestamp=timestamp):
        target = output / item.path
        target.write_text(item.content, encoding="utf-8")
        written.append(target)
    return written


def write_pack(report_path: str | Path, out_dir: str | Path, timestamp: str | None = None) -> list[Path]:
    return write_report_pack(parse_bob_report(report_path), out_dir, timestamp=timestamp)


def write_pack_from_directory(input_dir: str | Path, out_dir: str | Path, timestamp: str | None = None) -> list[Path]:
    source = Path(input_dir)
    report_path = source / "bob-report.md"
    if not report_path.exists():
        raise FileNotFoundError(f"missing required Bob report: {report_path}")
    report = parse_bob_report(report_path)
    for filename, kind in OPTIONAL_INPUTS:
        artifact_path = source / filename
        if artifact_path.exists():
            enrich_report_with_artifact(report, artifact_path, kind=kind)
    return write_report_pack(report, out_dir, timestamp=timestamp)


def read_replay_prompt(pack_dir: str | Path) -> str:
    return (Path(pack_dir) / "06_replay_prompt.md").read_text(encoding="utf-8")


def read_pr_summary(pack_dir: str | Path) -> str:
    return (Path(pack_dir) / "07_pr_summary.md").read_text(encoding="utf-8")
