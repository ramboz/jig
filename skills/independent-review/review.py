"""
jig independent-review helper — slices 004-01 (review-helper) + 011-02
(subagent-type-fallback-upgrade) + 031-01 (pr-review-pass) + 031-02
(arch-review-trigger).

Builds the standardized reviewer-subagent prompt for any of: an
implementation review, a reconciliation review, a craft pr-review pass
(slice 031-01), or an on-demand arch-review pass (slice 031-02). The
helper does NOT spawn the subagent itself — Claude owns the Task
invocation. This script just makes the prompt consistent across 100+
invocations.

Slice 011-02 added the `subagent-type` subcommand: it inspects
`${CLAUDE_PLUGIN_ROOT}` and prints either `reviewer` (jig installed as a
plugin — real subagent reachable) or `general-purpose` (fallback). SKILL.md's
bash recipe uses it to pick the Task tool's `subagent_type` argument
deterministically.

Slice 031-01 added the `pr-review` subcommand: a craft-pass prompt that
mirrors `implementation` but evaluates *craft* (scope / blockers / nits /
strengths) rather than acceptance criteria, with SPECIFIC ISSUES entries
tagged `[blocker]`/`[nit]`/`[strength]` so the workflow can decide what
blocks vs. becomes a reconciliation-log entry.

Slice 031-02 added the `arch-review` subcommand: a third on-demand pass
that runs only when a slice's frontmatter declares `arch_review: true`
(queried via `workflow.py arch-review-needed`). It mirrors `pr-review` in
shape but swaps the bucket names to match `jig:arch-review`'s canonical
output (summary / strengths / concerns / open questions).

Skill dispatch for both craft passes is FILE-READ based, not router-based:
the craft/arch pass runs in a read-only `reviewer` subagent with no `Skill`
tool, so it cannot use Claude's skill router. `detect_richer_skill()` checks
for a user-installed skill on disk (`~/.claude/skills/<name>/SKILL.md`); when
present the prompt hands the reviewer that concrete path to read-and-apply,
else it inlines jig's baseline buckets. (A live probe showed the original
prose-router dispatch was inert on the no-`Skill`-tool subagent path; this
promotes spec 031 Open-question-#1 option (b) from deferred fallback.)

Usage:
    python3 review.py implementation <spec.md> <slice-fragment> <deliverable-path>...
    python3 review.py reconciliation <spec.md> <slice-fragment>
    python3 review.py pr-review     <spec.md> <slice-fragment> <deliverable-path>...
    python3 review.py arch-review   <spec.md> <slice-fragment> <deliverable-path>...
    python3 review.py code-health   <spec.md> <slice-fragment> <deliverable-path>...
                                    [--summary-file PATH]
    python3 review.py subagent-type
        {implementation|reconciliation|pr-review|arch-review|code-health}
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import review_evidence as _evidence
from _common.atomic_io import atomic_write_text
from _common.parsing import SliceLookupError
from _common.parsing import load_slice as _load_slice_common


class ReviewError(RuntimeError):
    """User-facing error; CLI exits 2."""


def find_slice_label(spec_path, slice_fragment: str) -> str:
    """Return the full label of the slice whose `## Slice` heading contains
    `slice_fragment` (e.g. `001-01 — greenfield-scaffold`). Raises
    ReviewError on miss or ambiguity.

    Dual-read via `_common.parsing.load_slice`: resolves to either a
    sibling `slice-*.md` file or a `## Slice` section in `spec_path`,
    transparently. Slice 018-02 migrated this from text-based to
    path-based; the prompt builder only needs the label, not the body.
    """
    try:
        loc = _load_slice_common(spec_path, slice_fragment)
    except SliceLookupError as e:
        raise ReviewError(str(e)) from e
    return loc.label


# -------- Prompt templates --------

_PREAMBLE = (
    "You are an independent reviewer. You are seeing this work for the first "
    "time. You have not previously discussed this task with anyone — evaluate "
    "only what is in the files."
)

_PROHIBITIONS = """\
## What you must NOT do

- Do not refer to any prior reasoning or discussion about this task.
- Do not assume context that is not in the files you have been pointed at.
- Do not soften feedback to match what you think the implementer intended.
- Do not modify any files — you have read-only access.
- Do not write to `docs/memory/`. Defining the glossary, capturing learnings,
  or modifying the hot cache are jobs for `memory-sync`, not the reviewer.
"""

_OUTPUT_FORMAT = """\
## Output (required — do not deviate)

```
VERDICT: pass | fail | needs-changes

REASONING:
<2-4 sentences>

SPECIFIC ISSUES:
- <file:line> — <description>
(omit section if none)

RECONCILIATION NOTES:
<deviations the implementer should record in the deviation log>
```

