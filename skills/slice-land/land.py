"""
jig slice-land helper — slices 007-01 (land-prepare) + 007-02
(direct-mode-execute) + 007-03 (pr-mode-execute).

Deterministic readiness check + landing-plan emitter for a finished slice.
Mirrors the workflow.py / review.py / adr.py / tdd.py shape: SKILL.md drives
judgment; this script does file parsing + report generation + (in pr mode)
PR body file emission.

Subcommands:
    python3 land.py prepare <spec.md> <slice-fragment> [--mode {direct,pr}]
    python3 land.py execute --mode {direct,pr} <spec.md> <slice-fragment> [--dry-run]

Readiness checks:
  1. STATUS line under the slice header equals "DONE".
  2. `tdd.py run` (shelled out) returns 0 (green) — exit 2 (no runner)
     surfaces as a yellow warning, not a hard block. Exit 1 is a blocker.
  3. A `### Deviation log` (or case-variant prefix) subsection exists
     within the slice's section bounds.
  4. All DoD `- [ ]` boxes inside the slice section are ticked.

Exit codes:
  0 — all four checks pass (slice is ready to land).
  1 — at least one check failed (report still emits; blockers listed).
  2 — user error (missing spec, ambiguous fragment, invalid --mode).

prepare: does NOT mutate git state. Mode-specific next-steps appear as
  suggested commands the user copy-pastes. The only write is the PR body
  file (mode=pr). Read-only `git rev-parse --abbrev-ref HEAD` is permitted.
  A soft, never-gating servo advisory (spec 072-01) may trail the report
  when `.servo/` is present in the target — filesystem-probed only (no
  subprocess), opt-out via `.jig/no-servo-hint`; it never alters the exit code.

execute --mode direct: DOES mutate git state. Runs `git checkout main`,
  `git merge <branch> --ff-only`, `git push origin main`. Guards: refuses if
  current branch is main/master; refuses if main has diverged (FF not possible).
  `git worktree remove` is never executed — always printed as a suggestion.
  Use `--dry-run` to print the commands without running them.

execute --mode pr: DOES mutate remote state. Runs `git push -u origin
  <branch>` then `gh pr create --title <title> --body-file <path>`. Guards:
  refuses if current branch is main/master; refuses if `gh` is not on PATH;
  refuses if `origin` does not point at github.com.  `git worktree remove`
  and `gh pr merge` are never executed — both are post-landing suggestions.
  Use `--dry-run` to print the commands without running them.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.atomic_io import atomic_write_text
from _common.parsing import (
    SliceLookupError,
    check_deviation_log,  # noqa: F401 (re-export)
)
from _common.parsing import load_slice as _load_slice_common
from _common.parsing import parse_frontmatter as _parse_frontmatter


class LandError(RuntimeError):
    """User-facing CLI error — caller exits 2."""


VALID_MODES = ("direct", "pr")
DEVIATION_EXCERPT_MAX_CHARS = 500


def load_slice(spec_path, slice_fragment: str):
    """Resolve `slice_fragment` to a SliceLocation, dual-read (slice file
    or `## Slice` section in `spec_path`). Re-raises SliceLookupError as
    LandError so the CLI message keeps its `land:` prefix.

    Slice 018-02 migration: replaced `find_slice_section(text, fragment)`
    + manual `spec_path.read_text()` callers with a single helper that
    handles both layouts.
    """
    try:
        return _load_slice_common(spec_path, slice_fragment)
    except SliceLookupError as e:
        raise LandError(str(e)) from e


# ---------- readiness checks ----------


def check_status(section: str) -> tuple:
    """Returns (ok: bool, actual_status: str). ok iff status == DONE.

    Layout-aware (slice 018-02): looks for the prose `**STATUS:**`
    marker first (legacy + embedded), then falls back to the
    frontmatter `status:` field — slice files (file-per-slice layout
    from 018-01) carry status in frontmatter rather than as a marker.
    """
    m = re.search(r"\*\*STATUS:\s*([A-Z_]+)\*\*", section)
    if m:
        return m.group(1) == "DONE", m.group(1)
    # Try frontmatter — slice files (018-01) start with `---\n...---\n`.
    # `parse_frontmatter` requires the block at column 0, so feed the
    # section as-is for slice files. For embedded sections that have
    # frontmatter AFTER the heading, also try skipping the heading line.
    fm_fields, _ = _parse_frontmatter(section)
    if not fm_fields:
        nl = section.find("\n")
        if nl >= 0 and section.startswith("##"):
            fm_fields, _ = _parse_frontmatter(section[nl + 1:].lstrip("\n"))
    status = fm_fields.get("status", "").strip()
    if status:
        return status == "DONE", status
    return False, "MISSING"


def check_tests(target: Path) -> tuple:
    """Shell out to tdd.py run. Returns (status, exit_code) where status
    is one of 'green', 'red', 'warn'."""
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", "")).resolve() \
        if os.environ.get("CLAUDE_PLUGIN_ROOT") else \
        Path(__file__).resolve().parents[2]
    tdd_py = plugin_root / "skills" / "tdd-loop" / "tdd.py"
    if not tdd_py.is_file():
        # Helper missing entirely — surface as warning (env error, not
        # red tests).
        return "warn", -1
    try:
        result = subprocess.run(
            [sys.executable, str(tdd_py), "run", str(target)],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        return "warn", -1
    if result.returncode == 0:
        return "green", 0
    if result.returncode == 2:
        return "warn", 2
    return "red", result.returncode


# Slice 045-03: `check_deviation_log` was lifted to `_common.parsing` so the
# `workflow.py transition` gate (ADR-0014 §5) can reuse the SAME predicate
# without a cross-skill import. Imported above and re-exported here so this
# module's own callers keep using `land.check_deviation_log` unchanged
# (`test_land.py` exercises it transitively through `prepare()`).


CLOSE_OUT_RE = re.compile(r"(?im)^###\s+close[- ]?out\b")

# Inbox 2026-05-18 `slice-land/parser/checkboxes-in-code-blocks` —
# example checkbox lines embedded in fenced ```...``` blocks inside AC
# text were being counted as real DoD items. Mirrors the
# `_strip_fenced_blocks` helper used by the judgment-skill surface tests
# (clarify / contracts / arch-review / analyze / pr-review) for the same
# parser-ignores-fenced-region invariant. Allows leading whitespace on
# the fence so indented fenced blocks inside numbered-AC list items also
# get stripped (the surface-test variant doesn't need this because docs
# fence at the top level only).
_FENCED_BLOCK_RE = re.compile(r"(?ms)^[ \t]*```.*?^[ \t]*```[ \t]*$")


def check_dod(section: str) -> tuple:
    """Returns (ok, ticked, total) where ok iff total >= 1 AND ticked == total.

    Spec 009 / slice 009-01: a `### Close-out` subsection inside the slice
    terminates the DoD count — checkboxes inside it are treated as
    post-DONE follow-up (status-board regen, CLAUDE.md updates) and
    excluded from the count. Heading is case-insensitive and tolerates
    `Close-out` / `Closeout` / `close out` variants; H3 (`###`) is
    required to avoid accidentally matching H2/H4 headings.

    Fenced ```...``` blocks inside AC text are stripped before scanning
    so example checkbox lines in documentation don't count as real DoD
    items."""
    m = CLOSE_OUT_RE.search(section)
    dod_section = section[:m.start()] if m else section
    dod_section = _FENCED_BLOCK_RE.sub("", dod_section)
    # Find all `- [ ]` and `- [x]` lines in the DoD region.
    boxes = re.findall(r"(?m)^\s*-\s+\[([ xX])\]", dod_section)
    total = len(boxes)
    ticked = sum(1 for b in boxes if b.lower() == "x")
    ok = total >= 1 and ticked == total
    return ok, ticked, total


# ---------- branch/worktree detection ----------


def _detect_branch() -> str:
    """Read-only `git rev-parse --abbrev-ref HEAD`. Falls back to
    `<BRANCH>` placeholder if git is unavailable or not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        return "<BRANCH>"
    if result.returncode != 0:
        return "<BRANCH>"
    name = result.stdout.strip()
    return name or "<BRANCH>"


