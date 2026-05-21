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
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.atomic_io import atomic_write_text
from _common.parsing import iter_slices as _iter_slices_common
from _common.parsing import load_slice as _load_slice_common
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

# Inbox 2026-05-18 `spec-workflow/transition/status-marker-clobber` —
# anchor the slice's prose STATUS marker to the START of a line so
# quoted prose like `` `**STATUS: DRAFT**` `` inside a deviation log
# (preceded by a backtick or other character) doesn't get matched and
# rewritten as if it were the slice's own status line. The canonical
# shape is `**STATUS: VALUE**` starting at column 0, optionally followed
# by a trailing italic annotation like ` _(deferred — gated on …)_`
# (many legacy DEFERRED slices use this form, e.g. 005-02, 006-02,
# 007-04, 012-02, 014-02, 017-04). Only `^**` is anchored — trailing
# content after the closing `**` is allowed. Hit on slice 030-01
# (frontmatter-only slice with no real prose marker, where the regex
# matched the FIRST prose-quoted marker and clobbered it). All five
# sites in this file share this constant.
_STATUS_MARKER_RE = re.compile(r"(?m)^(\*\*STATUS:\s*)([A-Z_]+)(\*\*)")

# Slice 029-02: visible marker prepended to a slice's row when the slice's
# frontmatter carries `kind: spike`. Single emoji (no schema churn — see
# spec 029 Open question #3 lean), recomputed at render time from each
# slice's `kind:` field (so the marker is never the source of truth; the
# slice frontmatter is). Manual edits to the board that strip the marker
# are re-added on the next regen; manual edits to a slice's `kind:` field
# propagate on the next regen.
SPIKE_MARKER = "\U0001f52c"  # 🔬


class WorkflowError(RuntimeError):
    """Raised for user-facing workflow errors (CLI exits non-zero)."""


class StatusBoardRaceError(WorkflowError):
    """Slice 028-03: raised when `regenerate_status_board` detects that
    `docs/specs/README.md` changed on disk between pre-regen checksum
    and pre-write checksum (another worktree's regen ran in the gap).

    Caught explicitly in `main()` and surfaces as exit code 4 (after the
    0/1/2/3 conventions; see also `StatusBoardRaceError` reference in
    SKILL.md). Bypassable via the `--force` flag / `force=True` kwarg.
    """


# Slice 028-03: module-level helper extracted so tests can monkeypatch
# `_checksum` to inject deterministic mid-regen mutations
# (`patch.object(_wf, "_checksum", side_effect=[pre, post])`). SHA256 on
# read bytes (not mtime+size — mtime is coarse on some filesystems;
# SHA256 on a few-KB README is cheap and bulletproof).
def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_slice(spec_path, slice_fragment: str):
    """Resolve a slice fragment to a `SliceLocation` (path / text / start
    / end / label), dual-read across slice files and `## Slice` sections.
    Re-raises `SliceLookupError` as `WorkflowError` to keep CLI messages
    consistent.

    Slice 018-02 migration: replaced `find_slice_section(text, fragment)`
    + manual `read_text()` with this helper. Write-side callers use
    `atomic_write_text(loc.path, new_text)` (slice 032-01) to write back
    to whichever file the slice lives in (slice file or spec.md).
    """
    try:
        return _load_slice_common(spec_path, slice_fragment)
    except SliceLookupError as e:
        raise WorkflowError(str(e)) from e


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


_SLICE_HEADING_LINE_RE = re.compile(r"(?m)^##\s+Slice[^\n]*\n")


def _split_slice_section(section: str) -> tuple:
    """Split a slice section into (head_chunk, body_chunk).

    Two layouts (slice 018-02):
    - **Embedded** (section comes from a `## Slice ...` block inside
      spec.md): section starts with the heading line; frontmatter, if
      present, follows it. `head_chunk` is the heading line (including
      trailing `\\n`); `body_chunk` is everything after.
    - **Slice-file** (section is a whole `slice-*.md` file): file
      starts with a `---\\n...---\\n` frontmatter block; the heading
      appears later. `head_chunk` is empty so that `body_chunk` is the
      full file — `parse_frontmatter(body_chunk)` will then locate the
      frontmatter at column 0 as designed.

    Detection: if the section starts with `## Slice`, it's embedded;
    otherwise treat it as slice-file (or as a section with no header,
    in which case the whole thing is body)."""
    if section.startswith("##"):
        nl = section.find("\n")
        if nl < 0:
            return section, ""
        return section[: nl + 1], section[nl + 1:]
    # Slice-file layout (or no header at all) — body is the full section
    # so frontmatter parsing / writing operates on the canonical location.
    return "", section


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


# Slice 031-02: tokens treated as truthy in the `arch_review:` frontmatter
# field. Lowercase comparison; anything else is false. Spec 031-02 AC #1
# only names `true` explicitly, but we accept the YAML-permissive set
# (`true | yes | on | 1`) so a slice author's hand-edit isn't punished by
# token choice. PyYAML is not a jig dependency, so the set is hardcoded.
_ARCH_REVIEW_TRUTHY = ("true", "yes", "on", "1")


