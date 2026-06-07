---
slice: 065-05 — `/jig:explain` passage mode (explain a pasted snippet)
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-07T19:19:35Z
prompt_source: review.py implementation
---

VERDICT: pass

All six ACs are met at the documented SKILL.md surface and exercised by meaningful
structural tests. Passage mode is declared as the third mode; the explicit precedence
order (path→artifact / key→term / else→passage) and both carve-outs (term-mode honesty;
path-shaped-but-unresolvable → ask, clarify Q1) are documented; no-jig-vocab→generic (Q2),
no-hard-cap (Q4), and artifact-like-paste→nudge (Q3) are all present; provenance is
best-effort/never-fabricated; the never-invent line extends to passage tokens; no
explain.py added and the ephemeral contract holds; the two prior modes survive intact.
Judgment-only; the plain-language-quality gap is the accepted documented shape.

Nit (addressed in reconciliation): test_no_silent_dead_end pins a literal absent string;
reviewer (reading the already-edited file) judged it vacuous, but the string DID exist in
065-03's SKILL.md and was removed here. Strengthened with a positive assertion to remove
the ambiguity. Deviation log was _TODO_ at review time; now filled. (Reviewer:
jig:reviewer, read-only.)
