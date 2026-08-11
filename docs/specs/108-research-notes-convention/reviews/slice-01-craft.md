---
slice: 108-01 — living research-note home: template, index, hand-offs
pass: craft
verdict: pass
reviewer: jig:reviewer (fresh-context, Opus)
reviewed_at: 2026-08-11T18:55:24Z
prompt_source: review.py pr-review docs/specs/108-research-notes-convention/spec.md 108-01 <deliverables> --richer-skill none
substrate: non-interactive
---

Craft (pr-review) review of slice 108-01. Fresh-context read-only `jig:reviewer` (Opus). Prompt built by `review.py pr-review --richer-skill none` (jig baseline; docs slice — no code-review skill warranted).

## Verdict: pass

Coherent, well-scoped, internally consistent; correct relative links; test file follows `scripts/test_*.py` discovery convention with AC-tagged, non-vacuous assertions.

## Strengths
- [strength][impl] README's "sequential with, not a competitor to" refinement-todo framing + local-and-cheap numbering rationale make the convention self-explaining without a helper.
- [strength][impl] Frontmatter-key/status-option checks use `subTest` per item for precise failures.

## Nits (all addressed pre-REVIEWED)
- [nit][impl] `test_documents_inbox_to_note_handoff` only effectively checked the word "inbox". FIXED: now asserts the specific "inbox → note" hand-off label + the one-line R-NNN pointer regex.
- [nit][impl] `SeedCorpusIntact` "byte-unchanged" docstring over-claim (same as compliance). FIXED.
- [nit][impl] leak guard checked one hard-coded path. FIXED: added a content-signature + name scan across all of `templates/` (`test_no_research_note_template_leaks_anywhere_under_templates`).

Test count 18 → 19, all green, ruff clean after the strengthenings.
