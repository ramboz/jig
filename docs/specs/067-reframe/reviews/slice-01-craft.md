---
slice: 067-01 — The `/jig:reframe` skill: keystone ADR + dispositions
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T16:48:43Z
prompt_source: review.py craft docs/specs/067-reframe/spec.md 067-01 <deliverables>
---

VERDICT: pass

REASONING:
Judgment-only docs-and-registration slice; craft is strong. SKILL.md is clear, structured,
and internally consistent with ADR-0024 / spec / glossary / product-vision; all six
registration surfaces + both pinned-tier guards + the count-derived worked-example line
carry reframe consistently; relative-link convention matches the sibling bug-fix skill;
every surface-test assertion maps to real content and pins load-bearing structure (not
rubber-stamps). No correctness/security/robustness concerns for a doc/registration change.

SPECIFIC ISSUES:
- [strength] SKILL.md two-level coverage floor names the exact failure each level catches,
  grounds L1 in the n=2 servo skills/ miss, and adds a self-aware maintenance note.
- [strength] Tests pin load-bearing content (fixed L1 class list, does-not-eliminate honesty
  clause, T1 backstop, staleness note), honest about the accepted judgment gap.
- [strength] All source-of-truth tier tables AND both pinned-tier guards + the derived
  worked-example count carry reframe — the 065-03 "miss one surface" lesson heeded in full.
- [nit] slice-01 Close-out note says "5-disposition vocab" but the shipped vocab is 6
  (adds `rewrite`, ADR-0024 §3 n=2). Stale count in the planning checklist only.
- [nit] frontmatter description is long (~25 folded lines) — deliberate jig auto-trigger
  convention, required by the trigger-phrase/deferral/do-not-use test assertions; not a defect.

RECONCILIATION NOTES:
- Correct the slice-01 Close-out "5-disposition" -> "6-disposition" so the regenerated Notes
  column is accurate.
- The slice-01 Close-out line still references adding a "Skills table" row; it is stale
  relative to the AC1 post-076 caveat it supersedes — fix as doc-hygiene during reconcile.
