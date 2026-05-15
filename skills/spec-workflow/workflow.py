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
import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.parsing import find_slice_section as _find_slice_section_common
from _common.parsing import (
    SliceLookupError,
    parse_frontmatter,
    set_frontmatter_field,
)


VALID_STATUSES = (
    "DRAFT",
    "READY_FOR_REVIEW",
    "READY_FOR_IMPLEMENTATION",
    "IN_PROGRESS",
    "REVIEWED",
    "RECONCILED",
    "DONE",
    "DEFERRED",
)

# Slice 014-02: only DRAFT (and DEFERRED itself, idempotent) are valid
# outbound transitions from DEFERRED. Re-opening means going back to
# DRAFT and starting the lifecycle over. Other states require explicit
# DRAFT first to avoid silently skipping review gates.
_DEFERRED_ALLOWED_NEXT = ("DRAFT", "DEFERRED")

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


def _split_slice_section(section: str) -> tuple:
    """Split a slice section into (header_line, body) where header_line
    includes the trailing newline (or empty). The body is everything
    after the `## Slice ...` line. The body is the unit frontmatter
    sits in front of."""
    nl = section.find("\n")
    if nl < 0:
        return section, ""
    return section[: nl + 1], section[nl + 1:]


def _today() -> str:
    return datetime.date.today().isoformat()


def _slice_frontmatter(section: str) -> tuple:
    """Returns (fields, body_offset_within_section). body_offset is
    measured from the start of `section` (i.e. includes the header
    line)."""
    _hdr, body = _split_slice_section(section)
    fields, body_off = parse_frontmatter(body)
    header_len = len(section) - len(body)
    return fields, header_len + body_off


def _set_slice_frontmatter_field(section: str, key: str, value) -> str:
    hdr, body = _split_slice_section(section)
    new_body = set_frontmatter_field(body, key, value)
    return hdr + new_body


def _validate_dependencies(deps: list, project_dir: Path,
                           current_spec: Path) -> list:
    """For each dep token, verify it's satisfied. Returns a list of
    human-readable reasons for unsatisfied deps (empty == all good).

    Recognized tokens:
      - `NNN-MM` (slice fragment) — found in any spec, must be DONE.
      - `adr-NNNN` (case-insensitive) — corresponding ADR file under
        docs/decisions/, must show `Accepted` in Status section.

    Unrecognized token shapes are reported as `unknown dependency token`.
    """
    failures = []
    specs_dir = project_dir / "docs" / "specs"
    decisions_dir = project_dir / "docs" / "decisions"

    for dep in deps:
        token = dep.strip()
        if not token:
            continue
        slice_match = re.match(r"^(\d{3})-(\d{2})$", token)
        adr_match = re.match(r"(?i)^adr-(\d{1,4})$", token)
        if slice_match:
            found_status = _lookup_slice_status(specs_dir, token, current_spec)
            if found_status is None:
                failures.append(f"{token}: slice not found in any spec")
            elif found_status != "DONE":
                failures.append(f"{token}: STATUS is {found_status} (not DONE)")
        elif adr_match:
            num = adr_match.group(1).zfill(4)
            ok, reason = _lookup_adr_accepted(decisions_dir, num)
            if not ok:
                failures.append(f"adr-{num}: {reason}")
        else:
            failures.append(f"{token}: unknown dependency token shape")
    return failures


def _lookup_slice_status(specs_dir: Path, fragment: str,
                         current_spec: Path) -> str:
    """Walk every spec.md under specs_dir, return the status of the
    slice whose label contains `fragment`. Returns None if not found.
    Looks at the current spec file too — a slice can depend on an
    earlier slice in the same spec.
    """
    if not specs_dir.is_dir():
        return None
    for spec_md in sorted(specs_dir.glob("*/spec.md")):
        try:
            text = spec_md.read_text()
        except OSError:
            continue
        headers = list(re.finditer(r"(?im)^##\s+Slice\s+([^\n]+)$", text))
        for i, h in enumerate(headers):
            label = h.group(1).strip()
            if fragment.lower() not in label.lower():
                continue
            section_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            section = text[h.start():section_end]
            # Prefer frontmatter status, fall back to prose marker.
            fields, _ = _slice_frontmatter(section)
            if "status" in fields and fields["status"]:
                return fields["status"]
            m = re.search(r"\*\*STATUS:\s*([A-Z_]+)\*\*", section)
            if m:
                return m.group(1)
            return "UNKNOWN"
    return None


