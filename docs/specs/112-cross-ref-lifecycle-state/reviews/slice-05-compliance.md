---
slice: 112-05 — classb-claim-reservation
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-28T15:31:10Z
prompt_source: review.py compliance 112-05
---

Compliance pass (re-review after AC2 push-path fix) — PASS.

Initial pass found one blocker: the Class-B sibling/remote IN_PROGRESS halt (AC2)
fired only on the default path, degrading to advisory under --push/--pr. Fixed by
extracting _refuse_sibling_in_progress_claim (workflow.py:4941), called at the same
transition() point on BOTH paths (default via _refuse_start_collision:5048; push/pr
via the else-branch:1452, before the CAS reservation/trunk write). AC2 gap closed;
AC3 preserved by construction (whole block gated on new_status==IN_PROGRESS; hit
condition status==IN_PROGRESS + foreign claimed_by). New push-path tests non-vacuous
(assert_called_once on the 1452 site + WorkflowError + reserve_mock.assert_not_called).
AC1/AC4-AC7 unchanged from the passing initial review.

Deviation-log note: benign redundant gate check on the default path (outer function
returns early when disabled → no double bypass-emit).

Reviewer: jig:reviewer (isolated, read-only).
