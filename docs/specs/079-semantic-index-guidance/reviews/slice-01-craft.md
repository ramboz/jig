---
slice: 079-01 — workflow.md index guidance
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-20T15:38:01Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
The prose is clear, accurate, and faithfully matches the voice and four-part structure of its sibling subsections (bold lead claim, when/which/detect/limits). It correctly positions the index as the turn-count lever complementary to the existing per-turn levers, grounds claims in cited specs/EngTips, and is honest about index output being context too. Scope is tight and docs-only as the slice requires.

SPECIFIC ISSUES:
- [nit] scripts/test_semantic_index_guidance.py — (ADDRESSED post-review) `"ide"` was a bare substring matching "guide"/"provide"/etc.; replaced with the distinctive `"lsp"` and the whole assertion scoped to the subsection.
- [nit] scripts/test_semantic_index_guidance.py — (ADDRESSED post-review) `test_states_the_when` searched the whole file for "turn"+"grep"; now scoped to the new subsection via a `_subsection()` helper, so it genuinely pins the new paragraph.
- [strength] docs/workflow.md — the lead framing ("levers above cut the cost per turn; a semantic/code index cuts the number of turns … only attack the per-turn side of the product") integrates cleanly with the cost ≈ context × turns model and earns its placement.
- [strength] docs/workflow.md — the "Honest about limits" paragraph genuinely engages the counter-case (index output is itself re-read context; stale index can mislead) rather than paying lip service.
- [strength] docs/workflow.md — portable/public options centered with Adobe-internal tools demoted to "if available", matching the public-shipping constraint precisely.

RECONCILIATION NOTES:
Both test-craft nits addressed post-review; suite stays green. No scope creep; docs-only as required; nothing added to CLAUDE.md.
