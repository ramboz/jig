---
status: DONE
tier: standard
severity: high
claimed_by: claude/agitated-mayer-b120c5
regression_test: skills/spec-workflow/test_workflow.py::Bug042FrameGateSkipTests
main_repro_checked_at: 2026-11-20
main_repro_ref: origin/main@87610a93
main_repro_result: reproduces
red_confirmed_at: 2026-11-20
green_confirmed_at: 2026-11-20
fix_class: structural_fix
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 042: frame-critique-gate-skipped-past-ready-for-review

Reported: GitHub issue 251 (against v2.17.1, observed in a downstream project
2026-11-11). Re-confirmed on `origin/main@87610a93`.

## Symptom

A slice with `frame_review: true` and a recorded frame-critique verdict of
`needs-changes` is correctly refused at `READY_FOR_REVIEW`. The next command,
`workflow.py transition … READY_FOR_IMPLEMENTATION`, succeeds straight from
`DRAFT`, and `IN_PROGRESS` follows. The only pre-implementation evidence gate
is skipped with no `JIG_REVIEW_EVIDENCE_GATE=0` and no warning.

## Repro

Scratch project: `docs/specs/008-demo/` with a `status: DRAFT`,
`frame_review: true` slice `008-01` and
`reviews/slice-01-frame-critique.md` carrying `verdict: needs-changes`.
`JIG_REVIEW_EVIDENCE_GATE` unset.

```
$ workflow.py transition docs/specs/008-demo/spec.md 008-01 READY_FOR_REVIEW
cannot transition to READY_FOR_REVIEW — review evidence is incomplete (ADR-0014 §5):
  - [frame-critique] slice-01-frame-critique.md: verdict is 'needs-changes', not 'pass' …
exit=2
$ workflow.py transition docs/specs/008-demo/spec.md 008-01 READY_FOR_IMPLEMENTATION
transitioned 008-01 — thing: DRAFT → READY_FOR_IMPLEMENTATION
exit=0
$ workflow.py transition docs/specs/008-demo/spec.md 008-01 IN_PROGRESS
transitioned 008-01 — thing: READY_FOR_IMPLEMENTATION → IN_PROGRESS
exit=0
```

## Evidence

- `skills/spec-workflow/workflow.py` (pre-fix L891) —
  `_EVIDENCE_GATED_STATES = ("READY_FOR_REVIEW", "REVIEWED", "RECONCILED",
  "DONE")`; `_gate_evidence` returns immediately for any other target.
- Same function (pre-fix L937) — the frame-critique set is validated only
  under `if new_status == "READY_FOR_REVIEW":`. `_gate_evidence` received the
  target status only; it had no view of the status the slice was leaving.
- `transition` enforces a FROM-state restriction for exactly three origins
  (`DEFERRED`, `ABANDONED`, and `DONE → ABANDONED`). Every other origin may
  move to any target, so `READY_FOR_REVIEW` is skippable by construction.
- The comment block above `_EVIDENCE_GATED_STATES` and ADR-0014 §5 / spec 045
  AC4 list `READY_FOR_IMPLEMENTATION` and `IN_PROGRESS` as ungated. That was
  correct when written (2026-06-02, ddb8f35f): no pre-implementation gate
  existed. Slice 064-03 (2026-06-08, bcc4cc2b) added the frame-critique gate
  on the `READY_FOR_REVIEW` target without revisiting the two targets that
  lie past it.
- No test exercised a flagged slice skipping `READY_FOR_REVIEW`
  (`TransitionReadyForReviewFrameGateTests` only targets `READY_FOR_REVIEW`
  and `DONE`).

## Hypotheses

- [ ] H1: the skip is intended — frame-critique is advisory, and ADR-0014's
  "ungated" list is the contract. Falsify by: ADR-0020 describes the pass as
  a gate that runs before implementation, `session_plan` puts it first
  because "the adversarial pass gates DRAFT → READY_FOR_REVIEW
  (pre-implementation)", and the gate's own refusal one command earlier tells
  the author the work may not proceed. A gate that is refused and then
  walked around by naming the next state is not advisory by design —
  falsified; the owner also confirmed it as a bug.
