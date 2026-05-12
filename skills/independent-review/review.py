"""
jig independent-review helper — slice 004-01 (review-helper)

Builds the standardized reviewer-subagent prompt for either an implementation
review or a reconciliation review. The helper does NOT spawn the subagent
itself — Claude owns the Task invocation. This script just makes the prompt
consistent across 100+ invocations.

Usage:
    python3 review.py implementation <spec.md> <slice-fragment> <deliverable-path>...
    python3 review.py reconciliation <spec.md> <slice-fragment>
"""

import argparse
import re
import sys
from pathlib import Path


class ReviewError(RuntimeError):
    """User-facing error; CLI exits 2."""


def find_slice_label(spec_text: str, slice_fragment: str) -> str:
    """Locate the `## Slice ...` H2 containing `slice_fragment`. Returns the
    full slice label (e.g. `001-01 — greenfield-scaffold`). Raises on miss
    or ambiguity. Mirrors workflow.py's `find_slice_section` semantics."""
    headers = list(re.finditer(r"(?im)^##\s+Slice\s+([^\n]+)$", spec_text))
    if not headers:
        raise ReviewError("no '## Slice ...' headings found in spec")
    needle = slice_fragment.lower()
    matches = [h for h in headers if needle in h.group(0).lower()]
    if not matches:
        raise ReviewError(f"slice not found: '{slice_fragment}'")
    if len(matches) > 1:
        names = [h.group(1).strip() for h in matches]
        raise ReviewError(
            f"ambiguous slice fragment '{slice_fragment}' matches: {names}"
        )
    return matches[0].group(1).strip()


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


def build_implementation_prompt(spec_path: Path, slice_label: str,
                                deliverables: list) -> str:
    """Construct the standard implementation-review prompt."""
    deliverable_lines = "\n".join(f"   - `{d}`" for d in deliverables)
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
- Any security or robustness concerns relevant to this change?

{_OUTPUT_FORMAT}
"""


def build_reconciliation_prompt(spec_path: Path, slice_label: str) -> str:
    """Construct the standard reconciliation-review prompt."""
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
- Is the scope appropriate (no scope creep in doc updates)?

{_OUTPUT_FORMAT}
"""


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

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    spec = Path(ns.spec)
    if not spec.is_file():
        sys.stderr.write(f"spec not found: {spec}\n")
        return 2

    try:
        spec_text = spec.read_text()
        slice_label = find_slice_label(spec_text, ns.slice)
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