def slice_needs_arch_review(spec_path, slice_fragment: str) -> bool:
    """Return True iff the slice's frontmatter declares `arch_review: true`
    (or any of the lower-cased truthy tokens in `_ARCH_REVIEW_TRUTHY`:
    `true` / `yes` / `on` / `1`).

    Slice 031-02 AC #4: this helper drives the orchestrator's decision
    to spawn the on-demand arch-review pass. Defaults to False when:
      - the slice's frontmatter is absent entirely
      - the `arch_review:` field is absent
      - the value is anything other than a recognized truthy token

    Layout-aware via `_slice_frontmatter`: works for both file-per-slice
    (frontmatter at top of slice file) and legacy embedded slices
    (frontmatter inside the `## Slice` section). Consistent with how
    `collect_slices` / `compute_spec_status` / `_lookup_slice_status`
    read slice-level frontmatter elsewhere in this module.

    Raises WorkflowError on slice lookup failures (missing spec,
    unknown slice, ambiguous fragment) — the orchestrator must surface
    those as gating errors, not silently default to False.
    """
    loc = load_slice(spec_path, slice_fragment)
    fields, _ = _slice_frontmatter(loc.text[loc.start:loc.end])
    raw = fields.get("arch_review", "")
    if isinstance(raw, str):
        return raw.strip().lower() in _ARCH_REVIEW_TRUTHY
    # Defensive: list/other YAML shapes never indicate a boolean.
    return False


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
    """Walk every spec under specs_dir (both layouts via iter_slices),
    return the status of the slice whose label contains `fragment`.
    Returns None if not found. A slice can depend on an earlier slice
    in the same spec.

    Slice 018-02: uses `iter_slices` so dependency-validation sees
    file-per-slice slices, not just `## Slice` sections inside spec.md.
    """
    if not specs_dir.is_dir():
        return None
    needle = fragment.lower()
    for spec_md in sorted(specs_dir.glob("*/spec.md")):
        for loc in _iter_slices_common(spec_md):
            if needle not in loc.label.lower():
                continue
            section = loc.text[loc.start:loc.end]
            # Prefer frontmatter status, fall back to prose marker.
            fields, _ = _slice_frontmatter(section)
            if "status" in fields and fields["status"]:
                return fields["status"]
            m = _STATUS_MARKER_RE.search(section)
            if m:
                return m.group(2)
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

    loc = load_slice(spec_md, slice_fragment)
    section = loc.text[loc.start:loc.end]

    fm_fields, _ = _slice_frontmatter(section)
    has_frontmatter = bool(fm_fields)

    # Slice 014-02: DEFERRED can only transition to DRAFT (re-open) or
    # stay DEFERRED (idempotent). Other outbound transitions are refused
    # so the lifecycle gates (review, reconcile) aren't silently skipped.
    current_status = None
    if has_frontmatter and fm_fields.get("status"):
        current_status = fm_fields["status"]
    else:
        sm = _STATUS_MARKER_RE.search(section)
        if sm:
            current_status = sm.group(2)
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

    m = _STATUS_MARKER_RE.search(section)
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

    # Slice 018-02: `loc.label` is already the resolved slice label from
    # the common parser. Earlier code derived it by re-parsing the first
    # line of `new_section`, which broke for slice-file layout (first
    # line is `---`, not `## Slice ...`).
    slice_name = loc.label

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

    new_text = loc.text[:loc.start] + new_section + loc.text[loc.end:]
    # Slice 018-02: write back to whichever file the slice lives in —
    # `loc.path` is the slice file when dual-read picked it, or spec.md
    # otherwise. Same behavior for legacy specs, correct behavior for
    # file-per-slice ones.
    # Slice 032-01: atomic via _common.atomic_io to avoid torn writes on
    # interrupted transitions.
    atomic_write_text(loc.path, new_text)

    # Slice 030-01: roll up spec.md's frontmatter `status:` from the
    # current slice states. Idempotent — no-op when the rollup matches
    # what's already in spec.md (or when spec.md has no frontmatter).
    # Ordered AFTER the slice write so the rollup reflects the new state.
    _write_spec_rollup(spec_md)

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


def compute_spec_status(spec_path: Path) -> str:
    """Slice 030-01: derive the spec-level rollup from slice states.

    Returns one of "DRAFT", "IN_PROGRESS", "DONE":
      - No slices at all                                        → DRAFT
      - All slices DEFERRED                                     → DRAFT
      - All non-DEFERRED slices are DRAFT                       → DRAFT
      - At least one non-DEFERRED slice AND every non-DEFERRED
        slice has status DONE                                   → DONE
      - Anything else (mix of DONE+DRAFT, any IN_PROGRESS,
        REVIEWED, RECONCILED, READY_FOR_REVIEW, ...)            → IN_PROGRESS

    Pure function: reads spec slices via `iter_slices` (dual-layout,
    matches `collect_slices`'s status-read pattern). Defensive: a spec.md
    without frontmatter still gets a computed status — the WRITE step
    (handled by callers `transition` / `status-board`) is what's skipped
    on missing frontmatter, not the compute.
    """
    statuses = []
    for loc in _iter_slices_common(spec_path):
        section = loc.text[loc.start:loc.end]
        fm_fields, _ = _slice_frontmatter(section)
        if fm_fields.get("status"):
            statuses.append(fm_fields["status"])
            continue
        m = _STATUS_MARKER_RE.search(section)
        if m:
            statuses.append(m.group(2))

    # No slices at all → DRAFT
    if not statuses:
        return "DRAFT"

    non_deferred = [s for s in statuses if s != "DEFERRED"]

    # Every slice is DEFERRED → DRAFT (no live work)
    if not non_deferred:
        return "DRAFT"

    # Every non-DEFERRED slice is DONE → DONE
    if all(s == "DONE" for s in non_deferred):
        return "DONE"

    # Every non-DEFERRED slice is DRAFT → DRAFT (no work begun)
    if all(s == "DRAFT" for s in non_deferred):
        return "DRAFT"

    # Mix of DONE + DRAFT, or any active state → IN_PROGRESS
    return "IN_PROGRESS"


