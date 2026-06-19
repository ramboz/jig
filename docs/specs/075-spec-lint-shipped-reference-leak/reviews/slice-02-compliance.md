---
slice: 075-02 — normalize remaining shipped references
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-19T23:13:25Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All four ACs met. AC1: migrate/worked-example-slice-to-spec.md:152 runnable ref is plugin-root form. AC2: descriptive mentions (analyze SKILL.md 12/65/88/370, spec-workflow SKILL.md, slice-template) use the bare path-neutral tool name; the one runnable analyze ref (SKILL.md:70) is plugin-root-prefixed. AC3 (prior needs-changes): the new SpecLintReferenceShapeTests.test_no_bare_relative_scripts_path asserts count("scripts/spec_lint.py") == count("${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py") — GREEN now (1==1), RED if SKILL.md:70 regressed to a bare path (1!=0) — closing the gap. AC4: no bare scripts/spec_lint.py outside plugin-root form in skills/+templates/.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- The AC3 guard is a count-equality invariant relying on the plugin-root literal being a contiguous superstring of the bare path; record this so a future maintainer who line-wraps that literal understands the assertion's dependency.
- AC1/AC2 edits in migrate/spec-workflow/slice-template have no dedicated per-file surface test — only AC4's manual grep backs them. A committed shipped-surface grep test is proposed in docs/inbox.md (2026-06-19 shipped-skills/bare-path-invocations).
