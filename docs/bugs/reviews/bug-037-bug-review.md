---
bug: 037
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-17T19:32:21Z
prompt_source: review.py bug-review docs/bugs/037-orient-stale-claim-not-reaped.md skills/spec-workflow/workflow.py skills/spec-workflow/test_workflow.py
---

Independent bug-review pass (jig:reviewer subagent, read-only).

VERDICT: PASS

The fix addresses the documented root cause (no read-time liveness check for
`claimed_by`) with a genuine structural capability, not a symptom patch:
`orient --fetch` now resolves the focus slice's claim branch against origin and
reaps merged/gone claims from the headline. The regression suite
(`OrientClaimReapingTests`, 6 cases against a real bare origin) covers both
stale cases plus four fail-safe guards, and the record gives credible red/green
evidence anchored to origin/main@1014d3e. The design is fail-safe by
construction (every ambiguity returns silence), the refactor of
`_freshness_summary` into `_orient_verify`/`_freshness_from_refs` is justified
(single fetch, no duplication) and leaves no dangling references, and the
repository-closure inventory meets the ADR-0037/ADR-0052 enumeration bar.

Non-blocking: `## Learning` empty at review time (filled at reconciliation);
`green_confirmed_at` blank pending the REVIEWED transition gate. Reconciliation
notes: record the `_freshness_summary` decomposition as an intentional
consolidation; ensure the deferred board/check-board reaping refinement-todo
entry exists and cross-links the ADR-0045 reader-half entry; carry the
documented residual false-positives into the learning.
