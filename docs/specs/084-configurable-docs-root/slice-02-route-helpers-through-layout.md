---
status: DONE
dependencies: [084-01]
last_verified: 2026-06-30
frame_review: false  # mechanical rewiring behind the 084-01 contract; no new premise.
arch_review: true  # crosses module boundaries across ~9 skills — arch pass required.
---

## Slice 084-02 — Route read/write helpers through the layout helper

**Goal:** Replace hardcoded `project_dir / "docs" / …` in the jig helpers with
`project_layout` calls, AND switch project-root *discovery* from the `docs/`
probe to the sentinel, so a scaffolded project with `layout.docs_root="."` reads
and writes artifacts directly under the project root and never resolves its root
into an enclosing repo. Default layout behavior is unchanged. Two guard tests
prevent regressions: a no-stray-`"docs"`-literal guard (split-brain placement)
and a cross-project-bleed guard (discovery climbing past the sentinel).

**DoR:**
- ✅ 084-01 landed: `project_layout` contract proven in isolation.
- ✅ Call-site inventory grounded (replace `project_dir / "docs" / …`) —
  re-verified complete by an independent authorship review (greps the tree):
  `spec-workflow/workflow.py` (specs dir, status-board README, `new`,
  amendment-artifact scan), `adr-workflow/adr.py` (decisions dir, `new`,
  `index`), `independent-review/review.py`, `bug-fix/bug.py`,
  `memory-sync/decisions.py` (`lightweight-decisions.md`, ~line 43),
  **`memory-sync/memory.py`** (FIVE post-sentinel artifact paths:
  `docs/memory/glossary.md` ~202/503, `docs/memory/learnings.md` ~208,
  `docs/inbox.md` ~214, `docs/refinement-todo.md` ~221),
  **`_common/team_signal.py`** (`people_md_path` → `docs/memory/people.md` ~122),
  **`scaffold-init/stocktake.py`** (`docs/specs` ~38, `docs/refinement-todo.md`
  ~57 — reads on an *already-scaffolded* project, post-sentinel),
  `migrate/migrate.py`, `_common/lexicon.py`, `_common/review_evidence.py`
  (bug-evidence path). **Excluded by design (pre-sentinel — MUST keep the
  literal `docs/` probe, ADR-0033 §5):** `scaffold_state.looks_spec_driven`, the
  `scaffold.py` detection block (~276-289), and the tuned migrate/scaffold
  detectors. **Also out of scope (NOT artifact-root constructions):** `__file__`-
  based plugin-root resolution in `adr.py`/`bug.py`/`migrate.py` (`parents[N]`
  off `__file__`, not a project root).
- ✅ Discovery-site inventory grounded — **two** structure-derived categories,
  both routed through `project_layout.project_root_for` (ADR-0033 §5a); the
  construction-literal guard covers neither:
  - **Marker up-walk:** `independent-review/review.py` `_find_project_root`
    (climbs for `docs/architecture.md`).
  - **Depth arithmetic** (frame-critique round 1): `spec-workflow/workflow.py`
    `_project_root_for_spec` (line ~992) and the bare `parents[3]` at
    `_record_spec_ref` (line ~981) and the DONE-dependency check (line ~1149) —
    all assume `docs/specs/<dir>/spec.md` depth and silently climb into the
    enclosing repo under `"."`. These feed transition / slice-claim (`claimed_by`)
    / DONE-dependency / `.jig/spec-ref`. Sweep for any other `parents[N]`
    root-derivation.
- ✅ Anchoring gap acknowledged: this slice rewires path construction +
  discovery only; git anchoring (dirty-check / branch-routing / commit against
  the enclosing repo) is unchanged for all modes (084 spec) — 084-03 owns the
  push-mode loud refusal + the local-mode caveat.
- ✅ Threading model pinned: helpers resolve paths by calling `project_layout`
  with the `project_dir` they already hold (it reads `scaffold.json` per call) —
  NO new `docs_root` parameter is threaded through call signatures. The one
  non-obvious site is the on-main / local reservation in `new`, which rebuilds
  the specs dir inside the working tree; it uses `project_layout.specs_dir`. The
  **detached-worktree** reconstruction (`wt / "docs" / "specs"`,
  workflow.py ~2852/2855) is push-mode → **refused** in a subtree by 084-03, so
  it is NOT made layout-aware here (default-layout push is unchanged; it keeps
  `docs/specs`).

**Acceptance Criteria:**

1. **`status-board` honors `docs_root="."`.** `workflow.py status-board
   <project-dir>` reads/writes `<project-dir>/specs/README.md` when
   `docs_root="."`, and `<project-dir>/docs/specs/README.md` by default.
2. **`new` honors `docs_root="."`.** `workflow.py new <slug>` (local mode)
   creates `<project-dir>/specs/NNN-<slug>/…` when `docs_root="."`, default path
   otherwise. Number scan reads the configured specs dir.
3. **`adr new` honors `docs_root="."`.** `adr.py new <slug>` creates
   `<project-dir>/decisions/adr-NNNN-<slug>.md` when `docs_root="."`.
4. **`adr index` works for both layouts.** `adr.py index` enumerates the
   configured decisions dir under both default and `"."`.
5. **scaffold-state round-trip.** A project carrying `scaffold.json` with
   `layout.docs_root="."` classifies as `scaffolded` (sentinel-first, unchanged)
   AND every rewired helper thereafter uses the configured paths — no helper
   silently falls back to `docs/`.
