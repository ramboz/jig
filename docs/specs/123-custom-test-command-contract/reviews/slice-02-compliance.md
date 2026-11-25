---
slice: 123-02 — dead-end-policy-recipe
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-21T02:50:07Z
prompt_source: review.py implementation docs/specs/123-custom-test-command-contract/spec.md dead-end <10 deliverables>
---

VERDICT: pass

REASONING:
All eight ACs for slice 123-02 are met. On a no-runner project, `detect` and `run` (with and without `--test`) print the "no test runner detected" line first, then a line with the resolved recipes path, then a single guidance line under 300 characters naming everything the AC requires. The bug-fix FIXING gate test runs the real `tdd.py`. The recipe states every limit the AC asks for, and the stub-`gradlew` tests cover all AC6 cases plus a run through `tdd.py`. None of the tests would pass with the feature removed. All three test-quality signals in the snapshot are false.

SPECIFIC ISSUES:
- skills/tdd-loop/test-command-recipes.md — (Medium, non-blocking) `grep -h -o -E '<testsuite [^>]*>'` collects every `<testsuite ...>` match in the file, not just the header; a passing test that prints a full `<testsuite ... failures="1">` tag in captured output would be read as red. Read only the first match per file, or add such a noisy case.
- docs/adoption-readiness.md and its template — (Medium, wording) name the four runners and the contract but do not say the list is closed.
- skills/tdd-loop/test_tdd.py — (Low) the end-to-end subtest does not filter `JIG_GRADLE*` / `STUB_*` from the environment.
- skills/bug-fix/SKILL.md, skills/tdd-loop/SKILL.md — (Low) relative ADR-0068 links do not resolve inside installed host packages.

RECONCILIATION NOTES:
- Record the three-line stderr structure, the wrapper's `JIG_GRADLE_TASK` / `JIG_GRADLE_RESULTS` / `JIG_GRADLEW` settings, and the extra recipe guidance (crash mapping, non-1 failure codes, skipped tests) in the deviation log.
- AC8 verified by the orchestrator, not this review.
- Fix or record the `<testsuite>` captured-output flaw.
