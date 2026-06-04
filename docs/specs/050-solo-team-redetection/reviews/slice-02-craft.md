---
slice: 050-02 — stale-audit-team-signal
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-04T23:24:52Z
prompt_source: review.py pr-review docs/specs/050-solo-team-redetection/spec.md 050-02 skills/_common/team_signal.py skills/spec-workflow/workflow.py skills/scaffold-init/scaffold.py skills/memory-sync/memory.py ...
---

VERDICT: pass

REASONING:
The ADR-0002 rule-of-three extraction is clean: `skills/_common/team_signal.py`
imports only stdlib + `_common.atomic_io` (no circular import back into any skill),
the `scaffold.py` re-export shim preserves every prior public name (identity-pinned
by a test), and all three callers are repointed with the old importlib / `load_scaffold=`
seam fully retired from production `memory.py`. The `find_stale_items` 2-tuple → 3-tuple
change is fully propagated (the lone unpacker + all test consumers updated), and the
human-rendered `stale` text is unchanged. Tests assert behavior, not smoke. Deviation
#3's inline render is byte-identical to `copy_template` for the current template, with
one latent-drift nit worth logging.

SPECIFIC ISSUES:
- [strength] test_workflow.py:1066 `test_no_double_walk_counts_once` — seeds BOTH a
  last-verified row and a team-context row, spies the real `count_team_contributors`,
  asserts `call_count <= 1`. A genuine AC6 regression guard, not smoke.
- [strength] test_scaffold.py:523 `test_count_is_common_reexport` — `assertIs` pins the
  scaffold name to the shared function identity; a future re-implementation fails loudly.
- [strength] team_signal.py:124 `team_context_drift` — collapses the full predicate
  (signal AND no-people.md AND no-marker) into one shared fn reading git once; consumed by
  both the nudge (memory.py) and the audit (workflow.py), so AC3/AC6 parity is structural.
- [nit] memory.py:86 — the inline `.read_text().replace("{{PROJECT_NAME}}", ...)` drops
  scaffold's `render()` leftover-placeholder validation and the `_rewrite_skill_md_paths`
  post_render. Inert for the current single-placeholder template (output byte-identical,
  AC5 holds), but byte-identity is now an implicit invariant of template content rather
  than enforced by shared code. Add a comment recording the assumption AND/OR a cross-check
  test asserting the two render paths agree on the real template.
- [nit] test_workflow.py:987 — `test_finding_carries_team_context_category` asserts the
  contributor count but not the `/jig:memory-sync` bootstrap hint at the structured level
  (only the stdout-level test does). Coverage complete but split.

RECONCILIATION NOTES:
Write the deviation log (currently a `_TODO_` stub): (a) the inline-render decision +
latent-drift caveat; (b) AC4 resolved-intent (stale stays exit-0 vs the literal
"exits non-zero" — a real spec-vs-impl deviation that must be logged, not just commented);
(c) the importlib / `load_scaffold=` seam retirement from 050-01's reconciliation. Pending
close-out doc item: update the spec-workflow Skills-table row to mention the `team-context`
finding category in `stale`.

Reviewer: jig:reviewer (read-only craft pass, pr-review baseline). Suite green (Ran 2181, OK).
