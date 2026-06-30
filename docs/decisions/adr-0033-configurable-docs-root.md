---
status: Accepted
dependencies: []
last_verified: 2026-06-29
frame_review: true
---

# ADR-0033: Configurable docs root (single knob), git-machinery scoped out

## Status

Accepted (2026-06-29)

## Context

jig assumes every project artifact lives under `<project_dir>/docs/…`:
`docs/specs/`, `docs/decisions/`, `docs/workflow.md`, `docs/architecture.md`,
`docs/memory/`, `docs/refinement-todo.md`. The path `project_dir / "docs" / …`
is hardcoded across the helpers (`workflow.py`, `adr.py`, `migrate.py`,
`review.py`, `bug.py`, `decisions.py`, `lexicon.py`, `scaffold.py`,
`stocktake.py`).

We want **scoped/track-local adoption**: a subproject inside a larger repo, e.g.
`docs/opportunities/cwv/`, that runs jig for *itself* without forcing a second
`docs/` layer (`docs/opportunities/cwv/docs/specs/…`). Desired layout:

| Artifact | Path |
|---|---|
| project root | `docs/opportunities/cwv/` |
| docs root | `.` |
| specs | `docs/opportunities/cwv/specs/` |
| decisions | `docs/opportunities/cwv/decisions/` |
| workflow / architecture | `docs/opportunities/cwv/{workflow,architecture}.md` |
| scaffold manifest (sentinel) | `docs/opportunities/cwv/scaffold.json` |

### The structural finding (frame-critique)

A naive reading says "make the docs root configurable." But `project_dir` plays
**two** roles that coincide today and diverge under subtree adoption:

1. **Artifact root** — where jig writes specs/ADRs/docs. The offset that varies
   here is `project_dir → docs_root`.
2. **Git anchor** — the repo whose `origin/main` jig reserves against and lands
   into. The offset that varies here is `repo_root → project_dir` (the *subtree
   offset*), which `docs_root` does not capture.

The push-mode reservation path
([`_reserve_via_detached_worktree`](../../skills/spec-workflow/workflow.py))
checks out `origin/main` into an **ephemeral worktree** and rebuilds artifact
paths relative to that worktree's **root**. In a subtree, the worktree root is
the *big repo* root, not the subproject — so a `docs_root`-only solution would
write the reservation commit to `<repo-root>/specs/` instead of
`<repo-root>/docs/opportunities/cwv/specs/`, and would reserve against the whole
org's `main`. `docs_root` is **necessary but not sufficient** for the git-aware
paths; making them subtree-correct needs the *subtree offset*, a separate concern
with its own protected-branch / multi-project semantics.

Frame-critique (2026-06-29) sharpened two points behind this:

- **The cleavage is artifact placement vs git anchoring — not local vs push.**
  Even `reserve_spec(--no-push)` commits and runs `_refuse_if_dirty` /
  branch-routing against `project_dir`; in a subtree `git -C project_dir`
  resolves to the enclosing repo. So *git anchoring* is deferred for **all**
  modes, local included. Local mode is tolerable (its side-effects are
  local/recoverable) but inherits a real rough edge — a whole-repo dirty refusal.
- **Discovery is a second, worse failure category than construction.** Jig also
  walks *up* for a `docs/` marker to find the project root
  (`_find_project_root` → first ancestor with `docs/architecture.md`). Under
  `docs_root="."` that marker moves, so the walk silently resolves to an
  *ancestor* (the enclosing repo) — cross-project bleed, strictly worse than a
  miss. The robust project-root marker is the **sentinel** (`scaffold.json`),
  not `docs/`. (See §5a.)

## Decision

1. **One knob, `layout.docs_root`, defaulting to `"docs"`.** Config shape:

   ```json
   { "layout": { "docs_root": "docs" } }
   ```

   `docs_root` is a project-relative path. `"."` collapses the docs layer for
   track-local adoption. We do **not** make individual directories
   independently configurable (YAGNI — re-open only with a real second consumer,
   per ADR-0002 rule-of-three).

2. **A single leaf helper, `skills/_common/project_layout.py`,** owns the
   mapping. It reads `<project_dir>/scaffold.json`, returns `docs_root(project_dir)`
   and the derived `specs_dir` / `decisions_dir` / `workflow_path` /
   `architecture_path` / `memory_dir` / `refinement_todo_path`. Every helper that
   today writes `project_dir / "docs" / …` routes through it. `_common` stays a
   leaf (stdlib + `_common` only).

3. **Validation is load-bearing.** `docs_root` is rejected if it is absolute or
   contains a `..` component that escapes `project_dir` (the resolved path must
   stay within `project_dir`). This is the only barrier between config and an
   arbitrary-write primitive, so it is enforced in the helper and tested
   directly. Empty / missing → default `"docs"`.

4. **scaffold.json is the config home AND the completion sentinel, at the
   project root** (unchanged from spec 063 / ADR-0011). It must be found *before*
   `docs_root` is known, so it can never live under `docs_root`.

5. **Pre-scaffold detection stays hardcoded to `docs`.** `looks_spec_driven`
   (and the two tuned migrate/scaffold variants) run before any scaffold.json
   exists; they keep the literal `docs/` probe. Only *after* the sentinel exists
   does the configured `docs_root` take effect. This also preserves jig's own
   repo (which has no scaffold.json) resolving `docs/`.

