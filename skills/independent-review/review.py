"""
jig independent-review helper — slices 004-01 (review-helper) + 011-02
(subagent-type-fallback-upgrade)

Builds the standardized reviewer-subagent prompt for either an implementation
review or a reconciliation review. The helper does NOT spawn the subagent
itself — Claude owns the Task invocation. This script just makes the prompt
consistent across 100+ invocations.

Slice 011-02 added the `subagent-type` subcommand: it inspects
`${CLAUDE_PLUGIN_ROOT}` and prints either `reviewer` (jig installed as a
plugin — real subagent reachable) or `general-purpose` (fallback). SKILL.md's
bash recipe uses it to pick the Task tool's `subagent_type` argument
deterministically.

Usage:
    python3 review.py implementation <spec.md> <slice-fragment> <deliverable-path>...
    python3 review.py reconciliation <spec.md> <slice-fragment>
    python3 review.py subagent-type {implementation|reconciliation}
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.parsing import load_slice as _load_slice_common
from _common.parsing import SliceLookupError


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
    extra_check = ""
    project_root = _find_project_root(spec_path)
    if project_root and has_declared_contract_surfaces(project_root):
        extra_check = "\n" + _contract_surface_check_block()
    # Slice 024-01: append the principles-check block UNCONDITIONALLY.
    # No gating on project state — principle adherence is universal.
    extra_check += "\n" + _principles_check_block()
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
- Any security or robustness concerns relevant to this change?{extra_check}

{_OUTPUT_FORMAT}
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

    pt = sub.add_parser(
        "subagent-type",
        help="print the subagent_type name SKILL.md should pass to Task",
    )
    pt.add_argument(
        "mode",
        choices=["implementation", "reconciliation"],
        help=(
            "review mode (currently informational — both modes return the "
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

    spec = Path(ns.spec)
    if not spec.is_file():
        sys.stderr.write(f"spec not found: {spec}\n")
        return 2

    try:
        slice_label = find_slice_label(spec, ns.slice)
        if ns.command == "implementation":
            prompt = build_implementation_prompt(spec, slice_label, ns.deliverables)
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
