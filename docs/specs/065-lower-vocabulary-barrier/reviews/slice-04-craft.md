---
slice: 065-04 — Self-defining generation convention
pass: craft
verdict: pass
reviewer: jig:reviewer / pr-review
reviewed_at: 2026-06-07T19:58:09Z
prompt_source: review.py pr-review
---

VERDICT: pass

_ensure_self_defining_convention_block is a faithful, well-commented mirror of
_write_gitignore_secret_block (marker-find / end-marker / trailing-newline-trim /
three-case separator are line-for-line equivalent; the only divergence — mkdir(parents) +
"# Workflow" header — is justified for the docs path). No block-text drift: jig dogfoods
the managed block itself (single source of truth in _render_self_defining_block), and a
byte-identity cross-check guards it. Call sites correctly wired + mutually exclusive
(copy_machinery vs the --plugin-only else branch). Tests assert load-bearing behavior
(append-preserves-content, idempotent no-op, single block), not brittle substrings.

[strength] faithful mirror of the audited managed-block helper; half-block fall-through preserved.
[strength] dogfood = the managed block itself, eliminating drift; byte-identity guard added.
[nit, addressed] the inline-fallback test was a source-grep; rewritten to exercise the real
OSError branch. (Reviewer: jig:reviewer / pr-review.)
