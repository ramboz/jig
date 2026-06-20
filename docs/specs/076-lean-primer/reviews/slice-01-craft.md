---
slice: 076-01 — relocate + compress the Hot Cache
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-20T14:09:45Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
The slice delivers a genuinely lean primer (66 lines, well under the 70-line / 14KB cap) with definitional prose relocated to the glossary and the complete known-guard set preserved inline. The test design is unusually thoughtful: it pins not just the happy path but several latent-bug classes (single-paragraph loader truncation, index-term-equals-resolvable-key drift, full-directive markers rather than weak words). Every KEEP_INLINE_MARKER and RELOCATED_PROSE_FRAGMENT verified against actual content — all hold. Only minor craft nits, none blocking REVIEWED.

SPECIFIC ISSUES:
- [strength] scripts/test_lean_primer.py — test_relocated_entries_are_single_paragraph guards a real latent bug: lexicon._first_paragraph recovers only the first paragraph, so a multi-paragraph glossary entry would silently truncate under /jig:explain while the resolvability test still passes.
- [strength] scripts/test_lean_primer.py — test_index_display_term_equals_resolvable_key ties the hand-maintained RELOCATED_TERMS list to the real bold index in CLAUDE.md, so the test can't rot into asserting against terms no longer in the primer.
- [strength] scripts/test_lean_primer.py — keep-inline markers are the full directive ("MERGING main→v2 (not rebase)", not bare "v2"), so relocating a guard while leaving a stray keyword fails CI.
- [nit] scripts/test_lean_primer.py — import placement off-pattern (ADDRESSED post-review: `import re` moved to stdlib group).
- [nit] scripts/test_lean_primer.py — RELOCATED_PROSE_FRAGMENTS sampling was implicit (ADDRESSED post-review: comment added noting representative-sample scope).
- [nit] scripts/test_lean_primer.py — _glossary_sections duplicates the H2-walk loop in lexicon._parse_glossary_overlay; reviewer judged extraction not clearly worth it (test needs the raw body, not first-paragraph-only). Left as-is.

RECONCILIATION NOTES:
- AC #1 per-entry classification (guard vs definitional) must be recorded in the deviation log, plus the before/after token/byte delta as proof the change paid off.
- skills/explain/test_explain_skill_surface.py ClaudeMdRowTests was relaxed (not deleted) from a 065-era table-row assertion to a discoverability assertion as a consequence of removing the Skills table — note the lineage in the deviation log.
- Import-placement + sampling-comment nits addressed post-review; suite stays green (9/9), ruff clean.