- [ ] H2: the gate does run on these targets but reads the flag or verdict
  wrongly (e.g. a `needs-changes` verdict treated as clearing). Falsify by:
  the same slice and verdict are refused at `READY_FOR_REVIEW`, and
  `_gate_evidence` returns at its first line for the other two targets
  before any flag or verdict is read — falsified.
- [x] H3 (leading): the gate is keyed on the TARGET state while what it
  protects is an EDGE (leaving the pre-implementation zone), and `transition`
  has no ordering that would force a slice through the keyed target.
  Confirmed by the repro and by reading `_gate_evidence` + `transition`.

## Root cause

Process, not output: the frame-critique requirement was attached to the
`READY_FOR_REVIEW` *target*, on the unstated premise that every slice passes
through that state on its way to implementation. `transition` never enforced
that premise — it is a free-form status setter with three narrow FROM-state
rules — so the gate guards one door of a room with several. This is the same
target-not-edge framing bug 039 found in `bug.py`'s `FIXING` gates.

Grounding (ADR-0052): `_gate_evidence` has exactly one caller
(`transition`, `git grep '_gate_evidence('` over `skills/` + `scripts/`), and
`validate_evidence(…, "READY_FOR_REVIEW")` has exactly one gating call site
(inside `_gate_evidence`; the other caller, `review.py check-reviews`, is a
read-only pre-check). Both are plain module-level names with no reflection or
config wiring, and `hosts/` holds generated byte-copies, so the search closes
the set. Status can also be changed by hand-editing the slice file; that is
outside any in-helper gate by design (ADR-0011 / ADR-0014 — deliberateness,
not enforcement) and is not what this bug is about.

### Second hole checked: the flag is declared, never derived at the gate

