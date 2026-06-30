---
status: DONE
dependencies: [adr-0033]
last_verified: 2026-06-29
frame_review: true  # introduces the validation/write boundary — covered by the ADR-0033 frame pass.
---

## Slice 084-01 — `_common/project_layout.py` layout helper + validation

**Goal:** Ship the single leaf helper that maps a `project_dir` to its artifact
paths through the configured (or default) `docs_root`, with a hardened
path-escape validator AND a sentinel-anchored `project_root_for(path)` discovery
resolver. No call sites are rewired in this slice — it lands the foundation and
its tests in isolation so 084-02/03 can depend on a proven contract.

**DoR:**
- ✅ [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md) reserved
  (Proposed) — fixes the one-knob decision, the validation rule (reject absolute
  + `..` escape), and the default-`"docs"` fallback.
- ✅ Home grounded: `skills/_common/project_layout.py`. `_common` is a LEAF —
  stdlib + `_common` only (mirror `scaffold_state.py`'s import discipline). JSON
  via `json` stdlib (no `tomllib`; 3.9 floor per the Python-3.9 memory).
- ✅ Sentinel/config contract grounded: reads `<project_dir>/scaffold.json`
  (project root, never under `docs_root`).

**Acceptance Criteria:**

1. **`docs_root(project_dir)` resolves config.** Returns `"docs"` when
   `scaffold.json` is absent, present-but-no-`layout`, or
   `layout.docs_root` is absent/empty. Returns the configured value otherwise.
   `"."` is returned as-is (meaning "no docs layer").
2. **Derived path helpers.** `specs_dir`, `decisions_dir`, `workflow_path`,
   `architecture_path`, `memory_dir`, `refinement_todo_path` each return
   `<project_dir>/<docs_root>/<suffix>` normalized, with `docs_root="."`
   collapsing to `<project_dir>/<suffix>` (no `./` segment, no doubled
   separators). **Normalization is lexical** — `os.path.normpath` / `PurePosixPath`,
   no filesystem access, no `resolve()`, no symlink following; the paths need not
   exist. Observable: for default → identical to today's `project_dir / "docs" /
   …`; for `"."` → directly under `project_dir`.
3. **Escape rejection (load-bearing).** A `docs_root` that is absolute
   (`os.path.isabs`, POSIX semantics) OR whose lexically-normalized path escapes
   `project_dir` (`"../docs"`, `"a/../../x"`) raises **`project_layout.LayoutError`**
   (subclass of `ValueError`) — it does NOT fall back to default and does NOT
   return an out-of-tree path. Accepted (normalized path stays within
   `project_dir`): `"."`, `"docs"`, `"docs/internal"`, and the degenerate
   `"foo/.."` (normalizes to `.` = project_dir itself — accepted, treated as `"."`).
   **Known limit (explicit non-goal):** because normalization is lexical, a
   `docs_root` that is itself a *symlink* pointing outside `project_dir` is NOT
   caught — symlink-traversal containment is out of scope and stated as a
   documented limitation, not silently assumed.
4. **Malformed scaffold.json is safe.** Unparseable JSON, or `layout` /
   `docs_root` of the wrong *type* (non-string), raises **the same
   `LayoutError`** (fail loud) — escape and malformed are NOT distinguished by
   type; a test tells them apart by message only. **Boundary rule (one line):**
   `docs_root` absent OR empty-string (`""`, correct type) → silent default
   `"docs"`; present-but-wrong-type or unparseable JSON → raise.
5. **`project_root_for(path, *, fallback)` is sentinel-anchored.** Signature:
   `project_root_for(path: Path, *, fallback: Callable[[Path], Path]) -> Path`.
   `fallback` is **required** (no default). Walks up from `path` and returns the
   nearest ancestor (incl. `path` itself if a dir) containing `scaffold.json`.
   When NO sentinel is found, calls `fallback(path)` and returns its result
   (the per-caller legacy behavior — `parents[3]` here, `.git`/up-walk there);
   if `fallback` raises, the exception propagates (the resolver adds no
   swallowing). So default-layout projects and jig's own repo (no sentinel) are
   unchanged. This is the single resolver replacing both the `docs/`-marker
   up-walk and the `parents[3]` depth arithmetic (ADR-0033 §5a). Observable: for
   a subproject at `<root>/specs/<dir>/spec.md` with `scaffold.json` at `<root>`,
   returns `<root>` — never the enclosing repo — even when an ancestor also has a
   `docs/`-tree or `.git`.

   > **Implementer note (frame-critique round 2):** the sentinel branch is the
   > uniform path, but the *fallback* is per-caller legacy behavior (`parents[3]`
   > here, `.git` there, `docs/architecture.md` up-walk elsewhere). Coherent — the
   > fallback fires ONLY for sentinel-less paths (jig's own repo, test fixtures);
   > every scaffolded adopter carries `scaffold.json` and resolves via the
   > sentinel. But "one resolver" is really "one sentinel-walk + N preserved legacy
   > fallbacks," so each legacy path must stay correct. Prefer a single `fallback`
   > callable parameter over re-deriving per site.

**DoD:**
- [x] All ACs pass; full suite green (run_tests.py exit 0, OK skipped=9); pyright
      0 errors; `uvx ruff check .` clean; host-drift `--check` in sync (module
      synced into Claude + Codex host trees).
- [x] `test_project_layout.py` covers: default fallback (absent / no-layout /
      empty-string), `"."` collapse, `"docs"` and nested non-default, the
      `"foo/.."`-normalizes-to-`.` accepted case, every escape vector (absolute
      POSIX `os.path.isabs`, `..` escape, sneaky `a/../../x`) raising
      `LayoutError`, malformed-JSON / wrong-type raising the SAME `LayoutError`
      (assert escape-vs-malformed distinguishable by message only), the symlink
      known-limit (documented, asserted NOT caught), and `project_root_for`:
      sentinel hit at self/ancestor, no-sentinel → `fallback` invoked with `path`,
      `fallback`-raises propagates, and the nested-under-an-ancestor-with-`.git`/
      `docs/` case (must return the sentinel-bearing subproject, not the ancestor).
      (Drive-letter absolutes are out of scope — POSIX `Path` repo; `os.path.isabs`
      is the absolute check.)
- [x] Import-discipline asserted: module imports only stdlib + `_common`
      (AST test `test_module_imports_only_stdlib_or_common`).
- [x] Reviewed by `reviewer` subagent (frame-critique + compliance + craft); the
      escape validator got explicit adversarial-input attention (compliance
      reviewer hunted for an uncaught escape — none found within POSIX-lexical
      scope). Verdicts recorded under `reviews/`.

### Deviation log

- **No functional deviations from the slice ACs.** The implementation matches the
  pinned contracts exactly: `LayoutError(ValueError)`, `project_root_for(path, *,
  fallback)` with required `fallback`, lexical `os.path.normpath` validation,
  `os.path.isabs` absolute check, and all five ACs as written.
- **Craft-nit fixed in reconciliation:** test cleanup standardized from
  `__import__("shutil")` inline lambdas to a module-level `import shutil` +
  `self.addCleanup(shutil.rmtree, …, ignore_errors=True)` across all test classes
  (craft reviewer nit). Re-ran: 27 tests green, ruff clean.
- **Craft-nit deferred (logged, no action):** `typing.Callable` vs
  `collections.abc.Callable` — `typing.Callable` is correct on the 3.9 supported
  floor and not deprecated until well after; revisit when the floor rises.
- **Host-package sync (expected for any new `skills/` module):** ran
  `build_host_packages.py` to add `project_layout.py` to the Claude
  (`hosts/claude/skills/_common/`) and Codex (`hosts/codex/plugins/jig/skills/
  _common/`) trees — required by the host-drift gate; the runtime module ships,
  the test does not.

### Reconciliation sweep

- **ADR-0033 §3/§5a** — implementation matches (validator + sentinel-anchored
  `project_root_for`); no ADR correction needed.
- **Spec 084 / slice-01** — ACs implemented as authored after the authorship
  review folded in the pinned contracts; no spec drift.
- **Downstream contracts surfaced** — 084-02/03 must (a) route artifact paths +
  discovery through these helpers and (b) preserve the `project_root_for`
  resolve-vs-original-`path` asymmetry. Already captured in slice-02's discovery
  inventory and slice-01's implementer note; no new drift introduced.
- **No new `TODO`/`FIXME`; no `docs/inbox.md` / `refinement-todo.md` entries
  needed.** A glossary entry for "sentinel-anchored discovery / `project_root_for`"
  is a candidate for the session-end `memory-sync` step (not reconciliation).
