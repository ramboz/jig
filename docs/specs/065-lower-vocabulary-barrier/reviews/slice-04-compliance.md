---
slice: 065-04 — Self-defining generation convention
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-07T19:58:09Z
prompt_source: review.py implementation
---

VERDICT: pass

All four ACs met. AC1: docs/workflow.md carries the "Self-defining vocabulary" section
with load-bearing phrasing (doc-presence test). AC2: the HTML-comment reminder is present
in the slice template and in both distributed workflow.py renderers (_render_stub_spec +
the _render_stub_slice inline fallback — the real function; AC2's "_render_starter_slice"
was a naming guess, intent met). AC3: the idempotent, non-clobbering managed-block helper
_ensure_self_defining_convention_block is wired into both scaffold() and copy_machinery(),
mirroring the ADR-0013 .gitignore floor, with tests for fresh-scaffold / append-preserving /
idempotent-no-op / single-block. AC4: no gate or lint added; soft/forward-only/no-gate
intent stated and tested. The dogfooded block matches _render_self_defining_block verbatim.
Deviation log records the AC3 redesign + the AC2 name correction. (Reviewer: jig:reviewer.)