Suspected: `frame_review` is derived only on the way into `READY_FOR_REVIEW`,
so a slice skipping that state never gets flagged. Found: it is worse and
different. `derive_frame_review` has one caller, the `frame-review-needed`
CLI subcommand, which only prints `true`/`false`. `transition` never calls
it for any target. The gate, `session_plan` and `review_evidence` all read
the flag the author **declared** in slice frontmatter (SKILL.md "Creating a
new spec" step 7 tells the author to copy the derived value in). So a slice
whose spec carries real `## Assumptions` but whose author never set the flag
is ungated at every state, `READY_FOR_REVIEW` included, before and after
this fix.

Not fixed here. Enforcing the derived value at `transition` would newly gate
every existing downstream spec with a non-empty `## Assumptions` and an
unset flag, and the deriver reads the *spec-level* section, so it would flag
every slice of such a spec, including ones SKILL.md says stay default-off.
That changes ADR-0020's trigger model ("derived trigger set by the
author/clarify step") and needs its own decision. Follow-up, see `## Fix`.

## Repository closure inventory

**Equivalent / convergent logic searched:** `git grep` over `skills/`,
`scripts/`, `hooks/` for `_gate_evidence`, `_EVIDENCE_GATED_STATES`,
`validate_evidence(`, `frame_review`, `frame-critique`, `_ALLOWED_NEXT`,
`_ORDERED_TRANSITIONS`, `READY_FOR_IMPLEMENTATION`; after review round 1 also `_reserve_claim_ref`,
`refs/claims`, `_refuse_start_collision`, `_reserve_claim_on_main` (what
runs in `transition` between the status read and the gate). Convergent gates:
(a) `adr.py` `_gate_frame_critique` — the ADR-side frame-critique gate; it
sits on `accept`, the single function that flips an ADR to Accepted, so it
has no second door. (b) `bug.py` — uses an ordered-transition table
(`_ORDERED_TRANSITIONS`), so its gates cannot be skipped by naming a later
state; bug 039 already moved its `FIXING` gates to the forward edge.
(c) `workflow.py` `_DEFERRED_ALLOWED_NEXT` / `_ABANDONED_ALLOWED_NEXT` — the
existing FROM-state restrictions, added "so review gates aren't silently
skipped"; same concern, narrower origins. (d) `land.py` reads review
evidence at landing but only for the `REVIEWED`/`RECONCILED` sets. No
existing helper answers "is this a forward move out of pre-implementation".

**Relevant history inspected:** `git log -S'_EVIDENCE_GATED_STATES = '` →
ddb8f35f (2026-06-02, spec 045: three post-implementation gates, the other
targets genuinely had nothing to gate). `git log -S'if new_status ==
"READY_FOR_REVIEW":'` → bcc4cc2b (2026-06-08, slice 064-03: adds the
frame-critique gate on the `READY_FOR_REVIEW` target and the comment "This
is the only PRE-implementation evidence gate"). The hole dates from
bcc4cc2b; it is original to that slice, not a regression. Bug 039
(2026-10-04) made the frame-critique verdict exempt from
`review_reopened_at` staleness, which this fix relies on.

**Affected call sites:** `workflow.py` `_gate_evidence` (the gate) and its
one call in `transition`; the claim machinery `transition` runs on
`→ IN_PROGRESS` ahead of that call (so any new refusal has to sit ahead of
it in turn — the shipped frame gate does) — `_reserve_claim_ref` (creates
`refs/claims/<N>`, pushes it under `--push`/`--pr`),
`_refuse_start_collision`, `_refuse_sibling_in_progress_claim` — and
`_reserve_claim_on_main`, which runs after it; the comment block above `_EVIDENCE_GATED_STATES`;
the two "ungated" comments in `transition` (the foreign-claim warning and
the gate call); `skills/spec-workflow/SKILL.md` (gate + lifecycle prose);
`docs/workflow.md` (state-diagram prose + bypass note);
`templates/docs/workflow.md.template` if it mirrors that prose; generated
copies under `hosts/{claude,codex,copilot}`; ADR-0014 §5 and spec 045
slice 03 (closed records that list the two targets as ungated);
`review.py check-reviews --stage READY_FOR_REVIEW` (pre-check, unchanged
contract); `session_plan` (dispatches the pass first — already correct).

**Reuse decision:** reuse. The fix calls the existing
`validate_evidence(…, "READY_FOR_REVIEW")` for the wider set of edges
instead of adding a second validator, and reads the flag through
`review_evidence._frame_review_flag`, the validator's own reader.
It does not introduce an ordered-transition table: spec-workflow
deliberately lets unflagged slices skip states, and the lifecycle-family
spine (ADR-0023) defers that kind of extraction.

## Fix class

`structural_fix` — the gate moves from the target to the edge it protects.

## Fix

The frame-critique requirement moves out of `_gate_evidence` into its own
`_gate_frame_critique`, which
`transition` calls after the read-only cross-ref refusals and **before the
claim bookkeeping**. Its bypass audit event is still emitted by
`_gate_evidence`, at the old position after the claim refusals, so a
bypassed transition logs exactly one event and a refused one logs none. A new
`_crosses_frame_gate` predicate decides whether a transition carries a
`frame_review: true` slice out of the pre-implementation zone:

- target is past `READY_FOR_REVIEW` (`READY_FOR_IMPLEMENTATION`,
  `IN_PROGRESS`, `REVIEWED`, `RECONCILED`, `DONE`), **and**
- the slice is not already in a state where implementation has started
  (`IN_PROGRESS`, `REVIEWED`, `RECONCILED`, `DONE`), **and**
- the slice declares `frame_review: true`.

When it does, the `READY_FOR_REVIEW` evidence set is validated exactly as it
is for the `READY_FOR_REVIEW` target. Consequences, each pinned by a test:

- **Unflagged slices** are untouched and may still skip states.
- **A flagged slice with a `pass`** may still skip `READY_FOR_REVIEW`; the
  fix validates evidence, it does not impose ordering.
- **Back-edges are ungated** (`REVIEWED`/`RECONCILED → IN_PROGRESS`), with
  or without a frame-critique verdict, as is an `IN_PROGRESS →
  READY_FOR_IMPLEMENTATION` release. Code already exists there, so a
  pre-implementation gate has nothing to protect, and refusing would strand
  a slice in review unable to take fixes.
- **A slice released to the queue and picked up again** starts from
  `READY_FOR_IMPLEMENTATION`, so the pickup is gated; its earlier `pass`
  still clears because frame-critique is exempt from `review_reopened_at`
  staleness (bug 039).
- **A flagged slice already parked at `READY_FOR_IMPLEMENTATION` without a
  pass** (it used the hole, or was flagged late) is now refused at pickup.
  That is the intended catch; the documented bypass covers a deliberate
  exception.
- **An unknown or missing origin status fails closed** (counts as
  pre-implementation). So does a `READY_FOR_IMPLEMENTATION` re-stamp, and
  `--release` does not skip the gate: a flagged slice sitting in
  `READY_FOR_REVIEW` without its pass is released to `DRAFT`, not forward.
- **A refused pickup leaves no claim reservation.** `→ IN_PROGRESS`
  reserves `refs/claims/<N>` (and may push it). The gate runs ahead of
  that, so a refusal cannot strand a reservation for a slice that never
  started. (Review round 1 caught the first cut refusing *after* it.)
- **One flag reader.** The predicate reads the flag through
  `review_evidence._frame_review_flag`, the reader `validate_evidence`
  itself uses, so the two cannot disagree about whether a slice is flagged.
- **Bypass**: `JIG_REVIEW_EVIDENCE_GATE=0` still skips the check and emits
  the `review-evidence` `gate_bypassed` event. An unflagged move to the two
  newly covered targets emits nothing, so ordinary pickups under an
  inherited bypass do not flood the audit log.

Wider than the issue's two named targets: a flagged slice jumping from
`DRAFT` straight to `REVIEWED`/`RECONCILED`/`DONE` crosses the same edge and
is covered by the same predicate. On the normal walk those targets start
from `IN_PROGRESS` or later, so "frame-critique is not re-validated at
DONE" still holds.

**Follow-ups (not in this fix; 0 and 1 are filed in
`docs/refinement-todo.md`):**

0. Embedded-layout slices (a `## Slice` block inside `spec.md` rather than
   a `slice-NN-*.md` file): `review_evidence._slice_field` runs
   `parse_frontmatter` on a section that starts with the heading, and the
   frontmatter regex is anchored at the start, so no review flag
   (`frame_review`, `arch_review`, …) is ever read for that layout. Flagged
   embedded slices are ungated at every evidence stage. Pre-existing and
   wider than this bug; found in review round 1. This fix follows the
   validator's reader, so it neither widens nor narrows that hole.
1. The declared-vs-derived flag hole above — needs a decision on ADR-0020's
   trigger model before any enforcement.
2. ADR-0014 §5 and spec 045 slice 03 still list `READY_FOR_IMPLEMENTATION` /
   `IN_PROGRESS` as ungated. Amending closed records needs owner approval
   (spec 102); proposed `## Amendments` text is drafted in the PR for sign-off.

## Call-site closure

<!-- Spec 091 / ADR-0037: before REVIEWED, account for every site named
     in the inventory above as changed, tested, or intentionally left
     alone. Accounting, not mandatory widening. -->

**Disposition per affected site:**

- `workflow.py` `_gate_evidence` — **changed** (frame validation moved
  out; it takes `crosses_frame_gate` and still logs that gate's bypass);
  new `_crosses_frame_gate` + `_gate_frame_critique` — tested by
  `Bug042FrameGateSkipTests` end to end through the CLI.
- `workflow.py` `transition` — **changed**: calls `_gate_frame_critique`
  ahead of the claim block, and passes `crosses_frame_gate` to the later
  `_gate_evidence` call.
- `_reserve_claim_ref`, `_refuse_start_collision`,
  `_refuse_sibling_in_progress_claim` — **left alone**, now downstream of
  the frame gate; **tested** by
  `test_refused_pickup_leaves_no_claim_reservation_ref` (git-backed).
- `_reserve_claim_on_main` — **left alone**: it publishes
  `status: IN_PROGRESS` to the trunk copy but runs after both gates, so it
  is not a way around them.
- `review_evidence.required_passes` docstring — **changed** (pointer to the
  edge-keyed caller); `_slice_field` embedded-layout gap — **left alone**,
  follow-up 0.
- Comment block above `_EVIDENCE_GATED_STATES`, and the two "ungated"
  comments in `transition` — **changed** (live code comments corrected).
- `skills/spec-workflow/SKILL.md`, `docs/workflow.md` — **changed** (live
  prose corrected inline, ADR-0010).
- `templates/docs/workflow.md.template` — **left alone**: checked, it does
  not carry the frame-critique gate prose.
- `hosts/{claude,codex,copilot}` copies — **changed** by regeneration
  (`scripts/build_host_packages.py`), drift-checked.
- ADR-0014 §5, spec 045 slice 03 — **left alone** pending owner approval of
  the proposed amendment (spec 102).
- `adr.py` `_gate_frame_critique`, `bug.py` ordered transitions, `land.py`
  — **left alone**: single-door or ordered by construction, not exposed.
- `review.py check-reviews`, `session_plan`, `validate_evidence` —
  **left alone**: contracts unchanged; the fix reuses
  `validate_evidence(…, "READY_FOR_REVIEW")` as is.
- `derive_frame_review` / `frame-review-needed` — **left alone**: follow-up 1.

## Already tried

Nothing failed. A narrower fix (gate only the `READY_FOR_IMPLEMENTATION` and
`IN_PROGRESS` targets, regardless of origin) was considered and rejected: it
would refuse the `REVIEWED`/`RECONCILED → IN_PROGRESS` back-edges and the
idempotent `IN_PROGRESS` re-stamp for a flagged slice with no verdict,
stranding slices mid-lifecycle, and it would still leave `DRAFT → REVIEWED`
open.

## Regression test

`skills/spec-workflow/test_workflow.py::Bug042FrameGateSkipTests` (21 tests):
the reported walk with a `needs-changes` verdict; `DRAFT →
READY_FOR_IMPLEMENTATION`, `DRAFT → IN_PROGRESS`,
`READY_FOR_IMPLEMENTATION → IN_PROGRESS` and `DRAFT → REVIEWED` refused
without a pass; the forward walk and the skip with a pass; unflagged slices
free; back-edges, release, idempotent re-stamp and relaxing moves ungated;
the pass surviving a review back-edge; the bypass and its audit event.
Added after review round 1: a refused pickup leaves no `refs/claims` ref
(git-backed fixture); an unrecognised or missing origin status fails closed;
a late-flagged slice released to the queue is refused at re-pickup; the
`READY_FOR_IMPLEMENTATION` re-stamp is gated. After round 2: `--release`
does not skip the gate; a bypassed move logs exactly one audit event.

## Proof

Red, witnessed by the `→ FIXING` gate against the `origin/main` copy of
`workflow.py` (first cut of the class, 15 tests): 6 fail — the five
refusals and the bypass audit event; the other nine are guards that pass
either way. Green is witnessed by the `→ REVIEWED` gate (`green_confirmed_at`)
on the final 21-test class; `TransitionReadyForReviewFrameGateTests` and
`TransitionGateBypassTelemetryTests` are unchanged and pass.

## Learning

Recorded in `docs/memory/learnings.md` under "Bug 042".

## Main recheck

- 2026-11-20 - `origin/main@87610a93` -> reproduces: workflow.py transition <spec> 008-01 READY_FOR_IMPLEMENTATION on a frame_review:true slice with a needs-changes frame-critique verdict: exit 0 (DRAFT -> READY_FOR_IMPLEMENTATION), then IN_PROGRESS exit 0; READY_FOR_REVIEW correctly exit 2
