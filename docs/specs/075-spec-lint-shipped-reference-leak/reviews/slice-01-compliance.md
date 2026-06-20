---
slice: 075-01 — ship spec_lint and fix the runnable reference
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-19T22:58:28Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All three slice-075-01 ACs are met and meaningfully exercised. AC1: "scripts/spec_lint.py" added to RELEASE_INCLUDE_SCRIPT_FILES, shipped by iter_release_files. AC2: new test_spec_lint_shipped asserts presence in a real built zip and goes red if the entry is removed (reinforced by test_runtime_scripts_only + test_include_side_data_present exact-set pins). AC3: migrate SKILL.md:415 uses ${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py with the project-relative argument unchanged. The spec_lint comment correctly states pure-stdlib / no _common.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- No deviations from planned shape. New test reuses the shared _build_once() real-source build fixture (idiomatic).
- Out-of-scope-by-design references left for 075-02 remain untouched — no scope creep.