def _detect_worktree_path() -> str:
    """Canonical cwd — same shape as workflow.py reads `os.getcwd()`."""
    try:
        return os.getcwd()
    except (OSError, FileNotFoundError):
        return "<WORKTREE>"


# ---------- AC extraction (for PR body) ----------


def extract_ac_items(section: str) -> list:
    """Parse the numbered Acceptance Criteria list out of the slice section.
    Returns a list of (number, first_line_text) tuples.

    The AC list starts after `**Acceptance Criteria:**` and continues as
    long as lines begin with `N. ` or are continuations of a prior item.
    Stops at a blank line followed by a `**Some Bold:**` paragraph header
    or another section."""
    m = re.search(r"\*\*Acceptance\s+Criteria:\*\*\s*\n", section)
    if not m:
        return []
    rest = section[m.end():]
    items = []
    # Walk line-by-line; group numbered items
    current_num = None
    current_lines = []
    for line in rest.splitlines():
        if not line.strip() and current_num is None:
            continue
        num_match = re.match(r"^(\d+)\.\s+(.*)$", line)
        if num_match:
            # Flush previous item
            if current_num is not None:
                items.append((current_num, " ".join(current_lines).strip()))
            current_num = int(num_match.group(1))
            current_lines = [num_match.group(2)]
            continue
        # Continuation: indented line (or non-empty) belongs to current item
        if current_num is not None:
            if line.startswith(("   ", "\t")) and line.strip():
                # Skip continuations; we only need first line per AC
                continue
            if not line.strip():
                # Blank line — likely end of list, but allow one blank
                # before stopping
                continue
            # Non-indented, non-blank, non-numbered line — end of list
            break
    if current_num is not None:
        items.append((current_num, " ".join(current_lines).strip()))
    return items


def extract_deviation_excerpt(section: str, max_chars: int = DEVIATION_EXCERPT_MAX_CHARS) -> str:
    """Extract the first ~max_chars of the Deviation log subsection."""
    m = re.search(r"(?im)^###\s+deviation\s+log\b[^\n]*\n", section)
    if not m:
        return ""
    body = section[m.end():].strip()
    if len(body) <= max_chars:
        return body
    return body[:max_chars].rstrip() + "..."


