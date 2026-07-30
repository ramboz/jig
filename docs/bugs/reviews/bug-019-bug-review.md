---
bug: 019
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent (independent, read-only)
reviewed_at: 2026-07-30T19:05:41Z
prompt_source: review.py bug-review
---

VERDICT: pass

REASONING:
The fix addresses the documented root cause at its source: `find_slice_target`
returns the `SliceLocation.path` the shared loader already resolved, a single
`_slice_source` renderer phrases the reading target once, and all seven
spec+slice builders plus `main()` thread it through — no per-builder string
patching. Blast radius is handled correctly: the ADR `frame-critique` branch
passes no `slice_path` so it keeps naming the ADR itself, `record_review` still
goes through the preserved `find_slice_label` wrapper, and both generated host
copies carry the new symbols. `FilePerSliceReviewTargetTests` is non-vacuous —
with `slice_path` reverted the slice file's path never appears in any prompt's
`## What to read` block, so all four of its tests go red; the CLI-level
subprocess harness means they exercise the real dispatch path, not the builders
in isolation.

SPECIFIC ISSUES:
- test_review.py — `EmbeddedLayoutReviewTargetTests` would still pass with the
  fix fully reverted. Not a defect (it is declared an overcorrection guard),
  but it carries no red-before/green-after evidence and must not be counted as
  regression coverage. ADDRESSED: a mixed-layout case was added, which the
  craft pass independently identified as the shape that can actually fail.
- learnings.md — the bug-019 learning was written while the record's
  `## Learning` was still empty and status was FIXING. ADDRESSED: the record's
  `## Learning` section is now filled and points at the memory entry.

RECONCILIATION NOTES:
- `_slice_source` returns a `(noun, phrase)` pair; two builders discarded the
  noun. ADDRESSED: frame-critique now indexes `[1]` explicitly with a docstring
  reason, and reconciliation now USES the noun (the craft pass showed dropping
  it created a grammatical ambiguity).
- The SKILL.md contract note was documented only under the reconciliation
  recipe though it holds for all seven modes. ADDRESSED: hoisted above the
  recipes.
- `green_confirmed_at:` and `## Proof` empty at review time is correct for this
  point in the lifecycle — green is stamped by the `-> REVIEWED` gate, and
  Proof is a `-> VERIFIED` requirement that applies to gnarly/security tiers
  only, not to this `tier: standard` record.
- Host-package parity was verified by symbol count only (read-only). Confirmed
  during reconciliation by running `build_host_packages.py --check`: in sync.
