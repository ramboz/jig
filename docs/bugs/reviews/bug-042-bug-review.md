---
bug: 042
pass: bug-review
verdict: pass
reviewer: reviewer subagent (fresh, round 3)
reviewed_at: 2026-11-21T02:43:55Z
prompt_source: review.py bug-review
---

VERDICT: pass

REASONING:
The fix addresses the recorded root cause: the frame-critique requirement is keyed on the edge out of the pre-implementation zone (`_crosses_frame_gate`) and reuses `validate_evidence(…, "READY_FOR_REVIEW")` unchanged. The gate validates ahead of the claim bookkeeping, so a refused pickup leaves no `refs/claims/<N>` reservation, and the bypass audit event is still emitted once, by `_gate_evidence`. Red-before-fix is evident by reading (pre-fix `_gate_evidence` returned at its first line for the two targets); the reviewer was read-only, so green rests on the `→ REVIEWED` gate run. Remaining items were nits.

ROUND HISTORY (fresh reviewer each round):
- Round 1, needs-changes: the new `→ IN_PROGRESS` refusal fired after `_reserve_claim_ref` had created (and under `--push` published) the claim ref; the fixture was not git-backed so no test could see it; the inventory and call-site closure omitted the claim machinery; `## Proof` asserted green before the stamp; the predicate and the validator read the flag through differently shaped readers (embedded-layout slices); no test for a late-flagged slice released to the queue and re-picked without a pass.
- Round 2, needs-changes: record still named the old flag reader; "`--release` does not skip the gate" had no test; under the bypass the audit event was emitted before the claim refusals, so a transition refused later still logged one; `_crosses_frame_gate` failed open on `EvidenceError`; the bypass test asserted at-least-one event.
- Round 3, pass (nits): two stale record sentences (signature, "call is unchanged"); "a bypassed transition refused later logs no event" and the `EvidenceError` branch hold by code ordering, untested; the foreign-claim warning text still suggests `READY_FOR_IMPLEMENTATION --release`; one unwrapped SKILL.md line.

RECONCILIATION NOTES (reviewer):
- Scope is wider than issue 251's two named targets: a flagged DRAFT → REVIEWED / RECONCILED / DONE jump, a READY_FOR_IMPLEMENTATION re-stamp and a `--release` to it are gated. The record states this.
- The READY_FOR_REVIEW-target validation now runs before the claim block and the DONE dependency check; refusal precedence changes when both would fire. Harmless.
- Under the bypass a flagged crossing to READY_FOR_IMPLEMENTATION / IN_PROGRESS emits a `gate_bypassed` event even when a pass is on record — same as the existing gated targets, but new audit volume.
- ADR-0014 §5 and spec 045 slice 03 still list the two targets as ungated, pending owner approval (spec 102). Follow-ups 0 (embedded-layout flag read) and 1 (declared vs derived flag) stay open.

DISPOSITION (implementer, after round 3):
- The two stale record sentences are corrected; the SKILL.md line is rewrapped.
- Follow-ups 0 and 1 are filed in docs/refinement-todo.md.
- Left as is: the foreign-claim warning text (a foreign claim on a flagged pre-implementation slice normally means it already holds its pass; the caveat is in SKILL.md), and the two by-ordering claims without tests.