5a. **Project-root discovery is sentinel-anchored — never structure-derived.**
   A single helper `project_root_for(path)` walks up to the nearest
   `scaffold.json` (the sentinel) and returns that dir; only when no sentinel is
   found does it fall back to today's behavior (preserving default + jig's own
   repo, which has no sentinel). ALL discovery sites route through it. There are
   **two** structure-derived discovery categories that both break under `"."`,
   and the construction-literal guard catches neither:

   - **Marker up-walk** — `_find_project_root` (review.py) climbs for
     `docs/architecture.md`; under `"."` it resolves to an *ancestor* with that
     file (the enclosing repo) → cross-project bleed.
   - **Depth arithmetic** (found in frame-critique round 1, workflow.py) —
     `_project_root_for_spec` and the bare `parents[3]` at `_record_spec_ref`
     and the DONE-dependency check assume `docs/specs/<dir>/spec.md` (root =
     `parents[3]`). Under `"."` a real spec is at `<project_dir>/specs/<dir>/
     spec.md`, so `parents[3]` (and the `.git` fallback) resolve to the
     enclosing repo. This drives the *post-`new`* lifecycle (transition,
     slice-claim `claimed_by`, DONE-dependency validation, the `.jig/spec-ref`
     stamp) — the very operations slice 084-02's `status-board`/`new`/`adr` ACs
     do NOT exercise, so the bleed would surface only when a real adopter runs a
     full slice lifecycle.

   Both are symptoms of one anti-pattern: inferring the root from an artifact's
   position under an assumed docs layout. Sentinel-anchoring removes the
   assumption.

6. **scaffold-init gains `--docs-root <path>` (default `docs`).** Default output
   is byte-for-byte unchanged (no `layout` block written when `docs_root ==
   "docs"`; written only when non-default). With `--docs-root .`, templates are
   emitted directly under the project root rather than under `docs/`, and rendered
   primer links (CLAUDE.md / AGENTS.md) are layout-aware.

### Explicitly scoped OUT of this decision (deferred, named)

- **Subtree-aware git anchoring (all modes).** v1 makes **artifact paths**
  layout-aware; it does **not** change git anchoring. Even local-mode
  reservation runs its dirty-check / branch-routing / commit against the
  enclosing repo (a known rough edge: whole-repo dirty refusal in a monorepo
  subtree — documented, not silently shipped). Push-mode in a subtree is
  **refused loudly** (it would write to the wrong root and reserve against a
  shared `main`). This is not promised as a near follow-up: reserving/landing
  against a monorepo's shared `main` may be a **category mismatch**, not merely
  unbuilt — revisit only with a concrete multi-project reservation model. The
  push-refusal guard's subtree test (`git_toplevel(project_dir) != project_dir`)
  is only well-defined if `project_dir` is the subproject root; callers/hosts
  must resolve it via the sentinel anchor (§5a `project_root_for`), not pass the
  enclosing repo root — otherwise the guard silently never fires (frame-critique
  round-1 secondary). This resolution discipline is pinned, not assumed.
- **Per-directory layout config** (independent `specs_dir`, `decisions_dir`, …).
- **Migrate-into-subtree.** v1 adoption is via greenfield `scaffold-init
  --docs-root`. `migrate.py` gains no layout entry point here; adopting an
  *existing* subtree under a non-default root is a separate concern.
- **CLAUDE.md / AGENTS.md auto-load placement.** A primer at
  `docs/opportunities/cwv/CLAUDE.md` is not auto-loaded by the host from the repo
  root; that is a host concern, not jig's.
- **Multi-jig-per-repo coordination** (two subprojects each `docs_root="."`
  sharing one branch / status-board namespace).

## Consequences

- Backward compatible: absent scaffold.json or absent `layout` → `"docs"`; every
  existing project and jig itself is unaffected; default scaffold output is
  unchanged.
- Completeness is the dominant risk: a missed `project_dir / "docs"` literal
  yields split-brain artifact placement. Mitigated by a guard test that the
  helper tree carries no stray `"docs"` path-join literals and that the named
  acceptance commands (`status-board`, `new`, `adr new/index`) honor `"."`.
- The validation boundary turns a config string into a constrained write target;
  escape attempts (`../docs`, absolute) are rejected at the helper, tested.
- The subtree git-machinery gap is a *named* limitation, not a silent foot-gun;
  push-mode in a subtree is refused until the follow-up spec lands.

## Alternatives considered

- **Per-directory path map** (`specs_dir`, `decisions_dir`, … each configurable).
  Rejected for v1: no second real consumer; one knob covers the CWV case.
- **Boolean `nest_under_docs`** instead of a path. Rejected: a string is the same
  cost once validated and leaves room for `docs/internal`-style roots without a
  schema change.
- **Symlink / accept double `docs/`** (`docs/opportunities/cwv/docs/specs`).
  Zero-code but ugly and surprising; the explicit ask is the clean layout.
- **Make `docs_root` carry the subtree offset too** (i.e. solve git machinery
  now). Rejected as scope creep — it pulls in shared-`main` reservation
  semantics; deferred to its own spec.
