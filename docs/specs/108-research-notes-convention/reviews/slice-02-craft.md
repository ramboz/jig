---
slice: 108-02 — codify in conventions.md + register deferred machinery
pass: craft
verdict: pass
reviewer: jig:reviewer (fresh-context, Opus)
reviewed_at: 2026-08-11T19:13:16Z
prompt_source: review.py pr-review docs/specs/108-research-notes-convention/spec.md 108-02 <deliverables> --richer-skill none
substrate: non-interactive
---

Craft (pr-review) review of slice 108-02. Fresh-context read-only `jig:reviewer` (Opus). Prompt built by `review.py pr-review --richer-skill none` (jig baseline; docs slice).

## Verdict: pass (after one needs-changes round)

conventions.md rule + five refinement-todo deferrals are high-craft (terse Rule/Why/How; demand-gated falsifiable triggers citing ADR-0054 + sibling commands). Strengths noted on the block-scoped non-vacuous test pattern and the demand-gating quality.

## Findings (addressed → re-verdict pass)
- [blocker][impl] `test_conventions_states_phase_distinction` vacuous (bare "refinement-todo" pre-existed at conventions.md:97). FIXED: asserts rule-unique "sequential with, not a competitor to".
- [nit][impl] non-distinctive deferral needles → distinctive heading phrases.
- [nit][impl] trigger test docstring overpromised vs. implementation → reimplemented as block-split, heading-scoped per-entry trigger assertion + count check; docstring aligned.

Reconciliation note carried forward: the slice-closing primer compression (CLAUDE.md/AGENTS.md), glossary index term, and status-board regen are reconciliation-phase work, to be picked up in the sweep — not part of these three craft deliverables.