Be terse but specific. Cite file:line when flagging issues."""


# -------- Contract-surface check (slice 022-02) --------

# Matches the H2 heading that the `/jig:vision-elicitation` skill writes
# when Section 13 (Contract surfaces — added by spec 022-02) is filled.
_CONTRACT_SURFACES_HEADING_RE = re.compile(
    r"(?m)^##\s+Contract\s+surfaces\s*$",
)

# Match a candidate "declared surface" bullet — the wizard writes lines
# like `- **HTTP API** (recommended artifact: OpenAPI 3.x at `openapi.yaml`)
# — …` under the `## Contract surfaces` H2. The regex finds the bold
# token; `_is_declared_surface_bullet` then filters out negation phrasings
# (e.g. `- **No external surfaces** — this is a library`) that a user
# might write in lieu of leaving the section skipped. A skipped section
# produces a `<!-- elicited: … / status: skipped -->` marker with no
# declared-surface bullet, so this gate stays quiet.
_DECLARED_SURFACE_BULLET_RE = re.compile(
    r"(?m)^-\s+\*\*([^*]+)\*\*",
)

# Negation tokens at the START of a bullet's bold text — these signal a
# user opting OUT in-bullet instead of via the marker. Treat as "not a
# real declaration." Lowercase-compared; trailing whitespace stripped.
_NEGATION_BOLD_PREFIXES = (
    "no ", "no external", "not ", "none", "n/a",
    "tbd", "skipped", "deferred", "not yet",
)


def _is_declared_surface_bullet(bold_text: str) -> bool:
    """True iff the bullet's bold token looks like a real surface
    declaration. Filters out negation phrasings that produce false
    positives (e.g. `- **No external surfaces** — this is a library`)."""
    bold = bold_text.strip().lower()
    return not any(bold.startswith(neg) for neg in _NEGATION_BOLD_PREFIXES)


def _find_project_root(spec_path: Path) -> Path | None:
    """Walk up from `spec_path` looking for a sibling `docs/architecture.md`.
    Returns the directory containing `docs/` or None on miss.

    Conservative: bails on miss rather than guessing. Used to find the
    project-root so the reviewer-prompt conditional check can read
    `docs/architecture.md` for a `## Contract surfaces` declaration.
    """
    spec_path = Path(spec_path).resolve()
    for candidate in [spec_path.parent, *spec_path.parents]:
        if (candidate / "docs" / "architecture.md").is_file():
            return candidate
    return None


def has_declared_contract_surfaces(project_root: Path) -> bool:
    """Return True iff `<project_root>/docs/architecture.md` has a
    `## Contract surfaces` section with at least one declared-surface
    bullet. Used to decide whether `build_*_prompt` should append the
    contract-surface evaluation hint.

    Conservative on every error mode (missing file, unreadable, no
    `## Contract surfaces` section, section present but empty / skipped):
    returns False. No reviewer-prompt noise when the project hasn't
    declared surfaces (per spec 022-02 AC #2's "no surfaces → no check"
    requirement).
    """
    arch_path = Path(project_root) / "docs" / "architecture.md"
    try:
        text = arch_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    heading_match = _CONTRACT_SURFACES_HEADING_RE.search(text)
    if not heading_match:
        return False
    # Bound the section: from end-of-heading to next `## ` (or EOF).
    section_start = heading_match.end()
    next_h2 = re.search(r"(?m)^##\s+", text[section_start:])
    section_body = (text[section_start:section_start + next_h2.start()]
                    if next_h2 else text[section_start:])
    # Require at least one non-negation bullet. A bullet whose bold token
    # starts with a negation prefix (e.g. "No external surfaces") is
    # treated as an in-bullet opt-out, not a declaration.
    for match in _DECLARED_SURFACE_BULLET_RE.finditer(section_body):
        if _is_declared_surface_bullet(match.group(1)):
            return True
    return False


def _contract_surface_check_block() -> str:
    """The conditional evaluation hint appended to both implementation and
    reconciliation prompts when the project has declared contract surfaces.

    Wording mirrors spec 022-02 AC #2: "slice touches a declared contract
    surface? artifact updated in the same change-set?" Phrased as a
    suggestion-not-blocker per the nudge-don't-mandate ethos (AC #4)."""
    return """\
- **Contract-surface check** (added by spec 022-02 because this project
  declared external contract surfaces in `docs/architecture.md`'s
  `## Contract surfaces` section): does this slice touch any of those
  declared surfaces (HTTP API / event bus / RPC / GraphQL / internal
  data shapes / config / CLI output)? If yes, is the corresponding
  artifact (`openapi.yaml` / `*.schema.json` / `*.proto` /
  `schema.graphql` / etc.) updated in the same change-set as the
  code change? Flag a *suggestion* not a *blocker* — the project may
  have a documented opt-out (ADR or in-section note)."""


# -------- Principles check (slice 024-01 — constitution-gate) --------


def _principles_check_block() -> str:
    """The UNCONDITIONAL evaluation hint appended to both implementation and
    reconciliation prompts. Unlike the contract-surface check (which gates
    on `has_declared_contract_surfaces`), principle adherence is universal
    — every slice review gets this fragment.

    Names principles 1 and 7 by their short-names so a reviewer can grep
    `docs/product-vision.md` § Design principles for the canonical text.
    Stays under 500 characters per prompt-size hygiene (same precedent
    as `_contract_surface_check_block()`)."""
    return """\
- **Principles check** (added by spec 024-01 — constitution-gate): verify
  this slice doesn't violate any of the seven design principles listed in
  `docs/product-vision.md` § Design principles — from principles 1 (hooks
  deterministic / skills judgment) through principles 7 (scaffolding beats
  renting). Flag violations as findings."""


# -------- Engineering-practices check (SDD process gaps) --------


def _practices_check_block() -> str:
    """UNCONDITIONAL evaluation hint covering four SDD process gaps that are
    easy to miss in AC-focused review. Tailored to jig's spec structure
    (`## Tasks`, `### Approach`, ADR pointer convention,
    `docs/inbox.md` / `docs/refinement-todo.md` debt-tracking files).

    Universal — every slice review gets this fragment. The reviewer
    self-gates on "not applicable" cases (e.g. no `## Tasks` section
    means the task-completeness check fires silently).

    Stays under ~900 characters per prompt-size hygiene (looser than the
    500-char principles bound — four sub-bullets need more room than one)."""
    return """\
- **Engineering-practices check**: four SDD process gaps to scan:
  1. **Task completeness** — if a `## Tasks` section exists, are
     unticked items paired with a deferral rationale (inbox link,
     follow-up slice)?
  2. **Approach alignment** — does the implementation follow the spec's
     stated technical approach, or is the deviation documented in the
     deviation log?
  3. **ADR signal** — for architecturally significant changes, is the
     decision recorded somewhere (existing ADR, new ADR, spec rationale)?
  4. **Tech-debt tracking** — new `TODO` / `FIXME` comments need a
     tracking entry (`docs/inbox.md`, `docs/refinement-todo.md`, issue
     link). Pre-existing debt on unmodified lines: out of scope.
  Tag findings with confidence (High / Medium); suppress Low."""


# -------- Test-quality snapshot (slice 043-04) --------