6. **No-stray-literal guard (scope + allowlist pinned).** A test scans an
   **explicit module set** — exactly the rewired construction-inventory modules
   above — via **AST** (a `Str`/`Constant` node equal to `"docs"` used in a
   path-join, not a raw regex) and asserts none remains. The **allowlist** (sites
   that legitimately keep a `"docs"` literal) is enumerated inline: the
   pre-sentinel detectors (`scaffold_state.looks_spec_driven`, `scaffold.py`
   detection block, tuned migrate/scaffold detectors), `templates/docs/…` scaffold
   *source* paths, and the scaffold-init write paths owned by slice 084-03. The
   guard does NOT scan all of `skills/` (that would false-positive on 084-03's
   write paths and template emitters). Prevents split-brain regressions.
7. **Sentinel-anchored discovery + no cross-project bleed (both categories).**
   Every discovery site — the `_find_project_root` marker up-walk AND the
   `_project_root_for_spec` / `parents[3]` depth-arithmetic family — resolves the
   root via `project_root_for` (sentinel). Guard exercises BOTH: (a) given a
   subproject (`scaffold.json` at its root) nested under an ancestor that has
   `docs/architecture.md`, `_find_project_root` returns the subproject; (b) given
   a real spec at `<subproject>/specs/<dir>/spec.md` with the sentinel at
   `<subproject>` and a `.git` at the enclosing ancestor, a `transition` /
   slice-claim / DONE-dependency op resolves `claimed_by` + dep validation
   against `<subproject>`, never the ancestor. Default-layout discovery
   (parents[3] result) is unchanged.
8. **Default layout unchanged.** Full existing suite green with no path changes
   for default-layout projects (incl. jig's own repo, which has no
   `scaffold.json`).

**DoD:**
- [x] All ACs pass; full suite green (3074 tests OK, skipped=9); pyright 0 errors
      across changed modules; `uvx ruff check .` clean; host packages resynced +
      `--check` in sync.
- [x] New tests (`test_layout_routing.py`, 13) cover default vs `"."` for
      `status-board`, `adr index`, the scaffold-state round-trip, AND the
      newly-inventoried artifact writers — `memory.py`
      (glossary/inbox/…), `team_signal.py` (`people_md_path`), `stocktake.py`
      (specs), `decisions.py` (`lightweight_path`) — each landing under
      `<project>/…` not `<project>/docs/…`. The no-stray-literal guard runs its
      module set + inline allowlist (AST-based); the cross-project-bleed guard
      exercises BOTH the marker up-walk AND the depth-arithmetic discovery path.
      **Caveat (deviation-logged):** `new` / `adr new` are NOT directly
      parametrized (git-fixture-heavy); covered by the path rewiring
      (`reserve_spec`/`reserve_adr` now resolve `specs_dir`/`decisions_dir` via
      `project_layout`) + the unchanged default reserve suite.
- [x] Reviewed by `reviewer` subagent (compliance + craft + arch) — all PASS;
      verdicts recorded under `reviews/slice-02-{compliance,craft,arch}.md`.

### Deviation log

- **Inventory scoping refinements** (from the rewiring + the independent reviews):
  - `migrate.py` **excluded** — on inspection all its `docs/` sites are
    pre-sentinel layout *detection* of the project being adopted; migrate-into-
    subtree is an explicit ADR-0033 non-goal. (DoR had listed it as a rewire
    target.)
  - `review_evidence.py` **no change** — `bug_evidence_path` is file-relative
    (derives `reviews/` from the bug path), carries no `project_dir/"docs"` join.
  - `lexicon.py` kept **stdlib-only** — it must stay hook-safe (zero local-package
    imports, enforced by `test_lexicon.py`'s `test_stdlib_only_…`), so it CANNOT
    import `project_layout`. Resolved via a small fail-soft inline `_memory_dir`
    that reads `layout.docs_root` itself (read-only, no escape validation). The
    suite caught my first attempt (importing `_common`) and a follow-on bug
    (dropped `/memory` suffix); both fixed + behaviorally tested.
- **`project_layout.docs_base()` added** to 084-01's module — the generic
  docs-root accessor for long-tail files (`product-vision.md`, `inbox.md`,
  `bugs/`, `lightweight-decisions.md`). Extends the DONE slice's API.
- **`sys.path` bootstrap added** to `decisions.py` + `stocktake.py` (they had no
  prior `_common` import); mirrors the existing pattern in `workflow.py`/`adr.py`.
- **`review._find_project_root`** uses an `os.devnull` marker to preserve its
  `Optional[Path]` return while routing through `project_root_for` (which returns
  `Path`).
- **AC2/AC3 test caveat** (already in DoD): `new` / `adr new` not directly
  parametrized for `docs_root="."` (git-fixture-heavy); covered by the
  `reserve_spec`/`reserve_adr` path rewiring + unit-tested `pl.specs_dir`.

### Reconciliation sweep

- **ADR-0033 §5a / spec 084** — implementation matches; no doc correction needed.
- **084-01 contract** — `project_root_for` resolve-vs-original-`path` asymmetry
  preserved at both consumers (verified by arch review). `docs_base()` extension
  is additive.
- **Deferred follow-ups (logged, not blockers)** — (a) widen `project_root_for`
  fallback to `Path | None` to drop the `os.devnull` marker (ripples into the DONE
  resolver + Path-expecting callers); (b) anchor the AST guard's allowlist on
  `ast.Name` id rather than source-text substring; (c) rule-of-three watch: a
  third hook-safe `docs_root` consumer would trigger extracting a stdlib-only
  `docs_root_relaxed()` into `project_layout`. None route to `inbox.md`/
  `refinement-todo.md` (small, owner = next layout-cleanup pass).
- **No new `TODO`/`FIXME`.** Glossary candidate ("`docs_base` / configurable docs
  root") → session-end `memory-sync`, not reconciliation.
