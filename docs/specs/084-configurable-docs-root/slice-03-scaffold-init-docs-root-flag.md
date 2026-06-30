---
status: DONE
dependencies: [084-01, 084-02]
last_verified: 2026-06-30
frame_review: false  # CLI + render wiring on the 084-01/02 contract; no new premise.
arch_review: true  # touches host packaging + the release-trio contract surface (verify_install).
---

## Slice 084-03 — scaffold-init `--docs-root` flag + layout-aware output

**Goal:** Let `scaffold-init` produce a track-local project. Add
`--docs-root <path>` (default `docs`). With the default, output is byte-for-byte
unchanged. With `--docs-root .`, templates land directly under the project root,
the `layout.docs_root` block is written to `scaffold.json`, and rendered primer
links are layout-aware. Push-mode reservation in a subtree is refused loudly
(the non-goal boundary made observable).

**DoR:**
- ✅ 084-01 + 084-02 landed: helper proven, read/write call sites honor the
  configured root.
- ✅ Render sites grounded: `scaffold.py` emits the `docs/` template tree at
  `target / "docs"` (the rglob loop) and renders CLAUDE.md/AGENTS.md primer
  templates whose bodies carry literal `docs/specs/…` links. Manifest write
  (`scaffold.json`) is the place to persist `layout.docs_root`.
- ✅ Contract guards grounded: `scripts/scaffold_contract.py` /
   `scripts/verify_install.py` validate the manifest + scaffold output. Confirmed
   `validate_scaffold_manifest` is required-field-allowlist (not strict-extra-key-
   reject), so a new top-level `layout` block does NOT trip the manifest validator;
   the only residual drift risk is byte-equality of shipped contract files
   ([memory: release-trio ships in the zip] — diff entry-by-entry).
- ✅ `git_toplevel(path)` is NET-NEW (AC5): no `rev-parse --show-toplevel`
  helper exists today (only `rev-parse --verify origin/main` / `HEAD`); neither
  084-01 (`project_root_for`, git-blind) nor 084-02 (path/discovery only)
  delivers it. This slice adds it — accounted scope, not reuse.

**Acceptance Criteria:**

1. **Default is byte-unchanged.** `scaffold-init` with no `--docs-root` (or
   `--docs-root docs`) writes NO `layout` block and produces output identical to
   today (default templates under `docs/`). The named existing suites must pass
   unmodified: `skills/scaffold-init/test_scaffold.py`,
   `skills/scaffold-init/test_scaffold_mode.py`, and
   `scripts/test_scaffold_contract.py` (there is no single golden fixture —
   these are the default-path guards).
2. **`--docs-root .` collapses the layer.** Templates that today land under
   `target/docs/<x>` land under `target/<x>`; `scaffold.json` carries
   `{"layout":{"docs_root":"."}}`; the project then classifies `scaffolded` and
   all helpers resolve track-local paths (verified end-to-end with an 084-02
   command, e.g. `status-board`).
3. **Primer links are layout-aware (exact rule).** Rendered CLAUDE.md/AGENTS.md
   links of the form `docs/<x>` are rewritten to `<docs_root>/<x>`, collapsing to
   `<x>` (leading `docs/` stripped) under `docs_root="."`. The rewrite runs on
   BOTH render paths — the machinery path (`_rewrite_skill_md_paths`) AND the
   plugin-only path where `doc_rewrite` is currently `None` (scaffold.py ~2228):
   the layout rewrite is independent of the machinery-path transform and must
   apply regardless. Default layout (`docs_root="docs"`) leaves links byte-for-
   byte unchanged.