def _lookup_adr_accepted(decisions_dir: Path, num: str) -> tuple:
    """Find docs/decisions/adr-<num>-*.md and verify its `## Status`
    section says Accepted. Returns (ok, reason)."""
    if not decisions_dir.is_dir():
        return False, "docs/decisions/ not found"
    candidates = sorted(decisions_dir.glob(f"adr-{num}-*.md"))
    if not candidates:
        return False, "ADR file not found under docs/decisions/"
    adr_text = candidates[0].read_text()
    sm = re.search(r"(?m)^##\s+Status\s*$", adr_text)
    if not sm:
        return False, f"{candidates[0].name} has no '## Status' section"
    rest = adr_text[sm.end():]
    nxt = re.search(r"(?m)^##\s", rest)
    section = rest[: nxt.start()] if nxt else rest
    if re.search(r"(?m)^Accepted\b", section):
        return True, "accepted"
    return False, f"{candidates[0].name} is not Accepted"


def transition(spec_md: Path, slice_fragment: str, new_status: str) -> str:
    """Transition the named slice's STATUS to `new_status`. Auto-ticks
    "Implementation review passed" on REVIEWED, and "Reconciliation
    review passed" on RECONCILED (slice 003-04). When the slice has a
    frontmatter block (slice 014-01), the `status:` field is updated
    too, and `last_verified: <today>` is written on the RECONCILED
    transition. DONE transitions refuse if any `dependencies:` entry
    is unsatisfied. Returns a summary string."""
    if new_status not in VALID_STATUSES:
        raise WorkflowError(
            f"invalid status: '{new_status}'. valid: {', '.join(VALID_STATUSES)}"
        )
    if not spec_md.is_file():
        raise WorkflowError(f"spec file not found: {spec_md}")

    text = spec_md.read_text()
    start, end = find_slice_section(text, slice_fragment)
    section = text[start:end]

    fm_fields, _ = _slice_frontmatter(section)
    has_frontmatter = bool(fm_fields)

    # Slice 014-02: DEFERRED can only transition to DRAFT (re-open) or
    # stay DEFERRED (idempotent). Other outbound transitions are refused
    # so the lifecycle gates (review, reconcile) aren't silently skipped.
    current_status = None
    if has_frontmatter and fm_fields.get("status"):
        current_status = fm_fields["status"]
    else:
        sm = re.search(r"\*\*STATUS:\s*([A-Z_]+)\*\*", section)
        if sm:
            current_status = sm.group(1)
    if current_status == "DEFERRED" and new_status not in _DEFERRED_ALLOWED_NEXT:
        raise WorkflowError(
            f"invalid transition: DEFERRED → {new_status}. "
            f"From DEFERRED, only DRAFT (re-open) is allowed."
        )

    # Pre-flight: DONE transition validates `dependencies:` from frontmatter.
    if new_status == "DONE" and fm_fields.get("dependencies"):
        # docs/specs/<spec-dir>/spec.md → project root is parents[3]:
        # [0]=<spec-dir>, [1]=specs, [2]=docs, [3]=project-root.
        project_dir = spec_md.resolve().parents[3]
        failures = _validate_dependencies(
            fm_fields["dependencies"], project_dir, spec_md,
        )
        if failures:
            joined = "\n  - ".join(failures)
            raise WorkflowError(
                "cannot transition to DONE — unsatisfied dependencies:\n  - "
                + joined
            )

    status_pattern = re.compile(r"(\*\*STATUS:\s*)([A-Z_]+)(\*\*)")
    m = status_pattern.search(section)
    old_status = None
    new_section = section
    if m:
        old_status = m.group(2)
        new_section = (
            section[: m.start()]
            + f"{m.group(1)}{new_status}{m.group(3)}"
            + section[m.end():]
        )
    if has_frontmatter:
        if old_status is None:
            old_status = fm_fields.get("status", "UNKNOWN")
        new_section = _set_slice_frontmatter_field(new_section, "status", new_status)
        if new_status == "RECONCILED":
            new_section = _set_slice_frontmatter_field(
                new_section, "last_verified", _today(),
            )
    if old_status is None:
        raise WorkflowError(
            "no `**STATUS: ...**` marker or frontmatter `status:` field "
            "found in slice section"
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


_RESOLUTION_TRIGGER_RE = re.compile(
    r"(?im)^\*\*Resolution trigger:\*\*\s*([^\n]+)"
)


def _extract_resolution_trigger(section: str) -> str:
    """Slice 014-02: pull the `**Resolution trigger:** ...` line out of a
    slice's body, mirroring the convention used in docs/refinement-todo.md.
    Returns "" when absent."""
    m = _RESOLUTION_TRIGGER_RE.search(section)
    return m.group(1).strip() if m else ""


def collect_slices(project_dir: Path) -> list:
    """Walk docs/specs/*/spec.md and collect (spec_dir, slice_label, status,
    resolution_trigger) tuples in file order. resolution_trigger is the
    empty string when the slice is not DEFERRED (or simply has no
    `**Resolution trigger:**` line)."""
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
            # `section` here is the body AFTER the header line (existing
            # legacy shape); frontmatter parser tolerates leading blank.
            section = text[h.end():section_end]
            # Prefer frontmatter `status:` when present; fall back to
            # prose `**STATUS:**` marker for legacy slices.
            fm_fields, _ = parse_frontmatter(section.lstrip("\n"))
            status = None
            if fm_fields.get("status"):
                status = fm_fields["status"]
            else:
                sm = re.search(r"\*\*STATUS:\s*([A-Z_]+)\*\*", section)
                if sm:
                    status = sm.group(1)
            trigger = (_extract_resolution_trigger(section)
                       if status == "DEFERRED" else "")
            rows.append((spec_dir, label, status or "UNKNOWN", trigger))
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
    Notes from the prior version of the board, looked up by (spec_dir, label).
    Tolerates both 3-tuple (legacy) and 4-tuple (slice 014-02) row shapes."""
    notes_map = notes_map or {}
    lines = ["| Spec | Slice | Status | Notes |", "|------|-------|--------|-------|"]
    for row in rows:
        spec_dir, label, status = row[0], row[1], row[2]
        spec_link = f"[{spec_dir}]({spec_dir}/spec.md)"
        status_cell = f"**{status}**" if status == "DONE" else status
        notes = notes_map.get((spec_dir, label), "")
        lines.append(f"| {spec_link} | {label} | {status_cell} | {notes} |")
    return "\n".join(lines) + "\n"


_DEFERRED_HEADING = "## Deferred slices"


def render_deferred_table(rows: list) -> str:
    """Slice 014-02: separate table for `DEFERRED` slices with the
    Resolution trigger as the per-row context. Returns the empty string
    when no rows are deferred (so the section is fully omitted, not
    rendered as a heading with an empty table)."""
    deferred = [r for r in rows if len(r) >= 3 and r[2] == "DEFERRED"]
    if not deferred:
        return ""
    lines = [
        "",
        _DEFERRED_HEADING,
        "",
        "> Slices parked with a stated resolution trigger. Re-open by "
        "transitioning to DRAFT.",
        "",
        "| Spec | Slice | Resolution trigger |",
        "|------|-------|--------------------|",
    ]
    for row in deferred:
        spec_dir, label = row[0], row[1]
        trigger = row[3] if len(row) >= 4 else ""
        spec_link = f"[{spec_dir}]({spec_dir}/spec.md)"
        lines.append(f"| {spec_link} | {label} | {trigger} |")
    return "\n".join(lines) + "\n"


def regenerate_status_board(project_dir: Path) -> str:
    """Regenerate docs/specs/README.md table from spec.md files.
    Preserves preamble before the first `| Spec` line AND Notes column
    content from the existing table. Slice 014-02: appends a separate
    `## Deferred slices` table after the active table when any slice
    is in `DEFERRED`. Idempotent."""
    board_path = project_dir / "docs" / "specs" / "README.md"
    if not board_path.is_file():
        raise WorkflowError(f"status board not found: {board_path}")

    existing = board_path.read_text()
    notes_map = parse_existing_notes(existing)

    rows = collect_slices(project_dir)
    new_table = render_status_table(rows, notes_map)
    deferred_section = render_deferred_table(rows)

    m = re.search(r"(?m)^\|\s*Spec\b", existing)
    if m:
        preamble = existing[: m.start()]
    else:
        preamble = existing
        if not preamble.endswith("\n"):
            preamble += "\n"

    new_content = preamble + new_table + deferred_section
    if new_content == existing:
        return "status board already current; no changes"
    board_path.write_text(new_content)
    return (f"regenerated status board: {len(rows)} slice(s) across "
            f"{len({r[0] for r in rows})} spec(s)")


def _resolve_dep_path(dep: str, project_dir: Path) -> Path:
    """Map a dep token to its underlying doc file. Returns None if the
    token shape is unrecognized or no file matches."""
    slice_m = re.match(r"^(\d{3})-(\d{2})$", dep)
    adr_m = re.match(r"(?i)^adr-(\d{1,4})$", dep)
    if slice_m:
        spec_num = slice_m.group(1)
        # `docs/specs/<spec_num>-*/spec.md`
        candidates = sorted((project_dir / "docs" / "specs").glob(
            f"{spec_num}-*/spec.md"))
        return candidates[0] if candidates else None
    if adr_m:
        num = adr_m.group(1).zfill(4)
        candidates = sorted((project_dir / "docs" / "decisions").glob(
            f"adr-{num}-*.md"))
        return candidates[0] if candidates else None
    return None


def _file_modified_iso(path: Path) -> str:
    """Return the file's most-recent modification date as YYYY-MM-DD,
    preferring `git log -1 --format=%cs` when inside a git repo (so the
    answer reflects committed state, not local working-copy touches).
    Falls back to filesystem mtime when git is unavailable or the file
    isn't tracked."""
    import subprocess as _sp
    try:
        result = _sp.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            capture_output=True, text=True, cwd=str(path.parent),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, OSError):
        pass
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def _stale_check(item_path: Path, last_verified_str: str,
                 dependencies: list, days: int,
                 project_dir: Path, today: datetime.date) -> tuple:
    """Return ``(is_stale, reason)``. `reason` is a single-line summary
    when stale, otherwise the empty string."""
    try:
        verified = datetime.date.fromisoformat(last_verified_str)
    except ValueError:
        return False, ""
    age_days = (today - verified).days
    if age_days <= days:
        return False, ""
    # Age trigger fired; now check that at least one dep is fresher.
    for dep in dependencies:
        dep_path = _resolve_dep_path(dep.strip(), project_dir)
        if dep_path is None or not dep_path.is_file():
            continue
        dep_date_str = _file_modified_iso(dep_path)
        try:
            dep_date = datetime.date.fromisoformat(dep_date_str)
        except ValueError:
            continue
        if dep_date > verified:
            rel = dep_path.relative_to(project_dir) if dep_path.is_absolute() \
                else dep_path
            return True, (
                f"verified {last_verified_str} ({age_days} days ago); "
                f"dep {rel} modified {dep_date_str}"
            )
    return False, ""


