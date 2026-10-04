---
slice: 116-01 — progress-rollup
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-10-03T17:57:01Z
prompt_source: review.py implementation docs/specs/116-use-case-progress-report/spec.md 116-01 skills/spec-workflow/workflow.py skills/spec-workflow/test_workflow.py skills/spec-workflow/SKILL.md skills/_common/use_cases.py skills/spec-workflow/test_spec_workflow_skill_surface.py docs/product-vision.md
---

**Verdict: pass.** All ten ACs met. `workflow.py progress` joins `use_cases:` links with slice state under the same counting rule as `compute_spec_status`, both now reading statuses through the shared `_spec_slice_statuses` helper. Every AC has a fixture test that fails when its feature is removed (D/K values, `2/3 (+1 deferred)`, legacy layout, Unanchored with `UC-99` named, `no spec yet`, once-counted summary, no `%`, skipped / no-op / write-nothing / exit-0). Reviewer ran: the new + CoverageTests + skill-surface tests (50 OK), full `test_workflow` (572 OK), `test_use_cases` OK, `build_host_packages.py --check` exit 0, and `progress --project-dir .` on jig (exit 0, 22 use cases · 113 specs · 2 unanchored · 281/300, tree unchanged). AC9: vision bullet names the exception and links ADR-0064. AC10: no remaining `skills/` hit presents jig as not adopted. ADR-0064 bounds 1–5 hold.

**Non-blocking issues (folded into the polish round, see deviation log):** `skills/_common/test_use_cases.py` comments still said "jig itself" as the not-adopted example; `test_ac7_notes_match_coverage_two_states` compared keyword truthiness only.
