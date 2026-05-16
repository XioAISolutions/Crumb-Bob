from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$")
FILE_RE = re.compile(
    r"(?:^|[\s`'\"])([A-Za-z0-9_.@-]+(?:/[A-Za-z0-9_.@-]+)+(?:\.(?:ts|tsx|js|jsx|py|md|json|toml|yaml|yml|mjs|cjs|sql|css|html|sh|env|txt))?)(?:$|[\s`'\".,:;)])"
)
COMMAND_RE = re.compile(
    r"\b(?:pnpm|npm|yarn|python|pytest|vitest|turbo|node|uvicorn|docker|git|pip)\s+[^\n`]+"
)
RISK_WORDS = (
    "risk",
    "fragile",
    "unclear",
    "missing",
    "manual",
    "todo",
    "gap",
    "blocker",
    "assumption",
)
TEST_WORDS = ("test", "smoke", "typecheck", "lint", "build", "pytest", "vitest", "coverage")
NEXT_WORDS = ("next", "recommend", "todo", "implement", "improve", "fix", "add", "create", "ship")

_RISK_RE = re.compile(r"\b(?:" + "|".join(RISK_WORDS) + r")\b", re.IGNORECASE)
_TEST_RE = re.compile(r"\b(?:" + "|".join(TEST_WORDS) + r")\b", re.IGNORECASE)
_NEXT_RE = re.compile(r"\b(?:" + "|".join(NEXT_WORDS) + r")\b", re.IGNORECASE)

# Cap per-category extraction so CRUMB files stay concise and scannable.
MAX_SIGNALS = 12


@dataclass(frozen=True)
class SourceArtifact:
    path: str
    kind: str
    text: str


@dataclass
class BobReport:
    source_path: str
    title: str = "IBM Bob Session"
    summary: str = ""
    sections: dict[str, list[str]] = field(default_factory=dict)
    bullets: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    source_artifacts: list[SourceArtifact] = field(default_factory=list)
    raw_text: str = ""


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).strip("` ")


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        cleaned = _clean(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _first_paragraph(lines: list[str]) -> str:
    chunk: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if chunk:
                break
            continue
        if stripped.startswith("#"):
            continue
        chunk.append(stripped)
    return _clean(" ".join(chunk))


def extract_signals(text: str) -> dict[str, list[str]]:
    bullets: list[str] = []
    files: list[str] = []
    commands: list[str] = []
    signal_lines: list[str] = []
    for line in text.splitlines():
        cleaned = _clean(line)
        if cleaned:
            signal_lines.append(cleaned)
        bullet = BULLET_RE.match(line)
        if bullet:
            bullets.append(bullet.group(1))
        for match in FILE_RE.finditer(line):
            files.append(match.group(1))
        for match in COMMAND_RE.finditer(line):
            commands.append(match.group(0).strip())
    base_lines = bullets or signal_lines
    return {
        "bullets": _dedupe(bullets),
        "files": _dedupe(files),
        "commands": _dedupe(commands),
        "risks": _dedupe(line for line in base_lines if _RISK_RE.search(line)),
        "tests": _dedupe(line for line in base_lines if _TEST_RE.search(line)),
        "next_steps": _dedupe(line for line in base_lines if _NEXT_RE.search(line)),
    }


def enrich_report_with_artifact(
    report: BobReport, path: str | Path, kind: str | None = None
) -> None:
    """Mutate *report* in place with signals extracted from an additional artifact."""
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    artifact = SourceArtifact(path=str(source), kind=kind or source.name, text=text)
    signals = extract_signals(text)
    report.source_artifacts.append(artifact)
    report.raw_text = (
        f"{report.raw_text}\n\n--- {artifact.kind}: {artifact.path} ---\n{text}".strip()
    )
    report.bullets = _dedupe([*report.bullets, *signals["bullets"]])
    report.files = _dedupe([*report.files, *signals["files"]])
    report.commands = _dedupe([*report.commands, *signals["commands"]])
    report.risks = _dedupe([*report.risks, *signals["risks"]])[:MAX_SIGNALS]
    report.tests = _dedupe([*report.tests, *signals["tests"]])[:MAX_SIGNALS]
    report.next_steps = _dedupe([*report.next_steps, *signals["next_steps"]])[:MAX_SIGNALS]


def parse_bob_report(path: str | Path) -> BobReport:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    report = BobReport(source_path=str(source), raw_text=text)
    current = "overview"
    report.sections[current] = []
    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            title = _clean(heading.group(2))
            if report.title == "IBM Bob Session":
                report.title = title
            current = title.lower().replace("/", " ").replace("&", "and")
            current = re.sub(r"[^a-z0-9]+", "-", current).strip("-") or "section"
            report.sections.setdefault(current, [])
            continue
        report.sections.setdefault(current, []).append(line)
        bullet = BULLET_RE.match(line)
        if bullet:
            report.bullets.append(bullet.group(1))
        for match in FILE_RE.finditer(line):
            report.files.append(match.group(1))
        for match in COMMAND_RE.finditer(line):
            report.commands.append(match.group(0).strip())
    report.summary = (
        _first_paragraph(lines)
        or "IBM Bob analyzed the repository and produced a reusable development report."
    )
    report.bullets = _dedupe(report.bullets)
    report.files = _dedupe(report.files)
    report.commands = _dedupe(report.commands)
    signal_lines = report.bullets or [_clean(line) for line in lines if _clean(line)]
    report.risks = _dedupe(line for line in signal_lines if _RISK_RE.search(line))[:MAX_SIGNALS]
    report.tests = _dedupe(line for line in signal_lines if _TEST_RE.search(line))[:MAX_SIGNALS]
    report.next_steps = _dedupe(line for line in signal_lines if _NEXT_RE.search(line))[
        :MAX_SIGNALS
    ]
    return report