def find_stale_items(project_dir: Path, days: int = 90) -> list:
    """Walk slices and ADRs; return list of (display_path, reason) for
    items that meet the conjunctive staleness criterion. Read-only."""
    today = datetime.date.today()
    out = []

    # Slices: every `## Slice ...` section in docs/specs/*/spec.md
    specs_dir = project_dir / "docs" / "specs"
    if specs_dir.is_dir():
        for spec_md in sorted(specs_dir.glob("*/spec.md")):
            text = spec_md.read_text()
            headers = list(re.finditer(r"(?im)^##\s+Slice\s+([^\n]+)$", text))
            for i, h in enumerate(headers):
                label = h.group(1).strip()
                section_end = (headers[i + 1].start()
                               if i + 1 < len(headers) else len(text))
                section = text[h.end():section_end]
                fm, _ = parse_frontmatter(section.lstrip("\n"))
                lv = fm.get("last_verified", "").strip()
                deps = fm.get("dependencies") or []
                if not lv or not deps:
                    continue
                rel_spec = spec_md.relative_to(project_dir)
                display = f"{rel_spec} :: Slice {label}"
                is_stale, reason = _stale_check(
                    spec_md, lv, deps, days, project_dir, today,
                )
                if is_stale:
                    out.append((display, reason))

    # ADRs: docs/decisions/adr-NNNN-*.md
    decisions_dir = project_dir / "docs" / "decisions"
    if decisions_dir.is_dir():
        for adr_path in sorted(decisions_dir.glob("adr-*.md")):
            if not re.match(r"^adr-\d{4}-", adr_path.name):
                continue
            text = adr_path.read_text()
            fm, _ = parse_frontmatter(text)
            lv = fm.get("last_verified", "").strip()
            deps = fm.get("dependencies") or []
            if not lv or not deps:
                continue
            rel = adr_path.relative_to(project_dir)
            is_stale, reason = _stale_check(
                adr_path, lv, deps, days, project_dir, today,
            )
            if is_stale:
                out.append((str(rel), reason))
    return out


def stale(project_dir: Path, days: int = 90) -> str:
    """Render the stale-items report to a string. Always exits 0;
    the report is informational, never gating."""
    items = find_stale_items(project_dir, days=days)
    if not items:
        return f"no stale items (threshold: {days} days)\n"
    lines = [f"stale items ({len(items)}; threshold: {days} days):"]
    for display, reason in items:
        lines.append(f"  {display}: {reason}")
    return "\n".join(lines) + "\n"


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

    ps = sub.add_parser(
        "stale",
        help="list slices/ADRs whose last_verified is > N days old AND "
             "whose dependencies have changed since",
    )
    ps.add_argument("--project-dir", default=".",
                    help="project root directory (default: cwd)")
    ps.add_argument("--days", type=int, default=90,
                    help="staleness threshold in days (default: 90)")
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
        elif ns.command == "stale":
            report = stale(Path(ns.project_dir), days=ns.days)
            sys.stdout.write(report)
    except WorkflowError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"workflow.py failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
