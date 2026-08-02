---
slice: 098-01 — entry-gate nudge (Claude host)
pass: frame-critique
verdict: pass
reviewer: reviewer subagent (read-only, independent)
reviewed_at: 2026-08-02T07:38:55Z
prompt_source: review.py frame-critique prompt; deliverables: entry_gate.py, jig-entry-gate.sh, hooks.json, verify_install.py, tests
---

Adversarial frame critique (slice declares frame_review: true). **Verdict: pass.**

The framing holds under attack. Both prior dead-gate failure modes are genuinely
avoided, and — critically — the dependencies that make the anti-dead-gate
argument true are present in the tree, not assumed: #138's
`_CLAIM_WORKING_STATUSES` (workflow.py) and 098-04's `bug=` marker (bug.py). The
"inside" test requires marker-names-item AND claimed_by==claim_id AND a live
status, so it fires on jig's own `main` and on a `.`-rooted project's source. The
tests assert the falsifying cases directly.

Framing concerns — all acceptable-and-documented, none blocking:
1. Closes only the "nothing in flight" subset of #111 (an in-slice ad-hoc edit
   hides inside the claim; Bash-written edits never reach the hook). Accepted
   limit, already recorded in ADR-0044 (resolved q1 second objection; Consequences
   Bash-write limit; under-fire kill criterion).
2. Bug arm uses the full OPEN_STATUSES span (broader than the slice arm). **Added
   an explicit accepted-limit comment** at the `_BUG_OPEN_STATUSES` definition so
   098-02 (Codex parity) keeps the same span; bounded because 098-04 clears the
   marker at every terminal state.
3. Once-per-session cadence under-fires by construction (many edits → 1 nudge);
   intended (settled call #2), durable per-edit capture deferred to 098-03.
4. Marker stamped at IN_PROGRESS; a slice going straight to READY_FOR_REVIEW would
   lack a marker. Edge case, acknowledged in the AC.

Reconciliation notes (addressed): the stale "NOT YET STARTABLE" banner + ⏳ DoR
items were corrected to reflect that both deps are satisfied.
