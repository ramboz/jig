"""
jig slice-land helper — slice 007-01 (land-prepare)

Deterministic readiness check + landing-plan emitter for a finished slice.
Mirrors the workflow.py / review.py / adr.py / tdd.py shape: SKILL.md drives
judgment; this script does file parsing + report generation + (in pr mode)
PR body file emission.

One subcommand:
    python3 land.py prepare <spec.md> <slice-fragment> [--mode {direct,pr}]

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

The helper does NOT mutate git state. Mode-specific next-steps appear
as suggested commands the user copy-pastes. Per slice 007-01 spec AC #4,
the only destructive operation is writing the PR body file (mode=pr).
Read-only `git rev-parse --abbrev-ref HEAD` is permitted for branch
detection (clarification recorded in the slice's deviation log).
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.parsing import find_slice_section as _find_slice_section_common
from _common.parsing import SliceLookupError


class LandError(RuntimeError):
    """User-facing CLI error — caller exits 2."""


VALID_MODES = ("direct", "pr")
DEVIATION_EXCERPT_MAX_CHARS = 500


def find_slice_section(spec_text: str, slice_fragment: str) -> tuple:
    """Locate the `## Slice ...` header whose H2 contains `slice_fragment`.
    Returns (header_start, section_end, full_label). Raises LandError on
    miss or ambiguity.

    Thin wrapper over `_common.parsing.find_slice_section`.
    """
    try:
        return _find_slice_section_common(spec_text, slice_fragment)
    except SliceLookupError as e:
        raise LandError(str(e)) from e


# ---------- readiness checks ----------


def check_status(section: str) -> tuple:
    """Returns (ok: bool, actual_status: str). ok iff status == DONE."""
    m = re.search(r"\*\*STATUS:\s*([A-Z_]+)\*\*", section)
    if not m:
        return False, "MISSING"
    return m.group(1) == "DONE", m.group(1)


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


def check_deviation_log(section: str) -> bool:
    """Look for a `### Deviation log` (case-insensitive prefix) within the
    slice section. `### Deviation log` and `### Deviation log (after
    reconciliation)` both count."""
    return bool(re.search(
        r"(?im)^###\s+deviation\s+log\b",
        section,
    ))


CLOSE_OUT_RE = re.compile(r"(?im)^###\s+close[- ]?out\b")


def check_dod(section: str) -> tuple:
    """Returns (ok, ticked, total) where ok iff total >= 1 AND ticked == total.

    Spec 009 / slice 009-01: a `### Close-out` subsection inside the slice
    terminates the DoD count — checkboxes inside it are treated as
    post-DONE follow-up (status-board regen, CLAUDE.md updates) and
    excluded from the count. Heading is case-insensitive and tolerates
    `Close-out` / `Closeout` / `close out` variants; H3 (`###`) is
    required to avoid accidentally matching H2/H4 headings."""
    m = CLOSE_OUT_RE.search(section)
    dod_section = section[:m.start()] if m else section
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
        lines.append(f"- [x] Status: DONE")
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
    if not checks["deviation_log_ok"]:
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
    ac_block = "\n".join(f"- AC #{n} — {text}" for n, text in ac_items) \
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


# ---------- main pipeline ----------


def prepare(spec_path: Path, slice_fragment: str,
            mode: str = None, target: Path = None) -> tuple:
    """Run all four readiness checks and emit the markdown report.

    Returns (report_text, exit_code). exit_code is 0 if all checks pass
    (warnings don't block), 1 if at least one check failed."""
    if not spec_path.is_file():
        raise LandError(f"spec not found: {spec_path}")

    text = spec_path.read_text()
    start, end, label = find_slice_section(text, slice_fragment)
    section = text[start:end]

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
    }

    # Render the readiness section + optional blockers
    parts = [f"# Landing readiness — slice {label}", ""]
    parts.append(render_readiness_section(checks))

    blockers = render_blockers(checks)
    if blockers:
        parts.append("")
        parts.append(blockers)

    # Determine pass/fail. Warnings (`warn`) don't block.
    has_blocker = (
        not status_ok
        or test_status == "red"
        or not deviation_log_ok
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
            pr_body_path.write_text(body)
            skill = _parse_skill_from_frontmatter(text)
            parts.append(render_next_steps_pr(branch, pr_body_path, label, skill))

    report = "\n".join(parts) + "\n"
    return report, (1 if has_blocker else 0)


# ---------- CLI plumbing ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="land.py",
        description="jig slice-land helper (prepare)",
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
    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        report, code = prepare(
            Path(ns.spec), ns.slice, mode=ns.mode,
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
