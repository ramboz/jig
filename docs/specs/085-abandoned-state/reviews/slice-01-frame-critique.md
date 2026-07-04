---
slice: 085-01 — abandoned-as-lifecycle-state
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-04T02:52:55Z
prompt_source: review.py frame-critique docs/specs/085-abandoned-state/spec.md 085-01 (round 5 of 5)
---

VERDICT: pass

REASONING:
The spec's core mechanism claims are independently verifiable against `skills/spec-workflow/workflow.py` and check out: `VALID_STATUSES` is exactly 8 values and AC1's "every pre-DONE state" list is precisely that set minus `DONE`; `compute_spec_status` (workflow.py:1310-1358) currently returns exactly the 3 documented values with no other caller branching on the value (`_write_spec_rollup` at :1377 does opaque equality only); `_validate_dependencies` (workflow.py:711) does an exact `!= "DONE"` string check, confirming AC8's premise that `ABANDONED` — unlike a spike's `Outcome: abandoned` — permanently trips it; and `render_deferred_table` (workflow.py:1541-1572) confirms per-slice detail is already rendered independently of the spec-level rollup, which is the load-bearing fact underpinning round 4's "no information is lost" argument. Round 4's resolution is a genuine decision (consistency with an existing, unchanged precedent, plus a concrete resolution trigger) rather than relabeled uncertainty, and no fifth load-bearing crack was found after an adversarial pass focused specifically on the newest patch (the DEFERRED+ABANDONED→DRAFT rollup).

SPECIFIC ISSUES:
none blocking — the frame's most recent and most contested joint (round 4's rollup consistency argument) is grounded in the actual rendering code (status-board sections are independent of the coarse rollup value, verified at workflow.py:1552 and the `## Abandoned slices` analog this slice adds), and every other load-bearing mechanism claim (VALID_STATUSES exhaustiveness, compute_spec_status's consumer set, `_validate_dependencies`'s exact-DONE check) is confirmed by direct reads rather than asserted by analogy. The one residual soft spot — whether a human scanning a mixed DEFERRED+ABANDONED spec's `DRAFT` rollup will actually notice the distinction lives in the per-slice sections rather than the rollup itself — is explicitly acknowledged with a concrete, cheap-to-trigger resolution trigger (observed board-scanning confusion), which is the correct place to park a genuinely UX-shaped (not correctness-shaped) residual risk rather than blocking implementation on it.

---

This is the FIFTH round of frame-critique on this spec. Prior rounds (recorded
here for the audit trail, since `record-review` overwrites in place):

Round 1 (needs-changes): flagged an unjustified `DONE → ABANDONED`
reachability claim — resolved by refusing that transition, naming it an
explicit Non-goal with a resolution trigger.

Round 2 (needs-changes): flagged an inexact "no cascade to dependents"
analogy to the spike-Outcome precedent (a spike's `Outcome: abandoned` still
reaches `DONE` and never trips `_validate_dependencies`'s exact `"DONE"`
check; `ABANDONED` permanently does) — resolved by adding AC8, a one-time,
non-blocking, non-cascading stderr warning naming live dependents at the
moment of abandonment.

Round 3 (needs-changes): flagged that AC4's widening of
`compute_spec_status`'s return type from 3 documented values to 4 needed
verification against actual consumers rather than an appeal to the DEFERRED
precedent — resolved by auditing every consumer (`_write_spec_rollup`,
`land.py`, `bug.py`, `adr.py`) and finding none branch on a closed 3-value
set.

Round 4 (needs-changes): flagged that the "mixed DEFERRED+ABANDONED (no
DONE/live) → DRAFT" rollup rule was carried as an acknowledged-but-unresolved
risk baked into a hard AC/test rather than an actual settled decision —
resolved by explicitly settling it (consistency with the existing, unchanged
all-DEFERRED → DRAFT precedent), with a stated resolution trigger, without
changing any AC's tested behavior.

Round 5 (this pass): confirmed all four resolutions hold under independent
re-verification and found no new load-bearing crack.