def _write_spec_rollup(spec_path: Path) -> bool:
    """Slice 030-01: idempotently update spec.md's frontmatter `status:`
    field to the computed rollup. Returns True if the file was written
    (rollup value changed), False otherwise.

    Defensive — when spec.md has NO frontmatter block at all, return
    False without writing (no frontmatter insertion; lazy-migration
    consistent with slice 015-01).
    """
    if not spec_path.is_file():
        return False
    text = spec_path.read_text()
    fields, _ = parse_frontmatter(text)
    if not fields:
        # No frontmatter block → leave the file alone (defensive).
        return False
    computed = compute_spec_status(spec_path)
    current = fields.get("status", "")
    if current == computed:
        return False
    new_text = set_frontmatter_field(text, "status", computed)
    if new_text == text:
        return False
    atomic_write_text(spec_path, new_text)
    return True


def collect_slices(project_dir: Path) -> list:
    """Walk docs/specs/*/spec.md and collect (spec_dir, slice_label, status,
    resolution_trigger, kind) tuples in file order. resolution_trigger is
    the empty string when the slice is not DEFERRED (or simply has no
    `**Resolution trigger:**` line). `kind` is the slice's frontmatter
    `kind:` value (slice 029-01: `"spike"` / `"feature"` / `""` for
    unset). Slice 029-02 reads this to drive the marker in
    `render_status_table` — recomputed every regen from the slice's
    frontmatter, so the marker is never stored separately."""
    specs_dir = project_dir / "docs" / "specs"
    if not specs_dir.is_dir():
        return []
    rows = []
    for spec_md in sorted(specs_dir.glob("*/spec.md")):
        spec_dir = spec_md.parent.name
        # Slice 018-02: walk both layouts via the common iterator. Slice
        # files come first (sorted by filename), then embedded sections in
        # spec.md document order — deterministic display.
        for loc in _iter_slices_common(spec_md):
            section = loc.text[loc.start:loc.end]
            # Layout-aware status read: frontmatter at top (slice file)
            # OR after the heading line (embedded section).
            fm_fields, _ = _slice_frontmatter(section)
            status = None
            if fm_fields.get("status"):
                status = fm_fields["status"]
            else:
                sm = _STATUS_MARKER_RE.search(section)
                if sm:
                    status = sm.group(2)
            trigger = (_extract_resolution_trigger(section)
                       if status == "DEFERRED" else "")
            # Slice 029-02: read `kind:` from frontmatter (slice 029-01
            # convention). Defaults to "" when unset — same as feature.
            kind = str(fm_fields.get("kind", "")).strip()
            rows.append(
                (spec_dir, loc.label, status or "UNKNOWN", trigger, kind),
            )
    return rows


def parse_existing_notes(existing: str) -> dict:
    """Extract a {(spec_dir, slice_label): notes_text} map from the current
    board's table. Used to preserve curated Notes across regen — the workflow's
    most valuable per-row content (test counts, review state, links).

    Slice 029-02: the slice cell may be marker-prefixed (`🔬 <label>`) for
    spike rows. The marker is stripped when computing the lookup key so
    notes-preservation is stable across marker comes/goes (e.g. a slice
    whose `kind:` changes between regens, or a user who hand-strips the
    marker on the board — see AC #2).
    """
    notes_map = {}
    # Match `| [spec-link]... | slice | status | notes |` rows; preamble + headers skipped.
    # Two constraints are load-bearing for not gluing adjacent rows together:
    #   1. `[^\S\n]*` (horizontal whitespace only) between the status cell and
    #      the notes cell — prevents `\s*` from consuming `\n` and continuing
    #      the match onto the NEXT line when the current row has 3 cells (e.g.
    #      rows from the `## Deferred slices` table, shape `| spec | slice |
    #      trigger |`).
    #   2. `[^|\n]*?` for the notes cell — rejects already-corrupted rows whose
    #      notes cell contains pipes (the sign of a previously-glued row). Clean
    #      notes never contain a raw `|` by convention (SKILL.md gotcha lists
    #      `&#124;` as the escape).
    row_pattern = re.compile(
        r"^\|\s*\[([^\]]+)\][^|]*\|\s*([^|]+?)\s*\|\s*[^|]+\|[^\S\n]*([^|\n]*?)\s*\|\s*$",
        re.MULTILINE,
    )
    for m in row_pattern.finditer(existing):
        spec_dir = m.group(1).strip()
        label = m.group(2).strip()
        notes = m.group(3).strip()
        # Skip the header row ("Spec" / "Slice" / "Status" / "Notes")
        if spec_dir.lower() == "spec":
            continue
        # Slice 029-02: strip a leading `SPIKE_MARKER ` prefix so the
        # lookup key is the unmarked label. Without this, a hand-curated
        # note on a spike row would orphan whenever the marker comes
        # or goes across regens.
        if label.startswith(SPIKE_MARKER):
            label = label[len(SPIKE_MARKER):].lstrip()
        notes_map[(spec_dir, label)] = notes
    return notes_map


