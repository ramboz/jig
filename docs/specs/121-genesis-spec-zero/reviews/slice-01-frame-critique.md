---
slice: 121-01 — genesis-seed
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-10-27T00:00:48Z
prompt_source: review.py frame-critique docs/specs/121-genesis-spec-zero/spec.md 121-01 <slice> <spec> <adr-0067>
---

Two rounds.
Round 1 (needs-changes): the pointer invariant was framed as render-or-not, assuming a present genesis is always 000-adopt-jig; a --force re-scaffold of a legacy-seed project would render a dangling 000 link, and AC3 banned the correct 001 target. Fixed: AC7 resolves the pointer to the genesis actually present (000, legacy 001 by slug + skill frontmatter, or none); AC3 scoped to greenfield; fixtures for legacy and no-genesis re-scaffolds asserting on the files directly (the completion verify is greenfield-only and its docs check does not scan AGENTS.md).
Round 2 (pass): 000 handled like any number across workflow.py, entry_gate, bug.py, claim_check (:03d glob), no zero-excluding regex. Notes folded in: fixture (b) must hold an own spec (spec-less dir is greenfield, re-seeded by design); greenfield-ness decided before primers render with the same predicate as the seed. Host-package rebuilds rmtree, so no stale 002 template copies.
