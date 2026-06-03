---
slice: 056-03 — `.jig/spec-ref` marker for exact session→spec attribution
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-03T04:41:26Z
prompt_source: review.py implementation 056-03
---

VERDICT: pass

REASONING:
All four acceptance criteria of slice 056-03 are met by the deliverable. AC #1: `_write_spec_ref_marker` stamps `<root>/.jig/spec-ref` only on the IN_PROGRESS transition, idempotently via `atomic_write_text`, fully wrapped in a broad except so any failure is swallowed and never blocks the transition or its gates. AC #2: `attribute_session` prefers the marker and falls back to the content heuristic. AC #3: `render` surfaces a marker-vs-heuristic count and a lower-confidence caveat only when heuristic sessions contributed. AC #4: the marker write is ordered after all status writes and after the review-evidence gate, and a regression test confirms the gate still refuses an unsupported REVIEWED transition. Tests are meaningful — notably the marker-wins-over-conflicting-content test, which proves precedence rather than asserting it superficially.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- A scoped `.gitignore` entry (`.jig/spec-ref` only, not a blanket `.jig/`) was added — a fifth touched file beyond the four enumerated deliverables, and correct (keeps the tracked `.jig/test-command` unignored). Worth a line in the deviation log.
- Attribution by marker depends on a session's `cwd` equalling the project root that holds `.jig` (the worktree≈root assumption). The marker write derives root from `spec_md.resolve().parents[3]` rather than from cwd; consistent with the worktree-per-task model but worth recording as a documented load-bearing assumption.
- DoD items beyond the ACs (deviation log, reconciliation review, status-board Notes regen, CLAUDE.md compression) are reconciliation-phase artifacts, flagged for that step.