# Default base branch for the merge-base computation. Hardcoded to `main`
# because it's jig's convention and the snapshot is best-effort — a
# project on a different default branch falls back to the graceful
# `_Test-quality snapshot unavailable: ..._` line.
_TEST_QUALITY_BASE_BRANCH = "main"


def _test_quality_snapshot_block(spec_path: Path) -> str:
    """Compute the deterministic test-quality snapshot for the current
    slice and return a markdown block to embed in the implementation
    prompt (slice 043-04).

    Mechanics:
      1. Resolve the project root via `_find_project_root(spec_path)`. If
         the spec doesn't live in a project (no `docs/architecture.md`
         ancestor), fall back to `spec_path.parent`.
      2. Compute `git merge-base main HEAD` from the project root.
      3. `git diff <merge-base>...HEAD` → write to a tempfile.
      4. Invoke `quality.py --diff-file <tmp>` and embed the stdout in a
         markdown fenced YAML block.

    Failure modes (all collapse to a single-line `_Test-quality snapshot
    unavailable: <reason>._`):
      - merge-base not found (detached HEAD, no `main` ref, git absent)
      - empty diff (slice happens to touch nothing diffable)
      - quality.py exited non-zero
      - quality.py emitted `applicable: false`

    The block ends with the cite-or-stay-silent sentences (AC #2) so a
    reviewer reads them in context with the YAML."""
    try:
        project_root = _find_project_root(spec_path)
        if project_root is None:
            # Best-effort: a spec without `docs/architecture.md` may still
            # live inside a git repo. Use the spec's parent as the cwd.
            spec_resolved = Path(spec_path).resolve()
            cwd = spec_resolved.parent if spec_resolved.parent.exists() else None
            if cwd is None:
                return _test_quality_unavailable("merge-base not found")
        else:
            cwd = project_root

        # 1. merge-base main HEAD
        mb = subprocess.run(
            ["git", "merge-base", _TEST_QUALITY_BASE_BRANCH, "HEAD"],
            cwd=str(cwd), capture_output=True, text=True, check=False,
        )
        if mb.returncode != 0 or not mb.stdout.strip():
            return _test_quality_unavailable("merge-base not found")
        merge_base = mb.stdout.strip()

        # 2. diff <merge-base>...HEAD
        diff = subprocess.run(
            ["git", "diff", f"{merge_base}...HEAD"],
            cwd=str(cwd), capture_output=True, text=True, check=False,
        )
        if diff.returncode != 0:
            return _test_quality_unavailable("git diff failed")
        diff_text = diff.stdout
        if not diff_text.strip():
            return _test_quality_unavailable("empty diff")

        # 3. write to tempfile, invoke quality.py
        quality_py = Path(__file__).resolve().parent.parent / "tdd-loop" / "quality.py"
        if not quality_py.is_file():
            return _test_quality_unavailable("quality.py not found")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".diff", delete=False, encoding="utf-8",
        ) as tmp:
            tmp.write(diff_text)
            tmp_path = tmp.name
        try:
            qres = subprocess.run(
                [sys.executable, str(quality_py), "--diff-file", tmp_path],
                capture_output=True, text=True, check=False,
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if qres.returncode != 0:
            return _test_quality_unavailable("quality.py exited non-zero")

        yaml_out = qres.stdout
        # If the snapshot says applicable: false, surface its reason inline.
        m = re.search(r"(?m)^\s*applicable:\s*(\w+)", yaml_out)
        if m and m.group(1).lower() == "false":
            reason_m = re.search(r"(?m)^\s*reason:\s*\"?([^\"\n]+)\"?", yaml_out)
            reason = reason_m.group(1).strip() if reason_m else "unknown"
            return _test_quality_unavailable(f"not applicable ({reason})")

        # 4. wrap in the markdown block (AC #1 + AC #2)
        return (
            "## Test-quality snapshot (deterministic)\n"
            "\n"
            "```yaml\n"
            f"{yaml_out.rstrip()}\n"
            "```\n"
            "\n"
            "When raising a test-quality finding, cite the fired signal by name.\n"
            "When all signals read false, do not invent test-quality concerns —\n"
            "absence of a signal is evidence of nothing-to-flag."
        )
    except Exception as exc:  # noqa: BLE001 — graceful degradation per AC #3
        return _test_quality_unavailable(f"helper error: {exc.__class__.__name__}")


def _test_quality_unavailable(reason: str) -> str:
    """Fallback single-line per AC #3 — the reviewer is told to proceed
    on judgment alone when the snapshot can't be built."""
    return f"_Test-quality snapshot unavailable: {reason}._"


def build_implementation_prompt(spec_path: Path, slice_label: str,
                                deliverables: list) -> str:
    """Construct the standard implementation-review prompt.

    Slice 022-02 added a conditional contract-surface check: if the
    project's `docs/architecture.md` has a `## Contract surfaces`
    section with at least one declared surface, the Evaluate block
    grows an extra bullet asking the reviewer to flag missing artifact
    updates. Quiet when no surfaces are declared.

    Slice 024-01 added an UNCONDITIONAL principles-check block — every
    review (regardless of project state) gets a line asking the reviewer
    to verify the slice doesn't violate any of the seven principles in
    `docs/product-vision.md` § Design principles.
    """
    deliverable_lines = "\n".join(f"   - `{d}`" for d in deliverables)
    # Slice 022-02: contract-surface bullet sits at the tail of the Evaluate
    # bullet list when the project declared surfaces.
    pre_snapshot_check = ""
    project_root = _find_project_root(spec_path)
    if project_root and has_declared_contract_surfaces(project_root):
        pre_snapshot_check = "\n" + _contract_surface_check_block()
    # Slice 043-04: deterministic test-quality snapshot. Lands BETWEEN
    # the Evaluate bullets and the principles/practices check blocks, as
    # its own H2. Append unconditionally — the helper degrades gracefully
    # (returns a single-line `_unavailable_` fallback) on every error mode.
    snapshot_block = _test_quality_snapshot_block(spec_path)
    # Slice 024-01: principles-check block (UNCONDITIONAL). Slice 043-04
    # repositioned this block to land AFTER the snapshot, per the
    # "between Evaluate and _principles_check_block" placement rule.
    post_snapshot_check = "\n" + _principles_check_block()
    # Engineering-practices check appended UNCONDITIONALLY — process
    # gaps (task completeness, approach alignment, ADR signal, tech-debt
    # tracking) are universal across slices.
    post_snapshot_check += "\n" + _practices_check_block()
    return f"""{_PREAMBLE}

## Your job

Review the implementation of slice **{slice_label}** against its spec and
acceptance criteria.

## What to read (in this order)

1. The spec — `{spec_path}`. **Focus on Slice {slice_label} only.** Other
   slices in the same spec (DONE or DRAFT) are out of scope; do not re-review them.
2. The slice's plan and tasks if present (alongside `spec.md`).
3. The deliverables:
{deliverable_lines}

{_PROHIBITIONS}
## Evaluate

For each acceptance criterion in slice {slice_label}, verify:
- Is it met by the deliverable?
- Are tests exercising the AC meaningfully (not just superficial assertions)?
- Are there bugs (correctness, edge cases)?
- Any security or robustness concerns relevant to this change?{pre_snapshot_check}

{snapshot_block}

## Cross-cutting checks
{post_snapshot_check}

{_OUTPUT_FORMAT}
"""


# -------- Richer-skill detection (file-read dispatch) --------
#
# The craft (pr-review) and arch (arch-review) passes spawn a `reviewer`
# subagent whose tools are Read/Glob/Grep only — it has NO `Skill` tool, so
# it CANNOT route to a user-installed skill via Claude's skill router. A live
# probe (an actual `reviewer`-shaped subagent handed the real craft prompt)
# confirmed this: the subagent reports no skill-invocation capability at all,
# but CAN `Read` files under `~/.claude/`. So the original prose dispatch
# ("apply the most-specific SKILL.md the router resolves to") was inert on the
# subagent path — the reviewer just followed the baseline buckets inlined in
# this prompt and never reached a richer user skill.
#
# Fix: deterministically detect a richer user-installed skill on disk and hand
# the reviewer its concrete path to read-and-apply. This promotes spec 031
# Open-question-#1 option (b) ("filesystem-detect installed skills") from
# "fallback if (a) misroutes" now that (a) is shown to misroute here.


def detect_richer_skill(skill_name: str) -> "str | None":
    """Return the path to a USER-scope installed `<skill_name>` SKILL.md
    (`~/.claude/skills/<skill_name>/SKILL.md`), or None when only jig's
    bundled baseline is available.

    User-scope only, by design: a *project*-scope `.claude/skills/<name>/`
    may be jig's OWN baseline, copied in by `scaffold-init` — indistinguishable
    by path from a genuinely richer project skill — so detecting it would
    false-positive on every scaffolded repo. User installs are unambiguous.
    Project-scope detection is deferred (see docs/refinement-todo.md).

    Conservative on every error (returns None): never block the craft/arch
    pass because a `Path`/`home()`/`stat` call raised. `Path.home()` honors
    `$HOME`, which keeps this hermetically testable.
    """
    try:
        candidate = Path.home() / ".claude" / "skills" / skill_name / "SKILL.md"
        if candidate.is_file():
            return str(candidate)
    except (OSError, ValueError, RuntimeError):
        pass
    return None


# -------- pr-review prompt (slice 031-01) --------


_PR_REVIEW_OUTPUT_FORMAT = """\
## Output (required — do not deviate)

```
VERDICT: pass | fail | needs-changes

REASONING:
<2-4 sentences>

SPECIFIC ISSUES:
- [blocker] <file:line> — <description>
- [nit] <file:line> — <description>
- [strength] <file:line> — <description>
(omit section if none; tag every entry with one of [blocker] / [nit] /
 [strength] so the workflow can decide what blocks vs. logs)

RECONCILIATION NOTES:
<nits and strengths that should land in the deviation log rather than
 block the REVIEWED transition>
```

Be terse but specific. Cite file:line when flagging issues."""


def build_pr_review_prompt(spec_path: Path, slice_label: str,
                           deliverables: list) -> str:
    """Construct the standard pr-review (craft pass) prompt.

    Slice 031-01: the orchestrator runs this pass AFTER the compliance
    pass (`build_implementation_prompt`) and BEFORE the REVIEWED
    transition. The pass produces the four canonical buckets the
    `jig:pr-review` skill emits — scope / blockers / nits / strengths —
    wrapped in the same VERDICT / REASONING / SPECIFIC ISSUES /
    RECONCILIATION NOTES envelope as the compliance pass so the workflow
    can consume one verdict shape regardless of which pass produced it.

    Dispatch is file-read based, not router-based. The craft pass runs in
    a read-only `reviewer` subagent with no `Skill` tool, so it cannot use
    Claude's skill router. `detect_richer_skill("pr-review")` checks for a
    user-installed skill on disk; when present, the prompt hands the reviewer
    that concrete path to read-and-apply (it supersedes the inlined baseline
    buckets). When absent, the prompt inlines jig's baseline buckets. Either
    way, findings are normalized into the shared verdict envelope below.

    NOTE: unlike `build_implementation_prompt` and
    `build_reconciliation_prompt`, this builder does NOT append
    `_principles_check_block()`. The craft pass is scoped to scope /
    blockers / nits / strengths only — constitution-adherence is the
    compliance pass's job (and is repeated on the reconciliation pass).
    Adding it here would duplicate work and conflict with the four-bucket
    framing the `jig:pr-review` skill description establishes.
    """
    deliverable_lines = "\n".join(f"   - `{d}`" for d in deliverables)
    richer = detect_richer_skill("pr-review")
    if richer:
        routing_para = (
            f"A richer `pr-review` skill is installed at `{richer}`.\n"
            "**Read that SKILL.md in full now — and any reference files it "
            "points to — then apply ITS review rubric as your craft pass.** It "
            "supersedes the baseline buckets below. Your tools are read-only; "
            "if you cannot read that path, fall back to the baseline. Whatever "
            "rubric you apply, normalize your findings into the required output "
            "envelope at the end of this prompt.\n\n"
            "For reference, the four canonical buckets jig's bundled "
            "`pr-review` SKILL.md baseline produces are:"
        )
    else:
        routing_para = (
            "Apply the craft concerns from jig's bundled `pr-review` SKILL.md "
            "baseline. Its four canonical output buckets are:"
        )
    return f"""{_PREAMBLE}

## Your job

You are running the **craft pass** (pr-review) on slice **{slice_label}**.
The compliance pass (jig:independent-review) has already evaluated the
slice against its acceptance criteria — that work is done, and you must
NOT re-evaluate it. Your job is to evaluate the *craft* of the
implementation: scope, blockers, nits, and strengths.

{routing_para}

1. **Scope** — what the change touches, what it does not touch.
2. **Blockers** — concrete must-fix items (correctness, security, missing
   tests for risky logic).
3. **Nits** — nice-to-haves and small polish items.
4. **Strengths** — patterns or choices worth repeating.

## What to read (in this order)

1. The spec — `{spec_path}`. Read slice **{slice_label}** for context,
   but do NOT re-evaluate the acceptance criteria — that's the
   compliance pass's job.
2. The deliverables:
{deliverable_lines}
3. Any related files in the repo you need to verify whether the new
   code follows existing patterns (read-only).

{_PROHIBITIONS}
## Evaluate

- Does the implementation match the spec's stated scope?
- Are there correctness, security, or robustness concerns?
- Are tests exercising the change meaningfully?
- Are there nits worth flagging (naming, structure, idioms)?
- What does the change get right that's worth calling out?

{_PR_REVIEW_OUTPUT_FORMAT}
"""


# -------- arch-review prompt (slice 031-02) --------


def build_arch_review_prompt(spec_path: Path, slice_label: str,
                             deliverables: list) -> str:
    """Construct the standard arch-review (architecture pass) prompt.

    Slice 031-02: the orchestrator runs this pass AFTER the compliance
    + craft passes, but ONLY when the slice's frontmatter declares
    `arch_review: true`. Unlike `pr-review` (which always fires), this
    pass is on-demand — slices that don't touch module boundaries or
    public contracts skip it.

    The pass produces the four canonical buckets the `jig:arch-review`
    skill emits — summary / strengths / concerns / open questions —
    wrapped in the same verdict envelope as the compliance + craft
    passes so the workflow can consume one verdict shape across all
    three passes.

    Same file-read dispatch as `build_pr_review_prompt`: the read-only
    `reviewer` subagent has no `Skill` tool, so
    `detect_richer_skill("arch-review")` checks disk for a user-installed
    skill and hands the reviewer its concrete path to read-and-apply when
    present; otherwise the prompt inlines jig's baseline arch buckets.

    NOTE: like `build_pr_review_prompt`, this builder does NOT append
    `_principles_check_block()`. Constitution-adherence is checked in
    the compliance + reconciliation passes; the arch pass is scoped to
    architectural concerns only.
    """
    deliverable_lines = "\n".join(f"   - `{d}`" for d in deliverables)
    richer = detect_richer_skill("arch-review")
    if richer:
        routing_para = (
            f"A richer `arch-review` skill is installed at `{richer}`.\n"
            "**Read that SKILL.md in full now — and any reference files it "
            "points to — then apply ITS review rubric as your arch pass.** It "
            "supersedes the baseline buckets below. Your tools are read-only; "
            "if you cannot read that path, fall back to the baseline. Whatever "
            "rubric you apply, normalize your findings into the required output "
            "envelope at the end of this prompt.\n\n"
            "For reference, the four canonical buckets jig's bundled "
            "`arch-review` SKILL.md baseline produces are:"
        )
    else:
        routing_para = (
            "Apply the architectural concerns from jig's bundled `arch-review` "
            "SKILL.md baseline. Its four canonical output buckets are:"
        )
    return f"""{_PREAMBLE}

## Your job

You are running the **arch pass** (arch-review) on slice **{slice_label}**.
The slice declared `arch_review: true` in its frontmatter — meaning it
touches module boundaries, public contracts, or other
architecture-shaped concerns. The compliance pass
(jig:independent-review) and the craft pass (pr-review) have already
returned — that work is done, and you must NOT re-evaluate either. Your
job is to evaluate the *architecture*: does the change preserve module
boundaries, public contracts, and design coherence?

{routing_para}

1. **Summary** — what the change does architecturally and your overall
   assessment.
2. **Strengths** — specific architectural decisions or trade-offs the
   change gets right.
3. **Concerns** — risks, gaps, missing rationale, or unaddressed
   failure modes specific to this change.
4. **Open questions** — things you can't decide from the change alone;
   phrase as questions for the author.

## What to read (in this order)

1. The spec — `{spec_path}`. Read slice **{slice_label}** for context,
   but do NOT re-evaluate the acceptance criteria — that's the
   compliance pass's job.
2. The deliverables:
{deliverable_lines}
3. The project's `docs/architecture.md` if present — verify the
   change is consistent with documented module boundaries and
   contract surfaces.
4. Any related files in the repo needed to understand how the change
   composes with existing architecture (read-only).

{_PROHIBITIONS}
## Evaluate

- Does the change preserve module boundaries documented in
  `docs/architecture.md`?
- If public contracts are touched (HTTP API, event schemas, RPC,
  GraphQL, internal data shapes), are the corresponding artifacts
  updated in the same change-set?
- Are there architectural concerns the implementation doesn't
  address (failure modes, coupling, layering violations)?
- What architectural decisions does the change get right?

{_PR_REVIEW_OUTPUT_FORMAT}
"""


# -------- code-health prompt (slice 060-05) --------


def build_code_health_review_prompt(spec_path: Path, slice_label: str,
                                    deliverables: list, summary: str) -> str:
    """Construct the standard code-health-review prompt (slice 060-05).

    The on-demand code-health pass runs AFTER the compliance + craft (+
    arch) passes, but ONLY when the slice's frontmatter declares
    `code_health_review: true` (queried via
    `workflow.py code-health-review-needed`). It is gated, not always-on:
    ADR-0017 flags the per-slice review cost (specs 055/057
    context-cost discipline) and recommends gating it like arch-review.

    SPINE-RUNS-THE-TOOL / REVIEWER-JUDGES-THE-SUMMARY (AC2). The reviewer
    subagent is read-only (Read / Glob / Grep, NO Bash), so `health.py`
    is run by the orchestrator / CI and its tight summary is passed IN
    here as `summary` — never raw logs, never run by the subagent. The
    reviewer renders the judgment a *tool* cannot: is this duplication
    within the ADR-0002 inline-mirror budget? is this complexity inherent
    or fixable? are these lint findings worth blocking on?

    The pass produces the same VERDICT / REASONING / SPECIFIC ISSUES /
    RECONCILIATION NOTES envelope as the other passes, with each SPECIFIC
    ISSUES entry tagged `[blocker]` / `[nit]` / `[strength]` so the
    workflow can decide what blocks the REVIEWED transition vs. becomes a
    reconciliation-log item.

    NOTE: like `build_pr_review_prompt` / `build_arch_review_prompt`, this
    builder does NOT append `_principles_check_block()`. The code-health
    pass is scoped to the health-summary judgment only.

    Richer-skill deferral is intentionally NOT wired here (unlike
    pr-review / arch-review): there is no established "richer code-health
    reviewer" skill category to detect, so jig's rubric is inlined. (See
    the deviation log.)
    """
    deliverable_lines = "\n".join(f"   - `{d}`" for d in deliverables)
    summary_block = summary.rstrip() if summary and summary.strip() else \
        "_(no health.py summary was provided — judge on the deliverables " \
        "alone, and note the missing summary in your reasoning.)_"
    return f"""{_PREAMBLE}

## Your job

You are running the **code-health pass** on slice **{slice_label}**. The
slice declared `code_health_review: true` in its frontmatter. The
compliance pass (jig:independent-review), the craft pass (pr-review), and
(if applicable) the arch pass have already returned — that work is done,
and you must NOT re-evaluate any of it. Your job is the judgment a static
tool *cannot* make about the change's code health.

**`health.py` has already been run by the orchestrator / CI — you are
read-only (no Bash) and must NOT try to run it.** Its tight summary is
provided below; judge THAT summary (and the deliverables), never raw logs.

## health.py summary (run by the spine; judge this, do not re-run)

```
{summary_block}
```

## What to read (in this order)

1. The spec — `{spec_path}`. Read slice **{slice_label}** for context,
   but do NOT re-evaluate the acceptance criteria — that's the
   compliance pass's job.
2. The deliverables:
{deliverable_lines}
3. Any related files in the repo you need to judge whether a flagged
   pattern is acceptable (read-only).

{_PROHIBITIONS}
## Evaluate (the judgment a tool can't)

- **Duplication** — is any reported duplication within the ADR-0002
  inline-mirror budget (two callers may mirror; a third triggers an
  extract), or is it genuine copy-paste that should be a shared helper?
- **Complexity** — is a flagged complex function *inherent* to the
  problem (and well-tested), or fixable bloat worth refactoring now?
- **Lint findings** — which findings are worth blocking on vs. nits, and
  are any false positives for this change's context?
- **Net direction** — does the change leave the codebase's health better,
  neutral, or worse?

Tag every SPECIFIC ISSUES entry with one of `[blocker]` / `[nit]` /
`[strength]`: `[blocker]` entries block the REVIEWED transition;
`[nit]`/`[strength]` entries become reconciliation-log items.

{_PR_REVIEW_OUTPUT_FORMAT}
"""


def build_reconciliation_prompt(spec_path: Path, slice_label: str) -> str:
    """Construct the standard reconciliation-review prompt.

    Slice 022-02 added a conditional contract-surface check: if the
    project's `docs/architecture.md` declares contract surfaces, the
    Evaluate block grows a bullet asking the reviewer to verify the
    deviation log accounts for any artifact updates (or documents the
    opt-out). Quiet when no surfaces are declared.

    Slice 024-01 added an UNCONDITIONAL principles-check block — every
    reconciliation review gets a line asking the reviewer to verify
    the deviation log doesn't paper over principle violations.
    """
    extra_check = ""
    project_root = _find_project_root(spec_path)
    if project_root and has_declared_contract_surfaces(project_root):
        extra_check = "\n" + _contract_surface_check_block()
    # Slice 024-01: append the principles-check block UNCONDITIONALLY.
    extra_check += "\n" + _principles_check_block()
    # Engineering-practices check appended UNCONDITIONALLY — the
    # reconciliation pass verifies the deviation log didn't paper over
    # task / approach / ADR / tech-debt gaps.
    extra_check += "\n" + _practices_check_block()
    return f"""{_PREAMBLE}

## Your job

You are doing a RECONCILIATION REVIEW for slice **{slice_label}**. The
implementation was already reviewed (verdict was pass-or-acceptable; any
issues were either fixed or deferred). The implementer then wrote a
deviation log capturing what changed during implementation and why.

**Your job is to verify the deviation log matches reality.** You are NOT
re-reviewing against original ACs — that's done.

## What to read

1. `{spec_path}` — focus on the Slice {slice_label} section, especially the
   "Deviation log (after reconciliation)" subsection.
2. Any implementation files the deviation log claims to describe — read them
   as needed to verify claims.

{_PROHIBITIONS}
## Evaluate

For each deviation-log claim:
- Does the code/doc match what's described?
- Is anything important silently changed but not logged?
- Is anything overstated or invented post-hoc?
- Is the scope appropriate (no scope creep in doc updates)?{extra_check}

{_OUTPUT_FORMAT}
"""


# -------- Subagent-type selection (slice 011-02) --------


def detect_subagent_type() -> str:
    """Return `reviewer` when jig is installed as a plugin (the real
    filesystem-based agent is reachable), `general-purpose` otherwise.

    Primary signal: `${CLAUDE_PLUGIN_ROOT}` env var, populated by Claude
    Code when running plugin scripts. If set, we verify it contains
    `agents/reviewer.md` to distinguish "this is jig's plugin root" from
    "this is some other plugin's root that happens to set the var."

    Graceful fallback: any failure to read the env var, resolve the path,
    or stat the agent file returns `general-purpose` with no traceback.
    Users running jig from source without installing it MUST NOT be
    blocked. (See spec 011-02 AC #3.)
    """
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not plugin_root:
        return "general-purpose"
    try:
        if (Path(plugin_root) / "agents" / "reviewer.md").is_file():
            return "reviewer"
    except (OSError, ValueError):
        # Path-construction or stat failure — defensively fall back.
        pass
    return "general-purpose"


# -------- Review-evidence CLI (slice 045-02) --------
#
# `record-review` writes a durable verdict file; `check-reviews` validates
# the evidence set for a slice. The schema, path resolution, vocabularies,
# and the gate predicate all live in `_common/review_evidence.py` (ADR-0014
# §7) so `workflow.py transition` (slice 045-03) shares the same validator
# rather than reimplementing it.
#
# Stale-but-passing detection (a `pass` artifact predating a later
# deliverable change) is DEFERRED per ADR-0014 Scope / docs/refinement-todo.md
# — neither subcommand compares deliverable mtime against `reviewed_at`. The
# superseded-only case (a `fail`/`needs-changes` not yet overwritten) IS
# caught: it reduces to `verdict != pass`, which `check-reviews` already
# reports via the shared validator.


def _now_iso8601() -> str:
    """UTC timestamp in ISO-8601 with a trailing `Z` (provenance field).
    `reviewed_at` records when the verdict was written, per ADR-0014 §2."""
    import datetime
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def _read_summary(args) -> str:
    """Resolve the freeform verdict body from --summary-file or stdin.

    A verdict file's body mirrors the existing VERDICT/REASONING/SPECIFIC
    ISSUES/RECONCILIATION NOTES envelope (ADR-0014 §2). The recorder does
    not impose that shape — it stores whatever the reviewer flow produced
    — so the body is accepted verbatim from a file or stdin.
    """
    if args.summary_file:
        p = Path(args.summary_file)
        if not p.is_file():
            raise ReviewError(f"summary file not found: {p}")
        return p.read_text(encoding="utf-8")
    # Fall back to stdin. An empty body is allowed (the frontmatter carries
    # the machine-checkable verdict); the body is human context.
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def record_review(args) -> int:
    """Write a verdict file for a (slice, pass). Overwrites in place on
    re-record (ADR-0014 §4 — git history is the audit trail, no append)."""
    spec = Path(args.spec)
    if not spec.is_file():
        sys.stderr.write(f"spec not found: {spec}\n")
        return 2

    if args.pass_name not in _evidence.PASSES:
        sys.stderr.write(
            f"unknown pass '{args.pass_name}'; expected one of "
            f"{', '.join(_evidence.PASSES)}\n"
        )
        return 2
    if args.verdict not in _evidence.VERDICTS:
        sys.stderr.write(
            f"unknown verdict '{args.verdict}'; expected one of "
            f"{', '.join(_evidence.VERDICTS)}\n"
        )
        return 2

    try:
        # Resolve the canonical path + the full slice label. evidence_path
        # also re-validates the slice target and pass name.
        out_path = _evidence.evidence_path(spec, args.slice, args.pass_name)
        slice_label = find_slice_label(spec, args.slice)
        body = _read_summary(args)
    except (ReviewError, _evidence.EvidenceError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    # Frontmatter in canonical field order (ADR-0014 §2). The `slice` field
    # records the full label so the artifact is self-describing.
    frontmatter = (
        "---\n"
        f"slice: {slice_label}\n"
        f"pass: {args.pass_name}\n"
        f"verdict: {args.verdict}\n"
        f"reviewer: {args.reviewer}\n"
        f"reviewed_at: {_now_iso8601()}\n"
        f"prompt_source: {args.prompt_source}\n"
        "---\n"
    )
    content = frontmatter + "\n" + body
    if not content.endswith("\n"):
        content += "\n"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(out_path, content)
    sys.stdout.write(f"recorded {args.pass_name} verdict → {out_path}\n")
    return 0


def check_reviews(args) -> int:
    """Validate the evidence set for a slice at a transition stage. Exits 2
    with actionable diagnostics when the set does not clear (AC2); exits 0
    when clean."""
    spec = Path(args.spec)
    if not spec.is_file():
        sys.stderr.write(f"spec not found: {spec}\n")
        return 2

    diagnostics = _evidence.validate_evidence(spec, args.slice, args.stage)
    if diagnostics:
        sys.stderr.write(
            f"review evidence does not clear {args.stage} for slice "
            f"'{args.slice}':\n"
        )
        for d in diagnostics:
            sys.stderr.write(f"  - {d}\n")
        return 2
    sys.stdout.write(
        f"review evidence clears {args.stage} for slice '{args.slice}'\n"
    )
    return 0


# -------- CLI plumbing --------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="review.py",
                                description="jig independent-review prompt builder")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("implementation",
                        help="construct an implementation-review prompt")
    pi.add_argument("spec", help="path to spec.md")
    pi.add_argument("slice", help="slice name or fragment (case-insensitive substring)")
    pi.add_argument("deliverables", nargs="+", help="one or more deliverable paths")

    pr = sub.add_parser("reconciliation",
                        help="construct a reconciliation-review prompt")
    pr.add_argument("spec", help="path to spec.md")
    pr.add_argument("slice", help="slice name or fragment (case-insensitive substring)")

    # Slice 031-01: craft (pr-review) pass — mirrors `implementation`
    # signature; differs in prompt content + output buckets.
    pp = sub.add_parser(
        "pr-review",
        help="construct a craft-pass (pr-review) prompt",
    )
    pp.add_argument("spec", help="path to spec.md")
    pp.add_argument("slice", help="slice name or fragment (case-insensitive substring)")
    pp.add_argument("deliverables", nargs="+", help="one or more deliverable paths")

    # Slice 031-02: arch (arch-review) pass — on-demand, mirrors `pr-review`.
    pa = sub.add_parser(
        "arch-review",
        help="construct an arch-pass (arch-review) prompt",
    )
    pa.add_argument("spec", help="path to spec.md")
    pa.add_argument("slice", help="slice name or fragment (case-insensitive substring)")
    pa.add_argument("deliverables", nargs="+", help="one or more deliverable paths")

    # Slice 060-05: code-health pass — on-demand (gated by
    # `code_health_review: true`), mirrors `arch-review` plus a summary.
    # `health.py` is run by the spine; its tight summary is fed IN via
    # --summary-file (or stdin) — the read-only reviewer never runs it.
    pch = sub.add_parser(
        "code-health",
        help="construct a code-health-pass prompt",
    )
    pch.add_argument("spec", help="path to spec.md")
    pch.add_argument("slice", help="slice name or fragment (case-insensitive substring)")
    pch.add_argument("deliverables", nargs="+", help="one or more deliverable paths")
    pch.add_argument(
        "--summary-file", dest="summary_file", default=None,
        help="path to the health.py summary text (default: read stdin)",
    )

    # Slice 045-02: record a durable verdict file for a (slice, pass).
    prec = sub.add_parser(
        "record-review",
        help="record a review verdict as durable slice evidence",
        description=(
            "Write a verdict file at "
            "docs/specs/NNN-slug/reviews/slice-NN-<pass>.md (ADR-0014 §1). "
            "Re-recording the same (slice, pass) overwrites in place — git "
            "history is the audit trail (ADR-0014 §4). The freeform summary "
            "body is read from --summary-file or stdin."
        ),
    )
    prec.add_argument("spec", help="path to spec.md")
    prec.add_argument("slice",
                      help="slice name or fragment (case-insensitive substring)")
    prec.add_argument(
        "--pass", dest="pass_name", required=True,
        choices=list(_evidence.PASSES),
        help="review pass type",
    )
    prec.add_argument(
        "--verdict", required=True, choices=list(_evidence.VERDICTS),
        help="declared verdict",
    )
    prec.add_argument(
        "--reviewer", required=True,
        help="reviewer source (e.g. jig:reviewer / general-purpose / "
             "pr-review / arch-review) — provenance, freeform",
    )
    prec.add_argument(
        "--prompt-source", required=True, dest="prompt_source",
        help="the command that built the reviewer prompt (reproducibility)",
    )
    prec.add_argument(
        "--summary-file", dest="summary_file", default=None,
        help="path to the freeform verdict body (default: read stdin)",
    )

    # Slice 045-02: validate the evidence set for a slice at a stage.
    pchk = sub.add_parser(
        "check-reviews",
        help="validate the review-evidence set for a slice; exit 2 on gaps",
        description=(
            "Validate the verdict files required to enter a transition "
            "stage (ADR-0014 §5). Exits 0 when the set clears, or 2 with "
            "actionable diagnostics for missing files, malformed "
            "frontmatter, unknown pass/verdict values, non-clearing "
            "(superseded-only) verdicts, and invalid slice targets."
        ),
    )
    pchk.add_argument("spec", help="path to spec.md")
    pchk.add_argument("slice",
                      help="slice name or fragment (case-insensitive substring)")
    pchk.add_argument(
        "--stage", default="REVIEWED", choices=["REVIEWED", "RECONCILED"],
        help="transition stage whose required passes to validate "
             "(default: REVIEWED)",
    )

    pt = sub.add_parser(
        "subagent-type",
        help="print the subagent_type name SKILL.md should pass to Task",
    )
    pt.add_argument(
        "mode",
        choices=["implementation", "reconciliation", "pr-review",
                 "arch-review", "code-health"],
        help=(
            "review mode (currently informational — every mode returns the "
            "same name; the choice exists for forward compatibility)"
        ),
    )

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    # The `subagent-type` subcommand doesn't need a spec — handle it before
    # the spec-reading block below.
    if ns.command == "subagent-type":
        sys.stdout.write(detect_subagent_type() + "\n")
        return 0

    # Slice 045-02 evidence subcommands own their spec-not-found check and
    # their own exit codes (mirrors the prompt-builders' `return 2` on user
    # error / `return 1` on unexpected).
    if ns.command == "record-review":
        try:
            return record_review(ns)
        except ReviewError as exc:
            sys.stderr.write(f"{exc}\n")
            return 2
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"review.py failed: {exc}\n")
            return 1
    if ns.command == "check-reviews":
        try:
            return check_reviews(ns)
        except ReviewError as exc:
            sys.stderr.write(f"{exc}\n")
            return 2
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"review.py failed: {exc}\n")
            return 1

    spec = Path(ns.spec)
    if not spec.is_file():
        sys.stderr.write(f"spec not found: {spec}\n")
        return 2

    try:
        slice_label = find_slice_label(spec, ns.slice)
        if ns.command == "implementation":
            prompt = build_implementation_prompt(spec, slice_label, ns.deliverables)
        elif ns.command == "pr-review":
            prompt = build_pr_review_prompt(spec, slice_label, ns.deliverables)
        elif ns.command == "arch-review":
            prompt = build_arch_review_prompt(spec, slice_label, ns.deliverables)
        elif ns.command == "code-health":
            summary = _read_summary(ns)
            prompt = build_code_health_review_prompt(
                spec, slice_label, ns.deliverables, summary)
        else:
            prompt = build_reconciliation_prompt(spec, slice_label)
        sys.stdout.write(prompt)
    except ReviewError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"review.py failed: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
