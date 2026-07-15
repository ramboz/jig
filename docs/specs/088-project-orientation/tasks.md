# Tasks: 088 project orientation

## 088-01 — computed orientation at project pickup

- [x] Write red tests for AC1-AC8.
- [x] Implement `orient(project_dir)` and CLI dispatch.
- [x] Implement and register the SessionStart orientation hook.
- [x] Update pickup guidance for AC7.
- [x] Regenerate host packages and verify drift for AC9.
- [x] Run focused and full test suites.
- [x] Record all required review evidence.
- [x] Reconcile, transition to DONE, regenerate the status board, and prepare direct landing.

## 088-02 — the `/jig:orient` judgment skill

- [x] Adopt the contributed skill as `skills/orient/SKILL.md`; register Tier-1 across the pinned inventories + product prose.
- [x] Layer on `workflow.py orient`; keep zero-write (stdout) and `docs_root`-aware; fix the handoff to `jig:spec-workflow`.
- [x] Author the routing eval (project-level positives + mid-implementation route-away negatives); routing gate green.
- [x] Regenerate both host packages; full suite + spec_lint + drift green.
- [ ] Architecture review passed (`arch_review: true`) — under review on PR #90.
- [ ] Reconcile + record the deviation log after review.
