---
slice: 068-03 — reconcile-coverage-grounding
pass: arch
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-11T01:15:51Z
prompt_source: review.py arch-review (068-03)
---

VERDICT: pass

REASONING:
The boundary placement is sound and well-grounded. ADR-0025 §A4 (RESOLVED-by-probe) explicitly framed the choice as "a `workflow.py` helper, or a cross-spec extension of analyze" and falsified the reuse alternatives; placing the deterministic set-difference in `workflow.py` — where the read-only project-wide query family (`stale`/`routing-stats`/`amendment_digest`) already lives — and keeping `/jig:analyze` judgment-only is the correct application of that decision. The new `coverage()` function mirrors its siblings' contract exactly (signature `(project_dir: Path) -> str`, stdout-only dispatch, unconditional exit 0) and reuses slice 02's `_common/use_cases.py` API unchanged with zero duplicated resolution logic, preserving module boundaries. The third "unresolvable trace links" category is justified forward-shaping (honesty over silent data-loss), not scope creep.

SPECIFIC ISSUES:
- [strength] workflow.py — `coverage()` joins the read-only project-wide query family with a byte-for-byte-consistent contract: same `(project_dir: Path) -> str` shape as `stale`/`amendment_digest`, same `sys.stdout.write(...)` dispatch falling through to `return 0`. The public CLI grows by one cohesive sibling, not a new shape.
- [strength] workflow.py — genuine reuse of `_common/use_cases.py` (`parse_use_cases`/`resolve_use_cases`/`has_use_cases_section`) + `_common/parsing.parse_frontmatter`; resolution/set-difference logic is not re-implemented, so the deterministic core stays single-sourced in the module explicitly "shaped for that reuse".
- [strength] workflow.py — the always-exit-0 advisory contract is enforced at the dispatch branch and documented inline against ADR-0025 OQ3 / ADR-0011; the no-op-on-absent-`## Use cases` state is honored as load-bearing.
- [nit] workflow.py — `n_specs` re-globs `specs_dir.glob("*/spec.md")` a second time after the resolution loop. Cosmetic; a single `len(spec_paths)` over a materialized list avoids the double walk and the duplicated `is_dir()` guard.
- [nit] workflow.py — report renders bare `docs/specs/<name>` paths while the family/prompt favor `file:line`-grade locators; `docs/specs/<name>/spec.md` would be more actionable.

RECONCILIATION NOTES:
Two cosmetic nits for the deviation log rather than blocking REVIEWED: (1) `n_specs` double-globs — fold into one materialized iteration; (2) scope-creep/unresolvable rows emit `docs/specs/<name>` rather than `.../spec.md` — append `/spec.md` for a directly-openable path. The third report category exceeds the two AC1 directions but is sound forward-shaping consistent with ADR-0025 §A4's "reported, never raised" stance — record it as a deliberate subordinate honesty category.
