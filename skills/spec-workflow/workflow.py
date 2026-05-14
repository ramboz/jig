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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.parsing import find_slice_section as _find_slice_section_common
from _common.parsing import SliceLookupError


VALID_STATUSES = (
    "DRAFT",
    "READY_FOR_REVIEW",
    "READY_FOR_IMPLEMENTATION",
    "IN_PROGRESS",
    "REVIEWED",
    "RECONCILED",
    "DONE",
)

# Slice 003-04: auto-tick the review-passed DoD box on the gating
# transition. Maps `new_status` → label-substring (case-insensitive) the
# auto-tick logic looks for in the slice's DoD. Other transitions don't
# tick anything.
_AUTO_TICK_LABELS = {
    "REVIEWED": "implementation review passed",
    "RECONCILED": "reconciliation review passed",
}

# Same regex shape as slice-land's CLOSE_OUT_RE — keep them in sync; slice
# 009-01 established this convention. Boxes inside a `### Close-out (post-DONE)`
# subsection are post-DONE follow-up and NOT eligible for auto-tick.
_CLOSE_OUT_RE = re.compile(r"(?im)^###\s+close[- ]?out\b")


class WorkflowError(RuntimeError):
    """Raised for user-facing workflow errors (CLI exits non-zero)."""


def find_slice_section(spec_text: str, slice_fragment: str) -> tuple:
    """Locate the slice section whose H2 contains `slice_fragment`.
    Returns (start, end) byte offsets into spec_text bounding the slice
    section from header start to next H2 / EOF. Raises WorkflowError on
    miss or ambiguity.

    Thin wrapper over `_common.parsing.find_slice_section`; preserves
    this module's historical 2-tuple return shape and error type.
    """
    try:
        start, end, _label = _find_slice_section_common(spec_text, slice_fragment)
    except SliceLookupError as e:
        raise WorkflowError(str(e)) from e
    return start, end


def _auto_tick_review_box(section: str, label_substring: str) -> tuple:
    """In a slice's section, find the single `- [ ]` (or `- [x]`) checkbox
    whose label contains `label_substring` (case-insensitive) and flip it
    to ticked. Returns (new_section, warning_or_None).

    Behavior:
    - 0 matches → (section, None) — best-effort, no warning. The
      transition still succeeds; auto-tick isn't a gate.
    - 1 match (unticked) → flip to `[x]`; (new_section, None).
    - 1 match (already ticked) → no-op; (section, None) — idempotent.
    - 2+ matches → (section, warning_string), no tick. The user's DoD
      is non-canonical; the helper refuses to guess.

    Excludes any `### Close-out` subsection from the search (slice 009-01
    convention; post-DONE items aren't tickable by transition).
    """
    co = _CLOSE_OUT_RE.search(section)
    dod_region = section[:co.start()] if co else section

    box_re = re.compile(r"(?m)^(\s*-\s+\[)([ xX])(\]\s+)([^\n]*)$")
    matches = [
        cb for cb in box_re.finditer(dod_region)
        if label_substring.lower() in cb.group(4).lower()
    ]

    if len(matches) == 0:
        return section, None
    if len(matches) > 1:
        return section, (
            f"multiple matches for {label_substring!r} in slice DoD; "
            "not auto-ticking — please disambiguate manually"
        )

    cb = matches[0]
    if cb.group(2).lower() == "x":
        return section, None  # already ticked — idempotent

    new_box = cb.group(1) + "x" + cb.group(3) + cb.group(4)
    new_section = section[:cb.start()] + new_box + section[cb.end():]
    return new_section, None


def transition(spec_md: Path, slice_fragment: str, new_status: str) -> str:
    """Transition the named slice's STATUS to `new_status`. Auto-ticks
    "Implementation review passed" on REVIEWED, and "Reconciliation
    review passed" on RECONCILED (slice 003-04). Returns a summary string."""
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

    header_match = re.match(r"##\s+Slice\s+([^\n]+)$",
                            new_section.lstrip().splitlines()[0])
    slice_name = header_match.group(1).strip() if header_match else slice_fragment

    # Slice 003-04: auto-tick the corresponding review-passed DoD box on
    # the two gating transitions. Other transitions don't tick anything.
    auto_tick_label = _AUTO_TICK_LABELS.get(new_status)
    if auto_tick_label:
        new_section, warning = _auto_tick_review_box(new_section, auto_tick_label)
        if warning:
            # AC #5: name the spec and slice in the warning so a CI / log
            # grep can disambiguate which slice triggered it when many
            # specs share the same canonical DoD labels.
            sys.stderr.write(
                f"warning: {spec_md}: slice {slice_name}: {warning}\n"
            )

    new_text = text[:start] + new_section + text[end:]
    spec_md.write_text(new_text)

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
