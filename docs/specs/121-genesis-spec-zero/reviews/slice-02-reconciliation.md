---
slice: 121-02 — retire-genesis
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-10-27T02:03:06Z
prompt_source: review.py reconciliation docs/specs/121-genesis-spec-zero/spec.md 121-02
---

Two rounds.
R1 (needs-changes): deviation 1 (000-adopt-jig requires `skill: scaffold-init` in retire-genesis) diverged from scaffold-init's `_resolve_genesis_dir` (000 on slug alone), contradicting AC6's single predicate; workflow.py comment, SKILL.md bullet and glossary misdescribed it; sweep lacked docs/prompts.md and a statement on code files.
Fixed: `_resolve_genesis_dir` aligned (000 and legacy 001 both need the frontmatter) + new test `test_existing_000_without_seed_frontmatter_is_not_pointed_at`; comment/SKILL.md corrected; deviation 1 and sweep updated.
R2 (pass): predicate shared across scaffold, retire-genesis and the hint; prose accurate; no over-build (predicate local in each of two callers per ADR-0002). Folded in: scaffold.py docstring no longer claims `_emit_seed_spec`'s predicate for the existing-genesis branch; sweep row accounting for 121-01's committed files.
Full suite after alignment: 5170 tests OK (8 skipped).