def render_status_table(rows: list, notes_map: dict = None) -> str:
    """Build the Markdown table for the status board. `notes_map` carries
    Notes from the prior version of the board, looked up by (spec_dir, label).
    Tolerates 3-tuple (legacy), 4-tuple (slice 014-02), and 5-tuple
    (slice 029-02, with `kind`) row shapes.

    Slice 029-02: when a row's `kind == "spike"`, the slice cell is
    prepended with the `SPIKE_MARKER` glyph + a space. The marker is a
    pure rendering concern — `notes_map` is keyed by the unmarked label
    so curated notes survive across runs where the marker comes or goes.
    """
    notes_map = notes_map or {}
    lines = ["| Spec | Slice | Status | Notes |", "|------|-------|--------|-------|"]
    for row in rows:
        spec_dir, label, status = row[0], row[1], row[2]
        kind = row[4] if len(row) >= 5 else ""
        spec_link = f"[{spec_dir}]({spec_dir}/spec.md)"
        status_cell = f"**{status}**" if status == "DONE" else status
        notes = notes_map.get((spec_dir, label), "")
        # Slice 029-02: prepend the spike marker on the slice cell only
        # when the slice's `kind == "spike"`. Single-emoji + space prefix;
        # no schema churn, no new column.
        if kind == "spike":
            slice_cell = f"{SPIKE_MARKER} {label}"
        else:
            slice_cell = label
        lines.append(f"| {spec_link} | {slice_cell} | {status_cell} | {notes} |")
    return "\n".join(lines) + "\n"


_DEFERRED_HEADING = "## Deferred slices"


def render_deferred_table(rows: list) -> str:
    """Slice 014-02: separate table for `DEFERRED` slices with the
    Resolution trigger as the per-row context. Returns the empty string
    when no rows are deferred (so the section is fully omitted, not
    rendered as a heading with an empty table).

    Slice 029-02: tolerates the 5-tuple row shape and prepends the
    `SPIKE_MARKER` glyph for `kind == "spike"` rows so DEFERRED spikes
    are visually consistent with active spikes in the upper table.
    Falls back to no-marker rendering for legacy 3- or 4-tuple rows
    (no kind field available)."""
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
        kind = row[4] if len(row) >= 5 else ""
        spec_link = f"[{spec_dir}]({spec_dir}/spec.md)"
        slice_cell = f"{SPIKE_MARKER} {label}" if kind == "spike" else label
        lines.append(f"| {spec_link} | {slice_cell} | {trigger} |")
    return "\n".join(lines) + "\n"


def regenerate_status_board(project_dir: Path, force: bool = False) -> str:
    """Regenerate docs/specs/README.md table from spec.md files.
    Preserves preamble before the first `| Spec` line AND Notes column
    content from the existing table. Slice 014-02: appends a separate
    `## Deferred slices` table after the active table when any slice
    is in `DEFERRED`. Slice 030-01: also writes the spec.md `status:`
    rollup for each walked spec (idempotent — only writes when the
    computed value differs from what's currently in spec.md frontmatter,
    and skipped for spec.md files without frontmatter). Idempotent.

    Slice 028-03: checksum-based race-detection guard. The helper
    captures the pre-regen SHA256 of `docs/specs/README.md` and
    re-checksums immediately before the write. If the two checksums
    differ, another writer regenerated the board in the gap; the helper
    raises `StatusBoardRaceError` rather than silently overwriting.
    Surfaces as exit code 4 via `main()`. The `--force` flag (or
    `force=True` kwarg) bypasses the check and writes anyway.

    Spec-rollup writes (`_write_spec_rollup`) are NOT under the race
    check — they touch individual spec.md files (not the README) and
    happen before the race window opens.
    """
    board_path = project_dir / "docs" / "specs" / "README.md"
    if not board_path.is_file():
        raise WorkflowError(f"status board not found: {board_path}")

    existing = board_path.read_text()
    # Slice 028-03 AC #1: capture pre-regen checksum so we can detect a
    # mid-regen mutation by another writer. Skipped when `force=True`
    # since a forced overwrite intentionally bypasses the guard.
    pre_checksum = None if force else _checksum(board_path)
    notes_map = parse_existing_notes(existing)

    rows = collect_slices(project_dir)
    new_table = render_status_table(rows, notes_map)
    deferred_section = render_deferred_table(rows)

    # Slice 030-01: roll up spec-level status to spec.md frontmatter for
    # every spec walked. Side-effect of regen — independent of whether
    # the board's table text itself changed, so a spec whose frontmatter
    # drifted from its slice states still gets corrected. Idempotent
    # per spec via `_write_spec_rollup`.
    specs_dir = project_dir / "docs" / "specs"
    if specs_dir.is_dir():
        for spec_md in sorted(specs_dir.glob("*/spec.md")):
            _write_spec_rollup(spec_md)

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
    # Slice 028-03 AC #2: re-checksum right before the write. If the file
    # changed between the pre-regen read and now, another writer raced us
    # — refuse rather than silently overwrite their work. Skipped on
    # `--force` (the operator explicitly opted in to an overwrite).
    # Stale-checksum false-positive: if a concurrent writer rewrote the
    # README with identical content, SHA256 stays the same → no race
    # detected → write proceeds. Content-based check correctly treats
    # "same content" as "no race" (documented behavior, not a bug).
    if not force:
        post_checksum = _checksum(board_path)
        if post_checksum != pre_checksum:
            raise StatusBoardRaceError(
                "status board changed during regen — another writer may "
                "have run. Re-run `workflow.py status-board` to retry."
            )
    atomic_write_text(board_path, new_content)
    return (f"regenerated status board: {len(rows)} slice(s) across "
            f"{len({r[0] for r in rows})} spec(s)")