4. **Escape rejection at the CLI.** `--docs-root ../x` / absolute paths are
   rejected by `scaffold-init` (reusing 084-01's validator) before any write —
   no partial scaffold left behind.
5. **Subtree git-anchoring boundary made observable (non-goal made loud).**
   **Net-new scope (was mis-presented as reuse):** this slice ADDS a small
   `git_toplevel(path) -> Path | None` helper (`git -C path rev-parse
   --show-toplevel`; home: `spec-workflow/workflow.py`, alongside the existing
   git helpers) — no such helper exists today. The subtree condition compares
   **two distinct, separately-resolved inputs**:
   - `repo_root` = `git_toplevel(arg)` (the enclosing git work-tree), and
   - `subproject_root` = `project_layout.project_root_for(arg, fallback=…)` (the
     sentinel-anchored subproject, slice 084-01).

   A project is a **subtree** iff `repo_root` is set and
   `repo_root != subproject_root`. Then:
   - **Push mode** (`workflow.py new --push` / `_reserve_via_detached_worktree`)
     **refuses** with a clear "subtree push-mode unsupported — use local mode
     (spec 084 non-goal)" error rather than writing to the wrong root or reserving
     against a shared `main`. **Wiring caveat:** `_reserve_via_detached_worktree`
     currently receives a bare `project_dir` (workflow.py ~2816); the refusal
     must branch on `subproject_root` (the sentinel-resolved value), NOT on
     whatever `git -C` sees — else it never fires (frame-critique round-1
     secondary). A test asserts the guard fires when the arg is the subproject and
     an ancestor `.git` exists, and does NOT fire for a normal repo-root project.
   - **Local mode** is supported but its git side-effects (dirty-check /
     branch-routing / commit) run against the **enclosing repo** — unchanged by
     this spec. The whole-repo dirty refusal is documented (see AC6) so the
     adopter is not surprised; it is NOT silently swallowed.
6. **Local-mode caveat wording is pinned (not just "present").** When the
   scaffold writes a non-default layout (`docs_root != "docs"`), the generated
   `brief.md` (and the primer note) includes a caveat anchored on the
   load-bearing phrase **"whole-repo dirty check"** (the string a test asserts),
   explaining that local reservation's git side-effects run against the enclosing
   repo. Default layout (`docs_root="docs"`) emits NO such caveat → AC1
   byte-unchanged holds. The caveat is added via a conditional branch in
   `_render_brief`.

**DoD:**
- [x] All ACs pass; full suite green; pyright clean; `uvx ruff check .` clean;
      host-package drift `--check` in sync (scaffold-contract + verify-install
      bytes; verify_install ships in the release zip, not under hosts/).
- [x] Tests (`test_scaffold_docs_root.py`, 13) cover default-unchanged (no layout
      block / no caveat), `"."` end-to-end scaffold + helper round-trip + a real
      `status-board` command round-trip, primer-link rewriting on BOTH render
      paths, CLI escape rejection (no partial), the `git_toplevel`/subtree guard
      (fires for a subproject under an ancestor `.git`, NOT for a repo-root
      project) for BOTH `workflow new` and `adr new`, and the pinned
      `"whole-repo dirty check"` caveat present/absent by layout.
- [x] Reviewed by `reviewer` subagent (compliance + craft + arch) — all PASS
      (arch: R1 needs-changes → R2 pass after the adr-guard parity fix). Verdicts
      under `reviews/slice-03-{compliance,craft,arch}.md`.

### Deviation log

- **Scope grew beyond the grounded inventory (caught by tests/review):**
  - `_ensure_self_defining_convention_block` + `copy_machinery` (spec 065-04
    convention block) were emitting a stray `docs/workflow.md` under `"."` — found
    by the AC2 collapse test, now threaded with `docs_root` (copy_machinery
    defaults to `"docs"`, so migrate is unaffected).
  - `verify_install.check_scaffold_seed_present` made layout-aware (inline
    stdlib `_scaffold_docs_root` read — verify_install never imports jig
    internals); the `docs` doc-link smoke check is **skipped** for non-default
    layout (`scaffold_contract.scaffold_doc_problems` is `docs/`-shaped) — a named
    deferred follow-up, not a silent gap.
- **Arch parity fix (R1 needs-changes):** `adr new --push` was unguarded in a
  subtree. Extracted detection into a new `_common/subtree.py` leaf
  (`git_toplevel` + `detect_subtree`); BOTH `workflow new` and `adr new` now
  refuse via it (each raising its own error type). `workflow.git_toplevel` is a
  re-export.
- **Additive 084-01 extension:** `project_layout.validate_docs_root` (public
  wrapper of the escape validator) for the CLI pre-write check.
- **Compliance fixes:** brief.md `people.md` prose line made layout-aware; AC2
  strengthened with a real `status-board` command round-trip.
- **Craft fix:** the docs-base ternary DRYed into `_scaffold_docs_base`.

### Reconciliation sweep

- **ADR-0033 / spec 084** — implementation matches; the push-refusal invariant is
  now enforced symmetrically (both reservation doors). No ADR/spec correction
  needed (the ADR's scoped-OUT language already covers "push-mode in a subtree").
- **Deferred follow-ups (logged, non-blocking):** (a) layout-aware doc-link
  checking in `scaffold_contract`/`verify_install` for non-default layouts;
  (b) `migrate copy-machinery` into an existing subtree would write
  `docs/workflow.md` (gated behind the migrate-into-subtree non-goal); (c)
  `test_compose_default_is_passthrough` object() sentinel cosmetic.
- **No new `TODO`/`FIXME`.** Glossary candidate ("`--docs-root` / track-local
  adoption") → session-end `memory-sync`.
