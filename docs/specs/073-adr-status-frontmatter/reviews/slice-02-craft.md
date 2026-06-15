---
slice: 073-02 — writer stamps frontmatter status
pass: craft
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-15T18:18:29Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
Surgical, well-scoped implementation that matches the spec exactly: one template line, two `set_frontmatter_field` calls reusing the established helper, both folded into the existing single atomic write — no second write pass, reader untouched. The standout is AC#6's end-to-end test, which drives the real `_lookup_adr_accepted` reader through its frontmatter-first branch rather than asserting on a local copy, so it is genuine behavior verification, not a tautology. Tests are idiomatic with the surrounding unittest suites, all 131 pass, and ruff is clean. Findings are nits and strengths only.

SPECIFIC ISSUES:
- [strength] skills/adr-workflow/adr.py:140-143 — "why, not what" comment explaining status: Proposed comes from the template (contrast with the frame_review stamp); prevents a future maintainer adding a redundant stamp.
- [strength] skills/adr-workflow/test_adr.py — AC#6 exercises the real cross-module reader end-to-end (create→accept→supersede), asserting both negative (superseded not satisfied, reason names "Superseded") and positive (superseder still accepted).
- [strength] skills/adr-workflow/test_adr.py — AC#5 sync-lock guards assert frontmatter AND prose together for both accept and supersede; supersede uses a regex pinned to the real Superseded-by shape.
- [strength] skills/adr-workflow/test_adr.py — `_frontmatter_status` re-parses via adr.py's own `_parse_frontmatter`, pinning on-disk bytes independently of the reader under test.
- [nit] skills/adr-workflow/test_adr.py — `_frontmatter_status` calls `_import_adr_module()` per invocation, re-exec-ing adr.py per assertion; could take the already-imported module to match the setUp `self.adr` convention. Functionally harmless.
- [nit] skills/adr-workflow/test_adr.py — class docstring "cmd_new is the no-git scaffolder" phrasing reads slightly oddly. Cosmetic.

RECONCILIATION NOTES:
No blockers and nothing pre-merge. The two nits are optional polish to fold into reconciliation or leave; neither affects correctness, coverage, or the REVIEWED transition. The four strengths are patterns worth carrying into future adr.py/workflow.py contract work.

Reviewer: general-purpose subagent running the review.py `pr-review` (craft) prompt, applying the richer installed ~/.claude/skills/pr-review rubric. Independent context.
