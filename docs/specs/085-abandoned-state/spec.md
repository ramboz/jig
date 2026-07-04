---
status: IN_PROGRESS
skill: spec-workflow
dependencies: []
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 085: Abandoned state

## Overview

jig's spec lifecycle (`DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION →
IN_PROGRESS → REVIEWED → RECONCILED → DONE`, plus the parked sidetrack
`DEFERRED`) has no way to mark a slice or spec as **permanently dropped**.
`DEFERRED` specifically means "parked, with a stated resolution trigger that
will resurface it" (`SKILL.md` "DEFERRED state" section) — it is not a fit
for work that was scoped, sometimes even fully specced, and then deliberately
decided against with no intention of ever resuming.

This gap was flagged twice before without being resolved:

- [docs/refinement-todo.md](../../refinement-todo.md) carries a deferred
  decision for `workflow.py unreserve <NNN>` "for abandoned reservations" —
  but that's scoped narrowly to deleting a stub that was *never drafted*
  (empty `DRAFT`, zero slices), not to marking a slice/spec that *was*
  specced or partially built as abandoned.
- [spec 036](../036-closed-spec-drift/spec.md) Q3 explicitly asked "what
  about ... specs whose entire scope was abandoned?" and answered only the
  adjacent case ("In scope for SUPERSEDED, out for DEFERRED"), leaving the
  abandoned case unresolved.

Filed as [GitHub issue #72](https://github.com/ramboz/jig/issues/72) while
triaging [issue #71](https://github.com/ramboz/jig/issues/71).

This spec adds `ABANDONED` as a second terminal-adjacent lifecycle state,
built by mirroring how `DEFERRED` itself was introduced in
[slice 015-02](../015-structured-lifecycle-metadata/spec.md#slice-015-02--deferred-as-lifecycle-state):
same transition-restriction mechanism, same rollup-exclusion mechanism, same
status-board section pattern — swapping "resumable, with a trigger" for
"permanent, with a reason." It is a mirror of the *mechanism*, not a claim
that `ABANDONED` covers everything `DEFERRED` could reach — see Non-goals
for the one place the two deliberately diverge (`DONE` reachability).

**Not to be confused with:** a `kind: spike` slice's `Outcome:` field, which
already uses the free-text value `abandoned (reason)` (`SKILL.md` "Spike
slices" section) to record that an *investigation concluded* the approach
shouldn't be pursued — that spike slice still transitions to `STATUS: DONE`
(the investigation itself completed). This spec's `ABANDONED` is a
`status:` value for a slice/spec whose *build* work itself won't be
completed. The two don't collide: a spike's Outcome prose and a slice's
lifecycle `status:` are different fields with different life cycles.

## Non-goals

- Automating the decision of *when* something counts as abandoned — that's
  always a human call, same as `DEFERRED`.
- Retroactively reclassifying any of jig's own currently-`DEFERRED` slices
  as `ABANDONED`. None of them are actually abandoned today (all carry live
  resolution triggers); this spec only adds the mechanism.
- Touching `docs/conventions.md`. It documents the `DEFERRED` rule
  (lines 71-73) and a symmetrical `ABANDONED` rule belongs there, but
  `CLAUDE.md` requires explicit human approval before editing that file —
  out of scope for this spec, tracked as a follow-up (see reconciliation
  sweep).
- **Automatically re-linking, transitioning, or unblocking dependents**
  when a slice is marked `ABANDONED`. Same reasoning `SKILL.md`'s
  "Abandoned-spike manual-reshape failure mode" already gives for spikes:
  automation over-fires here ("approach A abandoned" often means "approach
  B from the same findings still satisfies the dependents") — a human
  decides what a live dependent should do next. This spec does NOT stay
  fully silent, though (see AC8): the spike precedent this reasoning
  leans on is a weaker analogy than it first looks, because a spike's
  `Outcome: abandoned` still lets that slice reach `DONE` (a completed
  investigation with a discouraging note), so a dependent can still
  satisfy `_validate_dependencies`'s exact-`"DONE"` check regardless.
  `ABANDONED`, by contrast, is a hard, permanent dead end for that same
  check — a live dependent would otherwise fail its own `→ DONE`
  transition silently, possibly long after the abandonment decision and
  by an author with no context on why. A one-time, non-blocking,
  non-cascading warning at the moment of abandonment (naming any existing
  live dependents) closes that gap without crossing into automation.
- **Marking already-shipped (`DONE`) work as abandoned/removed.** Frame-critique
  review of this spec (see Assumptions) surfaced that "specced but never
  attempted" and "built, shipped, then deliberately ripped out" are different
  events with different audit value — the latter implies working code existed
  and was later judged not worth keeping, which is closer to spec 036's
  SUPERSEDED/drift territory than to a `DRAFT`-adjacent park. Overloading one
  `ABANDONED` bucket (and one `**Abandonment reason:**` line) for both would
  erase that distinction exactly where an auditor most needs it. `DONE →
  ABANDONED` is therefore refused by this spec — `ABANDONED` covers only work
  that never reached `DONE`. **Resolution trigger:** a real, observed need to
  mark shipped-then-removed work as such on the status board — at which point
  design a distinct concept (e.g. `DEPRECATED`) for it rather than widening
  `ABANDONED`'s semantics after the fact.

## Slices

- [085-01 — abandoned-as-lifecycle-state](slice-01-abandoned-as-lifecycle-state.md)

## Assumptions

Every referenced call site (`VALID_STATUSES`, `_DEFERRED_ALLOWED_NEXT`, the
FROM-state check in `transition`, `compute_spec_status`, `collect_slices`,
`render_deferred_table`, `session_plan`'s DEFERRED skip,
`_validate_dependencies`, `_branch_freshness_warning`,
`slice-land/land.py`'s status check) was confirmed by direct read of source
before drafting — that part is grounded, not an assumption.

This spec went through five rounds of frame-critique (adversarial
pre-implementation review; `docs/specs/085-abandoned-state/reviews/`). Four
judgment calls were genuinely unresolved when first drafted; all four are
now settled, not contested — recorded here for provenance rather than as
live risks:

1. **`ABANDONED` reachable from `DONE`?** Round 1 found no argument for why
   collapsing "never attempted" and "shipped, then deliberately removed"
   into one bucket was *correct* rather than merely *convenient* — the two
   are different events with different audit value. **Settled:** `DONE →
   ABANDONED` is refused; see Non-goals.
2. **Silent "no cascade to dependents"?** Round 2 found the Non-goal's
   spike-precedent analogy inexact — a spike's `Outcome: abandoned` still
   reaches `DONE` and never trips `_validate_dependencies`'s exact
   `"DONE"` check, but `ABANDONED` permanently does, so a live dependent
   would otherwise fail its own `→ DONE` transition later with no context
   on why. **Settled:** AC8 adds a one-time, non-blocking, non-cascading
   stderr warning naming live dependents at the moment of abandonment.
3. **Widening `compute_spec_status`'s return type from 3 values to 4?**
   Round 3 required verification against every actual consumer rather than
   an appeal to the `DEFERRED` precedent (which only ever *excluded*
   slices from the rollup, never added a return value). **Settled, by
   audit:** `_write_spec_rollup` (`workflow.py:1377`, the function's only
   caller) treats the returned string opaquely — writes it, compares it
   for idempotence, never branches on it. Its own two call sites
   (`transition`, `regenerate_status_board`) don't branch on it either. No
   other module reads a spec's own frontmatter `status:` expecting a
   closed 3-way set: `slice-land/land.py`'s DoD/landing check reads a
   *slice's* status (`land.py:121`), never a spec-level rollup;
   `bug-fix/bug.py` and `adr-workflow/adr.py` have their own, unrelated
   status namespaces; and no status-board rendering path displays the
   spec-level rollup at all today (the original #72 triage finding —
   separate, unaffected by this change).
4. **Mixed `DEFERRED` + `ABANDONED` (no `DONE`/live work) → `DRAFT`?**
   Round 4 found this had shipped into AC4/AC7 as an
   acknowledged-but-unresolved risk rather than an actual decision.
   **Settled, by consistency with existing behavior:** a spec where every
   slice is `DEFERRED` already rolls up to `DRAFT` today (unchanged by
   this spec) on the reasoning "no live work, needs a human to pick it
   back up." A `DEFERRED`+`ABANDONED` mix needs exactly the same human
   action (reopen the resumable part, or close it out entirely), so it
   gets the same signal — and no detail is lost, since individual slice
   rows stay fully visible in their own board sections regardless of the
   coarse rollup. **Resolution trigger:** a real, observed case of a human
   misreading this rollup as "never started" and wasting time
   re-investigating already-decided scope — at which point reconsider a
   more prominent signal for this specific mix.

Round 5 independently re-verified all four resolutions against source and
found no further load-bearing gap (recorded verdict:
`docs/specs/085-abandoned-state/reviews/slice-01-frame-critique.md`).
