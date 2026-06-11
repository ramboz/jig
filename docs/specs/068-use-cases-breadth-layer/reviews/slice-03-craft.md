---
slice: 068-03 — reconcile-coverage-grounding
pass: craft
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-11T01:15:51Z
prompt_source: review.py pr-review (068-03)
---

VERDICT: pass

REASONING:
A tight, read-only advisory addition that mirrors the existing query-family idiom (stale / routing_stats / amendment_digest) faithfully: `--project-dir`, stdout-only, always exits 0, same bare-annotation and comment-banner style. It reuses slice 02's `parse_use_cases` / `resolve_use_cases` rather than re-scanning prose (AC2), handles the absent-vision, no-section no-op, and clean cases explicitly, and the 11 tests exercise every direction plus the honesty edge (unresolvable ≠ scope-creep). The 4 suite errors are a pre-existing `ModuleNotFoundError: No module named 'skills'` env artifact in `NewSpecScaffoldsFilePerSliceTests` (runner-only), unrelated to this slice. Only minor nits below.

SPECIFIC ISSUES:
- [nit] skills/spec-workflow/workflow.py — specs globbed twice (resolution loop + `n_specs` count). Bind `materialized = sorted(specs_dir.glob("*/spec.md"))` once, then `n_specs = len(materialized)`; closer to how `amendment_digest` collects its candidate list once.
- [nit] skills/spec-workflow/workflow.py — `resolve_use_cases(cited, vision_text)` re-parses the whole vision per spec, though `vision_ucs` is already parsed. Wasted work at O(specs); not worth touching slice 02's raw-text API for a reconcile-time advisory at jig's scale — leave it, but note it.
- [nit] skills/spec-workflow/workflow.py — `is_dir()` guard on `n_specs` is asymmetric with the unguarded loop glob; harmless (glob on missing dir yields nothing). Drop it or guard both.
- [nit] skills/spec-workflow/test_workflow.py — two tests reconstruct section boundaries by string-slicing on lowercased heading substrings; couples assertions to heading prose/ordering and a reworded heading could let `assertNotIn` pass vacuously. Structural split on `## ` headings would be more robust. Low priority — behavior correctly pinned today.
- [nit] skills/spec-workflow/test_workflow.py — `import shutil` inside `tearDown` rather than module top.
- [strength] skills/spec-workflow/workflow.py — the block comment is load-bearing: pins *why* this lives in workflow.py not /jig:analyze, names the no-op invariant as load-bearing, ties behaviors to AC/ADR.
- [strength] skills/spec-workflow/test_workflow.py — `test_unresolvable_spec_not_also_scope_creep` and `test_scope_creep_from_metadata_not_prose` pin the two easiest-to-get-wrong distinctions rather than the happy path.
- [strength] skills/spec-workflow/workflow.py — surfacing unresolvable/dangling links as a distinct, subordinate third category instead of silently dropping `result.unresolvable` is the right honesty call.

RECONCILIATION NOTES:
No blockers. The double-glob and the per-spec vision re-parse are the two findings worth a deviation-log line as known, accepted micro-redundancies (negligible at jig's scale; fixing the re-parse cleanly would touch slice 02's raw-text API). The asymmetric `is_dir()` guard, test section-slicing brittleness, and in-method `import shutil` are cosmetic. The 4 `ModuleNotFoundError` suite errors are a pre-existing env/import-path artifact in `NewSpecScaffoldsFilePerSliceTests`, not introduced here.
