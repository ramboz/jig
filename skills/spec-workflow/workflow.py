"""
jig spec-workflow helper — slice 003-01 (lifecycle-helper)

Deterministic state-transition + status-board sync for the spec-driven
workflow. Mirrors the scaffold.py / memory.py pattern: Claude reads the
SKILL.md for judgment-driven steps; this script handles file mutations.

Usage:
    python3 workflow.py transition <spec.md> <slice-name> <new-status>
    python3 workflow.py status-board <project-dir>
"""

import argparse
import os
import re
import sys
from pathlib import Path


VALID_STATUSES = (
    "DRAFT",
    "READY_FOR_REVIEW",
    "READY_FOR_IMPLEMENTATION",
    "IN_PROGRESS",
    "REVIEWED",
    "RECONCILED",
    "DONE",
)


class WorkflowError(RuntimeError):
    """Raised for user-facing workflow errors (CLI exits non-zero)."""


def find_slice_section(spec_text: str, slice_fragment: str) -> tuple:
    """Locate the slice section whose H2 contains `slice_fragment`.
    Returns (start, end) byte offsets into spec_text bounding the slice's
    content (from end-of-header to next H2 / EOF). Raises WorkflowError
    on miss or ambiguity."""
    headers = list(re.finditer(r"(?im)^##\s+Slice\s+[^\n]+$", spec_text))
    if not headers:
        raise WorkflowError("no '## Slice ...' headings found in spec")
    needle = slice_fragment.lower()
    matches = [h for h in headers if needle in h.group(0).lower()]
    if not matches:
        raise WorkflowError(f"slice not found: '{slice_fragment}'")
    if len(matches) > 1:
        names = [h.group(0).strip() for h in matches]
        raise WorkflowError(
            f"ambiguous slice fragment '{slice_fragment}' matches: {names}"
        )
    header = matches[0]
    rest = spec_text[header.end():]
    nxt = re.search(r"(?m)^##\s", rest)
    end = header.end() + (nxt.start() if nxt else len(rest))
    return header.start(), end


def transition(spec_md: Path, slice_fragment: str, new_status: str) -> str:
    """Transition the named slice's STATUS to `new_status`.
    Returns a summary string."""
    if new_status not in VALID_STATUSES:
        raise WorkflowError(
            f"invalid status: '{new_status}'. valid: {', '.join(VALID_STATUSES)}"
        )
    if not spec_md.is_file():
        raise WorkflowError(f"spec file not found: {spec_md}")

    text = spec_md.read_text()
    start, end = find_slice_section(text, slice_fragment)
    section = text[start:end]

    status_pattern = re.compile(r"(\*\*STATUS:\s*)([A-Z_]+)(\*\*)")
    m = status_pattern.search(section)
    if not m:
        raise WorkflowError("no `**STATUS: ...**` marker found in slice section")
    old_status = m.group(2)
    new_section = (
        section[: m.start()]
        + f"{m.group(1)}{new_status}{m.group(3)}"
        + section[m.end():]
    )
    new_text = text[:start] + new_section + text[end:]
    spec_md.write_text(new_text)

    header_match = re.match(r"##\s+Slice\s+([^\n]+)$",
                            new_section.lstrip().splitlines()[0])
    slice_name = header_match.group(1).strip() if header_match else slice_fragment
    return f"transitioned {slice_name}: {old_status} → {new_status}"


def collect_slices(project_dir: Path) -> list:
    """Walk docs/specs/*/spec.md and collect (spec_dir, slice_label, status)
    tuples in file order."""
    specs_dir = project_dir / "docs" / "specs"
    if not specs_dir.is_dir():
        return []
    rows = []
    for spec_md in sorted(specs_dir.glob("*/spec.md")):
        spec_dir = spec_md.parent.name
        text = spec_md.read_text()
        headers = list(re.finditer(r"(?im)^##\s+Slice\s+([^\n]+)$", text))
        for i, h in enumerate(headers):
            label = h.group(1).strip()
            section_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            section = text[h.end():section_end]
            sm = re.search(r"\*\*STATUS:\s*([A-Z_]+)\*\*", section)
            status = sm.group(1) if sm else "UNKNOWN"
            rows.append((spec_dir, label, status))
    return rows


def parse_existing_notes(existing: str) -> dict:
    """Extract a {(spec_dir, slice_label): notes_text} map from the current
    board's table. Used to preserve curated Notes across regen — the workflow's
    most valuable per-row content (test counts, review state, links)."""
    notes_map = {}
    # Match `| [spec-link]... | slice | status | notes |` rows; preamble + headers skipped
    row_pattern = re.compile(
        r"^\|\s*\[([^\]]+)\][^|]*\|\s*([^|]+?)\s*\|\s*[^|]+\|\s*(.*?)\s*\|\s*$",
        re.MULTILINE,
    )
    for m in row_pattern.finditer(existing):
        spec_dir = m.group(1).strip()
        label = m.group(2).strip()
        notes = m.group(3).strip()
        # Skip the header row ("Spec" / "Slice" / "Status" / "Notes")
        if spec_dir.lower() == "spec":
            continue
        notes_map[(spec_dir, label)] = notes
    return notes_map


def render_status_table(rows: list, notes_map: dict = None) -> str:
    """Build the Markdown table for the status board. `notes_map` carries
    Notes from the prior version of the board, looked up by (spec_dir, label)."""
    notes_map = notes_map or {}
    lines = ["| Spec | Slice | Status | Notes |", "|------|-------|--------|-------|"]
    for spec_dir, label, status in rows:
        spec_link = f"[{spec_dir}]({spec_dir}/spec.md)"
        status_cell = f"**{status}**" if status == "DONE" else status
        notes = notes_map.get((spec_dir, label), "")
        lines.append(f"| {spec_link} | {label} | {status_cell} | {notes} |")
    return "\n".join(lines) + "\n"


def regenerate_status_board(project_dir: Path) -> str:
    """Regenerate docs/specs/README.md table from spec.md files.
    Preserves preamble before the first `| Spec` line AND Notes column
    content from the existing table. Idempotent."""
    board_path = project_dir / "docs" / "specs" / "README.md"
    if not board_path.is_file():
        raise WorkflowError(f"status board not found: {board_path}")

    existing = board_path.read_text()
    notes_map = parse_existing_notes(existing)

    rows = collect_slices(project_dir)
    new_table = render_status_table(rows, notes_map)

    m = re.search(r"(?m)^\|\s*Spec\b", existing)
    if m:
        preamble = existing[: m.start()]
    else:
        preamble = existing
        if not preamble.endswith("\n"):
            preamble += "\n"

    new_content = preamble + new_table
    if new_content == existing:
        return "status board already current; no changes"
    board_path.write_text(new_content)
    return (f"regenerated status board: {len(rows)} slice(s) across "
            f"{len({r[0] for r in rows})} spec(s)")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="workflow.py",
                                description="jig spec-workflow helper")
    sub = p.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("transition", help="transition a slice's STATUS marker")
    pt.add_argument("spec", help="path to spec.md")
    pt.add_argument("slice", help="slice name or fragment (case-insensitive substring)")
    pt.add_argument("status", help=f"new status; one of: {', '.join(VALID_STATUSES)}")

    pb = sub.add_parser("status-board",
                        help="regenerate docs/specs/README.md from spec.md files")
    pb.add_argument("project", help="project root directory")
    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        if ns.command == "transition":
            summary = transition(Path(ns.spec), ns.slice, ns.status)
            print(summary)
        elif ns.command == "status-board":
            summary = regenerate_status_board(Path(ns.project))
            print(summary)
    except WorkflowError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"workflow.py failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
