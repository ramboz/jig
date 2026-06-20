---
slice: 075-02 — normalize remaining shipped references
pass: craft
verdict: pass
reviewer: jig:reviewer / pr-review
reviewed_at: 2026-06-19T23:13:26Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
Cleanly, minimally scoped: every shipped scripts/spec_lint.py reference now carries the resolvable ${CLAUDE_PLUGIN_ROOT} form for runnable guidance while purely descriptive mentions use the bare tool name, applied consistently. spec-workflow/SKILL.md and slice-template correctly left untouched (already bare-name). Surface tests updated to drop the stale pin; the substring-guard soft-spot was then closed in reconciliation by a committed count-equality guard.

SPECIFIC ISSUES:
- [strength] skills/analyze/SKILL.md:70 — runnable guidance quoted as plugin-root form while surrounding descriptive mentions stay bare; consistent and readable.
- [strength] skills/migrate/worked-example-slice-to-spec.md:152 — the remaining literal invocation rewritten to plugin-root form matching the 075-01 fix.
- [nit] skills/analyze/test_analyze_skill_surface.py — substring assertions alone didn't guard the relative-path regression (addressed in reconciliation by SpecLintReferenceShapeTests).

RECONCILIATION NOTES:
- Surgical scope, no prophylactic edits.
- Follow-up candidate (logged to inbox): a committed shipped-surface grep test would make the AC4 guard durable rather than manual.
