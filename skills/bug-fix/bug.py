#!/usr/bin/env python3
"""
jig bug-fix helper — spec 058-02 core.

Deterministic file mutations for bug records. The host skill owns judgment and
subagent orchestration; this helper handles local numbering, triage fields,
the bug board, and local claim/release bookkeeping.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.atomic_io import atomic_write_text
from _common.parsing import (
    clear_frontmatter_field,
    parse_frontmatter,
    set_frontmatter_field,
)

VALID_TIERS = ("trivial", "standard", "gnarly")
OPEN_STATUSES = {
    "REPORTED",
    "DIAGNOSING",
    "ROOT_CAUSED",
    "FIXING",
    "REVIEWED",
    "VERIFIED",
}


class BugError(RuntimeError):
    """User-facing helper error."""


def _today() -> str:
    return datetime.date.today().isoformat()


def _bugs_dir(project_dir: Path) -> Path:
    return project_dir / "docs" / "bugs"


def _slugify(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if not slug:
        raise BugError("slug must contain at least one letter or number")
    return slug


def _current_branch(project_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    branch = result.stdout.strip()
    return branch or None


def _claim_identifier(project_dir: Path) -> str:
    env = os.environ.get("JIG_CLAIM_ID")
    if env and env.strip():
        return env.strip()
    return _current_branch(project_dir) or "detached"


def _next_number(bugs_dir: Path) -> int:
    highest = 0
    if bugs_dir.is_dir():
        for path in bugs_dir.glob("*.md"):
            match = re.match(r"^(\d{3})-", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def _is_bug_record(path: Path) -> bool:
    return re.fullmatch(r"\d{3}-.+\.md", path.name) is not None


def _resolve_bug(project_dir: Path, ident: str) -> Path:
    bugs_dir = _bugs_dir(project_dir)
    if not bugs_dir.is_dir():
        raise BugError(f"bug directory not found: {bugs_dir}")
    raw = ident.strip()
    candidate = Path(raw)
    if candidate.suffix == ".md" and candidate.is_file():
        resolved_candidate = candidate.resolve()
        resolved_bugs_dir = bugs_dir.resolve()
        if resolved_candidate.parent != resolved_bugs_dir:
            raise BugError(
                f"direct bug paths must live under {resolved_bugs_dir}"
            )
        if not _is_bug_record(resolved_candidate):
            raise BugError(
                "direct bug paths must name a NNN-slug.md record under "
                f"{resolved_bugs_dir}"
            )
        return resolved_candidate
    if re.fullmatch(r"\d+", raw):
        prefix = f"{int(raw):03d}-"
    else:
        prefix = raw.removesuffix(".md")
        if not prefix.endswith("-"):
            prefix += "-"
    matches = sorted(
        p for p in bugs_dir.glob("*.md")
        if _is_bug_record(p)
        and (p.name == raw or p.stem == raw or p.name.startswith(prefix))
    )
    if not matches:
        raise BugError(f"bug not found: {ident}")
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        raise BugError(f"ambiguous bug id {ident!r}: {names}")
    return matches[0]


def _bug_id_and_slug(path: Path) -> tuple[str, str]:
    match = re.match(r"^(\d{3})-(.+)\.md$", path.name)
    if not match:
        raise BugError(f"invalid bug filename: {path.name}")
    return match.group(1), match.group(2)


def _record_text(number: int, slug: str, claimed_by: str) -> str:
    fields = [
        "---",
        "status: REPORTED",
        "tier:",
        "severity:",
        f"claimed_by: {claimed_by}",
        "regression_test:",
        "red_confirmed_at:",
        "green_confirmed_at:",
        "fix_class:",
        "security_surface: false",
        "escalated_to:",
        "---",
        "",
        f"# Bug {number:03d}: {slug}",
        "",
        "## Symptom",
        "",
        "## Repro",
        "",
        "## Evidence",
        "",
        "## Hypotheses",
        "",
        "## Root cause",
        "",
        "## Fix class",
        "",
        "## Fix",
        "",
        "## Already tried",
        "",
        "## Regression test",
        "",
        "## Proof",
        "",
        "## Learning",
        "",
    ]
    return "\n".join(fields)


def new_bug(project_dir: Path, slug: str) -> Path:
    slug = _slugify(slug)
    bugs_dir = _bugs_dir(project_dir)
    bugs_dir.mkdir(parents=True, exist_ok=True)
    number = _next_number(bugs_dir)
    path = bugs_dir / f"{number:03d}-{slug}.md"
    if path.exists():
        raise BugError(f"bug record already exists: {path}")
    atomic_write_text(path, _record_text(number, slug, _claim_identifier(project_dir)))
    return path


def triage_bug(project_dir: Path, ident: str, tier: str | None,
               severity: str | None) -> Path | None:
    path = _resolve_bug(project_dir, ident)
    text = path.read_text()
    fields, _ = parse_frontmatter(text)
    chosen = (tier or str(fields.get("tier") or "").strip()).lower()
    if chosen not in VALID_TIERS:
        raise BugError(
            "triage requires --tier trivial|standard|gnarly "
            "or an existing tier field"
        )
    if chosen == "trivial":
        path.unlink()
        print(
            "Trivial bug: write the failing test with `tdd-loop`, fix, "
            "commit; no bug record needed."
        )
        return None
    text = set_frontmatter_field(text, "tier", chosen)
    if severity is not None:
        text = set_frontmatter_field(text, "severity", severity)
    atomic_write_text(path, text)
    return path


def _append_release_log(text: str, released_from: str, reason: str) -> str:
    entry = f"- {_today()} - released claim from {released_from}: {reason.strip()}\n"
    body = text.rstrip("\n")
    if "## Release log" in text:
        return body + "\n" + entry
    return body + "\n\n## Release log\n\n" + entry


def pickup_bug(project_dir: Path, ident: str, release: bool = False,
               reason: str | None = None) -> Path:
    if release and not (reason and reason.strip()):
        raise BugError('--release requires --reason "<text>" for the audit trail')
    path = _resolve_bug(project_dir, ident)
    text = path.read_text()
    fields, _ = parse_frontmatter(text)
    existing = str(fields.get("claimed_by") or "").strip()
    status = str(fields.get("status") or "").strip()
    if release:
        released_from = existing or "(unclaimed)"
        text = clear_frontmatter_field(text, "claimed_by")
        text = _append_release_log(text, released_from, reason or "")
        atomic_write_text(path, text)
        return path

    owner = _claim_identifier(project_dir)
    if existing and existing != owner and status in OPEN_STATUSES:
        raise BugError(
            f"bug {path.name} is currently claimed by {existing!r} "
            f"(status {status}). To take it over, have the owner release it, "
            f'or force-release with: bug.py pickup {ident} --release '
            f'--reason "..."'
        )
    text = set_frontmatter_field(text, "claimed_by", owner)
    atomic_write_text(path, text)
    return path


def _parse_existing_notes(existing: str) -> dict[tuple[str, str], str]:
    notes: dict[tuple[str, str], str] = {}
    row_re = re.compile(
        r"^\|\s*(\d{3})\s*\|\s*([^|]+?)\s*\|(?:[^|]*\|){7}\s*([^|\n]*?)\s*\|\s*$",
        re.MULTILINE,
    )
    for match in row_re.finditer(existing):
        bug_id = match.group(1).strip()
        slug = match.group(2).strip()
        note = match.group(3).strip()
        if bug_id == "ID":
            continue
        notes[(bug_id, slug)] = note
    return notes


def _bug_rows(project_dir: Path) -> list[dict[str, str]]:
    bugs_dir = _bugs_dir(project_dir)
    if not bugs_dir.is_dir():
        return []
    rows = []
    for path in sorted(bugs_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        bug_id, slug = _bug_id_and_slug(path)
        fields, _ = parse_frontmatter(path.read_text())
        red = str(fields.get("red_confirmed_at") or "").strip()
        rows.append({
            "id": bug_id,
            "slug": slug,
            "severity": str(fields.get("severity") or "").strip(),
            "tier": str(fields.get("tier") or "").strip(),
            "status": str(fields.get("status") or "").strip(),
            "reproduces": "yes" if red else "no",
            "regression_test": str(fields.get("regression_test") or "").strip(),
            "claimed_by": str(fields.get("claimed_by") or "").strip(),
            "escalated_to": str(fields.get("escalated_to") or "").strip(),
        })
    return rows


def _render_board(rows: list[dict[str, str]],
                  notes: dict[tuple[str, str], str]) -> str:
    lines = [
        "| ID | slug | severity | tier | status | reproduces? | "
        "regression test | claimed_by | escalated_to | Notes |",
        "|----|------|----------|------|--------|-------------|"
        "-----------------|------------|--------------|-------|",
    ]
    for row in rows:
        note = notes.get((row["id"], row["slug"]), "")
        lines.append(
            f"| {row['id']} | {row['slug']} | {row['severity']} | "
            f"{row['tier']} | {row['status']} | {row['reproduces']} | "
            f"{row['regression_test']} | {row['claimed_by']} | "
            f"{row['escalated_to']} | {note} |"
        )
    return "\n".join(lines) + "\n"


def regenerate_status_board(project_dir: Path) -> Path:
    bugs_dir = _bugs_dir(project_dir)
    bugs_dir.mkdir(parents=True, exist_ok=True)
    board = bugs_dir / "README.md"
    existing = board.read_text() if board.exists() else "# Bug Status Board\n\n"
    notes = _parse_existing_notes(existing)
    table_start = existing.find("| ID |")
    preamble = existing[:table_start].rstrip() if table_start != -1 else existing.rstrip()
    if not preamble:
        preamble = "# Bug Status Board"
    content = preamble + "\n\n" + _render_board(_bug_rows(project_dir), notes)
    atomic_write_text(board, content)
    return board


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bug.py")
    project_parent = argparse.ArgumentParser(add_help=False)
    project_parent.add_argument(
        "--project-dir",
        default=".",
        help="project root containing docs/bugs (default: current directory)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    new_p = sub.add_parser(
        "new", parents=[project_parent], help="create a local bug record")
    new_p.add_argument("slug")

    triage_p = sub.add_parser(
        "triage", parents=[project_parent], help="persist or de-escalate tier")
    triage_p.add_argument("id")
    triage_p.add_argument("--tier", choices=VALID_TIERS)
    triage_p.add_argument("--severity")

    pickup_p = sub.add_parser(
        "pickup", parents=[project_parent], help="claim or release a bug record")
    pickup_p.add_argument("id")
    pickup_p.add_argument("--release", action="store_true")
    pickup_p.add_argument("--reason")

    sub.add_parser(
        "status-board",
        parents=[project_parent],
        help="regenerate docs/bugs/README.md",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    project_dir = Path(ns.project_dir).resolve()
    try:
        if ns.command == "new":
            path = new_bug(project_dir, ns.slug)
            print(path.relative_to(project_dir))
        elif ns.command == "triage":
            path = triage_bug(project_dir, ns.id, ns.tier, ns.severity)
            if path is not None:
                print(path.relative_to(project_dir))
            else:
                return 1
        elif ns.command == "pickup":
            path = pickup_bug(project_dir, ns.id, ns.release, ns.reason)
            print(path.relative_to(project_dir))
        elif ns.command == "status-board":
            path = regenerate_status_board(project_dir)
            print(path.relative_to(project_dir))
        else:  # pragma: no cover - argparse enforces this.
            parser.error(f"unknown command: {ns.command}")
    except BugError as exc:
        print(f"bug.py failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
