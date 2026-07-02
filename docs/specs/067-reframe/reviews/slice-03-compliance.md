---
slice: 067-03 — The noticing nudge (standing practice)
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T17:28:01Z
prompt_source: review.py compliance docs/specs/067-reframe/spec.md 067-03 <deliverables>
---

VERDICT: pass

REASONING:
All four ACs met and meaningfully tested. AC1: the "## Bringing in a new load-bearing
reference" subsection in jig's docs/workflow.md names all reference categories + points at
/jig:reframe. AC2: _render_reframe_practice_block / _ensure_reframe_practice_block, called by
copy_machinery AND scaffold's plugin-only branch (every scaffold path reaches the block), via
the sanctioned 065-04 managed-block injection (not a static template edit). AC3: one-line
/jig:reframe + "load-bearing reference" cross-refs in spec-workflow + adr-workflow SKILL.md.
AC4: no hook (hooks.json has zero reframe matches); text labelled "not a gate, not a detector".
The ADR-0002 rule-of-three extraction is genuine — _upsert_marked_block is a single shared core
with all three callers delegating; no duplicated inline logic remains. Host packages regenerated
(drift guard passes). No principle violations.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- Note in the deviation log that AC2's "scaffolded template" is satisfied via the
  copy_machinery/scaffold managed-block injection (mirroring _ensure_self_defining_convention_block),
  not a literal templates/docs/workflow.md.template edit — the 065-04 forward-only pattern.
- Fill the still-TODO deviation log + reconciliation sweep (RECONCILED gate requires both).
- Closing-slice close-out (compress Active-specs; confirm /jig:reframe discoverable) applies now
  that 067-01/02/03 are all DONE-bound.
- Minor: the test comment "written by BOTH scaffold() and copy_machinery()" is slightly loose
  (direct scaffold() call is the --plugin-only branch; --with-machinery reaches via copy_machinery).
  Behavior correct on every path.
