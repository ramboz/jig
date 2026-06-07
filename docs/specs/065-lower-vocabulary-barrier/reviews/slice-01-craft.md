---
slice: 065-01 — Lexicon foundation (shipped data + overlay loader)
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-07T15:52:40Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
Loader is small, idiomatic, stdlib-only, consistently fail-soft per the stated contract; single-purpose functions with docstrings explaining the non-obvious choices. Tests are behavior-named, tmpdir-isolated, cover positive/negative (H3-ignored, second-paragraph-dropped)/fail-soft/hook-subprocess/machinery-copy paths. One real craft observation: encoding-handling asymmetry between load_shipped() and load().

SPECIFIC ISSUES:
- [nit] skills/_common/lexicon.py:62 — load_shipped() uses read_text() (no errors=) while load() uses errors="replace". A non-UTF-8 shipped file raises UnicodeDecodeError, which is NOT OSError/ValueError and escapes the fail-soft clause. Theoretical (committed asset), but widens the "never raises" contract.
- [nit] skills/_common/lexicon.py:131 — merged.update(overlay) is a whole-entry replace, dropping shipped example/see_also on an overridden term. Intentional + tested; worth a one-line note so a future reader doesn't expect a field-level merge.
- [strength] __file__-relative path resolution; negative-path tests; real-copy machinery test.

RECONCILIATION NOTES:
Both nits non-blocking polish for the deviation log: consider catching UnicodeDecodeError in load_shipped() for symmetry; document that overlay is a whole-entry replace.
