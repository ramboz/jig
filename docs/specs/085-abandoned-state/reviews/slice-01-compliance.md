---
slice: 085-01 — abandoned-as-lifecycle-state
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-04T03:28:46Z
prompt_source: review.py implementation docs/specs/085-abandoned-state/spec.md 085-01 skills/spec-workflow/workflow.py skills/spec-workflow/test_workflow.py
---

VERDICT: pass

REASONING:
All 8 acceptance criteria are implemented faithfully and mirror the `DEFERRED` precedent as the slice specifies: `ABANDONED` is added to `VALID_STATUSES`, gated to pre-`DONE` states with a named-reason refusal from `DONE` (workflow.py:1191-1199), restricted outbound edges mirroring `DEFERRED` (workflow.py:1183-1189), a dedicated status-board section that's correctly omitted when empty (workflow.py:1710-1739), a widened 4-value `compute_spec_status` rollup with all three specified edge cases handled correctly (workflow.py:1419-1486), `session_plan` skip (workflow.py:588), untouched auto-tick labels (no regression), and a non-blocking, non-cascading stderr warning for live dependents (workflow.py:1368-1387, 1030-1073). Tests in `AbandonedLifecycleTests` exercise every AC with meaningful, behavior-level assertions (state transitions, error text, board content, rollup values) rather than superficial checks, and are isolated via scaffolded temp projects with no risk to the real repo's spec numbering.

RECONCILIATION NOTES:
- The slice's deviation log and reconciliation sweep table are still template placeholders (_TODO_) — expected at this compliance-review stage, but must be filled honestly during reconciliation, particularly noting: (1) the spec's own Non-goals/Assumptions sections already document the four settled frame-critique judgment calls, so reconciliation should cross-reference rather than re-litigate them; (2) docs/refinement-todo.md's existing `unreserve` entry (scoped to never-drafted stubs) remains untouched and distinct from this mechanism, as the spec's Overview notes.
- Confirmed via direct read that `render_status_table` renders ABANDONED rows in the main table in addition to the dedicated Abandoned section — this exactly mirrors pre-existing `DEFERRED` behavior (verified against docs/specs/README.md's current DEFERRED rows appearing in both the active table and the Deferred table), so it is not a defect, but worth a one-line callout in the reconciliation sweep so a future reader doesn't mistake it for a new gap.
- No docs/conventions.md changes were made, consistent with the spec's explicit Non-goal (deferred as a follow-up, out of scope here).