def _resolve_dep_path(dep: str, project_dir: Path) -> Path:
    """Map a dep token to its underlying doc file. Returns None if the
    token shape is unrecognized or no file matches.

    Slice 018-02: for slice deps, walk both layouts via `iter_slices`
    and return the file the slice actually lives in (slice-NN-*.md
    when file-per-slice, spec.md when embedded). Staleness checks
    against this path then reflect the right mtime.
    """
    slice_m = re.match(r"^(\d{3})-(\d{2})$", dep)
    adr_m = re.match(r"(?i)^adr-(\d{1,4})$", dep)
    if slice_m:
        spec_num = slice_m.group(1)
        specs_dir = project_dir / "docs" / "specs"
        needle = dep.lower()
        for spec_md in sorted(specs_dir.glob(f"{spec_num}-*/spec.md")):
            for loc in _iter_slices_common(spec_md):
                if needle in loc.label.lower():
                    return loc.path
        return None
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

    # Slices: walk every slice in every spec dir, both layouts (018-02).
    specs_dir = project_dir / "docs" / "specs"
    if specs_dir.is_dir():
        for spec_md in sorted(specs_dir.glob("*/spec.md")):
            for loc in _iter_slices_common(spec_md):
                section = loc.text[loc.start:loc.end]
                # Layout-aware frontmatter read (handles both shapes).
                fm, _ = _slice_frontmatter(section)
                lv = fm.get("last_verified", "").strip()
                deps = fm.get("dependencies") or []
                if not lv or not deps:
                    continue
                # Display path: prefer the slice file's relative path
                # when the slice lives in its own file; fall back to
                # spec.md :: Slice label for embedded layout.
                if loc.path != spec_md:
                    rel = loc.path.relative_to(project_dir)
                    display = str(rel)
                else:
                    rel_spec = spec_md.relative_to(project_dir)
                    display = f"{rel_spec} :: Slice {loc.label}"
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


# ---------- Slice 003-03: reserve-spec-on-main ----------

# Valid slug shape: starts with lowercase letter; lowercase letters,
# digits, hyphens; no `--` (which would create empty path segments after
# any future split-on-hyphen). Mirrors the convention used across all
# existing `docs/specs/NNN-<slug>/` directories.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# Stderr substrings (case-insensitive) that classify a `git push` failure
# as a protection / permission refusal — these trigger the PR-fallback
# path (AC #3). Anything else is treated as a hard error (race-on-push
# gets its own classifier via _PUSH_RACE_SIGNALS).
_PUSH_PROTECTION_SIGNALS = (
    "protected branch",
    "permission denied",
    "pre-receive hook declined",
    "not authorized",
    "cannot lock ref",
)

# Stderr substrings that classify a `git push origin main` failure as a
# race (someone else advanced main in the gap between fetch and push).
# Structurally distinct from protection refusal: PR-fallback would still
# fail; the right recovery is to re-run after picking the next free
# number (AC #6).
_PUSH_RACE_SIGNALS = (
    "non-fast-forward",
    "fetch first",
    "[rejected]",
    "rejected",
)


def _title_case_slug(slug: str) -> str:
    """Spec AC #2: `parallel-worktree-collision` → `Parallel-worktree collision`.

    Replace the LAST hyphen with a space (so the slug reads as
    `<adjective-chain> <noun>`), then capitalize only the first letter.
    Single-token slugs (no hyphens) just get a capital first letter.
    """
    if "-" in slug:
        head, tail = slug.rsplit("-", 1)
        joined = f"{head} {tail}"
    else:
        joined = slug
    if not joined:
        return joined
    return joined[0].upper() + joined[1:]


def _next_spec_number(specs_dir: Path) -> int:
    """Scan `specs_dir` for `NNN-*/` entries; return max(NNN) + 1.
    Ignores non-spec entries (README.md, files, dirs that don't start
    with three digits + hyphen). Returns 1 when the directory is empty."""
    max_n = 0
    if not specs_dir.is_dir():
        return 1
    for entry in specs_dir.iterdir():
        if not entry.is_dir():
            continue
        m = re.match(r"^(\d{3})-", entry.name)
        if m:
            n = int(m.group(1))
            if n > max_n:
                max_n = n
    return max_n + 1


def _render_stub_spec(num_str: str, slug: str, today_iso: str) -> str:
    """Build the spec.md stub body. Header-only — slice bodies live in
    sibling `slice-NN-*.md` files (slice 018-03).

    Note: kept `## SPIDR analysis` as a placeholder section name in the
    legacy stub through 018-02. Slice 018-03 renames it to
    `## Decomposition` (matching jig's own spec.md prose convention)
    and adds a `## Slices` link section that points to the starter
    slice file emitted alongside this spec.md."""
    title = _title_case_slug(slug)
    starter_slice_fragment = f"{num_str}-01"
    starter_slice_filename = "slice-01-tbd.md"
    return (
        "---\n"
        "status: DRAFT\n"
        "skill:\n"
        "---\n"
        "\n"
        f"# Spec {num_str}: {title}\n"
        "\n"
        f"> Reserved on {today_iso} via `workflow.py new`. "
        "Body to be drafted in a feature branch.\n"
        "\n"
        "## Overview\n"
        "\n"
        "_TBD_\n"
        "\n"
        "## Decomposition\n"
        "\n"
        "_TBD — SPIDR analysis. See SKILL.md for the five axes "
        "(Spike / Paths / Interfaces / Data / Rules)._\n"
        "\n"
        "## Slices\n"
        "\n"
        f"- [{starter_slice_fragment} — tbd]({starter_slice_filename})\n"
    )


