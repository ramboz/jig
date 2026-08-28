---
slice: 112-02 — classa-create-advance
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-28T02:35:58Z
prompt_source: review.py craft 112-02
substrate: non-interactive
---

Craft pass — PASS.

_refuse_integrated_advance cleanly placed in transition() before status flip/claim
bookkeeping; reuses the 112-01 primitive with land.py's best-effort + bypass
conventions; --reopen is a first-class audited escape (short-circuits before the git
read). Scope-split with _refuse_start_collision is coherent and mutually exclusive by
status. Vacuous-test claim holds (5/9 deletion-sensitive via assert_called_with anchor).

Reconciliation-log nits (non-blocking):
- Rule-of-three: three cross-ref DONE-check sites now (_refuse_start_collision +
  _refuse_integrated_advance + land.py check_cross_ref_state); the two workflow guards
  use divergent helpers/wording. Unify onto the 112-01 primitive at next touch.
  Deferral justified inline (avoids double origin read for IN_PROGRESS; 051-04 also
  covers the foreign-claim case).
- UX asymmetry: --reopen doesn't apply to the → IN_PROGRESS start-collision path
  (that uses JIG_START_COLLISION_GATE=0). Out of scope; note for future consolidation.

Reviewer: jig:reviewer (isolated, read-only).
