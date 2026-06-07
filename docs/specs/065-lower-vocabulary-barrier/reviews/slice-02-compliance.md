---
slice: 065-02 — Hook surfaces lexicon definitions
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-07T16:12:16Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All five ACs met by jig-memory-scan.sh and meaningfully exercised by test_hooks.py (28/28 green). Lexicon path isolated in its own try/except (AC5 fail-open), reads via _common/lexicon.py (AC4), matches on word/phrase boundaries (AC1), caps at 5 in first-appearance order (AC3), composes additively with the unchanged unknown-reference surfacing (AC2). The scrutinized deviation — loosening test_silent_on_known_terms_in_glossary — is a correct, necessary consequence of AC4 (a project glossary term now surfaces an overlay def), not a masked regression: the new assertion still guards that glossary terms are never flagged as unknown.

SPECIFIC ISSUES:
- skills/memory-sync/test_hooks.py:112 — the loosened assertion is wrapped in `if out is not None:`, so it would pass vacuously if a future regression silenced BOTH the lexicon and unknown paths. Low/Medium. Assert `out is not None` (the lexicon def is now expected) before the assertNotIn. Not a blocker — MemoryScanLexiconTests cover the positive path.

RECONCILIATION NOTES:
- Record the pre-existing-test modification + rationale in the deviation log.
- Fill the slice's `_TODO._` deviation log before RECONCILED.
- Consider applying the test_hooks.py:112 robustness fix.