def _render_stub_slice(num_str: str, slice_num: str = "01",
                       name: str = "tbd") -> str:
    """Build a starter slice file body from `templates/docs/specs/
    slice-template.md`. Substitutes `{{NUMBER}}` → `<spec_num>-<slice_num>`
    and `{{NAME}}` → `name`. Returns the rendered text.

    Falls back to an inline minimal template when the file template
    isn't reachable (e.g. running the helper outside the jig tree)."""
    template_path = (Path(__file__).resolve().parents[2]
                     / "templates" / "docs" / "specs" / "slice-template.md")
    fragment = f"{num_str}-{slice_num}"
    try:
        body = template_path.read_text()
    except OSError:
        # Inline fallback — keeps the helper functional even when the
        # template file isn't on disk (e.g. minimal scaffold smoke tests).
        body = (
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified:\n---\n"
            "\n## Slice {{NUMBER}} — {{NAME}}\n\n"
            "**Goal:** _TBD_\n"
        )
    return body.replace("{{NUMBER}}", fragment).replace("{{NAME}}", name)


def _run(argv: list, cwd: Path) -> tuple:
    """Run a subprocess and return (returncode, stdout, stderr).

    Uses module-level `subprocess.run` so tests can patch it via
    `patch.object(_workflow, "subprocess")`. Mirrors the
    `_run_git_cmd` / `_run_gh_cmd` shape from skills/slice-land/land.py
    (ADR-0003 — inline-mirror until a third caller emerges)."""
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, cwd=str(cwd),
        )
    except FileNotFoundError:
        return 127, "", f"{argv[0]}: not found on PATH"
    return result.returncode, result.stdout or "", result.stderr or ""


def _classify_push_failure(stderr: str) -> str:
    """Classify a `git push origin main` stderr into one of:
      - "protection" — protected branch / permission denied / ...
      - "race" — non-fast-forward / fetch first / rejected
      - "other" — connection refused, DNS errors, anything else

    Case-insensitive substring match. Race wins over protection if both
    appear (race recovery requires the stranded commit drop)."""
    low = stderr.lower()
    for sig in _PUSH_RACE_SIGNALS:
        if sig in low:
            return "race"
    for sig in _PUSH_PROTECTION_SIGNALS:
        if sig in low:
            return "protection"
    return "other"


def _validate_slug(slug: str) -> None:
    """Raise WorkflowError naming both the slug and the violated rule.
    AC #5: bad slug refusal happens before any mutation."""
    if not slug:
        raise WorkflowError("invalid slug: empty (rule: must start "
                            "with [a-z], no '--')")
    if "--" in slug:
        raise WorkflowError(
            f"invalid slug {slug!r}: contains '--' "
            f"(rule: no consecutive hyphens)"
        )
    if not _SLUG_RE.match(slug):
        raise WorkflowError(
            f"invalid slug {slug!r}: must match {_SLUG_RE.pattern} "
            f"(lowercase letters, digits, hyphens; starts with letter)"
        )


def _preflight_branch_and_worktree(project_dir: Path) -> None:
    """AC #5: refuse if current branch != main, or worktree is dirty.
    Both checks happen before any file mutation."""
    rc, stdout, stderr = _run(
        ["git", "symbolic-ref", "--short", "HEAD"], cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"could not determine current branch (git: {stderr.strip()})"
        )
    branch = stdout.strip()
    if branch != "main":
        raise WorkflowError(
            f"refusing: current branch is {branch!r}, must be 'main' "
            f"(reservation lands on main; switch with `git checkout main`)"
        )

    rc, stdout, _stderr = _run(
        ["git", "status", "--porcelain"], cwd=project_dir,
    )
    if rc != 0:
        # Non-fatal if status itself fails — but if it's truly broken,
        # downstream git commands will fail anyway. Treat as clean.
        return
    if stdout.strip():
        raise WorkflowError(
            "refusing: working tree has uncommitted changes (rule: "
            "clean worktree required). Run `git status` to see them, "
            "then stash or commit before reserving."
        )


def _check_gh_and_remote(project_dir: Path) -> None:
    """AC #4 prereqs: `gh` on PATH AND `origin` URL contains `github.com`.
    Mirrors the slice-land 007-03 guard precedent."""
    if shutil.which("gh") is None:
        raise WorkflowError(
            "refusing PR-fallback: 'gh' CLI not found on PATH. "
            "Install GitHub CLI (https://cli.github.com/) or re-run "
            "with `--no-push` to commit locally only."
        )
    rc, stdout, stderr = _run(
        ["git", "config", "--get", "remote.origin.url"], cwd=project_dir,
    )
    if rc != 0 or not stdout.strip():
        raise WorkflowError(
            "refusing PR-fallback: no 'origin' remote configured "
            f"(git: {stderr.strip() or 'empty url'})"
        )
    url = stdout.strip()
    if "github.com" not in url:
        raise WorkflowError(
            f"refusing PR-fallback: remote 'origin' does not point at "
            f"github.com (url: {url}). PR-fallback requires a GitHub "
            f"remote; re-run with `--no-push` for local-only commit."
        )


