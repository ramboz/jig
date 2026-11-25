---
slice: 123-02 — dead-end-policy-recipe
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-21T03:08:10Z
prompt_source: review.py reconciliation docs/specs/123-custom-test-command-contract/spec.md dead-end
---

VERDICT: pass

REASONING:
The deviation log's claims hold against the code and docs. `tdd.py` writes three stderr lines; the hint is about 290 characters and names `.jig/test-command`, `{test}`, the exit contract, the build-failure caveat and `test-command-recipes.md`. The wrapper reads only the first `<testsuite>` tag of each report, deletes old `TEST-*.xml` before calling Gradle, and reads `JIG_GRADLE_TASK` / `JIG_GRADLE_RESULTS` / `JIG_GRADLEW`. The no-real-Gradle disclaimer and the `clean<TaskName>` fallback are present. Both SKILL.md files, product-vision, adoption-readiness and its template, the refinement-todo entry and all three host copies say what the log claims. The sweep is credible.

SPECIFIC ISSUES:
- slice-02 sweep primer row says "The scaffold template change is in 123-02's row" — copied from slice-01's sweep; should point to this sweep's adoption-readiness row. Cosmetic.
- The sweep does not list the test files this slice changed (`skills/tdd-loop/test_tdd.py`, `skills/bug-fix/test_bug.py`); deviation item 8 mentions them. Add a row.
- The hint says "first non-comment line"; the recipe says "first non-blank, non-comment line". Not conflicting; not blocking.

RECONCILIATION NOTES:
- Files in the changed-files list from origin/main drift (spec 122, bug 041, CHANGELOG, manifests, agents/reviewer.md, docs/conventions.md) are outside spec 123 and rightly absent; one sentence saying so would make it explicit.
- Deviation item 5 (three environment settings, extra contract guidance) accepted: each setting has a real caller AC5 names.
- Principles and engineering checks clean: ADR-0068 records the decision, no new TODO/FIXME, the deferred JUnit-XML reader has a demand-gated entry.
