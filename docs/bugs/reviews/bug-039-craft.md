---
bug: 039
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-10-04T20:50:20Z
prompt_source: pr-review skill craft pass (diff-shaped; round 2, v2 diff)
---

VERDICT: PASS (re-confirmed on the v2 diff)

Craft re-review of bug 039 (v2): every first-round follow-up was applied correctly.
- The reopen stamp covers all bug review back-edges and the failed-green demote, plus every non-forward spec exit from REVIEWED/RECONCILED/DONE.
- The tests run on a shared _BugTransitionFixture base, above the __main__ guard.
- review.py delegates to the shared now_iso8601.
- Pure-function tests cover the fail-closed branches. Integration tests cover the frame-critique exemption and RECONCILED re-entry.
- The code is lean, Python 3.9-compatible and fits the surrounding style.

Low notes, and what happened to them:
- REOPENED_FIELD comment: fixed; it now points to the call sites.
- Manual FIXING → DIAGNOSING: now stamps.
- Whitespace and class docstrings: fixed.
- Backward moves within the review family (RECONCILED → REVIEWED, DONE → REVIEWED/RECONCILED): kept unstamped on purpose. A trial of stamping them broke the gated RECONCILED → REVIEWED move and would have forced compliance/craft re-review with no code change. No implementation work happens on these moves and the target is itself evidence-gated. Documented in workflow.py and in the record's residuals.
