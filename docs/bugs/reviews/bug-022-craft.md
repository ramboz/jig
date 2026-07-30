---
bug: 022
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (round 2)
reviewed_at: 2026-07-30T21:11:12Z
prompt_source: pr-review skill craft pass
---

Round 2 (after revision) — VERDICT: pass.

All five round-1 items genuinely resolved:

1. BLOCKER cleared — the `_project_docs_root` docstring
   (`skills/migrate/migrate.py:1901-1919`) now names both consumers (LOOK vs
   WRITE) and states the bounded-but-not-free consequence of the
   `except Exception: return "docs"` fallback. The "bounded" claim was verified
   against `skills/_common/project_layout.py:95-108` — `_validate_docs_root`
   rejects absolute and `..`-escaping roots and `docs_root()` routes through it
   — so the docstring is accurate, not merely plausible.
2. Call-site comment trimmed to four lines; `façade` and em-dash now match
   module idiom.
3. `test_nested_docs_root_is_honoured` now asserts the real invariant
   unconditionally (`assertFalse(... .exists())`), so it cannot degrade to a
   trivial pass if the marker constant drifts.
4. `_seed` returns `(project, workflow)`; the `.parents[N]` depth arithmetic is
   gone from all call sites.
5. The malformed-`scaffold.json` degrade path is now pinned.

Three migrate.py copies are byte-identical in both changed regions; no
drive-by edits; new tests reuse imports already present.

Nits raised in this round and since addressed: the call-site comment said the
sibling scan was "above" (its definition is, but it runs below at :2110) —
reworded to drop the directional claim; and
`test_malformed_layout_degrades_instead_of_failing_the_copy` asserted only
`returncode == 0` — it now also asserts the degrade outcome
(`docs/workflow.md` exists), so a copy that exited 0 while writing no blocks
would fail it.

Noted as deliberate: the docstring reproduces the record's bounded/not-free
reasoning nearly verbatim. It is contract-bearing and belongs in the code,
but it sits at the upper edge of proportionate — duplication by intent, not
drift.
