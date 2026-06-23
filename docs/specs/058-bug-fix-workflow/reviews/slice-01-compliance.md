---
slice: 058-01 — `tdd.py` targeted-test support
pass: compliance
verdict: pass
reviewer: jig-reviewer
reviewed_at: 2026-06-23T22:21:47Z
prompt_source: review.py implementation docs/specs/058-bug-fix-workflow/spec.md 058-01 skills/tdd-loop/tdd.py skills/tdd-loop/test_tdd.py skills/tdd-loop/SKILL.md docs/specs/058-bug-fix-workflow/slice-01-tdd-targeted-test.md hosts/claude/skills/tdd-loop/tdd.py hosts/claude/skills/tdd-loop/SKILL.md hosts/codex/plugins/jig/skills/tdd-loop/tdd.py hosts/codex/plugins/jig/skills/tdd-loop/SKILL.md
---

VERDICT: pass

REASONING:
The targeted `--test` behavior now meets the slice ACs: pytest receives native node ids, vitest/jest map `path::name` to file plus `-t`, unresolved selectors return 2 with the selector named, and non-targeted runs keep existing behavior. The prior pytest and JS false-positive classifier issues are covered by regression tests, and host helper copies match the source. No principle, ADR, or tracked-debt issue found.

SPECIFIC ISSUES:
None.

RECONCILIATION NOTES:
None.
