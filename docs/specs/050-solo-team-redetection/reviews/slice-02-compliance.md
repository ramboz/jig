---
slice: 050-02 — stale-audit-team-signal
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-04T23:24:51Z
prompt_source: review.py implementation docs/specs/050-solo-team-redetection/spec.md 050-02 skills/_common/team_signal.py skills/spec-workflow/workflow.py skills/scaffold-init/scaffold.py skills/memory-sync/memory.py ...
---

VERDICT: pass

REASONING:
All 7 ACs of slice 050-02 are met with meaningful (non-smoke) test coverage.
The team-context finding row text is verbatim per AC1; the opt-out marker and the
people.md-exists / solo / monorepo cases all suppress it (AC3/AC7); the finding
carries a `category: team-context` tag distinct from `last-verified` rows (AC5);
and `team_context_drift` walks git at most once per invocation, pinned by a spy
asserting `call_count <= 1` even with a co-present last-verified finding (AC6).
AC4's literal "exits non-zero" rests on a false premise — `stale`'s long-standing
015-03 contract is exit-0/informational (workflow.py:2861-2931 falls through to
`return 0`) and the literal contradicts this slice's own AC2 ("same posture as the
rest of stale") and Goal 6 ("surface" the drift); the implementation honors AC4's
*intent* (exit unchanged / uniform), pinned by `test_stale_exits_zero_with_team_finding`.
The ADR-0002 extraction does not regress 050-01: `TEAM_THRESHOLD` lives only in
`_common/team_signal.py`, the parity matrix asserts the scaffold re-export is the
same function object, and `--bootstrap` still renders the real template with
`{{PROJECT_NAME}}` substituted and no leaked placeholder.

SPECIFIC ISSUES:
None blocking. Minor robustness note (not a defect): `memory.py:86` uses a bare
`.replace("{{PROJECT_NAME}}", ...)` rather than scaffold's `render()` (which raises
on leftover placeholders). Safe today — the template carries only that one
placeholder and a regression test pins no-leak — but if the template later gains a
second placeholder, memory-sync bootstrap would silently ship it unrendered while
scaffold would catch it. For the deviation log / inbox.

RECONCILIATION NOTES:
Record in the (currently `_TODO_` stub) deviation log: (a) the AC4 literal-vs-intent
resolution (stale stays exit-0); (b) the ADR-0002 rule-of-three extraction into the
new `_common/team_signal.py` with all three callers repointed; (c) the inlined-render
latent-drift caveat above.

Reviewer: jig:reviewer (read-only compliance pass). Suite green (Ran 2181, OK).
