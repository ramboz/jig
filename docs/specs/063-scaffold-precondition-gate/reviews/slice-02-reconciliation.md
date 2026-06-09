---
slice: 063-02 — skill-step0-precondition
pass: reconciliation
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-09T00:14:05Z
prompt_source: review.py reconciliation
---

VERDICT: pass

REASONING:
Every deviation-log claim checks out against the files. The Step 0 precondition exists as item 0
of SKILL.md's "Creating a new spec" section (lines 109-134) — it fires before reserving/drafting,
routes greenfield -> /jig:scaffold-init and existing-layout -> /jig:migrate, names the loose-`slices/`
anti-pattern with "do not hand-roll directories," points at workflow.py new without restating the
heuristic, and matches the 063-01 code's routing strings + JIG_SCAFFOLD_PRECONDITION bypass
verbatim. The "copy-live, no separate template" claim is corroborated (spec-workflow is in
_TIER_SKILLS; the copy applies only _rewrite_skill_md_paths, a path transform). Both guard tests
are real and green: the section-scoped SpecWorkflowStep0Precondition (4 tests, incl. the negative
AC2 assertion) in scripts/test_workflow_contract.py and the --with-machinery scaffold-parity test
in skills/scaffold-init/test_scaffold_mode.py. The two craft nits are consciously dispositioned as
acceptable-as-is, the DoD's adr.py-new follow-on is a genuinely trigger-gated refinement-todo entry,
and the working-tree-only snapshot note honestly explains the empty diff.

SPECIFIC ISSUES (both non-blocking, expected mid-reconciliation):
- docs/specs/README.md still shows both 063 slices as DRAFT while slice-01 is DONE and slice-02 is
  REVIEWED. NOT a reconciliation miss: the slice's `### Close-out (post-DONE)` section explicitly
  defers board regen to post-DONE. Must be regenerated at the spec's DONE close-out (the checklist
  tracks it).
- docs/refinement-todo.md's new entry labels spec 063 "(DONE)" — forward-looking, accurate once this
  changeset lands (consistent with the lands-as-one-changeset model). Verify the DONE transition
  completes.

RECONCILIATION NOTES:
None required — the deviation log is complete and honest. Principles: no violations (deterministic
063-01 gate stays source of truth; prose is a thin judgment-layer pointer; routes-not-blocks per
ADR-0011; shared classify_scaffold_state reused, no third copy). DoD's only unticked boxes are this
reconciliation review and the post-DONE close-out, both correct. No new ADR warranted (spec non-goal
confirms). The one deferred decision (adr.py-new) is tracked in refinement-todo with a concrete
trigger. No new TODO/FIXME introduced.