def _do_pr_fallback(project_dir: Path, branch_name: str,
                    num_str: str, slug: str,
                    pr_body: str) -> None:
    """AC #4 — branch-and-PR sequence. Any step's failure aborts and
    surfaces what state the user's repo is left in.

    Sequence:
      1. git branch <branch> HEAD
      2. git reset --hard origin/main (un-strand local main)
      3. git checkout <branch>
      4. git push -u origin <branch>
      5. gh pr create --title ... --body ...
    """
    _check_gh_and_remote(project_dir)

    # 1. Create the branch at the reservation commit.
    rc, _out, err = _run(
        ["git", "branch", branch_name, "HEAD"], cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback failed at `git branch {branch_name} HEAD`: "
            f"{err.strip()}. The reservation commit is still on local main; "
            f"re-run after fixing, or `git reset --hard origin/main` to drop it."
        )

    # 2. Reset local main so it no longer carries the stranded commit.
    rc, _out, err = _run(
        ["git", "reset", "--hard", "origin/main"], cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback failed at `git reset --hard origin/main`: "
            f"{err.strip()}. The reservation commit lives on local "
            f"{branch_name!r}; check `git log {branch_name}` to confirm "
            f"before pushing manually."
        )

    # 3. Switch to the reservation branch.
    rc, _out, err = _run(
        ["git", "checkout", branch_name], cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback failed at `git checkout {branch_name}`: "
            f"{err.strip()}. The branch exists locally; switch to it "
            f"manually with `git checkout {branch_name}`."
        )

    # 4. Push the branch to origin.
    rc, _out, err = _run(
        ["git", "push", "-u", "origin", branch_name], cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback failed at `git push -u origin {branch_name}`: "
            f"{err.strip()}. The reservation commit lives on local "
            f"{branch_name!r}; push manually once the remote allows it."
        )

    # 5. Open the PR.
    title = f"docs(specs): reserve {num_str}-{slug}"
    rc, out, err = _run(
        ["gh", "pr", "create", "--title", title, "--body", pr_body],
        cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback failed at `gh pr create`: {err.strip()}. "
            f"The branch is already pushed to origin/{branch_name}; "
            f"open the PR manually via the GitHub web UI."
        )
    pr_url = out.strip()
    if pr_url:
        print(pr_url)


def reserve_spec(slug: str, project_dir: Path,
                 no_push: bool = False, pr_mode: bool = False) -> int:
    """Slice 003-03 entry point. Reserve the next free spec number by
    committing a stub spec.md and (by default) pushing it to origin/main.

    Returns the intended process exit code (0 on success). Raises
    WorkflowError for refusals — main() converts these to exit 2.
    """
    # AC #5 (bad-slug) — refuse BEFORE any other check. Bad slug is the
    # cheapest failure to surface and shouldn't waste git invocations.
    _validate_slug(slug)

    # AC #5 (specs-dir-absent) — the helper only makes sense inside a
    # scaffolded jig project.
    specs_dir = project_dir / "docs" / "specs"
    if not specs_dir.is_dir():
        raise WorkflowError(
            f"refusing: docs/specs/ not found under {project_dir} "
            f"(not inside a scaffolded jig project)"
        )

    # AC #5 (not-on-main, dirty-worktree) — applies even to `--no-push`
    # so the reservation commit always lands on a clean main.
    _preflight_branch_and_worktree(project_dir)

    # Fetch origin/main first (AC #1) so the next-number scan reflects
    # the freshest state. Skipped for --no-push (no remote contract).
    if not no_push:
        rc, _out, err = _run(
            ["git", "fetch", "origin", "main"], cwd=project_dir,
        )
        # A failed fetch isn't fatal — we still proceed with the local
        # view. The push step will catch any out-of-date condition via
        # the race-on-push classifier (AC #6).
        if rc != 0:
            sys.stderr.write(
                f"warning: `git fetch origin main` failed: "
                f"{err.strip()}; proceeding with local view\n"
            )

    # Compute the next number AFTER the fetch so we pick up any specs
    # that landed in the gap.
    next_n = _next_spec_number(specs_dir)
    num_str = f"{next_n:03d}"
    spec_dirname = f"{num_str}-{slug}"
    spec_dir = specs_dir / spec_dirname

    # Defensive: if the target dir already exists, refuse rather than
    # overwrite. This shouldn't happen in practice (we just computed
    # max + 1) but guards against unexpected race-with-self.
    if spec_dir.exists():
        raise WorkflowError(
            f"refusing: {spec_dir} already exists. Re-run after "
            f"resolving the conflict."
        )

    # Write the stub (slice 018-03: spec.md header + starter slice file).
    spec_dir.mkdir(parents=True)
    spec_md = spec_dir / "spec.md"
    today_iso = _today()
    atomic_write_text(spec_md, _render_stub_spec(num_str, slug, today_iso))
    starter_slice = spec_dir / "slice-01-tbd.md"
    atomic_write_text(starter_slice, _render_stub_slice(num_str))

    # Stage + commit locally.
    rel_spec = f"docs/specs/{spec_dirname}/spec.md"
    rel_slice = f"docs/specs/{spec_dirname}/slice-01-tbd.md"
    rc, _out, err = _run(["git", "add", rel_spec, rel_slice], cwd=project_dir)
    if rc != 0:
        raise WorkflowError(
            f"`git add {rel_spec} {rel_slice}` failed: {err.strip()}. "
            f"The stub files are on disk; stage and commit manually."
        )
    commit_msg = f"docs(specs): reserve {spec_dirname}"
    rc, _out, err = _run(
        ["git", "commit", "-m", commit_msg], cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"`git commit` failed: {err.strip()}. "
            f"The stub spec.md is staged; commit manually."
        )

    # Print the success line BEFORE any push so users see the
    # reservation even on subsequent push failure.
    print(f"reserved {spec_dirname}")
    print(str(spec_md.resolve()))

    # AC #7 — `--no-push` stops here.
    if no_push:
        return 0

    pr_body = _build_pr_body(num_str, slug, project_dir)
    branch_name = f"reserve/{spec_dirname}"

    # AC #7 — `--pr` skips the direct-push attempt entirely.
    if pr_mode:
        _do_pr_fallback(project_dir, branch_name, num_str, slug, pr_body)
        return 0

    # AC #3 — default: try direct push first.
    rc, _out, err = _run(
        ["git", "push", "origin", "main"], cwd=project_dir,
    )
    if rc == 0:
        print(f"reserved {spec_dirname} on origin/main")
        return 0

    kind = _classify_push_failure(err)
    if kind == "race":
        # AC #6 — drop the stranded commit so re-run starts clean.
        sys.stderr.write(
            f"race detected: origin/main advanced during reservation. "
            f"Re-run 'workflow.py new {slug}' to pick the next free "
            f"number.\n"
        )
        _reset_rc, _reset_out, _reset_err = _run(
            ["git", "reset", "--hard", "HEAD~1"], cwd=project_dir,
        )
        # Refinement-todo (slice 003-03 review): `git reset --hard HEAD~1`
        # un-strands the commit but leaves the now-empty spec dir on disk.
        # Functionally harmless (`_next_spec_number` works either way) but
        # untidy and surfaces as a "dirty worktree" smell on `git status`.
        # Remove it unconditionally on race recovery; harmless if it's
        # somehow already gone.
        shutil.rmtree(spec_dir, ignore_errors=True)
        # Even if reset fails, the race signal already fired — surface
        # the original push failure to the user.
        raise WorkflowError(
            f"race-on-push: {err.strip()}"
        )

    if kind == "protection":
        # AC #4 — fall back to branch + PR.
        sys.stderr.write(
            f"direct push refused ({err.strip()}); falling back to "
            f"PR mode...\n"
        )
        _do_pr_fallback(project_dir, branch_name, num_str, slug, pr_body)
        return 0

    # AC #3 — anything else: hard error; leave commit in place.
    raise WorkflowError(
        f"`git push origin main` failed: {err.strip()} "
        f"(local commit left in place; inspect with `git log -1` "
        f"and decide how to recover)."
    )


