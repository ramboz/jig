---
slice: 057-01 — Delegation-first session template
pass: arch
verdict: pass
reviewer: arch-review
reviewed_at: 2026-06-03T22:17:15Z
prompt_source: /tmp/057-01-arch-prompt.txt
---

Arch pass — adds one stdout-only, side-effect-free CLI subcommand that is a pure function of a spec's slices+frontmatter, preserves module boundaries (helpers read specs; nothing writes across), reuses the shared FRONTMATTER_TRUTHY predicate so the plan's notion of 'needs arch' cannot drift from the review-evidence gate, soft/advisory per ADR-0011. Naming-coherence nit on the {skill} column (agent/phase mislabeled as skill) ADDRESSED inline. No structural concerns.
