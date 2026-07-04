---
slice: 085-01 — abandoned-as-lifecycle-state
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-04T03:30:40Z
prompt_source: review.py pr-review docs/specs/085-abandoned-state/spec.md 085-01 skills/spec-workflow/workflow.py skills/spec-workflow/test_workflow.py
---

VERDICT: pass

REASONING:
The implementation is a faithful, well-documented mirror of the DEFERRED precedent (slice 015-02) — same FROM-state restriction shape, same rollup-exclusion mechanism, same status-board section pattern, same **Abandonment reason:** extraction convention as _extract_resolution_trigger. Test coverage is thorough and maps cleanly onto every AC (transition matrix, board rendering with/without reason, rollup permutations, session-plan skip, auto-tick no-op, live-dependent warning with/without dependents). Two minor craft nits found, neither rising to blocker: a dead/unused function parameter and a vacuous test assertion.

SPECIFIC ISSUES:
- [nit] skills/spec-workflow/workflow.py:1030-1032 — `_find_live_dependents`'s `abandoned_spec_md` parameter is accepted but never read in the function body; only `abandoned_slice_path` drives the exclusion. Either use it or drop the parameter.
- [nit] skills/spec-workflow/test_workflow.py:1023 — `self.assertNotEqual(dependent_md, None)` is vacuous (`_write_spec` never returns `None`); it verifies nothing beyond the `assertIn("801-01", result.stderr)` check on the prior line. Safe to delete.
- [strength] skills/spec-workflow/workflow.py:1419-1487 — `compute_spec_status`'s widened rollup logic is clearly commented with the exact truth table and each branch cites the spec's Assumptions section for the reasoning behind non-obvious calls.
- [strength] skills/spec-workflow/workflow.py:1710-1739 — `render_abandoned_table` is a near-exact structural mirror of `render_deferred_table`, keeping the two board sections visually and behaviorally consistent without duplicating logic awkwardly.
- [strength] skills/spec-workflow/test_workflow.py:819-1094 — `AbandonedLifecycleTests` covers every AC with dedicated, isolated fixtures, giving good signal-to-noise per test.

RECONCILIATION NOTES:
- SKILL.md's "DEFERRED state" section (lines 561-577) has no sibling "ABANDONED state" section yet — expected to land during reconciliation, not craft; flag it so the reconciliation sweep doesn't skip it.
- The two nits above (unused abandoned_spec_md parameter, vacuous test assertion) are good deviation-log candidates — small cleanup, non-blocking for REVIEWED.
- Non-goals section explicitly refuses DONE → ABANDONED and no-cascade-to-dependents automation; both are faithfully honored in the code — worth noting in the deviation log as confirmed-faithful rather than drifted.
