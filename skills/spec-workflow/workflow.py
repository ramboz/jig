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
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import team_signal  # noqa: F401  (re-exported for test monkeypatching)
from _common.atomic_io import atomic_write_text
from _common.parsing import (
    FRONTMATTER_TRUTHY,
    SliceLookupError,
    check_deviation_log,
    clear_frontmatter_field,
    frontmatter_flag_truthy,
    parse_frontmatter,
    set_frontmatter_field,
)
from _common.parsing import iter_slices as _iter_slices_common
from _common.parsing import load_slice as _load_slice_common
from _common.review_evidence import validate_evidence
from _common.team_signal import team_context_drift

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


def _clear_slice_frontmatter_field(section: str, key: str) -> str:
    """Slice 049-01: drop a frontmatter field from a slice section,
    layout-aware (mirrors `_set_slice_frontmatter_field`)."""
    hdr, body = _split_slice_section(section)
    new_body = clear_frontmatter_field(body, key)
    return hdr + new_body


# Slice 031-02: tokens treated as truthy in the `arch_review:` frontmatter
# field. Slice 045-03 (must-do d) lifted the tuple + the truthiness test
# into `_common.parsing` so this orchestrator reader and
# `review_evidence._arch_review_flag` (the gate's reader) share ONE source
# and cannot drift. The module-level name is kept as an alias to the shared
# constant — pinned to be the SAME object by
# `ArchReviewTruthyUnificationTests` — so prior in-module references stay
# valid while the source of truth is single.
_ARCH_REVIEW_TRUTHY = FRONTMATTER_TRUTHY


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

    Slice 045-03: truthiness now delegates to
    `_common.parsing.frontmatter_flag_truthy` (handles the non-string /
    defensive cases too) so this and the gate share one predicate.
    """
    loc = load_slice(spec_path, slice_fragment)
    fields, _ = _slice_frontmatter(loc.text[loc.start:loc.end])
    return frontmatter_flag_truthy(fields.get("arch_review", ""))


def slice_needs_code_health_review(spec_path, slice_fragment: str) -> bool:
    """Return True iff the slice's frontmatter declares
    `code_health_review: true` (slice 060-05; mirrors
    `slice_needs_arch_review` exactly).

    Drives the orchestrator's decision to spawn the on-demand code-health
    review pass, and keeps the spawner in lock-step with the evidence
    gate's reader (`review_evidence._code_health_review_flag`) via the same
    shared `frontmatter_flag_truthy` predicate. Defaults to False on any
    miss (no frontmatter, field absent, non-truthy value) so every
    existing slice (no flag) is unaffected — the pass is opt-in/gated.

    Layout-aware via `load_slice`; raises WorkflowError on slice lookup
    failures, like `slice_needs_arch_review`.
    """
    loc = load_slice(spec_path, slice_fragment)
    fields, _ = _slice_frontmatter(loc.text[loc.start:loc.end])
    return frontmatter_flag_truthy(fields.get("code_health_review", ""))


# ---------- session-plan: delegation-first dispatch plan (slice 057-01) ----------

# The standard per-slice phase sequence. Each tuple is
# (phase, subagent type, skill) — the orchestrator dispatches each phase to
# the named subagent + skill rather than doing the turn-heavy work itself.
# Each phase is either DELEGATED to a subagent (runs in its own isolated
# context) or an ORCHESTRATOR dispatch step (the orchestrator's own loop).
# Fields: (phase, mode, actor, skill) where mode is "delegate"|"dispatch",
# `actor` is the subagent type for delegated phases (None for dispatch
# steps the orchestrator drives itself), and `skill` is the jig skill the
# phase runs (None when the phase has no skill — e.g. `implement`, which
# the `implementer` *agent* performs). Mirrors CLAUDE.md "Session workflow"
# and docs/workflow.md "Post-implementation review".
# The arch phase is conditional (emitted iff the slice declares
# `arch_review: true`); it is inserted between `craft` and `reconcile`.
# The code-health phase is likewise conditional (emitted iff the slice
# declares `code_health_review: true` — slice 060-05); it is inserted
# after the arch phase (or after craft when no arch) and before reconcile.
_SESSION_PLAN_PHASES = (
    ("implement", "delegate", "implementer", None),
    ("compliance", "delegate", "reviewer", "jig:independent-review"),
    ("craft", "delegate", "reviewer", "pr-review"),
    # arch + code-health (both conditional) inserted here, in that order.
    ("reconcile", "dispatch", None, "jig:independent-review"),
    ("land", "dispatch", None, "jig:slice-land"),
)

_SESSION_PLAN_ARCH_PHASE = ("arch", "delegate", "reviewer", "arch-review")

# Where the conditional arch phase slots into the sequence (after craft).
_SESSION_PLAN_ARCH_AFTER = "craft"

# The conditional code-health phase (slice 060-05). Slots in right after
# the craft block (and after arch, since arch is emitted first).
_SESSION_PLAN_CODE_HEALTH_PHASE = (
    "code-health", "delegate", "reviewer", "jig:code-health")


def _slice_status_from_section(section: str) -> str:
    """Layout-aware status read for a slice section/file — frontmatter
    `status:` first, else the prose `**STATUS: X**` marker. Mirrors the
    read in `collect_slices` / `compute_spec_status`. Returns "" when
    neither is present."""
    fm_fields, _ = _slice_frontmatter(section)
    if fm_fields.get("status"):
        return str(fm_fields["status"])
    sm = _STATUS_MARKER_RE.search(section)
    return sm.group(2) if sm else ""


def session_plan(spec_path: Path) -> str:
    """Slice 057-01: emit a deterministic, delegation-first dispatch plan
    for a spec — each non-DEFERRED slice mapped to its phase sequence
    (implement → compliance → craft → [arch iff `arch_review: true`] →
    reconcile → land) with the subagent type + skill for each phase.

    Pure function of the spec's slices + their frontmatter — no hidden
    state, no side effects on spec/slice files (clarify Q1/Q2: helper
    form, stdout-only). The orchestrator then *dispatches against the
    plan* rather than improvising each step across many turns — cutting
    turn count, the data-confirmed cost driver (cost ∝ turns, r = 0.92).

    Empty / non-standard edge case: a spec with zero non-DEFERRED slices
    prints a clear "no slices to plan" message (with the reason) rather
    than crashing or emitting an empty plan.
    """
    spec_path = Path(spec_path)

    # Enumerate slices via the shared dual-layout iterator, excluding
    # DEFERRED. `arch_review` is read per-slice from its frontmatter via
    # the shared truthy predicate (no hand-rolled truthiness).
    planned = []  # list of (label, needs_arch, needs_code_health)
    total = 0
    for loc in _iter_slices_common(spec_path):
        total += 1
        section = loc.text[loc.start:loc.end]
        status = _slice_status_from_section(section)
        if status == "DEFERRED":
            continue
        fm_fields, _ = _slice_frontmatter(section)
        needs_arch = frontmatter_flag_truthy(fm_fields.get("arch_review", ""))
        needs_code_health = frontmatter_flag_truthy(
            fm_fields.get("code_health_review", ""))
        planned.append((loc.label, needs_arch, needs_code_health))

    lines = []
    lines.append(f"# Session plan — {spec_path}")
    lines.append("")
    # Delegation-first framing + turn-count rationale (AC #2).
    lines.append("Delegation-first dispatch plan. The orchestrator re-reads "
                 "its full context on EVERY turn, so its cost is roughly "
                 "context-size x turn count (the data-confirmed driver: "
                 "cost is proportional to turns, r = 0.92). Push multi-turn "
                 "sub-work into bounded subagents that return compact "
                 "summaries; the orchestrator DISPATCHES each phase below and "
                 "INTEGRATES the result, rather than doing turn-heavy work "
                 "itself.")
    lines.append("")
    lines.append("Each phase is either DELEGATED to a [subagent] (runs in its "
                 "own isolated context) or an ORCHESTRATOR step (the "
                 "orchestrator's own dispatch-and-integrate loop). A phase that "
                 "runs a jig {skill} names it; `implement` runs the "
                 "[implementer] agent (no skill), and `reconcile`/`land` are "
                 "orchestrator-driven steps.")
    lines.append("")

    if not planned:
        if total == 0:
            reason = "this spec has no slices"
        else:
            reason = "every slice is DEFERRED"
        lines.append(f"No slices to plan ({reason}).")
        return "\n".join(lines) + "\n"

    def _render_phase(step, phase, mode, actor, skill, note=""):
        if mode == "delegate":
            head = f"DELEGATE to [{actor}] subagent"
        else:  # dispatch — orchestrator's own loop
            head = "ORCHESTRATOR step"
        if skill:
            head += f", runs {{{skill}}}"
        line = f"  {step}. {phase} — {head}"
        if note:
            line += f"  {note}"
        return line

    for label, needs_arch, needs_code_health in planned:
        lines.append(f"## Slice {label}")
        lines.append("")
        step = 1
        for phase, mode, actor, skill in _SESSION_PLAN_PHASES:
            lines.append(_render_phase(step, phase, mode, actor, skill))
            step += 1
            if phase == _SESSION_PLAN_ARCH_AFTER:
                # arch first (when declared), then code-health — both
                # conditional, both slotted between craft and reconcile.
                if needs_arch:
                    aphase, amode, aactor, askill = _SESSION_PLAN_ARCH_PHASE
                    lines.append(_render_phase(
                        step, aphase, amode, aactor, askill,
                        note="(slice declares arch_review: true)"))
                    step += 1
                if needs_code_health:
                    cphase, cmode, cactor, cskill = \
                        _SESSION_PLAN_CODE_HEALTH_PHASE
                    lines.append(_render_phase(
                        step, cphase, cmode, cactor, cskill,
                        note="(slice declares code_health_review: true)"))
                    step += 1
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


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


# ---------- Slice 045-03: review-evidence transition gate (ADR-0014 §5) ----------

# The states whose transitions are gated on review evidence (ADR-0014 §5).
# REVIEWED → compliance+craft(+arch); RECONCILED → reconciliation + deviation
# log; DONE → the full set re-validated (plus the existing dependency check).
# Every OTHER target — DRAFT / READY_FOR_REVIEW / READY_FOR_IMPLEMENTATION /
# IN_PROGRESS / DEFERRED, the DEFERRED→DRAFT re-open, and the two review
# back-edges (REVIEWED→IN_PROGRESS, RECONCILED→IN_PROGRESS) — relaxes or
# advances status with nothing to gate and is left untouched (AC4).
_EVIDENCE_GATED_STATES = ("REVIEWED", "RECONCILED", "DONE")

# Falsey tokens that disable the gate via `JIG_REVIEW_EVIDENCE_GATE`. The
# gate is ON by default; this is the documented bypass for a deliberate
# actor / automation. Per ADR-0011 (cited by ADR-0014 §6), an in-process
# gate sits inside the agent's trust boundary — it is a *deliberateness*
# signal, not human-only enforcement — so an env-var escape hatch is
# consistent with the model (cf. `JIG_CONVENTIONS_APPROVED`). The
# dependency check on DONE is NOT part of the evidence gate and still runs
# under the bypass.
_GATE_DISABLE_VALUES = ("0", "false", "off", "no")


def _evidence_gate_enabled() -> bool:
    """The review-evidence gate is enabled unless `JIG_REVIEW_EVIDENCE_GATE`
    is set to one of the falsey tokens (case-insensitive)."""
    raw = os.environ.get("JIG_REVIEW_EVIDENCE_GATE")
    if raw is None:
        return True
    return raw.strip().lower() not in _GATE_DISABLE_VALUES


def _gate_evidence(spec_md: Path, slice_fragment: str, section: str,
                   new_status: str) -> None:
    """Enforce the ADR-0014 §5 evidence requirements for a gated transition.

    Raises `WorkflowError` (the user-facing type → CLI exit 2) with a
    diagnostic that names the missing/invalid artifact and the command to
    produce it (AC3). No-op for ungated states or when the gate is disabled.

    Delegates shape/verdict validation to
    `review_evidence.validate_evidence` (the 045-02 validator — single
    source of truth) and the deviation-log presence check to the shared
    `_common.parsing.check_deviation_log` (the 007-01 heading predicate,
    lifted to `_common` by this slice so `land.py` and the gate share it).
    """
    if new_status not in _EVIDENCE_GATED_STATES:
        return
    if not _evidence_gate_enabled():
        return

    diagnostics: list = []
    # REVIEWED-stage evidence is required for REVIEWED and re-validated for
    # DONE (ADR-0014 §5: DONE re-runs REVIEWED + RECONCILED).
    if new_status in ("REVIEWED", "DONE"):
        diagnostics.extend(
            validate_evidence(spec_md, slice_fragment, "REVIEWED")
        )
    # RECONCILED-stage: the reconciliation verdict AND the deviation log,
    # required for RECONCILED and re-validated for DONE.
    if new_status in ("RECONCILED", "DONE"):
        diagnostics.extend(
            validate_evidence(spec_md, slice_fragment, "RECONCILED")
        )
        if not check_deviation_log(section):
            diagnostics.append(
                "[reconciliation] deviation log missing — add a "
                "`### Deviation log` subsection under the slice heading "
                "before reconciling (the reconciliation reviewer attests "
                "its content; the gate only checks presence)"
            )

    if diagnostics:
        joined = "\n  - ".join(diagnostics)
        raise WorkflowError(
            f"cannot transition to {new_status} — review evidence is "
            f"incomplete (ADR-0014 §5):\n  - " + joined
        )


# ---------- Slice 056-03: .jig/spec-ref attribution marker ----------
#
# When a slice begins (transition -> IN_PROGRESS), stamp a working-tree-local
# `.jig/spec-ref` marker so `scripts/usage.py` can map this session's
# transcripts to the exact spec, instead of guessing from content mentions.
#
# Format (simple, line-oriented `key=value`, one per line — both this writer
# and usage.py's reader agree on it):
#
#     spec=056
#     slice=056-03
#
# `spec=` is the three-digit spec number (the attribution key usage.py reads);
# `slice=` records the current slice for human/debug context. The file lives at
# <project-root>/.jig/spec-ref — alongside the tracked `.jig/test-command` —
# and is git-ignored (a scoped `.gitignore` entry, NOT a blanket `.jig/`
# ignore, so the tracked test-command file is unaffected). It is working-tree-
# local on purpose: it reflects what THIS tree is working on and must not
# travel across branches as a tracked file.
IN_PROGRESS_STATUS = "IN_PROGRESS"


def _spec_number_from_label(label: str) -> str:
    """Extract the three-digit spec number from a slice label like
    ``056-03 — foo`` / ``Slice 056-03``. Returns "" when no NNN-NN id is
    present (defensive — the marker write then no-ops via the caller)."""
    m = re.search(r"\b(\d{3})-\d{2}\b", label)
    return m.group(1) if m else ""


def _slice_id_from_label(label: str) -> str:
    """Extract the ``NNN-NN`` slice id from a slice label. Returns "" when
    absent."""
    m = re.search(r"\b(\d{3}-\d{2})\b", label)
    return m.group(1) if m else ""


def _write_spec_ref_marker(spec_md: Path, slice_label: str) -> None:
    """Best-effort: stamp `<project-root>/.jig/spec-ref` with the spec number
    and current slice (slice 056-03). Idempotent — a repeated IN_PROGRESS
    transition rewrites the same bytes via `atomic_write_text`.

    Side-effect-isolated (AC #1 / AC #4): wrapped so ANY failure (unwritable
    `.jig`, a non-dir occupying the path, a permission error, an
    unresolvable project root) is swallowed and the transition — including
    its review-evidence gates — proceeds unaffected. The marker is a
    reporting aid, never a gate.

    Project root is the spec's `parents[3]` (docs/specs/<dir>/spec.md ->
    [0]=<dir>, [1]=specs, [2]=docs, [3]=root), matching the DONE-dependency
    resolution in `transition`.
    """
    try:
        spec_num = _spec_number_from_label(slice_label)
        if not spec_num:
            return  # no recognizable spec number — nothing useful to stamp
        slice_id = _slice_id_from_label(slice_label)
        root = spec_md.resolve().parents[3]
        jig_dir = root / ".jig"
        jig_dir.mkdir(parents=True, exist_ok=True)
        body = f"spec={spec_num}\n"
        if slice_id:
            body += f"slice={slice_id}\n"
        atomic_write_text(jig_dir / "spec-ref", body)
    except Exception:  # noqa: BLE001 — best-effort; never block the transition
        return


def _project_root_for_spec(spec_md: Path) -> Path:
    """Best-effort project root for a `docs/specs/<dir>/spec.md` path
    (= `parents[3]`: [0]=<dir>, [1]=specs, [2]=docs, [3]=root). Slice
    049-01 used a bare `parents[3]`, which raises `IndexError` for a
    shallow / non-standard path (e.g. a test fixture at `/tmp/x/spec.md`
    — only three parents). Degrade gracefully so claim bookkeeping never
    crashes on path depth: fall back to the nearest ancestor containing a
    `.git`, else the spec's own directory. For a real nested spec path the
    result is identical to `parents[3]`."""
    resolved = spec_md.resolve()
    parents = resolved.parents
    if len(parents) > 3:
        return parents[3]
    for anc in parents:
        if (anc / ".git").exists():
            return anc
    return resolved.parent


def transition(spec_md: Path, slice_fragment: str, new_status: str, *,
               push: bool = False, pr_mode: bool = False,
               release: bool = False, reason: str = None) -> str:
    """Transition the named slice's STATUS to `new_status`. Auto-ticks
    "Implementation review passed" on REVIEWED, and "Reconciliation
    review passed" on RECONCILED (slice 003-04). When the slice has a
    frontmatter block (slice 014-01), the `status:` field is updated
    too, and `last_verified: <today>` is written on the RECONCILED
    transition. DONE transitions refuse if any `dependencies:` entry
    is unsatisfied.

    Slice 045-03: REVIEWED / RECONCILED / DONE are gated on review
    evidence (ADR-0014 §5) — the move is refused unless the required
    verdict artifacts exist and clear (and, for RECONCILED/DONE, the
    deviation log is present). The gate is ON by default; bypass with
    `JIG_REVIEW_EVIDENCE_GATE=0`.

    Slice 049-01: → IN_PROGRESS stamps a `claimed_by:` identifier
    (branch name, or `JIG_CLAIM_ID`) and refuses an on-disk foreign
    claim that is still IN_PROGRESS (AC3); `push`/`pr_mode` additionally
    reserve the claim on origin/main so parallel worktrees see it (local
    by default). → REVIEWED / READY_FOR_IMPLEMENTATION / DRAFT clear the
    claim. `release` (with a `reason`) force-clears a stale claim and
    appends a `## Release log` entry. Returns a summary string."""
    if new_status not in VALID_STATUSES:
        raise WorkflowError(
            f"invalid status: '{new_status}'. valid: {', '.join(VALID_STATUSES)}"
        )
    if not spec_md.is_file():
        raise WorkflowError(f"spec file not found: {spec_md}")

    # Slice 049-01: --release requires an audit reason (AC5).
    if release and not (reason and reason.strip()):
        raise WorkflowError(
            '--release requires --reason "<text>" for the audit trail.'
        )

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

    # Slice 049-01: claim context. Claims live in slice frontmatter, so the
    # claim machinery is a no-op for legacy prose-only (no-frontmatter)
    # slices — stamping a field there would synthesize a spurious `---`
    # block. project_dir mirrors the DONE-branch derivation below
    # (docs/specs/<dir>/spec.md → parents[3]), via a depth-safe helper.
    existing_claim = str(fm_fields.get(CLAIM_FIELD) or "").strip()
    claim_identifier = None
    if has_frontmatter and new_status == IN_PROGRESS_STATUS and not release:
        claim_project_dir = _project_root_for_spec(spec_md)
        claim_identifier = _claim_identifier(claim_project_dir)
        # AC3: refuse a foreign claim that is already IN_PROGRESS on disk.
        if (existing_claim and existing_claim != claim_identifier
                and current_status == "IN_PROGRESS"):
            raise WorkflowError(
                f"slice {loc.label} is currently claimed by "
                f"{existing_claim!r} (status IN_PROGRESS). To take it over, "
                f"have the owner release it, or force-release with:\n"
                f"    workflow.py transition <spec> {loc.label} "
                f'READY_FOR_IMPLEMENTATION --release --reason "..."'
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

    # Slice 045-03: gate REVIEWED / RECONCILED / DONE on review evidence
    # (ADR-0014 §5). Runs AFTER the DONE dependency check so a missing
    # dependency surfaces on its own; raises WorkflowError before any status
    # write. No-op for ungated targets, the review back-edges, and when the
    # gate is bypassed via JIG_REVIEW_EVIDENCE_GATE.
    _gate_evidence(spec_md, slice_fragment, section, new_status)

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

    # Slice 049-01: claim bookkeeping in the slice frontmatter (no-op on
    # legacy prose-only slices, which have no frontmatter to carry a claim —
    # stamping a field there would synthesize a spurious `---` block).
    #   - release        : clear claimed_by + append a ## Release log entry.
    #   - → IN_PROGRESS  : stamp claimed_by (the identifier resolved above).
    #   - → REVIEWED /
    #     READY_FOR_IMPLEMENTATION / DRAFT : clear claimed_by (AC4).
    if has_frontmatter:
        if release:
            released_from = existing_claim or "(unclaimed)"
            new_section = _clear_slice_frontmatter_field(
                new_section, CLAIM_FIELD)
            new_section = _append_release_log(
                new_section, released_from, reason)
        elif new_status == IN_PROGRESS_STATUS:
            new_section = _set_slice_frontmatter_field(
                new_section, CLAIM_FIELD, claim_identifier,
            )
        elif new_status in _CLAIM_CLEARING_STATUSES and existing_claim:
            new_section = _clear_slice_frontmatter_field(
                new_section, CLAIM_FIELD)

        # The claim is LOCAL by default (no network — preserves the everyday
        # "start a slice" UX). `--push` / `--pr` opt into reserving it on
        # origin/main so parallel worktrees see it. The reservation runs
        # BEFORE the local write, so a collision / race / unreachable-origin
        # refusal leaves the caller's slice file untouched.
        if (new_status == IN_PROGRESS_STATUS and not release
                and (push or pr_mode)):
            claim_project_dir = _project_root_for_spec(spec_md)
            rel_path = loc.path.resolve().relative_to(
                claim_project_dir).as_posix()
            _reserve_claim_on_main(
                claim_project_dir, rel_path, claim_identifier, loc.label,
                pr_mode=pr_mode,
            )
    elif release or (new_status == IN_PROGRESS_STATUS and (push or pr_mode)):
        # Claims require a frontmatter slice; surface rather than silently
        # synthesize a block on a legacy prose-only slice.
        raise WorkflowError(
            f"slice {loc.label} has no frontmatter block — claim operations "
            f"(--push / --pr / --release) require a file-per-slice "
            f"(frontmatter) layout (spec 018)."
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

    # Slice 056-03: when a slice begins, stamp the working-tree-local
    # `.jig/spec-ref` attribution marker. Ordered AFTER all status writes
    # so the marker only follows a successful status transition (no git
    # commit happens here — the ordering is about local write success). Best-effort and
    # side-effect-isolated — a failed write never blocks the transition or
    # its review-evidence gates (the gate already ran and passed above).
    if new_status == IN_PROGRESS_STATUS:
        _write_spec_ref_marker(spec_md, slice_name)

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
    resolution_trigger, kind, claimed_by) tuples in file order.
    resolution_trigger is the empty string when the slice is not DEFERRED
    (or simply has no `**Resolution trigger:**` line). `kind` is the slice's
    frontmatter `kind:` value (slice 029-01: `"spike"` / `"feature"` / `""`
    for unset). Slice 029-02 reads this to drive the marker in
    `render_status_table` — recomputed every regen from the slice's
    frontmatter, so the marker is never stored separately. `claimed_by`
    (slice 049-02) is the slice's frontmatter `claimed_by:` value (set by
    `transition … IN_PROGRESS`, spec 049-01; `""` when unclaimed),
    rendered as a suffix on IN_PROGRESS Status cells."""
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
            # Slice 049-02: read `claimed_by:` (spec 049-01). "" when unset.
            claimed_by = str(fm_fields.get(CLAIM_FIELD, "")).strip()
            rows.append(
                (spec_dir, loc.label, status or "UNKNOWN", trigger, kind,
                 claimed_by),
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


# Slice 049-02: cap the `claimed_by` suffix rendered in the board's Status
# cell so a long branch name can't blow out the column width. A claim at or
# below CLAIM_DISPLAY_MAX renders in full; a longer one is truncated to
# CLAIM_DISPLAY_TRUNC chars + an ellipsis. Invariant: keep
# CLAIM_DISPLAY_TRUNC < CLAIM_DISPLAY_MAX so a truncated suffix is always
# shorter than the untruncated bound (the +ellipsis still fits the budget).
CLAIM_DISPLAY_MAX = 30
CLAIM_DISPLAY_TRUNC = 27


def _render_claim_suffix(claimed_by: str) -> str:
    """Slice 049-02: ` (<claim>)` suffix for an IN_PROGRESS Status cell, or
    "" when unclaimed. Truncates an over-long claim to keep the cell bounded
    (AC6)."""
    claim = (claimed_by or "").strip()
    if not claim:
        return ""
    if len(claim) > CLAIM_DISPLAY_MAX:
        claim = claim[:CLAIM_DISPLAY_TRUNC] + "…"
    return f" ({claim})"


def render_status_table(rows: list, notes_map: dict = None) -> str:
    """Build the Markdown table for the status board. `notes_map` carries
    Notes from the prior version of the board, looked up by (spec_dir, label).
    Tolerates 3-tuple (legacy), 4-tuple (slice 014-02), 5-tuple
    (slice 029-02, with `kind`), and 6-tuple (slice 049-02, with
    `claimed_by`) row shapes.

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
        claimed_by = row[5] if len(row) >= 6 else ""
        spec_link = f"[{spec_dir}]({spec_dir}/spec.md)"
        status_cell = f"**{status}**" if status == "DONE" else status
        # Slice 049-02: surface the owning worktree on IN_PROGRESS rows.
        # Other states are untouched (byte-identical render); legacy /
        # unclaimed IN_PROGRESS rows fall back to plain `IN_PROGRESS`.
        if status == "IN_PROGRESS":
            status_cell = status + _render_claim_suffix(claimed_by)
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
    """Walk slices and ADRs; return a list of `(display, reason, category)`
    findings. Read-only.

    `category` distinguishes finding kinds so downstream filters (CI,
    scripts) can act on them differently (slice 050-02 AC5):
      - `"last-verified"` — the conjunctive freshness drift (last_verified
        older than `days` AND a dependency changed since); the original and
        only finding kind before slice 050-02.
      - `"team-context"` — the team signal fires but `docs/memory/people.md`
        is absent (and the `.jig/no-people-md` opt-out marker is absent).
        Computed once per invocation via `team_context_drift` (a single git
        walk — AC6, no double-walk)."""
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
                    out.append((display, reason, "last-verified"))

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
                out.append((str(rel), reason, "last-verified"))

    # Slice 050-02 — team-context drift: the team signal fires but
    # docs/memory/people.md is absent (and no .jig/no-people-md opt-out).
    # `team_context_drift` encodes the full predicate (signal + absences) and
    # performs at most one git walk, so the count is computed once per `stale`
    # invocation (AC6 — no double-walk; AC3 — marker suppresses; AC2 —
    # read-only, it never writes). Surfaced as a finding row like every
    # last_verified drift (AC1); stale stays exit-0 (AC4 resolved intent).
    contributor_count = team_context_drift(project_dir)
    if contributor_count is not None:
        out.append((
            "team-signal",
            f"project has {contributor_count} contributors but people.md "
            "is absent. Run /jig:memory-sync to bootstrap.",
            "team-context",
        ))

    return out


def stale(project_dir: Path, days: int = 90) -> str:
    """Render the stale-items report to a string. Always exits 0; the report
    is informational, never gating (a deliberate 015-03 design — the CLI
    dispatch returns 0 regardless of findings).

    Each finding is a `(display, reason, category)` tuple (slice 050-02);
    `category` is carried for downstream filtering but not rendered in the
    human report, which stays the unchanged `  <display>: <reason>` shape so
    a `team-context` row reads `  team-signal: project has N contributors
    but people.md is absent. Run /jig:memory-sync to bootstrap.`"""
    items = find_stale_items(project_dir, days=days)
    if not items:
        return f"no stale items (threshold: {days} days)\n"
    lines = [f"stale items ({len(items)}; threshold: {days} days):"]
    for display, reason, _category in items:
        lines.append(f"  {display}: {reason}")
    return "\n".join(lines) + "\n"


# ---------- Slice 041-02: skill-routing histogram ----------
#
# Read surface for the routing observability the PreToolUse/Skill hook
# (hooks/scripts/jig-skill-trace.sh) captures. Renders a category-split
# histogram from the shared .claude/skill-usage.jsonl trace: per category
# (the invoked skill's name with any leading `jig:` plugin scope stripped),
# how many invocations were jig's baseline (`jig:<name>`) vs. a non-jig
# ("other", typically a richer user-installed) skill. That split is what
# answers "did the deferral route away from jig's baseline?" (spec 031 /
# the two refinement-todo entries this spec closes).
#
# Two event sources share the file. Only `event == "skill_invoked"` rows
# carry a skill name; the Task-spawn rows written by jig-telemetry.sh do
# not, so they are filtered out (load-bearing invariant — see the verifier
# in docs/skill-routing-verification.md). Stdout-only; never writes, never
# raises for normal empty states (mirrors `stale`, which is informational).


def _parse_iso_utc(ts: str):
    """Parse an ISO-8601 timestamp to an aware UTC datetime, or None when
    unparseable. Tolerates a trailing 'Z' and naive (offset-less) stamps
    (assumed UTC). The hook writes `datetime.now(timezone.utc).isoformat()`
    (offset `+00:00`); this stays tolerant in case that format drifts."""
    if not ts:
        return None
    raw = ts.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def routing_stats(project_dir: Path, days: int = 30) -> str:
    """Render the skill-routing histogram to a string. Always informational
    (the caller exits 0); never gates. Reads .claude/skill-usage.jsonl,
    filters to `skill_invoked` events within the last `days`, and buckets
    each by category (jig baseline vs. other)."""
    log_path = project_dir / ".claude" / "skill-usage.jsonl"
    if not log_path.is_file():
        return (
            f"no routing data — {log_path} not found.\n"
            "the PreToolUse/Skill trace (hooks/scripts/jig-skill-trace.sh) "
            "writes it as skills fire.\n"
        )

    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=days))
    counts: dict = {}  # category -> [jig_count, other_count]
    total = 0
    outside_window = 0

    # errors="replace": a non-UTF-8 byte in the trace must not raise — it
    # would escape the per-line try below and break the "always exits 0"
    # contract (AC #5). A corrupted line decodes to replacement chars and is
    # then dropped by the json.loads guard, same as any other malformed line.
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except (ValueError, TypeError):
            continue  # malformed line — skip, never crash
        if not isinstance(entry, dict) or entry.get("event") != "skill_invoked":
            continue  # Task-spawn rows (no event/skill_name) and noise
        name = str(entry.get("skill_name") or "").strip()
        if not name:
            continue
        dt = _parse_iso_utc(str(entry.get("timestamp") or ""))
        if dt is None:
            continue  # can't window an unparseable timestamp
        if dt < cutoff:
            outside_window += 1
            continue
        is_jig = name.startswith("jig:")
        category = name[len("jig:"):] if is_jig else name
        bucket = counts.setdefault(category, [0, 0])
        bucket[0 if is_jig else 1] += 1
        total += 1

    if total == 0:
        plural = "y" if outside_window == 1 else "ies"
        return (
            f"no skill invocations in the last {days} days "
            f"({outside_window} older entr{plural} outside the window).\n"
        )

    # Sort by total desc, then category asc for a stable, scannable order.
    rows = sorted(
        ((cat, jig, other) for cat, (jig, other) in counts.items()),
        key=lambda r: (-(r[1] + r[2]), r[0]),
    )

    cat_w = max(len("category"), max(len(r[0]) for r in rows))
    cat_plural = "y" if len(rows) == 1 else "ies"
    header = f"  {'category':<{cat_w}}  {'jig':>4}  {'other':>5}  {'total':>5}"
    sep = f"  {'-' * cat_w}  {'-' * 4}  {'-' * 5}  {'-' * 5}"
    lines = [
        f"skill-routing stats (last {days} days) — {log_path}",
        f"  {total} skill invocation(s) across {len(rows)} categor{cat_plural}; "
        f"{outside_window} outside window; Task-spawn rows excluded.",
        "",
        header,
        sep,
    ]
    for cat, jig, other in rows:
        lines.append(f"  {cat:<{cat_w}}  {jig:>4}  {other:>5}  {jig + other:>5}")
    lines.append("")
    lines.append(
        "legend: 'jig' = jig baseline (jig:<name>) fired; 'other' = a non-jig\n"
        "(typically a richer user-installed) skill in that category fired. "
        "Where jig\nships a deferring baseline, 'other' > 0 with 'jig' = 0 means "
        "routing chose\nthe richer skill over jig's."
    )
    return "\n".join(lines) + "\n"


# ---------- Slice 048-04: amendment-effective-state digest ----------

# A closed record's "current truth" lives under a `## Amendments` section
# (per ADR-0010): the original prose is preserved in place and a dated
# entry overrides it. This digest indexes those overrides so a reader finds
# current state without rereading every historical drift block. The regexes
# mirror the ones proven in scripts/test_closed_spec_drift_sweep.py. Em-dash,
# en-dash, or hyphen is accepted as the date↔title separator.
_AMENDMENTS_HEADING_RE = re.compile(r"^## Amendments\s*$", re.MULTILINE)
_AMENDMENT_ENTRY_RE = re.compile(
    r"^###\s+(\d{4}-\d{2}-\d{2})\s*[—–-]\s*(.+?)\s*$", re.MULTILINE,
)
# ```-fenced regions: an illustrative `## Amendments` example shown as
# documentation (e.g. ADR-0008, which documents the amendment *format* in a
# fenced block) is NOT a real amendment and must not enter the digest.
_CODE_FENCE_RE = re.compile(r"(?ms)^[ \t]*```.*?^[ \t]*```[ \t]*$")


def _strip_code_fences(text: str) -> str:
    """Remove ```-fenced code blocks so a `## Amendments` heading shown
    *inside* a fence (an illustrative example, not a live amendment) is not
    mistaken for a real one."""
    return _CODE_FENCE_RE.sub("", text)


def _amendments_section(text: str) -> str:
    """Return the body after a `## Amendments` heading up to the next `## `
    heading (or EOF), or '' if the artifact has no amendments section.
    Fenced code blocks are stripped first so documented examples don't
    register as amendments."""
    text = _strip_code_fences(text)
    m = _AMENDMENTS_HEADING_RE.search(text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    return rest if nxt is None else rest[: nxt.start()]


def find_amendment_artifacts(project_dir: Path):
    """Scan amendment-bearing artifacts under `docs/specs/` (spec.md +
    slice files) and `docs/decisions/` (ADRs). Return a list of
    (relative_posix_path, [(date, title), ...]) for every artifact that
    carries a `## Amendments` section with at least one dated entry.
    Sorted by path; entries within each artifact sorted by date. Read-only
    — never modifies any artifact (ADR-0010: history is preserved)."""
    docs = project_dir / "docs"
    candidates = []
    specs_dir = docs / "specs"
    if specs_dir.is_dir():
        candidates.extend(specs_dir.rglob("*.md"))
    decisions_dir = docs / "decisions"
    if decisions_dir.is_dir():
        candidates.extend(decisions_dir.glob("*.md"))

    results = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        body = _amendments_section(text)
        if not body:
            continue
        entries = sorted(
            (m.group(1), m.group(2).strip())
            for m in _AMENDMENT_ENTRY_RE.finditer(body)
        )
        if not entries:
            continue
        results.append((path.relative_to(project_dir).as_posix(), entries))
    results.sort(key=lambda r: r[0])
    return results


def amendment_digest(project_dir: Path) -> str:
    """Render the amendment digest to a string. Read-only and never gating
    (always exits 0). Indexes the `## Amendments` overrides on closed
    records (ADR-0010) so a reader sees current truth without rereading the
    preserved historical prose."""
    artifacts = find_amendment_artifacts(project_dir)
    lines = ["# Amendment digest", ""]
    if not artifacts:
        lines.append(
            "No amendment-bearing artifacts found under docs/specs/ or "
            "docs/decisions/."
        )
        return "\n".join(lines) + "\n"
    n_entries = sum(len(entries) for _, entries in artifacts)
    lines.append(
        f"Effective overrides recorded under `## Amendments` in closed "
        f"records (ADR-0010); the original prose is preserved in place. "
        f"{n_entries} amendment(s) across {len(artifacts)} artifact(s)."
    )
    lines.append("")
    for rel, entries in artifacts:
        # Heading is a markdown link so the path is both visible (CLI) and
        # click-navigable back to the source if the digest is rendered.
        lines.append(f"## [{rel}]({rel})")
        for date, title in entries:
            lines.append(f"- {date} — {title}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


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


def _next_spec_number(specs_dir: Path,
                      project_dir: Path = None,
                      use_origin: bool = False) -> int:
    """Scan for `NNN-*/` entries; return max(NNN) + 1.

    Spec 037-02: in push mode (`use_origin=True`), the listing source
    is `origin/main` (via `git ls-tree --name-only origin/main
    docs/specs/`) so the reservation honors the team-wide contract
    instead of the local working tree. The `--no-push` path keeps
    using the working tree (no remote contract to honor — AC #2).

    Algorithm (matches the spec 037 clarifications Q1, Q4, Q5; mirrors
    `_check_ff_viable`'s fall-through shape at `land.py:555-655`):

      1. If `use_origin=False` (i.e. `--no-push`), scan
         `specs_dir.iterdir()` as before. AC #2 contract.
      2. Otherwise:
         a. If `git config --get remote.origin.url` fails, fall
            through SILENTLY to the working-tree scan (AC #3, Q4 —
            local-only-repo contract, no warning).
         b. If `git rev-parse --verify origin/main` returns non-zero
            OR empty stdout (ref absent or fetch failed earlier per
            AC #6), fall through SILENTLY to the working-tree scan
            (AC #3, AC #6).
         c. Otherwise run `git ls-tree --name-only origin/main
            docs/specs/` and apply the same `NNN-*` regex as the
            working-tree path (AC #1). Non-spec entries ignored.

    Ignores non-spec entries (README.md, files, dirs that don't start
    with three digits + hyphen). Returns 1 when the directory is empty."""
    if use_origin and project_dir is not None:
        # Step 2a — origin presence
        url_rc, url_out, _url_err = _run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=project_dir,
        )
        if url_rc == 0 and url_out.strip():
            # Step 2b — origin/main ref existence (post-fetch)
            verify_rc, verify_out, _verify_err = _run(
                ["git", "rev-parse", "--verify", "origin/main"],
                cwd=project_dir,
            )
            if verify_rc == 0 and verify_out.strip():
                # Step 2c — enumerate against origin/main
                ls_rc, ls_out, _ls_err = _run(
                    ["git", "ls-tree", "--name-only",
                     "origin/main", "docs/specs/"],
                    cwd=project_dir,
                )
                if ls_rc == 0:
                    max_n = 0
                    for line in ls_out.splitlines():
                        # ls-tree may emit `docs/specs/NNN-slug` or
                        # `NNN-slug` depending on pathspec form; both
                        # are handled by extracting the basename.
                        name = line.strip().rstrip("/").rsplit("/", 1)[-1]
                        m = re.match(r"^(\d{3})-", name)
                        if m:
                            n = int(m.group(1))
                            if n > max_n:
                                max_n = n
                    return max_n + 1
            # rev-parse failed OR ls-tree failed: silent fall-through
        # No origin or origin/main ref: silent fall-through (AC #3)

    # Working-tree scan (AC #2 path, and AC #3 fall-back).
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


def _preflight_diverged_main(project_dir: Path) -> None:
    """Spec 037-02 AC #4: refuse if local `main` is strictly behind
    `origin/main`.

    Algorithm (mirrors `_check_ff_viable` at `land.py:555-655`, the
    sibling slice's precedent):

      1. If `git rev-parse --verify origin/main` fails OR returns
         empty SHA, fall through silently (no origin/main to compare
         against — AC #3 / AC #6).
      2. Read the local `main` SHA via `git rev-parse main`. If that
         fails, fall through silently.
      3. If the two SHAs are equal, local is in sync — no refusal.
      4. Otherwise run `git merge-base --is-ancestor main
         origin/main`:
         - rc == 0 AND SHAs differ → local is STRICTLY behind →
           raise `WorkflowError`. AC #4: message MUST contain
           "origin/main" and "pull or rebase" (substrings are
           fixture-stable).
         - rc != 0 → local is ahead-or-diverged; the push step's
           race classifier (AC #7) handles any actual conflict.

    AC #5: raises `WorkflowError`, which `main()` already maps to
    exit 2 — no new exit code is introduced.
    """
    rc, out, _err = _run(
        ["git", "rev-parse", "--verify", "origin/main"], cwd=project_dir,
    )
    if rc != 0 or not out.strip():
        return  # no origin/main ref → silent fall-through
    origin_sha = out.strip()

    rc, out, _err = _run(
        ["git", "rev-parse", "main"], cwd=project_dir,
    )
    if rc != 0 or not out.strip():
        return  # no local main SHA → can't compare; let later steps fail
    local_sha = out.strip()

    if local_sha == origin_sha:
        return  # in sync

    anc_rc, _anc_out, _anc_err = _run(
        ["git", "merge-base", "--is-ancestor", "main", "origin/main"],
        cwd=project_dir,
    )
    if anc_rc == 0:
        # main is a strict ancestor of origin/main → local is behind.
        raise WorkflowError(
            "refusing: local main is behind origin/main — "
            "pull or rebase before reserving"
        )


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
        # Spec 065-04 — self-defining vocabulary reminder, emitted into the
        # spec stub so an author meets it where they write (reaches scaffolded
        # projects, where the template file is not distributed).
        "<!-- jig self-defining vocabulary (soft, forward-only): expand each "
        "acronym on first use and link the term to docs/memory/glossary.md (or "
        "jig's lexicon). See docs/workflow.md \"Self-defining vocabulary\". -->\n"
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
        # template file isn't on disk (e.g. minimal scaffold smoke tests, or a
        # scaffolded project where the template is not distributed). Carries the
        # spec 065-04 self-defining-vocabulary reminder so the author meets it
        # here too, in parity with the on-disk slice-template.md.
        body = (
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified:\n---\n"
            "\n<!-- jig self-defining vocabulary (soft, forward-only): expand "
            "each acronym on first use and link the term to "
            "docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "
            "\"Self-defining vocabulary\". -->\n"
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


def _refuse_if_dirty(project_dir: Path) -> None:
    """Refuse if the worktree has uncommitted changes. The on-main
    reservation path commits on local `main`, so it must start clean.

    The branch==main check that used to live here moved to the
    `_current_branch` dispatch in `reserve_spec` (see the worktree-aware
    reservation block) so off-main callers route to the detached-worktree
    path instead of being refused — keeping the single `git symbolic-ref`
    call the on-main path already made."""
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


# ---------- Worktree-aware reservation (prototype) ----------
#
# The 003-03 flow above commits on local `main`, then pushes `origin main`.
# That requires the caller to BE on `main` — but a linked git worktree can
# never check out `main` (it is held by the primary worktree; `git checkout
# main` there fails with "'main' is already used by worktree at ..."). So
# the branch==main guard was structurally unsatisfiable from exactly the
# place jig's own worktree-based workflow puts you. The helpers below make
# reservation work from any branch or worktree by building the reservation
# commit in an EPHEMERAL DETACHED worktree checked out at origin/main —
# detached, so it sidesteps the one-checkout-per-branch rule — then pushing
# `HEAD:main`. The caller's cwd, branch, and branch tip are never touched.


def _current_branch(project_dir: Path):
    """Return the current branch name, or None if detached / undeterminable.

    A linked worktree reports its own branch here (never `main`, which the
    primary worktree holds), which is what routes reservation onto the
    worktree-aware path."""
    rc, out, _err = _run(
        ["git", "symbolic-ref", "--short", "HEAD"], cwd=project_dir,
    )
    if rc != 0:
        return None
    return out.strip() or None


def _print_draft_hint(spec_dirname: str) -> None:
    """The reservation lands on origin/main, not in the caller's branch.
    Tell them how to pull it in to start drafting. Written to stderr so the
    stdout contract (reserved-line + path) stays clean for scripts."""
    sys.stderr.write(
        f"note: reservation {spec_dirname} lives on origin/main, not in "
        f"your current branch. To draft it here:\n"
        f"    git fetch origin main && git merge origin/main\n"
        f"then edit docs/specs/{spec_dirname}/spec.md\n"
    )


def _reserve_local_on_current_branch(slug: str, project_dir: Path,
                                     specs_dir: Path) -> int:
    """`--no-push` from off-main: commit a provisional reservation stub to
    the CURRENT branch. The number is computed from the local working tree,
    so it is PROVISIONAL — it may collide at merge time. Use the default
    (push) mode to claim a number for real on origin/main."""
    next_n = _next_spec_number(specs_dir)
    num_str = f"{next_n:03d}"
    spec_dirname = f"{num_str}-{slug}"
    spec_dir = specs_dir / spec_dirname
    if spec_dir.exists():
        raise WorkflowError(
            f"refusing: {spec_dir} already exists. Re-run after "
            f"resolving the conflict."
        )
    spec_dir.mkdir(parents=True)
    today_iso = _today()
    atomic_write_text(spec_dir / "spec.md",
                      _render_stub_spec(num_str, slug, today_iso))
    atomic_write_text(spec_dir / "slice-01-tbd.md",
                      _render_stub_slice(num_str))
    rel_spec = f"docs/specs/{spec_dirname}/spec.md"
    rel_slice = f"docs/specs/{spec_dirname}/slice-01-tbd.md"
    rc, _out, err = _run(["git", "add", rel_spec, rel_slice], cwd=project_dir)
    if rc != 0:
        raise WorkflowError(
            f"`git add {rel_spec} {rel_slice}` failed: {err.strip()}. "
            f"The stub files are on disk; stage and commit manually."
        )
    # Pathspec-limited commit: only the stub lands, even if the caller had
    # unrelated work already staged. Off-main reservation deliberately does
    # NOT require a clean tree (worktree sessions are usually mid-edit), so
    # we must not sweep that staged work into the reservation commit.
    commit_msg = f"docs(specs): reserve {spec_dirname}"
    rc, _out, err = _run(
        ["git", "commit", "-m", commit_msg, "--", rel_spec, rel_slice],
        cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"`git commit` failed: {err.strip()}. "
            f"The stub spec.md is staged; commit manually."
        )
    print(f"reserved {spec_dirname} (local provisional — not yet on origin/main)")
    print(str((spec_dir / "spec.md").resolve()))
    return 0


def _pr_fallback_from_worktree(sha: str, project_dir: Path,
                               reserve_branch: str, num_str: str,
                               slug: str, pr_body: str) -> None:
    """Protected-branch fallback for the detached-worktree path. Simpler
    than the on-main `_do_pr_fallback` (there is no local `main` to
    un-strand): push the detached reservation commit (BY SHA, from
    `project_dir` so a relative `origin` URL resolves) straight to a new
    remote branch and open the PR. `gh`/remote guards mirror 003-03."""
    _check_gh_and_remote(project_dir)
    rc, _out, err = _run(
        ["git", "push", "origin", f"{sha}:refs/heads/{reserve_branch}"],
        cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback push to {reserve_branch!r} failed: {err.strip()}. "
            f"The reservation commit exists only in the reservation "
            f"worktree; re-run to retry."
        )
    title = f"docs(specs): reserve {num_str}-{slug}"
    rc, out, err = _run(
        ["gh", "pr", "create", "--title", title, "--body", pr_body,
         "--head", reserve_branch, "--base", "main"],
        cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback `gh pr create` failed: {err.strip()}. "
            f"Branch origin/{reserve_branch} is pushed; open the PR "
            f"manually via the GitHub web UI."
        )
    pr_url = out.strip()
    if pr_url:
        print(pr_url)


def _reserve_via_detached_worktree(slug: str, project_dir: Path,
                                   pr_mode: bool = False) -> int:
    """Push-mode reservation that works from ANY branch or worktree.

    Claims the next free spec number on origin/main by building the
    reservation commit inside an ephemeral, detached worktree checked out
    at origin/main, then pushing `HEAD:main`. The caller's working tree,
    branch, and branch tip are never touched. Race + protection handling
    mirror the on-main 003-03 flow; race recovery is trivial here (the
    stranded commit lives only in the worktree we remove in `finally`)."""
    # Fresh origin/main so the number scan + commit parent are current.
    rc, _out, err = _run(["git", "fetch", "origin", "main"], cwd=project_dir)
    if rc != 0:
        sys.stderr.write(
            f"warning: `git fetch origin main` failed: {err.strip()}; "
            f"proceeding with the local origin/main view\n"
        )

    wt = Path(tempfile.mkdtemp(prefix="jig-reserve-spec-"))
    try:
        # Detached checkout of origin/main: no branch is checked out, so
        # this never collides with `main` being held by another worktree.
        rc, _out, err = _run(
            ["git", "worktree", "add", "--detach", str(wt), "origin/main"],
            cwd=project_dir,
        )
        if rc != 0:
            raise WorkflowError(
                f"could not create the ephemeral reservation worktree at "
                f"origin/main ({err.strip()}). Most likely there is no "
                f"origin/main to reserve against — use `--no-push` for a "
                f"local provisional reservation, or run from a clone with "
                f"an 'origin' remote."
            )

        # Number scan reads the freshly checked-out origin/main tree.
        next_n = _next_spec_number(wt / "docs" / "specs")
        num_str = f"{next_n:03d}"
        spec_dirname = f"{num_str}-{slug}"
        spec_dir = wt / "docs" / "specs" / spec_dirname
        if spec_dir.exists():
            raise WorkflowError(
                f"refusing: {spec_dirname} already exists on origin/main."
            )

        spec_dir.mkdir(parents=True)
        today_iso = _today()
        atomic_write_text(spec_dir / "spec.md",
                          _render_stub_spec(num_str, slug, today_iso))
        atomic_write_text(spec_dir / "slice-01-tbd.md",
                          _render_stub_slice(num_str))
        rel_spec = f"docs/specs/{spec_dirname}/spec.md"
        rel_slice = f"docs/specs/{spec_dirname}/slice-01-tbd.md"
        rc, _out, err = _run(["git", "add", rel_spec, rel_slice], cwd=wt)
        if rc != 0:
            raise WorkflowError(
                f"`git add` in the reservation worktree failed: "
                f"{err.strip()}."
            )
        commit_msg = f"docs(specs): reserve {spec_dirname}"
        rc, _out, err = _run(["git", "commit", "-m", commit_msg], cwd=wt)
        if rc != 0:
            raise WorkflowError(
                f"`git commit` in the reservation worktree failed: "
                f"{err.strip()}."
            )
        print(f"reserved {spec_dirname}")

        # Resolve the reservation commit's SHA so we can push it BY SHA from
        # `project_dir`. Pushing from `wt` would resolve a RELATIVE `origin`
        # URL against the temp dir and fail; the commit's objects live in the
        # shared object store, so its SHA is reachable from `project_dir`,
        # where the `origin` remote-name resolves correctly.
        rc, sha, err = _run(["git", "rev-parse", "HEAD"], cwd=wt)
        if rc != 0 or not sha.strip():
            raise WorkflowError(
                f"could not resolve the reservation commit SHA ({err.strip()}); "
                f"the ephemeral worktree will be removed."
            )
        sha = sha.strip()

        pr_body = _build_pr_body(num_str, slug, project_dir)
        reserve_branch = f"reserve/{spec_dirname}"

        if pr_mode:
            _pr_fallback_from_worktree(
                sha, project_dir, reserve_branch, num_str, slug, pr_body,
            )
            _print_draft_hint(spec_dirname)
            return 0

        # Direct push of the detached reservation commit onto main, BY SHA
        # from project_dir (where the `origin` remote-name resolves).
        rc, _out, err = _run(
            ["git", "push", "origin", f"{sha}:refs/heads/main"],
            cwd=project_dir,
        )
        if rc == 0:
            print(f"reserved {spec_dirname} on origin/main")
            _print_draft_hint(spec_dirname)
            return 0

        kind = _classify_push_failure(err)
        if kind == "race":
            # No `reset --hard HEAD~1` needed: the stranded commit lives
            # only in the worktree the `finally` removes.
            sys.stderr.write(
                f"race detected: origin/main advanced during reservation. "
                f"Re-run 'workflow.py new {slug}' to pick the next free "
                f"number.\n"
            )
            raise WorkflowError(f"race-on-push: {err.strip()}")

        if kind == "protection":
            sys.stderr.write(
                f"direct push refused ({err.strip()}); falling back to "
                f"PR mode...\n"
            )
            _pr_fallback_from_worktree(
                sha, project_dir, reserve_branch, num_str, slug, pr_body,
            )
            _print_draft_hint(spec_dirname)
            return 0

        raise WorkflowError(
            f"`git push origin {sha}:refs/heads/main` failed: {err.strip()} "
            f"(the reservation commit lived only in the reservation "
            f"worktree, which has been removed; inspect and re-run)."
        )
    finally:
        # Always tear down the ephemeral worktree. --force because git sees
        # it as carrying a checkout; ignore errors so cleanup never masks
        # the real outcome.
        _run(["git", "worktree", "remove", "--force", str(wt)],
             cwd=project_dir)
        shutil.rmtree(wt, ignore_errors=True)
        # Prune any stale .git/worktrees/ admin entry so it can't accumulate
        # if `worktree remove` ever failed above.
        _run(["git", "worktree", "prune"], cwd=project_dir)


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

    # Worktree-aware routing (prototype): the original flow below REQUIRES
    # being on `main` (it commits on local main, then pushes `origin main`).
    # A linked worktree can't check out `main`, so route off-main callers to
    # the detached-worktree path (push) or a current-branch commit
    # (`--no-push`) instead of refusing. On `main`, the proven 003-03 +
    # 037-02 flow runs unchanged.
    if _current_branch(project_dir) != "main":
        if no_push:
            return _reserve_local_on_current_branch(
                slug, project_dir, specs_dir,
            )
        return _reserve_via_detached_worktree(
            slug, project_dir, pr_mode=pr_mode,
        )

    # On `main`: enforce a clean tree (the commit lands on local main).
    # The branch check already happened at the dispatch above.
    _refuse_if_dirty(project_dir)

    # Fetch origin/main first; both the next-number scan and the
    # divergence preflight read from it (spec 037-02 AC #1 + AC #4 +
    # AC #8). Skipped for --no-push (no remote contract).
    if not no_push:
        rc, _out, err = _run(
            ["git", "fetch", "origin", "main"], cwd=project_dir,
        )
        # A failed fetch isn't fatal — we still proceed with the local
        # view (spec 037-02 AC #6 preserves this verbatim). The push
        # step will catch any out-of-date condition via the race-on-
        # push classifier (003-03 AC #6 / 037-02 AC #7).
        if rc != 0:
            sys.stderr.write(
                f"warning: `git fetch origin main` failed: "
                f"{err.strip()}; proceeding with local view\n"
            )
        # Spec 037-02 AC #4: refuse if local main is strictly behind
        # origin/main. Internally guarded so a failed fetch (no
        # origin/main ref) silently falls through — preserving AC #6.
        _preflight_diverged_main(project_dir)

    # Compute the next number AFTER the fetch so we pick up any specs
    # that landed in the gap. Spec 037-02 AC #1: push-mode reads from
    # `origin/main` via `git ls-tree`; `--no-push` keeps the working-
    # tree scan (AC #2).
    next_n = _next_spec_number(
        specs_dir, project_dir=project_dir, use_origin=not no_push,
    )
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


# ---------- Slice 049-01: claim-on-transition ----------
#
# Mirrors the spec 028-01 / 003-03 reserve-on-main primitives (reused
# directly: _run, _classify_push_failure, _check_gh_and_remote,
# _current_branch) and the spec 051 / ADR-0015 worktree-aware
# detached-checkout shape. Where `workflow.py new` reserves a NEW spec
# number by CREATING files, the IN_PROGRESS transition reserves a CLAIM
# on an EXISTING slice file: it flips `status: IN_PROGRESS` and stamps
# `claimed_by:` on the origin/main copy so two parallel worktrees cannot
# both pick up the same slice. A single detached-worktree path serves
# every branch (incl. a linked worktree that can't check out `main`),
# since the claim edits an existing file rather than creating one. Per
# ADR-0002's three-callers rule the push/race/PR-fallback shape stays
# inline-mirrored, not extracted (this is the second caller).

CLAIM_FIELD = "claimed_by"
_CLAIM_CLEARING_STATUSES = ("REVIEWED", "READY_FOR_IMPLEMENTATION", "DRAFT")


def _claim_identifier(project_dir: Path) -> str:
    """Identity stamped into `claimed_by:`. The `JIG_CLAIM_ID` env
    override wins (spec 049 non-goal: no human-identity inference);
    otherwise the current branch name (parity with `workflow.py new`'s
    routing). Falls back to 'detached' when neither is available."""
    env = os.environ.get("JIG_CLAIM_ID")
    if env and env.strip():
        return env.strip()
    return _current_branch(project_dir) or "detached"


def _ref_safe(label: str) -> str:
    """Slug a slice label into a git-ref-safe token for the PR-fallback
    branch name. The human label (e.g. `049-01 — claim-and-release`)
    carries spaces / em-dashes that are invalid in a ref; lower-case and
    collapse every non-`[a-z0-9]` run to a single hyphen (mirrors the
    003-03 precedent of branching off the filesystem-safe `spec_dirname`,
    not the prose label)."""
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "slice"


def _build_claim_pr_body(slice_label: str, identifier: str,
                         rel_path: str) -> str:
    """PR body for the protected-branch claim fallback."""
    return (
        f"Claims slice `{slice_label}` for `{identifier}` on the shared "
        f"trunk, so parallel worktrees cannot both pick it up.\n"
        f"\n"
        f"This PR flips `status: IN_PROGRESS` and stamps "
        f"`claimed_by: {identifier}` on `{rel_path}`.\n"
        f"\n"
        f"Generated by `workflow.py transition ... IN_PROGRESS` "
        f"(see spec 049-01 slice-claim-on-IN_PROGRESS for rationale).\n"
    )


def _claim_pr_fallback(sha: str, project_dir: Path, claim_branch: str,
                       slice_label: str, identifier: str,
                       pr_body: str) -> None:
    """Protected-branch fallback for the claim push: push the claim
    commit (BY SHA, from project_dir so a relative `origin` URL resolves)
    to a new `claim/` branch and open a PR. Mirrors
    `_pr_fallback_from_worktree` (003-03) with claim-flavored messaging."""
    _check_gh_and_remote(project_dir)
    rc, _out, err = _run(
        ["git", "push", "origin", f"{sha}:refs/heads/{claim_branch}"],
        cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback push to {claim_branch!r} failed: {err.strip()}. "
            f"The claim commit exists only in the ephemeral worktree; "
            f"re-run to retry."
        )
    title = f"docs(specs): claim {slice_label} ({identifier})"
    rc, out, err = _run(
        ["gh", "pr", "create", "--title", title, "--body", pr_body,
         "--head", claim_branch, "--base", "main"],
        cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"PR-fallback `gh pr create` failed: {err.strip()}. "
            f"Branch origin/{claim_branch} is pushed; open the PR "
            f"manually via the GitHub web UI."
        )
    pr_url = out.strip()
    if pr_url:
        print(pr_url)


def _reserve_claim_on_main(project_dir: Path, rel_path: str,
                           identifier: str, slice_label: str,
                           pr_mode: bool = False) -> None:
    """Reserve a slice claim on origin/main. Fetches origin/main, reads
    the slice's origin/main copy, refuses if it is already claimed by a
    different identifier while IN_PROGRESS (the collision backstop), then
    builds the claim commit in an ephemeral detached worktree and pushes
    `HEAD:main` BY SHA. Race → re-run; protected branch → PR fallback.
    Raises WorkflowError on collision / race / unreachable origin; the
    caller's working tree, branch, and branch tip are never touched."""
    rc, _out, err = _run(["git", "fetch", "origin", "main"], cwd=project_dir)
    if rc != 0:
        raise WorkflowError(
            f"cannot reserve the claim: `git fetch origin main` failed "
            f"({err.strip()}). origin/main is unreachable — re-run with "
            f"--no-push for a local provisional claim."
        )

    rc, content, err = _run(
        ["git", "show", f"origin/main:{rel_path}"], cwd=project_dir,
    )
    if rc != 0:
        raise WorkflowError(
            f"cannot reserve the claim: {rel_path} is not on origin/main "
            f"({err.strip()}). Land the slice on main first, or use "
            f"--no-push for a local provisional claim."
        )

    fields, _ = parse_frontmatter(content)
    existing = str(fields.get(CLAIM_FIELD) or "").strip()
    origin_status = str(fields.get("status") or "").strip()
    if existing and existing != identifier and origin_status == "IN_PROGRESS":
        raise WorkflowError(
            f"slice {slice_label} is already claimed by {existing!r} on "
            f"origin/main (status IN_PROGRESS). Have the current owner "
            f"release it, or force-release with:\n"
            f"    workflow.py transition <spec> {slice_label} "
            f'READY_FOR_IMPLEMENTATION --release --reason "..."'
        )
    if existing == identifier and origin_status == "IN_PROGRESS":
        # Idempotent re-claim — already ours on origin/main; nothing to push.
        print(f"claim already held by {identifier!r} on origin/main")
        return

    new_content = set_frontmatter_field(content, "status", "IN_PROGRESS")
    new_content = set_frontmatter_field(new_content, CLAIM_FIELD, identifier)

    wt = Path(tempfile.mkdtemp(prefix="jig-claim-"))
    try:
        rc, _out, err = _run(
            ["git", "worktree", "add", "--detach", str(wt), "origin/main"],
            cwd=project_dir,
        )
        if rc != 0:
            raise WorkflowError(
                f"could not create the ephemeral claim worktree at "
                f"origin/main ({err.strip()})."
            )

        target = wt / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(target, new_content)
        rc, _out, err = _run(["git", "add", rel_path], cwd=wt)
        if rc != 0:
            raise WorkflowError(
                f"`git add {rel_path}` in the claim worktree failed: "
                f"{err.strip()}."
            )
        commit_msg = f"docs(specs): claim {slice_label} ({identifier})"
        rc, _out, err = _run(["git", "commit", "-m", commit_msg], cwd=wt)
        if rc != 0:
            raise WorkflowError(
                f"`git commit` in the claim worktree failed: {err.strip()}."
            )

        # Resolve the SHA so we can push BY SHA from project_dir (a relative
        # `origin` URL would not resolve against the temp worktree — the
        # 051 lesson).
        rc, sha, err = _run(["git", "rev-parse", "HEAD"], cwd=wt)
        if rc != 0 or not sha.strip():
            raise WorkflowError(
                f"could not resolve the claim commit SHA ({err.strip()})."
            )
        sha = sha.strip()

        pr_body = _build_claim_pr_body(slice_label, identifier, rel_path)
        claim_branch = f"claim/{_ref_safe(slice_label)}"

        if pr_mode:
            _claim_pr_fallback(
                sha, project_dir, claim_branch, slice_label, identifier,
                pr_body,
            )
            return

        rc, _out, err = _run(
            ["git", "push", "origin", f"{sha}:refs/heads/main"],
            cwd=project_dir,
        )
        if rc == 0:
            print(f"claimed {slice_label} on origin/main as {identifier!r}")
            return

        kind = _classify_push_failure(err)
        if kind == "race":
            # The stranded commit lives only in the worktree the `finally`
            # removes — no reset needed.
            raise WorkflowError(
                f"race-on-push claiming {slice_label}: origin/main advanced "
                f"({err.strip()}). Re-run the transition to re-check the "
                f"claim against the new origin/main."
            )
        if kind == "protection":
            sys.stderr.write(
                f"direct push refused ({err.strip()}); falling back to "
                f"PR mode...\n"
            )
            _claim_pr_fallback(
                sha, project_dir, claim_branch, slice_label, identifier,
                pr_body,
            )
            return

        raise WorkflowError(
            f"`git push origin {sha}:refs/heads/main` failed claiming "
            f"{slice_label}: {err.strip()} (the claim commit lived only in "
            f"the ephemeral worktree, which has been removed; re-run)."
        )
    finally:
        _run(["git", "worktree", "remove", "--force", str(wt)],
             cwd=project_dir)
        shutil.rmtree(wt, ignore_errors=True)
        _run(["git", "worktree", "prune"], cwd=project_dir)


def _append_release_log(section: str, released_from: str, reason: str) -> str:
    """Append a dated release entry to the slice's `## Release log`
    section (created if absent). Audit trail for `--release` (AC5)."""
    entry = f"- {_today()} — released claim from {released_from}: {reason.strip()}\n"
    body = section.rstrip("\n")
    if "## Release log" in section:
        return body + "\n" + entry
    return body + "\n\n## Release log\n\n" + entry


# ---------- end slice 049-01 ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="workflow.py",
                                description="jig spec-workflow helper")
    sub = p.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("transition", help="transition a slice's STATUS marker")
    pt.add_argument("spec", help="path to spec.md")
    pt.add_argument("slice", help="slice name or fragment (case-insensitive substring)")
    pt.add_argument("status", help=f"new status; one of: {', '.join(VALID_STATUSES)}")
    # Slice 049-01: slice-claim flags (meaningful on the IN_PROGRESS
    # transition + --release). The claim is local by default; --push / --pr
    # opt into reserving it on origin/main.
    pt.add_argument("--push", action="store_true",
                    help="(IN_PROGRESS) reserve the claim on origin/main so "
                         "parallel worktrees see it (default: local-only)")
    pt.add_argument("--pr", dest="pr_mode", action="store_true",
                    help="(IN_PROGRESS) reserve the claim on origin/main via "
                         "a PR instead of a direct push (implies --push)")
    pt.add_argument("--release", action="store_true",
                    help="force-release an existing claim (clears claimed_by); "
                         "requires --reason")
    pt.add_argument("--reason", default=None,
                    help="audit reason recorded in the slice's ## Release log "
                         "(required with --release)")

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

    # Slice 041-02: read-only histogram of skill-routing observations from
    # .claude/skill-usage.jsonl — jig baseline vs. richer/"other" per
    # category. Surfaces whether deferral routed away from jig's baseline.
    prs = sub.add_parser(
        "routing-stats",
        help="histogram of which skills fired (jig baseline vs. richer/"
             "other) from .claude/skill-usage.jsonl (slice 041-02)",
    )
    prs.add_argument("--project-dir", default=".",
                     help="project root directory (default: cwd)")
    prs.add_argument("--days", type=int, default=30,
                     help="window in days (default: 30)")

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

    # Slice 060-05: code-health-pass gating mirror of arch-review-needed.
    pch = sub.add_parser(
        "code-health-review-needed",
        help="print 'true' if the slice's frontmatter declares "
             "`code_health_review: true`; 'false' otherwise (slice 060-05)",
    )
    pch.add_argument("spec", help="path to spec.md")
    pch.add_argument("slice",
                     help="slice name or fragment (case-insensitive substring)")

    # Slice 057-01: delegation-first per-slice dispatch plan (stdout-only).
    psp = sub.add_parser(
        "session-plan",
        help="print a delegation-first dispatch plan for a spec — each "
             "non-DEFERRED slice mapped to its phase sequence (implement → "
             "reviews → reconcile → land) with subagent + skill per phase "
             "(slice 057-01)",
    )
    psp.add_argument("spec", help="path to spec.md")

    # Slice 048-04: read-only digest of the `## Amendments` overrides on
    # closed records (ADR-0010) — current truth without rereading drift.
    pam = sub.add_parser(
        "amendments",
        help="digest the `## Amendments` overrides on closed records "
             "under docs/specs/ and docs/decisions/ (slice 048-04)",
    )
    pam.add_argument("--project-dir", default=".",
                     help="project root directory (default: cwd)")
    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        if ns.command == "transition":
            summary = transition(
                Path(ns.spec), ns.slice, ns.status,
                push=ns.push, pr_mode=ns.pr_mode,
                release=ns.release, reason=ns.reason,
            )
            print(summary)
        elif ns.command == "status-board":
            summary = regenerate_status_board(Path(ns.project), force=ns.force)
            print(summary)
        elif ns.command == "stale":
            report = stale(Path(ns.project_dir), days=ns.days)
            sys.stdout.write(report)
        elif ns.command == "routing-stats":
            sys.stdout.write(
                routing_stats(Path(ns.project_dir), days=ns.days)
            )
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
        elif ns.command == "code-health-review-needed":
            needed = slice_needs_code_health_review(Path(ns.spec), ns.slice)
            sys.stdout.write("true\n" if needed else "false\n")
        elif ns.command == "session-plan":
            sys.stdout.write(session_plan(Path(ns.spec)))
        elif ns.command == "amendments":
            sys.stdout.write(amendment_digest(Path(ns.project_dir)))
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
