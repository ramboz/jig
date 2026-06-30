---
slice: 084-01 — `_common/project_layout.py` layout helper + validation
pass: craft
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T04:24:19Z
prompt_source: review.py pr-review (084-01); jig:reviewer subagent
---

VERDICT: pass

Craft pass on slice 084-01. Tightly scoped to the foundation-only mandate (pure
leaf helper + tests, no call-site rewiring). Mirrors `scaffold_state.py`'s
leaf-import discipline, sentinel constant, and docstring density faithfully.
Validation/discovery logic correct. Tests are meaningful and well-structured.
No blockers.

Strengths:
- `project_root_for` cleanly realizes the "one sentinel-walk + N preserved legacy
  fallbacks" framing: sentinel branch uses the resolved path, `fallback` receives
  the original un-resolved `path`, exceptions propagate; documented + pinned by
  tests.
- `test_nested_subproject_wins_over_ancestor` asserts the legacy `parents[3]` trap
  actually fires BEFORE proving the sentinel walk overrides it — regression-proof.
- `LayoutError(ValueError)` with inline rationale + subclass assertion is a clean
  error-type choice.

Nits (non-blocking):
- [FIXED in reconciliation] `__import__("shutil")` inline-cleanup inconsistency
  across test classes → standardized to module-level `import shutil` +
  `addCleanup(shutil.rmtree, …)`.
- [DEFERRED] `typing.Callable` vs `collections.abc.Callable` — `typing.Callable`
  is correct on the 3.9 floor and not deprecated until well after; revisit when
  3.9 is dropped.

Downstream note for 084-02/03: the `project_root_for` resolve-vs-original
asymmetry is an intentional contract — call-site rewiring must preserve it.
