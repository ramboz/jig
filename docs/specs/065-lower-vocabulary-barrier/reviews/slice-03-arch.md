---
slice: 065-03 — `/jig:explain` skill (term + artifact modes)
pass: arch
verdict: pass
reviewer: jig:reviewer / arch-review
reviewed_at: 2026-06-07T18:06:31Z
prompt_source: review.py arch-review
---

VERDICT: pass

The slice adds a new tier-1 judgment-only skill and registers it across the three skill
tables (scaffold._TIER_SKILLS as source of truth, install_contract.EXPECTED_SKILLS,
scaffold_contract._TIER_SKILLS) following jig's established restate-plus-consistency-test
convention, with surface tests pinning each restatement equal to the source so they cannot
drift. The judgment-only/no-`.py` shape is the right pattern — matches the proven sibling
skills (clarify, pr-review, arch-review); the only determinism (lexicon load via the 065-01
`load(project_dir)` loader, artifact reads) runs inline. Ephemeral/off-hot-path design holds:
nothing injected into CLAUDE.md or any always-loaded doc (consistent with 055/057); the only
external contract surface (SKILL.md frontmatter, per architecture.md §Contract surfaces) is
updated in the same change-set. No module-boundary violations.

[strength] three-table registration via restate-plus-consistency-test convention + the
judgment-only/no-`.py` reuse are the correct in-pattern architectural choices.
[nit, addressed] term-mode `python3 -c` recipe's `sys.path.insert` was layout-relative; the
046-01 rewrite policer targets `${CLAUDE_PLUGIN_ROOT}/skills/...` helper paths, not this
relative snippet, so it wouldn't be auto-corrected on copy — fixed during reconciliation to
probe both layouts. (Reviewer: jig:reviewer / arch-review, read-only.)
