---
slice: 116-02 — orient-surface
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-10-04T03:36:01Z
prompt_source: review.py implementation docs/specs/116-use-case-progress-report/spec.md 116-02 skills/spec-workflow/workflow.py skills/spec-workflow/test_workflow.py skills/orient/SKILL.md skills/orient/test_orient_skill_surface.py skills/spec-workflow/SKILL.md skills/spec-workflow/test_spec_workflow_skill_surface.py
---

**Verdict: pass** (two rounds). **Round 1 — pass:** AC1–AC6 met. `progress --summary` renders exactly three things from the same `_progress_data` as the full report (shared `_progress_summary_line` totals; untouched use cases tagged "no spec yet" / "no done slice"; Unanchored count + names), both lists capped at 10 with `… and N more`, no tree, no `%`, shared not-adopted early returns, exit 0. Orient gains a conditional read-only survey bullet and a "5. Use-case progress (when the use-case layer is adopted)" section with the copy rule, both exclusions, the full-listing pointer and the omission rule; "Orient writes nothing" unchanged. Re-ran: `progress --summary` exit 0; test_workflow 589, surface modules OK; host `--check` OK with correct per-host roots. Nits: an over-claiming test name; a negative-invariant test not to be counted as AC5 evidence; one over-long line; the stale 116-01 DoR tick.

**Round 2 — pass, after the owner-approved AC7 (unelicited vision = not adopted, `progress`-only).** `use_cases_unelicited` reads only the `## Use cases` section's own marker; `progress` checks it after the two existing not-adopted gates and before the mode branch; `coverage` / `classify_spec` / `has_use_cases_section` untouched; the 116-01 `## Amendments` entry quotes the original AC7 accurately. AC7 tests fail when the gate or helper is removed; AC1–AC6 still hold. test_workflow 595, test_use_cases 35, orient surface 30, spec-workflow surface 25 OK; host `--check` OK. Nits (folded into the follow-up fix round, see deviation log): stale "same two states" comment + docstring in workflow.py; no hashed-`filled` marker fixture (regex required `status:` last); orient's "(no section, or one not elicited yet)" parenthetical omits the missing-vision `skipped` case.
