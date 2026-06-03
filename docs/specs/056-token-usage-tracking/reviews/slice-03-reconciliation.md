---
slice: 056-03 — `.jig/spec-ref` marker for exact session→spec attribution
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-03T04:47:34Z
prompt_source: review.py reconciliation 056-03
---

VERDICT: pass

REASONING:
The deviation log is honest and complete — all five claims verify against the code. The marker format (`spec=NNN` / `slice=NNN-NN`, reader normalizes to 3 digits, tolerates a missing `slice=`) matches the writer/reader; the scoped `.jig/spec-ref` ignore (not blanket `.jig/`, preserving tracked `.jig/test-command`) is present; the `parents[3]` root-derivation invariant is recorded; and both craft-nit rewordings are present (workflow.py "no git commit happens here"; usage.py docstring present-tense). The CLAUDE.md key-term bullet is accurate and does not overclaim — totals are *measured* while `$` is *estimated*, attribution *prefers* the marker and *flags* heuristic-only sessions, pricing via ccusage not hand-rolled. Scope is appropriate: changes confined to the enumerated files plus tests, with no architecture/conventions/inbox edits (correctly justified — the slice crosses no module boundary).

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- No additional deviations observed. The load-bearing items (worktree≈root attribution invariant; scoped-gitignore decision) are both recorded in the deviation log.
- Close-out (post-DONE) checkboxes correctly remain unticked at REVIEWED — status-board regen + the marker-shape Notes entry are post-DONE actions handled at close.