def _build_pr_body(num_str: str, slug: str, project_dir: Path) -> str:
    """Compose a PR body explaining the reservation purpose, naming the
    slot, and pointing reviewers at this slice for context."""
    return (
        f"Reserves spec number `{num_str}` for slug `{slug}` on the "
        f"shared trunk, so parallel worktrees cannot both claim the "
        f"same `NNN`.\n"
        f"\n"
        f"This PR adds stubs `docs/specs/{num_str}-{slug}/spec.md` "
        f"(header + `## Overview` / `## Decomposition` / `## Slices` "
        f"placeholders) and `slice-01-tbd.md` (starter slice file). "
        f"The actual spec body and slice contents will be drafted in "
        f"a separate feature branch.\n"
        f"\n"
        f"Generated by `workflow.py new {slug}` "
        f"(see spec 003-03 reserve-spec-on-main for rationale).\n"
    )


# ---------- end slice 003-03 ----------


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
    # Slice 028-03: bypass the checksum-based race-detection guard.
    # Use when you intentionally want to overwrite a concurrent writer's
    # output (e.g., after manually resolving a known conflict).
    pb.add_argument("--force", action="store_true",
                    help="bypass the race-detection guard and overwrite even "
                         "if docs/specs/README.md changed mid-regen "
                         "(slice 028-03)")

    ps = sub.add_parser(
        "stale",
        help="list slices/ADRs whose last_verified is > N days old AND "
             "whose dependencies have changed since",
    )
    ps.add_argument("--project-dir", default=".",
                    help="project root directory (default: cwd)")
    ps.add_argument("--days", type=int, default=90,
                    help="staleness threshold in days (default: 90)")

    pn = sub.add_parser(
        "new",
        help="reserve the next free spec number on origin/main (slice 003-03)",
    )
    pn.add_argument("slug",
                    help="slug for the new spec (matches ^[a-z][a-z0-9-]*$, "
                         "no '--')")
    pn.add_argument("--project-dir", default=".",
                    help="project root directory (default: cwd)")
    mx = pn.add_mutually_exclusive_group()
    mx.add_argument("--no-push", action="store_true",
                    help="commit locally only; skip fetch / push entirely")
    mx.add_argument("--pr", action="store_true", dest="pr_mode",
                    help="skip direct-push; go straight to branch + PR")

    # Slice 031-02: orchestrator queries whether a slice opted into the
    # on-demand arch-review pass via its `arch_review:` frontmatter flag.
    pa = sub.add_parser(
        "arch-review-needed",
        help="print 'true' if the slice's frontmatter declares "
             "`arch_review: true`; 'false' otherwise (slice 031-02)",
    )
    pa.add_argument("spec", help="path to spec.md")
    pa.add_argument("slice",
                    help="slice name or fragment (case-insensitive substring)")
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
            summary = regenerate_status_board(Path(ns.project), force=ns.force)
            print(summary)
        elif ns.command == "stale":
            report = stale(Path(ns.project_dir), days=ns.days)
            sys.stdout.write(report)
        elif ns.command == "new":
            return reserve_spec(
                ns.slug,
                project_dir=Path(ns.project_dir).resolve(),
                no_push=ns.no_push,
                pr_mode=ns.pr_mode,
            )
        elif ns.command == "arch-review-needed":
            needed = slice_needs_arch_review(Path(ns.spec), ns.slice)
            sys.stdout.write("true\n" if needed else "false\n")
    except StatusBoardRaceError as exc:
        # Slice 028-03 AC #3: dedicated exit code 4 for status-board race.
        # Must be caught before the generic `WorkflowError → 2` handler so
        # the more specific subclass routes here. 3 is taken by scaffold /
        # migrate (config-conflict / unmanaged-hooks); 4 is next free.
        sys.stderr.write(f"{exc}\n")
        return 4
    except WorkflowError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"workflow.py failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
