---
adr: 0067
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-10-26T23:54:54Z
prompt_source: review.py frame-critique docs/decisions/adr-0067-genesis-spec-zero.md
---

Three rounds.
Round 1 (needs-changes): shipped skill prose (spec-workflow SKILL.md) names the seed by fixed path as the slice exemplar; renaming/retiring would dangle it in legacy and retired states; plugin-shipped exemplar (Option E) not considered; feedback source uncited. Fixed: decision 7 (state-resolved exemplar wording), Option E added and ruled out (spec 046 — scaffolded prose cannot point into the plugin), owner report cited.
Round 2 (needs-changes): primers/adoption-readiness render unconditionally on every scaffold incl. --force while the seed is greenfield-gated, so a re-scaffold re-introduces the dangling genesis link; legacy-stub detection rule unstated. Fixed: decision 4 invariant (pointers render only when a genesis spec is present/emitted), detection keyed on content/slug, not template bytes or integer value.
Round 3 (pass): primary assumption (000 handled like any spec number) holds — searched skills/scripts/hooks for integer-truthiness / positive-only handling, none. Notes folded in: motivation recast (scaffold verifier runs only at greenfield completion; lasting harm is dangling links), Option F (unnumbered in-project example) named and ruled out; slice 121-02's redundant verify-accepts-retired AC dropped.
