---
slice: 051-04 — start-time claim-collision guard (→ IN_PROGRESS)
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-11T15:56:38Z
prompt_source: review.py craft (051-04)
---

Independent craft / code-review pass of slice 051-04 (fresh reviewer).

VERDICT: pass — implementation faithful and well-crafted; all findings are nits, none block.

Strengths: clean split between the never-raising tagged-tuple remote read (`_origin_slice_state`) and the decision layer (`_refuse_start_collision`); AC6 DONE-gap closure carries a precise comment distinguishing a trunk-integrity guard (never bypassable) from the start-collision gate; documented no-double-fetch split (`not (push or pr_mode)`); strong test pyramid (mock decision-logic / recorder command-shape / real-git E2E), including the "DONE block wins over stale foreign claim" edge and the issue-81 rewind-to-stale-READY scenario. Error messages name the slice, the remedy, and the bypass env var.

Nits (→ reconciliation log):
1. [spec] The block covers only DONE + foreign IN_PROGRESS; a REVIEWED/RECONCILED origin copy falls through to proceed (faithful to AC scope, but the window is unnamed) — add a one-line spec note.
2. [impl] Add direct `_origin_slice_state` unit tests for the `unreadable` and `fetch-failed` classifications.
3. [impl] The `relative_to` ValueError fallback silently skips; AC5's contract is a loud warning — add a warning line.
4. [impl] The `git show origin/main:<rel>` + parse read-shape now exists in both `_origin_slice_state` and inline in `_reserve_claim_on_main` (2nd caller — within ADR-0003 inline-mirror budget; extraction candidate at a 3rd caller).
