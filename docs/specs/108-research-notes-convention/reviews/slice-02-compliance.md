---
slice: 108-02 — codify in conventions.md + register deferred machinery
pass: compliance
verdict: pass
reviewer: jig:reviewer (fresh-context, Opus)
reviewed_at: 2026-08-11T19:13:15Z
prompt_source: review.py implementation docs/specs/108-research-notes-convention/spec.md 108-02 <deliverables>
---

Compliance review of slice 108-02 (codify in conventions.md + register deferred machinery). Fresh-context read-only `jig:reviewer` (Opus). Prompt built by `review.py implementation`.

## Verdict: pass (after one needs-changes round)

Content ACs met on first read: `conventions.md` research-notes rule (home, phase distinction, both hand-offs, local-and-cheap non-reserved numbering, ADR-0054 link); `refinement-todo.md` registers all five deferrals with demand-gated resolution triggers; ADR-0054 open questions dispositioned.

## Findings (addressed → re-verdict pass)
- [needs-changes] Three 108-02 test assertions were vacuous (matched substrings pre-existing in the target files, so they'd pass even if the feature were deleted): `test_conventions_states_phase_distinction` (bare "refinement-todo"); `test_five_deferrals_present` needles (`link`/`collision`/`scaffold-init`); the global "Resolution trigger" check. FIXED: rule-unique phrase assertion; distinctive heading phrases; block-scoped per-entry trigger check + `assertEqual(matched, 5)`. Re-verified non-vacuous; 24 tests green.
