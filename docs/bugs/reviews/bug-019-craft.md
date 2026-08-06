---
bug: 019
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (independent, read-only)
reviewed_at: 2026-07-30T19:06:00Z
prompt_source: pr-review skill craft pass
---

VERDICT: pass

REASONING:
The fix does what the bug record claims: `load_slice`'s already-resolved
location is returned intact by `find_slice_target`, rendered once by
`_slice_source`, and threaded into all seven spec+slice builders from `main()`.
The seam is the right shape for a `structural_fix` — one renderer, an optional
trailing parameter that defaults to the old behaviour, and a `find_slice_label`
wrapper that keeps `record_review` and the three-arg test callers working. The
four new file-per-slice tests are non-vacuous (pre-fix the slice path never
appears in the prompt at all), bound to the `## What to read` section so they
test the routing instruction rather than an incidental mention, and the
embedded-layout guard covers overcorrection. Findings are nits only; nothing
blocks.

SPECIFIC ISSUES:
- [strength] review.py `_slice_source` — renders the layout difference in
  exactly one place. This is the seam that makes the eighth builder correct by
  default; seven hand-edited f-strings would have re-created the bug.
- [strength] review.py — backward compatibility is real, not asserted: all
  in-repo direct callers pass <=3 positionals, and for `code-health` the new
  parameter lands after `summary`, so no positional collision.
- [strength] test_review.py `extract_what_to_read` + the ordering test — bounds
  assertions to the reading list and pins "slice file before overview" rather
  than mere presence. That is the difference between testing the fix and
  testing that a string exists somewhere.
- [nit] review.py — the same three-line "Bug 019" note repeated verbatim in
  five docstrings, duplicating `_slice_source`'s own. FIXED: collapsed to a
  pointer; only the frame-critique and reconciliation variants keep prose the
  renderer's docstring doesn't carry.
- [nit] review.py reconciliation — discarding the noun left "the Slice X
  section" able to bind to the nearer `spec.md`. This is the one prompt the bug
  was reported against. FIXED: now `The slice — <path>. Focus on the Slice X
  section there, especially its ...`.
- [nit] test_review.py — the overcorrection guard built a directory with no
  `slice-*.md`, so `assertNotIn("slice-", block)` was satisfied by
  construction; the plausible overcorrection is the MIXED layout. FIXED:
  `test_mixed_layout_reads_spec_md_not_the_other_slices_file` added, covering
  all seven modes against a dir where a sibling slice file holds a different
  slice.
- [nit] review.py — `-> tuple` where the file already uses `Path | None`.
  FIXED: `tuple[str, Path]` / `tuple[str, str]`.
- [nit] review.py — "The slice's plan and tasks if present (alongside
  `spec.md`)" was the last hardcoded `spec.md` in a `## What to read` list.
  FIXED: "(in the same spec directory)".

RECONCILIATION NOTES:
- Documentation scope: the SKILL.md note was added only under the
  *Reconciliation review* section while all seven recipes pass `spec.md`.
  ADDRESSED: hoisted above the recipes as a blockquote covering all modes.
- Host mirrors under `hosts/claude/` and `hosts/codex/` were regenerated with
  the fix; `test_review.py` is not mirrored (host packages ship no tests).
  Intentional — recorded in the bug record's Fix section.
- The learnings entry was written during implementation rather than at
  memory-sync time. Recorded; the bug record's own `## Learning` now carries
  the same content and links to it.
