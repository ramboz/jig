---
status: READY_FOR_REVIEW
dependencies: [084-01]
last_verified: 2026-06-29
frame_review: false  # mechanical rewiring behind the 084-01 contract; no new premise.
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
- [ ] All ACs pass; full suite green; pyright clean; `uvx ruff check .` clean.
- [ ] New tests parametrize default vs `"."` for `status-board`, `new`, `adr
      new`, `adr index`, the scaffold-state round-trip, AND the newly-inventoried
      artifact writers — `memory.py` (glossary/learnings/inbox/refinement-todo),
      `team_signal.py` (`people_md_path`), `stocktake.py` (specs/refinement-todo)
      — each landing under `<project>/…` not `<project>/docs/…` when
      `docs_root="."`. The no-stray-literal guard is asserted with its module set
      + allowlist documented inline (AST-based); the cross-project-bleed guard
      exercises BOTH the marker up-walk (nested-ancestor case) AND the
      depth-arithmetic lifecycle path (transition / slice-claim / DONE-dependency
      resolving against the sentinel-bearing subproject, not the `.git` ancestor).
- [ ] Reviewed by `reviewer` subagent (compliance + craft + arch — touches
      module boundaries across several skills).
