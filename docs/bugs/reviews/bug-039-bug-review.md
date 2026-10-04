---
bug: 039
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-10-04T20:50:20Z
prompt_source: review.py bug-review (round 2, v2 diff)
---

VERDICT: PASS (round 2; round 1 was NEEDS-CHANGES)

The fix addresses the documented root cause. The FIXING entry gates now bind to the forward ROOT_CAUSED → FIXING edge, so the documented REVIEWED → FIXING back-edge is allowed and ungated. Every review back-edge, on both the bug and spec-workflow sides, stamps review_reopened_at. Re-entering REVIEWED/RECONCILED/DONE needs verdicts strictly newer than that stamp, and malformed values fail closed. The closure inventory lists the convergent back-edges, each with a disposition and a test, and records the intentional residuals honestly. The regression tests would be red without the fix.

Round 1 blockers resolved: the DIAGNOSING back-edges are now stamped; the record no longer contradicts itself; the test class sits above the __main__ guard.
Round 2 low notes, all addressed after the verdict: test counts in the record corrected; the residuals paragraph moved out of the Fix bullet list; the REOPENED_FIELD comment now points to the call sites; extra blank lines removed; the ADR amendment re-wrapped.

Post-verdict delta (orchestrator): a manual FIXING → DIAGNOSING now also stamps (craft round-2 note). Spec-side moves within the review family (e.g. RECONCILED → REVIEWED) stay unstamped, matching this pass's assessment that this is acceptable.
