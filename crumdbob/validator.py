from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SECTION_RE = re.compile(r"^\[([A-Za-z0-9_.:/-]+)\]$")
HEADER_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
ID_RE = re.compile(r"\bid=([A-Za-z0-9_.:-]+)")
DEP_RE = re.compile(r"\b(?:after|depends)=([A-Za-z0-9_.:-]+(?:,[A-Za-z0-9_.:-]+)*)")
CHECK_RE = re.compile(r"^[^:\n][^:\n]*\s::\s\S.*$")

REQUIRED_SECTIONS = {
    "map": {"project", "modules"},
    "task": {"goal", "context", "constraints"},
    "todo": {"tasks"},
    "agent": {"identity"},
    "audit": {"goal", "actions", "verdict"},
}
PACK_RESERVED_IDS = {"proof-chain", "replay-prompt", "pr-summary"}


@dataclass(frozen=True)
class CrumbDocument:
    path: Path
    headers: dict[str, str]
    sections: dict[str, list[str]]

    @property
    def id(self) -> str:
        return self.headers.get("id") or self.path.stem


@dataclass(frozen=True)
class ValidationError:
    path: Path
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class ValidationReport:
    documents: list[CrumbDocument] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def crumb_paths(target: str | Path) -> list[Path]:
    path = Path(target)
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.crumb"))
    return []


def parse_crumb(path: str | Path) -> tuple[CrumbDocument | None, list[ValidationError]]:
    source = Path(path)
    errors: list[ValidationError] = []
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "BEGIN CRUMB":
        errors.append(ValidationError(source, "missing BEGIN CRUMB"))
    if (
        not lines
        or next((line.strip() for line in reversed(lines) if line.strip()), "") != "END CRUMB"
    ):
        errors.append(ValidationError(source, "missing END CRUMB"))

    try:
        divider = lines.index("---")
    except ValueError:
        errors.append(ValidationError(source, "missing header divider ---"))
        return None, errors

    headers: dict[str, str] = {}
    for line in lines[1:divider]:
        if not line.strip():
            continue
        match = HEADER_RE.match(line)
        if not match:
            errors.append(ValidationError(source, f"invalid header line: {line}"))
            continue
        headers[match.group(1)] = match.group(2).strip()

    sections: dict[str, list[str]] = {}
    seen_sections: set[str] = set()
    current: str | None = None
    for line in lines[divider + 1 :]:
        if line.strip() == "END CRUMB":
            break
        section = SECTION_RE.match(line.strip())
        if section:
            current = section.group(1)
            if current in seen_sections:
                errors.append(ValidationError(source, f"duplicate section: [{current}]"))
            seen_sections.add(current)
            sections.setdefault(current, [])
            continue
        if current is None:
            if line.strip():
                errors.append(ValidationError(source, f"content outside section: {line}"))
            continue
        sections[current].append(line)

    return CrumbDocument(source, headers, sections), errors


def _nonempty(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip()]


def _ids_in(lines: list[str]) -> set[str]:
    ids: set[str] = set()
    for line in lines:
        ids.update(ID_RE.findall(line))
    return ids


def _deps_in(line: str) -> list[str]:
    deps: list[str] = []
    for match in DEP_RE.findall(line):
        deps.extend(item.strip() for item in match.split(",") if item.strip())
    return deps


def _refs_in(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _validate_document(
    doc: CrumbDocument, known_ids: set[str], validate_refs: bool
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for header in ("v", "kind", "title", "source"):
        if not doc.headers.get(header):
            errors.append(ValidationError(doc.path, f"missing required header: {header}"))
    if doc.headers.get("v") and doc.headers["v"] != "1.4":
        errors.append(ValidationError(doc.path, "unsupported version: expected v=1.4"))

    kind = doc.headers.get("kind")
    if kind and kind not in REQUIRED_SECTIONS:
        errors.append(ValidationError(doc.path, f"unsupported kind: {kind}"))
    for section in REQUIRED_SECTIONS.get(kind or "", set()):
        if section not in doc.sections or not _nonempty(doc.sections[section]):
            errors.append(ValidationError(doc.path, f"missing required section: [{section}]"))

    if validate_refs:
        for ref in _refs_in(doc.headers.get("refs", "")):
            if ref not in known_ids:
                errors.append(ValidationError(doc.path, f"unknown refs target: {ref}"))

    for line in _nonempty(doc.sections.get("checks", [])):
        if not CHECK_RE.match(line):
            errors.append(
                ValidationError(
                    doc.path, f"invalid [checks] line, expected 'name :: status': {line}"
                )
            )

    for line in _nonempty(doc.sections.get("handoff", [])):
        if not ID_RE.search(line):
            errors.append(ValidationError(doc.path, f"[handoff] line missing id=: {line}"))
        for dependency in _deps_in(line):
            if dependency not in known_ids:
                errors.append(
                    ValidationError(doc.path, f"unknown [handoff] dependency: {dependency}")
                )

    for line in _nonempty(doc.sections.get("workflow", [])):
        if not re.match(r"^\d+[.)]\s+", line):
            errors.append(ValidationError(doc.path, f"[workflow] line must be numbered: {line}"))
        if not ID_RE.search(line):
            errors.append(ValidationError(doc.path, f"[workflow] line missing id=: {line}"))
        for dependency in _deps_in(line):
            if dependency not in known_ids:
                errors.append(
                    ValidationError(doc.path, f"unknown [workflow] dependency: {dependency}")
                )

    return errors


def validate_paths(paths: list[Path]) -> ValidationReport:
    report = ValidationReport()
    for path in paths:
        doc, errors = parse_crumb(path)
        report.errors.extend(errors)
        if doc is not None:
            report.documents.append(doc)

    known_ids = {doc.id for doc in report.documents}
    known_ids.update(doc.path.stem for doc in report.documents)
    if len(report.documents) > 1:
        known_ids.update(PACK_RESERVED_IDS)
    for doc in report.documents:
        known_ids.update(_ids_in(doc.sections.get("handoff", [])))
        known_ids.update(_ids_in(doc.sections.get("workflow", [])))

    for doc in report.documents:
        report.errors.extend(
            _validate_document(doc, known_ids, validate_refs=len(report.documents) > 1)
        )
    return report


def validate_target(target: str | Path) -> ValidationReport:
    paths = crumb_paths(target)
    report = validate_paths(paths)
    if not paths:
        report.errors.append(ValidationError(Path(target), "no .crumb files found"))
    return report


def dependency_edges(target: str | Path) -> tuple[list[tuple[str, str, str]], ValidationReport]:
    report = validate_target(target)
    edges: list[tuple[str, str, str]] = []
    for doc in report.documents:
        source = doc.id
        refs = [item.strip() for item in doc.headers.get("refs", "").split(",") if item.strip()]
        for ref in refs:
            edges.append((source, ref, "refs"))
        for section_name in ("handoff", "workflow"):
            for line in _nonempty(doc.sections.get(section_name, [])):
                item_id = ID_RE.search(line)
                if not item_id:
                    continue
                for dependency in _deps_in(line):
                    edges.append((dependency, item_id.group(1), section_name))
    return edges, report
