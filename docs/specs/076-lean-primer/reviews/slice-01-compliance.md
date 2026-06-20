---
slice: 076-01 — relocate + compress the Hot Cache
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-20T14:09:45Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
Slice 076-01 is fully and faithfully implemented. CLAUDE.md is compressed to the index shape (66 lines, ~9.3KB — well under the ≤70-line / ≤14336-byte cap), dense ADR-prose bodies are relocated to docs/memory/glossary.md as single-paragraph H2 entries that all resolve through skills/_common/lexicon.py's merged loader, and every known behavioral guard is pinned inline as its full directive. The test suite is genuinely meaningful — it exercises loader resolution (not mere string presence), guards against silent first-paragraph truncation, asserts index-term-equals-lexicon-key, requires canonical links for recoverability, and enforces both line and byte budgets. No design-principle violations (the change directly advances principle 2 "dumb zone" and principle 4 "dogfood"); no regressions in dependent tests.

SPECIFIC ISSUES:
- None blocking. (Minor, suppressed-Low: scripts/test_lean_primer.py import placement — addressed post-review: `import re` moved to the stdlib import group.)

VERIFICATION NOTES:
- All 13 RELOCATED_TERMS resolve: each has a `## Term` H2 in glossary.md whose normalized key matches the bold index term in CLAUDE.md; each is a single paragraph carrying at least one markdown link.
- All 10 KEEP_INLINE_MARKERS verified present in CLAUDE.md as full directives.
- Budget: 66 lines / ~9.3KB — both caps satisfied.
- skills/explain/test_explain_skill_surface.py ClaudeMdRowTests correctly migrated from a table-row assertion to a /jig:explain-discoverable assertion (post-076), honestly documented. No other test asserts on the removed root-CLAUDE.md skills table.

RECONCILIATION NOTES:
- Budget anchor deviates from the DRAFT spec's AGENTS.md-parity calibration (AGENTS.md does not exist on this branch; ships with spec 033-02 on v2). Already documented in spec.md frame correction + slice DoR — confirm in deviation log.
- AC #2 reframed from "no information is lost" to two-hop recoverability (key-resolvability + canonical-link) per frame-critique. Record in deviation log.
- Deviation log + spec-056 before/after token-delta evidence to be captured during reconciliation.