def extract_goal_paragraph(section: str) -> str:
    """First Goal sentence/paragraph from the slice section.
    Returns the text after `**Goal:**` up to the next blank line."""
    m = re.search(r"\*\*Goal:\*\*\s*(.+?)(?:\n\s*\n|\n\*\*)", section, re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip()


# ---------- spec number / slice number extraction ----------


def parse_spec_slice_numbers(spec_path: Path, slice_label: str) -> tuple:
    """Extract (spec_number, slice_number) from a path like
    `docs/specs/007-slice-land/spec.md` and slice label like
    `007-01 — land-prepare`.

    Returns ("007", "01") on success. Falls back to ("000", "00") if
    parsing fails — used only for the predictable PR body file path."""
    spec_num = "000"
    slice_num = "00"
    # Spec number from parent dir like "007-slice-land"
    parent = spec_path.parent.name
    pm = re.match(r"(\d{3})-", parent)
    if pm:
        spec_num = pm.group(1)
    # Slice number from label like "007-01 — name" or just "007-01"
    sm = re.match(r"(\d{3})-(\d{2})", slice_label)
    if sm:
        spec_num = sm.group(1)
        slice_num = sm.group(2)
    return spec_num, slice_num


# ---------- report rendering ----------


def render_readiness_section(checks: dict) -> str:
    """Render the four-line readiness checklist."""
    lines = ["## Readiness checks", ""]

    # Status
    if checks["status_ok"]:
        lines.append("- [x] Status: DONE")
    else:
        actual = checks["status_actual"]
        lines.append(f"- [ ] Status: {actual} (must be DONE)")

    # Tests
    test_status = checks["test_status"]
    if test_status == "green":
        lines.append("- [x] Tests: green (`tdd.py run` exit 0)")
    elif test_status == "warn":
        # `[?]` marker — warning, neither pass nor fail
        lines.append("- [?] Tests: warning — no test runner detected "
                     "(slice may be doc-only)")
    else:  # red
        lines.append(f"- [ ] Tests: red (`tdd.py run` exit {checks['test_exit']})")

    # Deviation log
    if checks["deviation_log_ok"]:
        lines.append("- [x] Deviation log: present")
    elif checks.get("skip_deviation_log"):
        # Slice 019-01: caller passed --no-deviation-log to land
        # retroactively (e.g. a pre-jig DONE slice imported under
        # jig's lifecycle). Render as a warning, not a blocker.
        lines.append("- [?] Deviation log: skipped (--no-deviation-log)")
    else:
        lines.append("- [ ] Deviation log: missing "
                     "(`### Deviation log` subsection required)")

    # DoD
    if checks["dod_ok"]:
        lines.append(f"- [x] DoD: {checks['dod_ticked']}/{checks['dod_total']} "
                     "boxes ticked")
    else:
        lines.append(f"- [ ] DoD: {checks['dod_ticked']}/{checks['dod_total']} "
                     "boxes ticked (all must be ticked)")

    return "\n".join(lines)


def render_blockers(checks: dict) -> str:
    """If any check failed (excluding warns), render a Blockers section."""
    blockers = []
    if not checks["status_ok"]:
        blockers.append(
            f"- Status is `{checks['status_actual']}` — transition to DONE first."
        )
    if checks["test_status"] == "red":
        blockers.append(
            f"- Tests are red (`tdd.py run` exit {checks['test_exit']}). Fix failures first."
        )
    # Slice 019-01: skip the deviation-log blocker when the caller
    # opted in via --no-deviation-log. The check still runs and shows
    # in the readiness section as `[?]`; it just doesn't fail the gate.
    if not checks["deviation_log_ok"] and not checks.get("skip_deviation_log"):
        blockers.append(
            "- Deviation log subsection (`### Deviation log`) is missing from the slice. "
            "Add it under the slice heading before landing."
        )
    if not checks["dod_ok"]:
        blockers.append(
            f"- DoD: {checks['dod_total'] - checks['dod_ticked']} unchecked box(es) "
            f"({checks['dod_ticked']}/{checks['dod_total']} ticked). Finish DoD first."
        )
    if not blockers:
        return ""
    return "## Blockers\n\n" + "\n".join(blockers)


def render_next_steps_direct(branch: str, worktree: str) -> str:
    """Direct-mode (merge to main) git commands."""
    return (
        "## Next steps (mode: direct)\n\n"
        "Run these from the project root (NOT inside this worktree):\n\n"
        "```\n"
        "git checkout main\n"
        f"git merge {branch} --ff-only\n"
        "git push origin main\n"
        f"git worktree remove {worktree}  # optional, after the merge lands\n"
        "```\n"
    )


def _parse_skill_from_frontmatter(spec_text: str) -> str:
    """Extract the `skill:` value from the spec's YAML frontmatter (if any).
    Returns "" if not found — caller falls back to a generic prefix."""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", spec_text, re.DOTALL)
    if not m:
        return ""
    skill_match = re.search(r"^skill:\s*(\S+)\s*$", m.group(1), re.MULTILINE)
    return skill_match.group(1) if skill_match else ""


def render_next_steps_pr(branch: str, pr_body_path: Path, slice_label: str,
                         skill: str = "") -> str:
    """PR-mode (push + gh pr create) commands."""
    scope = f"({skill})" if skill else ""
    title = f"feat{scope}: {slice_label}"
    return (
        "## Next steps (mode: pr)\n\n"
        "Run these from the project root:\n\n"
        "```\n"
        f"git push -u origin {branch}\n"
        f"gh pr create --title \"{title}\" --body-file {pr_body_path}\n"
        "```\n\n"
        f"The PR body is staged at `{pr_body_path}`. Edit it before "
        "running `gh pr create` if needed.\n"
    )


def render_pr_body(slice_label: str, spec_path: Path, goal: str,
                   ac_items: list, deviation_excerpt: str) -> str:
    """Build the PR body markdown."""
    ac_block = "\n".join(f"- AC {n} — {text}" for n, text in ac_items) \
        if ac_items else "- (no acceptance criteria parsed)"
    dev_block = deviation_excerpt or "(no deviation log excerpt available)"
    return (
        f"# Slice {slice_label}\n\n"
        f"## Context\n\n"
        f"{goal}\n\n"
        f"Spec: [{spec_path}]({spec_path})\n\n"
        f"## Acceptance criteria\n\n"
        f"{ac_block}\n\n"
        f"## Deviation log\n\n"
        f"{dev_block}\n\n"
        f"## Test plan\n\n"
        f"- [x] All ACs pass (full suite green)\n"
        f"- [x] Reviewed by `reviewer` subagent\n"
        f"- [x] Reconciliation review pass\n\n"
        f"Generated by [jig slice-land](skills/slice-land/SKILL.md)\n"
    )


# ---------- servo pull-hint (spec 072-01) ----------
#
# A soft, never-gating, filesystem-only advisory that trails the readiness
# report when servo (jig's autonomous sibling plugin) is scaffolded into the
# target. ADR-0022 §5: mention servo ONLY when its infra is present — a jig
# user who never installed servo sees nothing. The hint points at servo's
# current post-ADR-0008 shape (a /goal-driven, Routine-triggerable loop) and
# names a resumable paused run when one exists. It runs NO subprocess and
# never invokes any servo:* command (the supervised-default boundary that is
# the reason servo is a separate plugin). Opt-out: `.jig/no-servo-hint`
# (parity with `.jig/no-people-md`, spec 050).


# servo's durable per-project manifest / oracle (servo architecture.md):
# either signals a scaffolded `.servo/`.
_SERVO_PRESENCE_SIGNALS = ("install.json", "oracle.sh")
# servo's opt-out marker, mirroring `.jig/no-people-md` (spec 050).
_SERVO_HINT_OPT_OUT = (".jig", "no-servo-hint")


def _servo_present(target: Path) -> bool:
    """Filesystem-only probe: servo is scaffolded iff `<target>/.servo/`
    contains `install.json` OR `oracle.sh`. No subprocess."""
    servo_dir = target / ".servo"
    return any((servo_dir / name).exists() for name in _SERVO_PRESENCE_SIGNALS)


def _servo_hint_opted_out(target: Path) -> bool:
    """True iff the `.jig/no-servo-hint` marker exists at the target root.
    Presence is the only state read; contents are ignored."""
    return (target / _SERVO_HINT_OPT_OUT[0] / _SERVO_HINT_OPT_OUT[1]).exists()


def _latest_paused_run(target: Path) -> Path:
    """Return the most recently modified `.servo/runs/*/state.json`, or None
    when there are no paused runs. Filesystem-only (glob + stat); no
    subprocess."""
    runs = list((target / ".servo" / "runs").glob("*/state.json"))
    if not runs:
        return None
    return max(runs, key=lambda p: p.stat().st_mtime)


def render_servo_advisory(target: Path) -> str:
    """Render the trailing `## servo` advisory section, or "" when servo is
    absent or the hint is opted out.

    Filesystem-only (no subprocess). Points at servo's current
    (`/goal`-driven, Routine-triggerable) shape and, when a paused run exists
    at `.servo/runs/<id>/state.json`, names it as resumable (referencing the
    relative path; the most recently modified run when several exist).
    Advisory-only — jig runs no servo command."""
    if _servo_hint_opted_out(target) or not _servo_present(target):
        return ""

    lines = [
        "## servo",
        "",
        "servo is scaffolded here (`.servo/` present). This is an advisory "
        "only — jig runs no servo command.",
        "",
        "Continue autonomously with servo's current `/goal`-driven, "
        "Routine-triggerable loop (servo `ADR-0008`).",
    ]

    run_state = _latest_paused_run(target)
    if run_state is not None:
        try:
            rel = run_state.relative_to(target)
        except ValueError:
            rel = run_state
        lines.append("")
        lines.append(
            f"A paused run exists — resume it from `{rel}`."
        )

    return "\n".join(lines)


# ---------- main pipeline ----------


def prepare(spec_path: Path, slice_fragment: str,
            mode: str = None, target: Path = None,
            skip_deviation_log: bool = False) -> tuple:
    """Run all four readiness checks and emit the markdown report.

    Returns (report_text, exit_code). exit_code is 0 if all checks pass
    (warnings don't block), 1 if at least one check failed."""
    if not spec_path.is_file():
        raise LandError(f"spec not found: {spec_path}")

    loc = load_slice(spec_path, slice_fragment)
    section = loc.text[loc.start:loc.end]
    label = loc.label

    # Run the four checks
    status_ok, status_actual = check_status(section)
    test_status, test_exit = check_tests(target or Path.cwd())
    deviation_log_ok = check_deviation_log(section)
    dod_ok, dod_ticked, dod_total = check_dod(section)

    checks = {
        "status_ok": status_ok,
        "status_actual": status_actual,
        "test_status": test_status,
        "test_exit": test_exit,
        "deviation_log_ok": deviation_log_ok,
        "dod_ok": dod_ok,
        "dod_ticked": dod_ticked,
        "dod_total": dod_total,
        "skip_deviation_log": skip_deviation_log,
    }

    # Render the readiness section + optional blockers
    parts = [f"# Landing readiness — slice {label}", ""]
    parts.append(render_readiness_section(checks))

    blockers = render_blockers(checks)
    if blockers:
        parts.append("")
        parts.append(blockers)

    # Determine pass/fail. Warnings (`warn`) don't block.
    # Slice 019-01: --no-deviation-log demotes the deviation-log
    # blocker to a warning. STATUS, tests, and DoD all still gate.
    has_blocker = (
        not status_ok
        or test_status == "red"
        or (not deviation_log_ok and not skip_deviation_log)
        or not dod_ok
    )

    # Next-steps section (only on --mode, regardless of blocker state —
    # the user might want the recipe even with blockers visible)
    if mode is not None:
        branch = _detect_branch()
        worktree = _detect_worktree_path()
        parts.append("")
        if mode == "direct":
            parts.append(render_next_steps_direct(branch, worktree))
        elif mode == "pr":
            spec_num, slice_num = parse_spec_slice_numbers(spec_path, label)
            pr_body_path = Path(tempfile.gettempdir()) / \
                f"jig-slice-{spec_num}-{slice_num}-pr-body.md"
            ac_items = extract_ac_items(section)
            deviation_excerpt = extract_deviation_excerpt(section)
            goal = extract_goal_paragraph(section)
            body = render_pr_body(label, spec_path, goal, ac_items,
                                  deviation_excerpt)
            atomic_write_text(pr_body_path, body)
            # Spec-level `skill:` frontmatter ALWAYS lives in spec.md,
            # never in a sibling slice file — read from spec_path directly.
            skill = _parse_skill_from_frontmatter(spec_path.read_text())
            parts.append(render_next_steps_pr(branch, pr_body_path, label, skill))

    # Spec 072-01 — soft, never-gating servo advisory. Appended AFTER
    # `has_blocker` is computed (purely from `checks`) and AFTER the
    # mode block, so it can never alter the exit code (AC4). Filesystem
    # probe of the target only (AC5); silent when servo is absent or the
    # `.jig/no-servo-hint` opt-out is set (AC2/AC6).
    servo_advisory = render_servo_advisory(target or Path.cwd())
    if servo_advisory:
        parts.append("")
        parts.append(servo_advisory)

    report = "\n".join(parts) + "\n"
    return report, (1 if has_blocker else 0)


# ---------- execute: main-worktree detection + git sequence ----------


_PROTECTED_BRANCHES = {"main", "master"}


def _detect_main_worktree_root() -> Path:
    """Return the root of the primary (main) worktree.

    In a linked worktree, `git rev-parse --git-common-dir` returns the
    absolute path to the main `.git` directory, whose parent is the main
    worktree root.  In the main worktree itself, it returns the relative
    path `.git`.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        return Path.cwd()
    if result.returncode != 0:
        return Path.cwd()
    common = result.stdout.strip()
    if common == ".git":
        return Path.cwd()
    return Path(common).resolve().parent


def _check_ff_viable(branch: str) -> tuple:
    """Returns (ok: bool, message: str).

    Verifies that a --ff-only merge of `branch` into the team-wide
    `main` (i.e. `origin/main`) will succeed.

    Spec 037-01: this helper reads `origin/main` rather than the
    local `main` ref, because the local ref may be stale relative
    to what the eventual `git push origin main` will be checked
    against. The previous version compared against local `main`
    and let a stale local-tree user merge into a `main` that the
    remote had since moved past, producing a non-FF push that left
    the user on a half-merged local branch with no recovery hint.

    Algorithm (matches the spec 037 clarifications Q2 + Q4):

      1. If there is no `origin` remote configured, fall through
         silently to the existing local ancestor check. This is the
         local-only repo contract — not a degraded network case, so
         no warning is emitted.
      2. Otherwise, attempt `git fetch origin main`.
         - If it fails (network, auth, etc.), emit a one-line
           warning to stderr and fall through to the local check.
           Mirrors `reserve_spec`'s precedent (workflow.py:1278–1282).
         - If it succeeds but `git rev-parse --verify origin/main`
           still fails, fall through silently to the local check.
      3. With `origin/main` available, run
         `git merge-base --is-ancestor origin/main <branch>`.
         Success → ok. Failure → refuse with a message that names
         both "origin/main" and a "pull or rebase" hint, so callers
         can pattern-match either string per AC #2.
    """
    # Step 1 — origin presence check. No `origin` configured → use the
    # local fallback silently (AC #5: silent on the local-only contract).
    try:
        origin_url_check = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        return False, "git not found"

    has_origin = (origin_url_check.returncode == 0
                  and origin_url_check.stdout.strip())

    if has_origin:
        # Step 2 — fetch. On failure: warn + fall through (AC #4).
        fetch_result = subprocess.run(
            ["git", "fetch", "origin", "main"],
            capture_output=True, text=True,
        )
        if fetch_result.returncode != 0:
            sys.stderr.write(
                "warning: git fetch origin main failed: "
                f"{fetch_result.stderr.strip()}; "
                "proceeding with local view\n"
            )
            # fall through to local check below
        else:
            # Step 3 — verify origin/main ref actually exists locally.
            # If it doesn't, silently fall through (AC #5).
            verify_origin = subprocess.run(
                ["git", "rev-parse", "--verify", "origin/main"],
                capture_output=True,
            )
            if verify_origin.returncode == 0:
                ancestor = subprocess.run(
                    ["git", "merge-base", "--is-ancestor",
                     "origin/main", branch],
                    capture_output=True,
                )
                if ancestor.returncode == 0:
                    return True, ""
                # AC #2: name origin/main + pull/rebase in the
                # refusal message.
                return False, (
                    "local main is behind origin/main — "
                    "pull or rebase before merging"
                )
            # origin/main verify failed: silent fall-through.

    # Local fallback (preserved verbatim from the pre-037-01 shape):
    # used when no origin is configured, when fetch failed (with
    # warning above), or when origin/main is not present locally.
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "main", branch],
            capture_output=True,
        )
    except FileNotFoundError:
        return False, "git not found"
    if result.returncode == 0:
        return True, ""
    # Distinguish "main not found" from "not an ancestor"
    verify = subprocess.run(
        ["git", "rev-parse", "--verify", "main"],
        capture_output=True,
    )
    if verify.returncode != 0:
        return False, "branch 'main' not found in this repo"
    return False, "main has diverged — FF merge not possible; pull or rebase first"


def _run_git_cmd(args: list, cwd: Path, dry_run: bool) -> tuple:
    """Run a single git command.  Returns (success: bool, output: str).
    In dry_run mode, returns (True, "[dry-run] git <args>") without running.
    """
    cmd = ["git"] + args
    if dry_run:
        return True, f"[dry-run] {' '.join(cmd)}"
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(cwd),
        )
    except FileNotFoundError:
        return False, "git not found on PATH"
    output = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
    return result.returncode == 0, output


def _run_gh_cmd(args: list, cwd: Path, dry_run: bool) -> tuple:
    """Run a single gh command.  Mirrors `_run_git_cmd` shape.
    Returns (success: bool, output: str).  In dry_run mode, returns
    (True, "[dry-run] gh <args>") without running.
    """
    cmd = ["gh"] + args
    if dry_run:
        return True, f"[dry-run] {' '.join(cmd)}"
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(cwd),
        )
    except FileNotFoundError:
        return False, "gh not found on PATH"
    output = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
    return result.returncode == 0, output


def _check_gh_available() -> tuple:
    """Slice 007-03 — verify the `gh` CLI is on PATH.  Returns (ok, msg)."""
    if shutil.which("gh") is None:
        return False, ("'gh' CLI not found on PATH — install GitHub CLI "
                       "(https://cli.github.com/) before --mode pr")
    return True, ""


def _check_github_remote(cwd: Path = None) -> tuple:
    """Slice 007-03 — verify that origin points at github.com.
    Substring-matches `github.com` against the origin URL so both HTTPS
    (`https://github.com/...`) and SSH (`git@github.com:...`) forms pass.
    Returns (ok, msg).
    """
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True,
            cwd=str(cwd) if cwd else None,
        )
    except FileNotFoundError:
        return False, "git not found on PATH"
    if result.returncode != 0:
        return False, "no 'origin' remote configured for this repo"
    url = result.stdout.strip()
    if not url:
        return False, "no 'origin' remote configured for this repo"
    if "github.com" not in url:
        return False, (f"remote 'origin' does not point at github.com "
                       f"(url: {url}) — --mode pr requires a GitHub remote")
    return True, ""


def execute(spec_path: Path, slice_fragment: str,
            mode: str = "direct",
            dry_run: bool = False, target: Path = None,
            skip_deviation_log: bool = False) -> tuple:
    """Run the landing sequence for a ready slice.

    Common pipeline:
      1. Run all four readiness checks (identical to `prepare`).
      2. Branch guard (refuse on main/master) — applies to both modes.
      3. Mode-specific guards + git/gh sequence (see `_execute_direct`
         and `_execute_pr`).

    `mode` is "direct" (default) or "pr".
    `target` is passed to the tdd.py invocation inside prepare(); defaults to
    Path.cwd(). Tests pass a tmpdir to avoid running the full suite.

    Returns (report_text, exit_code).
    """
    # Step 1 — readiness checks (reuse prepare logic, no mode output)
    prepare_report, prepare_code = prepare(spec_path, slice_fragment,
                                           mode=None, target=target,
                                           skip_deviation_log=skip_deviation_log)
    parts = [prepare_report.rstrip()]

    if prepare_code != 0:
        # Hard blocker — do not touch git or gh
        return "\n".join(parts) + "\n", 1

    branch = _detect_branch()

    # Step 2 — common branch guard
    if branch in _PROTECTED_BRANCHES:
        parts.append("")
        parts.append(
            f"## Error\n\nRefusing: current branch is '{branch}' — "
            f"execute --mode {mode} must run from a feature or worktree branch.\n"
        )
        return "\n".join(parts) + "\n", 1

    # Step 3 — mode dispatch
    if mode == "pr":
        return _execute_pr(parts, spec_path, slice_fragment, branch,
                           dry_run=dry_run)
    return _execute_direct(parts, branch, dry_run=dry_run)


def _execute_direct(parts: list, branch: str, dry_run: bool) -> tuple:
    """Direct-mode merge sequence: checkout main, merge --ff-only, push."""
    worktree = _detect_worktree_path()
    root = _detect_main_worktree_root()

    if not dry_run:
        ff_ok, ff_msg = _check_ff_viable(branch)
        if not ff_ok:
            parts.append("")
            parts.append(f"## Error\n\nRefusing: {ff_msg}.\n")
            return "\n".join(parts) + "\n", 1

    git_steps = [
        (["checkout", "main"], "git checkout main"),
        (["merge", branch, "--ff-only"], f"git merge {branch} --ff-only"),
        (["push", "origin", "main"], "git push origin main"),
    ]

    if dry_run:
        lines = ["", "## Dry-run — commands that would run", ""]
        lines.append("```")
        for args, _ in git_steps:
            lines.append("git " + " ".join(args))
        lines.append(f"# suggestion (not run): git worktree remove {worktree}")
        lines.append("```")
        parts.extend(lines)
        parts.append("")
        parts.append(
            f"## Post-landing\n\n"
            f"After the merge, optionally clean up the worktree:\n\n"
            f"```\ngit worktree remove {worktree}\n```\n"
        )
        return "\n".join(parts) + "\n", 0

    # Live execution
    log_lines = ["", "## Execute log", ""]
    failed = False
    for args, label in git_steps:
        log_lines.append(f"**{label}**")
        ok, output = _run_git_cmd(args, root, dry_run=False)
        if output:
            log_lines.append(f"```\n{output}\n```")
        if not ok:
            parts.extend(log_lines)
            parts.append("")
            parts.append(f"## Error\n\n`{label}` failed. See output above.\n")
            failed = True
            # Spec 037-01 AC #6: when the push step is the failing
            # one, the user is now on a half-merged local main with
            # no automatic rollback. Append a recovery paragraph
            # rather than performing destructive cleanup (Q1: print +
            # refuse; destructive helpers should not silently reset).
            if args and args[0] == "push":
                parts.append(
                    "Local `main` now carries the merge commit but "
                    "it could not be pushed. Inspect the rejection "
                    "with `git push origin main`; if the remote "
                    "moved, run `git fetch origin main` then "
                    "`git reset --hard origin/main` to drop the "
                    "local merge, then re-run `land.py execute` "
                    "after rebasing your feature branch on the new "
                    "origin.\n"
                )
            break
        log_lines.append("")

    if not failed:
        parts.extend(log_lines)
        parts.append(
            f"## Post-landing\n\n"
            f"Merge complete. Optionally clean up the worktree:\n\n"
            f"```\ngit worktree remove {worktree}\n```\n"
        )

    return "\n".join(parts) + "\n", (1 if failed else 0)


def _execute_pr(parts: list, spec_path: Path, slice_fragment: str,
                branch: str, dry_run: bool) -> tuple:
    """PR-mode push + gh pr create sequence.  Runs from the current
    worktree (not the main worktree root) because the feature branch is
    checked out there."""
    cwd = Path.cwd()

    # PR-specific safety guards
    gh_ok, gh_msg = _check_gh_available()
    if not gh_ok:
        parts.append("")
        parts.append(f"## Error\n\nRefusing: {gh_msg}.\n")
        return "\n".join(parts) + "\n", 1

    remote_ok, remote_msg = _check_github_remote(cwd)
    if not remote_ok:
        parts.append("")
        parts.append(f"## Error\n\nRefusing: {remote_msg}.\n")
        return "\n".join(parts) + "\n", 1

    # Re-parse spec to build PR body + title (same code path as prepare --mode pr)
    loc = load_slice(spec_path, slice_fragment)
    section = loc.text[loc.start:loc.end]
    label = loc.label
    spec_num, slice_num = parse_spec_slice_numbers(spec_path, label)
    pr_body_path = Path(tempfile.gettempdir()) / \
        f"jig-slice-{spec_num}-{slice_num}-pr-body.md"
    ac_items = extract_ac_items(section)
    deviation_excerpt = extract_deviation_excerpt(section)
    goal = extract_goal_paragraph(section)
    body = render_pr_body(label, spec_path, goal, ac_items, deviation_excerpt)
    atomic_write_text(pr_body_path, body)

    # Spec-level frontmatter (the `skill:` field for the PR title prefix)
    # ALWAYS lives in spec.md, never in a slice file — read spec_path
    # directly even when the slice body came from a sibling file.
    spec_md_text = spec_path.read_text()
    skill = _parse_skill_from_frontmatter(spec_md_text)
    scope = f"({skill})" if skill else ""
    title = f"feat{scope}: {label}"

    git_steps = [
        (["push", "-u", "origin", branch], f"git push -u origin {branch}"),
    ]
    gh_steps = [
        (["pr", "create", "--title", title, "--body-file", str(pr_body_path)],
         f"gh pr create --title \"{title}\" --body-file {pr_body_path}"),
    ]

    if dry_run:
        lines = ["", "## Dry-run — commands that would run", ""]
        lines.append("```")
        for args, _ in git_steps:
            lines.append("git " + " ".join(args))
        for _args, label_str in gh_steps:
            lines.append(label_str)
        lines.append("```")
        parts.extend(lines)
        parts.append("")
        parts.append(f"PR body staged at: `{pr_body_path}`\n")
        parts.append(
            f"## Post-landing\n\n"
            f"After review approval, merge via the GitHub UI or "
            f"`gh pr merge {branch}`.\n"
        )
        return "\n".join(parts) + "\n", 0

    # Live execution
    log_lines = ["", "## Execute log", ""]
    failed_label = None

    # 1. git push
    for args, label_str in git_steps:
        log_lines.append(f"**{label_str}**")
        ok, output = _run_git_cmd(args, cwd, dry_run=False)
        if output:
            log_lines.append(f"```\n{output}\n```")
        if not ok:
            failed_label = label_str
            break
        log_lines.append("")

    # 2. gh pr create (only if push succeeded)
    if failed_label is None:
        for args, label_str in gh_steps:
            log_lines.append(f"**{label_str}**")
            ok, output = _run_gh_cmd(args, cwd, dry_run=False)
            if output:
                log_lines.append(f"```\n{output}\n```")
            if not ok:
                failed_label = label_str
                break
            log_lines.append("")

    parts.extend(log_lines)
    if failed_label is not None:
        parts.append("")
        parts.append(f"## Error\n\n`{failed_label}` failed. See output above.\n")
        return "\n".join(parts) + "\n", 1

    parts.append(
        f"## Post-landing\n\n"
        f"PR opened.  After review approval, merge via the GitHub UI or "
        f"`gh pr merge {branch}`.\n"
    )
    return "\n".join(parts) + "\n", 0


# ---------- CLI plumbing ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="land.py",
        description="jig slice-land helper (prepare + execute)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser(
        "prepare",
        help="emit a landing-readiness report for a finished slice",
    )
    pp.add_argument("spec", help="path to spec.md")
    pp.add_argument("slice",
                    help="slice name or fragment (case-insensitive substring)")
    pp.add_argument("--mode", choices=VALID_MODES, default=None,
                    help="append a Next-steps section for the given mode")
    pp.add_argument("--target", default=None,
                    help="directory passed to tdd.py run (default: cwd)")
    pp.add_argument("--no-deviation-log", action="store_true",
                    dest="skip_deviation_log",
                    help="demote missing `### Deviation log` to a warning "
                         "(for retroactive landings of pre-jig DONE slices)")

    ep = sub.add_parser(
        "execute",
        help="run the merge sequence for a finished slice (destructive)",
    )
    ep.add_argument("spec", help="path to spec.md")
    ep.add_argument("slice",
                    help="slice name or fragment (case-insensitive substring)")
    ep.add_argument("--mode", choices=["direct", "pr"], required=True,
                    help="integration mode: 'direct' merges to main locally; "
                         "'pr' pushes the branch and opens a GitHub PR")
    ep.add_argument("--dry-run", action="store_true",
                    help="print commands without executing them")
    ep.add_argument("--target", default=None,
                    help="directory passed to tdd.py run (default: cwd)")
    ep.add_argument("--no-deviation-log", action="store_true",
                    dest="skip_deviation_log",
                    help="demote missing `### Deviation log` to a warning "
                         "(for retroactive landings of pre-jig DONE slices)")
    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        if ns.cmd == "prepare":
            report, code = prepare(
                Path(ns.spec), ns.slice, mode=ns.mode,
                target=Path(ns.target) if ns.target else None,
                skip_deviation_log=ns.skip_deviation_log,
            )
        else:  # execute
            report, code = execute(
                Path(ns.spec), ns.slice,
                mode=ns.mode,
                dry_run=ns.dry_run,
                target=Path(ns.target) if ns.target else None,
                skip_deviation_log=ns.skip_deviation_log,
            )
        sys.stdout.write(report)
        return code
    except LandError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:  # noqa: BLE001 — surface programming errors
        sys.stderr.write(f"land.py failed: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
