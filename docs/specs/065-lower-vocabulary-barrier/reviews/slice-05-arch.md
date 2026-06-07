---
slice: 065-05 — `/jig:explain` passage mode (explain a pasted snippet)
pass: arch
verdict: pass
reviewer: jig:reviewer / arch-review
reviewed_at: 2026-06-07T19:19:36Z
prompt_source: review.py arch-review
---

VERDICT: pass

The mode-precedence contract (path→artifact / key→term / else→passage) plus the two
carve-outs is sound, and the term-mode honesty carve-out prevents the failure the slice
flags as load-bearing: an unknown short query routes to term mode and gets its honest
"absent" flag rather than being absorbed into a confident passage guess. The new mode is
purely additive — it replaces an existing dead-end branch, touches no other module, adds no
.py, and the ephemeral/off-hot-path contract is preserved verbatim from 065-03 (055/057
holds). The Q2 generic-explainer expansion is bounded by an explicit non-conflict clause
with the deferral rule (handles absence of jig content, not presence of a richer skill).

[strength] carve-outs sit explicitly "on top of" the resolution order — the honest-absent
signal is a stated invariant the greedy else→passage branch must not erode.
[strength] large-paste→artifact-mode nudge keeps passage mode from silently becoming a
degraded substitute for artifact mode (which resolves linked refs).
[nit, addressed] term-honesty carve-out was bounded to "one- or two-word" — but lexicon keys
can be 3+ words; reworded to distinguish by shape (single-line query vs multi-line paste),
not word count.
[nit, addressed] path heuristic treated a bare `/` as path-shaped (over-triggers on
commands/URLs); narrowed to repo-doc path shape, bare `/` is now a passage.
Accepted trade-offs (named in deviation log): both heuristics are best-effort, consistent
with the judgment-skill framing. (Reviewer: jig:reviewer / arch-review, read-only.)
