---
slice: 075-01 — ship spec_lint and fix the runnable reference
pass: craft
verdict: pass
reviewer: jig:reviewer / pr-review
reviewed_at: 2026-06-19T22:58:28Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
Textbook minimal, well-scoped fix: one-line allowlist addition, a single runnable-reference rewrite to the ${CLAUDE_PLUGIN_ROOT} form matching sibling conventions, and regression tests that go red if the inclusion is removed. Follows existing module patterns; comments accurate; descriptive references and worked-example correctly deferred to 075-02. No blockers.

SPECIFIC ISSUES:
- [strength] scripts/test_build_release_zip.py:139-194 — test_spec_lint_shipped + test_runtime_scripts_only exact set-equality give a bidirectional guard satisfying AC2.
- [strength] scripts/install_contract.py:390-396 — allowlist comment extended with accurate pure-stdlib distinction; doc and data stay in sync.
- [strength] skills/migrate/SKILL.md:415 — rewrite matches the exact ${CLAUDE_PLUGIN_ROOT} form used elsewhere in the file; project-relative arg untouched.
- [nit] scripts/test_build_release_zip.py:192 — assertion message still says "runtime trio"; allowlist is now four files. Cosmetic; assertion is correct.
- [nit] skills/migrate/SKILL.md:418 — sibling status-board invocation uses a bare repo-relative path with the same consuming-project resolvability gap; out of 075's spec_lint inventory but worth tracking.

RECONCILIATION NOTES:
- Fix stale "trio" wording (test_build_release_zip.py:192).
- Flag migrate SKILL.md:418 bare-path status-board invocation (same bug class, out of scope) to inbox/follow-up.
