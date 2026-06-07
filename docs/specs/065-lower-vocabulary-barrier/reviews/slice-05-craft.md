---
slice: 065-05 — `/jig:explain` passage mode (explain a pasted snippet)
pass: craft
verdict: pass
reviewer: jig:reviewer / pr-review
reviewed_at: 2026-06-07T19:19:35Z
prompt_source: review.py pr-review
---

VERDICT: pass

The SKILL.md cleanly extends the two-mode skill to three with a single, internally
consistent precedence rule restated identically in the description, the Inputs section,
and the Gotchas (no drift). The two honesty carve-outs trace back to the clarify answers.
The 12 new surface assertions target real load-bearing prose, not incidental wording, and
the prose stays at the junior register it targets.

[strength] mode-precedence section: one-line rule + numbered cases + carve-outs "on top of"
the order; restated verbatim in three places without drift — exactly what an input-contract
change needs.
[strength] Q2 no-jig-vocab handling disarms the obvious objection inline ("doesn't conflict
with the deferral clause").
[nit, addressed] test_term_honesty_carveout's `"not"` conjunct was dead weight — replaced
with a pin on the distinctive negation phrase.
[nit, addressed] test-module docstring was still scoped to 065-03 — updated to cover 065-05.
(Reviewer: jig:reviewer / pr-review, read-only.)
