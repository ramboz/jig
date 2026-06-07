---
slice: 065-02 — Hook surfaces lexicon definitions
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-07T16:12:16Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
The lexicon-surfacing extension is cleanly isolated in its own try/except inside the existing outer one (double fail-open, AC5); the word-boundary regex (?<![\w-])...(?![\w-]) correctly prevents substring + hyphen-glued false matches (exercised by test_no_substring_match); JSON stays well-formed via a single json.dumps; the embedded Python reads clearly. Tests meaningfully exercise cap, ordering, composition, and a genuinely-broken lexicon (real failure injection). No blockers.

SPECIFIC ISSUES:
- [strength] jig-memory-scan.sh:72-103 — lexicon block nested in its own + the outer try/except; degrades to unknown-only rather than killing the hook.
- [strength] jig-memory-scan.sh:86 — (?<![\w-])/(?![\w-]) boundaries + re.escape keep substring/hyphen/multi-word matches safe.
- [strength] test_hooks.py:240-274 — cap test asserts exactly 5 + 7th dropped (order); fail-open test injects a real raising lexicon.py.
- [nit] jig-memory-scan.sh:84-92 — one re.search per lexicon term, O(terms). Negligible at current size; revisit only if the lexicon grows large.
- [nit] jig-memory-scan.sh:73-76 — JIG_LEXICON_COMMON_DIR is a clean, narrow test/override seam (mirrors the jig-context-check.sh SCRIPT_DIR idiom), not test-concern leakage.

RECONCILIATION NOTES:
Both nits non-blocking, no code change required. Worth a deviation-log line: per-term regex scan is O(terms) (acceptable now); JIG_LEXICON_COMMON_DIR is a deliberate clean seam.
