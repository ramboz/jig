---
status: DONE
dependencies: [adr-0033]
last_verified: 2026-06-29
use_cases: []
frame_review: true  # introduces a new config premise (layout.docs_root) + a
#                   # validation/write boundary — frame-critique before READY_FOR_REVIEW (ADR-0020).
---

# Spec 084 — Configurable docs root

## Overview

jig hardcodes `<project_dir>/docs/…` as the home for every artifact. This spec
adds a single configurable knob — `layout.docs_root` in `scaffold.json`,
defaulting to `"docs"` — so jig can be adopted **track-local** inside a larger
repo (e.g. a subproject at `docs/opportunities/cwv/` with `docs_root="."`,
putting specs at `docs/opportunities/cwv/specs/` rather than forcing a second
`docs/` layer). Decision + scoping: [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md).

**Backward compatibility is non-negotiable:** absent `scaffold.json` or absent
`layout` block resolves to `"docs"`; default scaffold output is byte-unchanged;
jig's own repo (no `scaffold.json`) keeps resolving `docs/`.

## The two-offset finding (why this spec is scoped the way it is)

`project_dir` plays two roles that coincide in the default layout and diverge
under subtree adoption:

| Role | Offset that varies | Owned by |
|---|---|---|
| **Artifact root** (where specs/ADRs are written) | `project_dir → docs_root` | **this spec** |
| **Git anchor** (which `origin/main` is reserved/landed) | `repo_root → project_dir` | **out of scope** (follow-up spec) |

`docs_root` captures only the first offset. The cleavage is **artifact placement
vs git anchoring** — not local vs push. Even `reserve_spec(--no-push)` commits
and runs `_refuse_if_dirty` / branch-routing against `project_dir`
([workflow.py:3015](../../../skills/spec-workflow/workflow.py)); in a subtree
`git -C project_dir` resolves to the enclosing repo. So this spec makes artifact
*paths* layout-aware and leaves git anchoring unchanged for **all** modes:

- **Local mode** is supported, with a documented rough edge — its dirty-check /
  branch-routing / commit run against the enclosing repo (whole-repo dirty
  refusal in a monorepo subtree).
- **Push mode** in a subtree is **refused loudly** (it would rebuild paths
  against an ephemeral worktree's *repo* root and reserve against a shared
  `main`). Not promised as a near follow-up — see ADR-0033.

There is also a **second offset-sensitive category beyond path construction**:
project-root **discovery** (`_find_project_root` walks up for
`docs/architecture.md`). Under `docs_root="."` that probe climbs into the
enclosing repo (cross-project bleed), so discovery switches to the **sentinel**
(`scaffold.json`) as its marker. See ADR-0033 §5a and slice 084-02.

## Non-goals

- Subtree-aware git anchoring (separate concern; needs the
  `repo_root → project_dir` offset + shared-`main` semantics). May be a category
  mismatch in a monorepo, not just unbuilt.
- Migrate-into-subtree: adoption is via greenfield `scaffold-init --docs-root`;
  `migrate.py` gains no layout entry point here.
- Per-directory configurability (independent `specs_dir`, `decisions_dir`, …).
- Changing the default scaffold layout.
- CLAUDE.md/AGENTS.md auto-load placement in a subtree (host concern).
- Any CWV-specific logic.
- Requiring existing projects to edit `scaffold.json`.

## Slices

- **084-01** — `_common/project_layout.py`: the layout helper + validation (leaf,
  fully tested in isolation). Foundation.
- **084-02** — Route read/write helpers through the layout helper AND switch
  project-root *discovery* from the `docs/` probe to the sentinel; the
  acceptance-criteria commands (`status-board`, `new`, `adr new/index`) honor
  `docs_root="."`. Includes the no-stray-`"docs"`-literal guard + a
  cross-project-bleed guard.
- **084-03** — scaffold-init `--docs-root` flag: writes `layout.docs_root` only
  when non-default, roots templates correctly under `"."`, renders layout-aware
  primer links, and refuses push-mode-in-subtree loudly.

## Assumptions

- `scaffold.json` stays at the project root and remains the completion sentinel
  (spec 063 / ADR-0011) — it is read to *discover* `docs_root` AND serves as the
  project-root up-walk marker (ADR-0033 §5a), so it can never live under
  `docs_root`. (Risk: contested only if a future change relocates the sentinel —
  none planned.)
- Adoption is via greenfield `scaffold-init --docs-root`. Migrating an *existing*
  subtree under a non-default root is out of scope (no `migrate.py` layout entry
  point). (Risk: contested if the first real adopter already has specs in the
  subtree — then a migrate path is needed before this is usable there.)
