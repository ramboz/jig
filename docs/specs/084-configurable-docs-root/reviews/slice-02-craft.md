---
slice: 084-02 — Route read/write helpers through the layout helper
pass: craft
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T05:00:29Z
prompt_source: review.py craft (084-02); jig:reviewer subagent
---

VERDICT: pass

The rewiring idiom is consistent across modules: named helpers for well-known
artifacts, docs_base() for long-tail ones, with a uniform sys.path bootstrap +
`from _common import project_layout` matching the pre-existing repo pattern. The
two discovery sites funnel cleanly through one project_root_for(path, *, fallback)
resolver; the guard tests assert behavior (subproject-vs-enclosing-repo
resolution, collapsed write paths), not code paths.

Strengths:
- project_root_for absorbs both legacy discovery shapes behind one sentinel-first
  contract; fallback receives the original un-resolved path, documented.
- The cross-project-bleed guard asserts the legacy parents[3] trap fires BEFORE
  proving the sentinel walk overrides it.

Addressed in reconciliation:
- [FIXED] lexicon._memory_dir (the forced stdlib-only duplication) had no
  behavioral test — only the AST literal guard, which cannot catch wrong-root
  logic. Added test_lexicon_overlay_honors_dot_root (docs_root="." → glossary
  overlay resolves to <project>/memory/glossary.md).

Deferred (logged, not blockers):
- review._find_project_root uses an os.devnull marker to preserve its
  Optional[Path] return through project_root_for. Cleaner would be widening
  project_root_for's fallback to `Path | None` — but that ripples into 084-01's
  DONE resolver + the workflow callers that consume a non-Optional Path. Deferred.
- The AST allowlist `_is_allowed` is a source-text substring match; anchoring on
  ast.Name id == "wt" would be more robust. Low risk given the explicit module set.
