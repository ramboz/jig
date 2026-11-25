---
adr: 0069
pass: frame-critique
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-11-21T02:57:55Z
prompt_source: review.py frame-critique docs/decisions/adr-0069-owner-review-human-attested-evidence.md
---

VERDICT: pass

REASONING:
Round 4 of the frame-critique (rounds 1–3 returned needs-changes and drove decision 6). The assumption the frame depends on most is that the ask stamp binds an owner verdict to the build that was actually offered: `review_reopened_at` < `owner_review_asked_at` <= `reviewed_at`. Every way found to break it is either a deliberate act (ADR-0011) or a residual the ADR already names under decision 6 "Limits, stated plainly", Open questions and kill criterion 2. The code matches decision 6: in `skills/_common/review_evidence.py` the owner checks run only when the verdict is not already stale after the reopen; `owner_ask_stale_problem` requires asked > reopened and fails closed when the ask was never recorded but a reopen exists; `owner_answer_predates_ask_problem` requires reviewed >= asked. In `skills/independent-review/review.py`, `record_review` calls `_reopen_owner_flagged_batch` for any non-`pass` REVIEWED-stage verdict (including owner-review) except an escalated arch verdict, and `owner_review_ask` stamps `owner_review_asked_at` only on a flagged slice.

SPECIFIC ISSUES:
- Attacked paths: owner `pass` before an automated rejection (stale via the reopen stamp); late reply to the earlier ask (blocked, asked <= reopened); old reply recorded then the ask re-run (blocked, reviewed < asked); same-second ordering (strict comparisons fail closed); ask never run with no reopen (the answer refers to the only build, not a wrong clear).
- Remaining paths all clear without a recorded rejection and are named in the ADR: ask run before the fix exists; a fix with no recorded rejection; fixes following a person's decision on an escalated arch verdict.
- [nit] Decision 6 could name the escalated-arch exclusion as one example of "a change with no recorded rejection".

RECONCILIATION NOTES:
None. Every residual is already named in the ADR; nothing blocks accepting it as written.
