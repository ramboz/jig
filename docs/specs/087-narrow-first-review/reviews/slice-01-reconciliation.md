---
slice: 087-01 — investigation guidance in code-review prompts + reviewer agent
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-11T19:13:07Z
prompt_source: review.py reconciliation docs/specs/087-narrow-first-review/spec.md 087-01
---

VERDICT: pass

REASONING:
Deviation log is faithful and complete — every load-bearing claim cross-checks
against the code: single `_INVESTIGATION` constant interpolated into exactly the
five code-review builders before `_PROHIBITIONS` and absent from the three prose
builders; guarding block comment documents the code-vs-prose split; nit #1 fold-in
present ("the change under review"); reviewer.md carries the deliberate 3-of-5
moves; spec has `## Current state (verified)` with `## Assumptions` = `None.`.
Tests assert all five moves, presence-in-5, absence-in-3, and the agent section.
All five named deviations (scoping, nit fold-in, 3-of-5, rebase, assumptions-
sentinel) are logged; sweep dispositions are credible.

SPECIFIC ISSUES:
- [nit] slice-01 reconciliation sweep — `docs/specs/README.md` disposition reads
  `updated` but board regen is a forward-referenced close-out step (done at DONE,
  not at reconciliation). Minor tense nuance; regen performed at close-out makes
  it accurate. Non-blocking.

RECONCILIATION NOTES:
- servo ADR-0025 (Proposed) cross-reference is accurate — filed in the servo repo
  this session as part of the same request.
