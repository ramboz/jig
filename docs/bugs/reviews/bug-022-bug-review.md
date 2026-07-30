---
bug: 022
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent (round 2)
reviewed_at: 2026-07-30T21:10:56Z
prompt_source: review.py bug-review
---

Round 2 (after revision) — VERDICT: pass.

All four round-1 findings resolved, not reworded:

1. `_project_docs_root`'s docstring (`skills/migrate/migrate.py:1902-1919`) now
   names both consumers (LOOK vs WRITE) and states the write-side consequence
   of the `"docs"` fallback on a `docs_root: "."` project with a malformed
   config. Byte-identical in both mirrors.
2. Mirror parity confirmed: docstring and call site line up at identical line
   numbers across all three copies of migrate.py.
3. The record's characterisation of `_validated_docs_root` is now accurate
   against `migrate.py:199-210` — it validates a raw string via
   `project_layout.validate_docs_root` and never reads scaffold.json, so it was
   never a candidate resolver.
4. `test_malformed_layout_degrades_instead_of_failing_the_copy` discriminates
   rather than passing vacuously: `{"docs_root": ["not","a","string"]}` raises
   `LayoutError` in `project_layout._read_raw_docs_root`, exactly the exception
   `_project_docs_root` swallows; a raising resolver surfaces as exit 2/1.

Fix stays within `local_patch` scope (one forwarded kwarg). The Codex
early-return limit was independently verified real
(`scaffold.py:2253-2257`; the only `_ensure_*_block` calls are at 2274/2278)
and is honestly scoped out.

Residual nits raised and addressed after this verdict: pre-fix line
coordinates in Symptom/Evidence/Hypotheses are now explicitly marked "as
found"; the Codex-host follow-up has been filed in `docs/inbox.md` rather than
left dangling.

Noted, not actioned (pre-existing, outside this fix's class):
`scaffold.copy_machinery`'s own docstring documents `installed_tiers` and
`host` but never `docs_root` — the very "invisible call site" this bug's
Learning names.
