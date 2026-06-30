---
slice: 084-02 — Route read/write helpers through the layout helper
pass: compliance
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T05:00:29Z
prompt_source: review.py compliance (084-02); jig:reviewer subagent
---

VERDICT: pass

All eight ACs satisfied. Construction across the nine rewired modules routes
through project_layout (specs_dir/decisions_dir/docs_base/memory_dir/
refinement_todo_path); both discovery categories — the marker up-walk
(review._find_project_root) and the depth-arithmetic family
(workflow._project_root_for_spec, feeding transition / slice-claim /
DONE-dependency) — resolve through the sentinel-anchored project_root_for. The
no-stray-literal AST guard's allowlist is honest: a tree sweep confirms every
surviving `X / "docs"` join in the rewired set is a templates/ source path or a
`wt / "docs"` push-mode reconstruction (refused in subtree by 084-03); no
non-allowlisted post-sentinel `docs/` join. Excluded surfaces (migrate.py
pre-sentinel; lexicon._memory_dir stdlib-only mirror) are sound. The AC2/AC3
"not directly tested" caveat is acceptable: reserve_spec (workflow.py:2978) and
reserve_adr (adr.py:672) resolve their dirs via project_layout, and that
layout-sensitive resolution is unit-tested via pl.specs_dir.

Known limitations (logged, non-defects):
- The AST guard is BinOp+textual-allowlist based, not a true literal-absence
  proof; a single-Constant `Path("docs/...")` join (decisions.py _LIGHTWEIGHT_REL,
  display-only — real path via project_layout.decisions_dir) is invisible to it.
  Recorded as a guard-scope limitation for any future "is the docs literal gone"
  audit.
- (Reviewer noted bug.py missing from the guard's REWIRED set; on re-check bug.py
  IS present in the list — no action.)
