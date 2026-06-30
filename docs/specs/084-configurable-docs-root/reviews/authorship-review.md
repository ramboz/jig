# Authorship review — spec 084 slices (READY_FOR_REVIEW stage)

Date: 2026-06-29. Three independent `jig:reviewer` subagents (no impl-conversation
context), one per slice. This is the spec-authorship pass (is each slice
implementable as written by a TDD implementer?) — NOT frame-critique (passed
separately) and NOT conformance (no code yet). Not gate evidence; recorded for
provenance. All three returned **needs-changes**; every finding was grounded in
code by the reviewer and all are folded into the slices.

## Slice 084-01 — verdict: needs-changes → resolved

Grounding verified accurate (leaf import-discipline, `json` stdlib, no existing
`project_layout`, both discovery anti-patterns present).

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | HIGH | `LayoutError` left as "e.g."; escape vs malformed same type? | AC3/AC4: pinned `project_layout.LayoutError(ValueError)`; both vectors raise it; distinguishable by message only. |
| 2 | HIGH | `project_root_for` fallback signature only a prose "prefer" | AC5: pinned `project_root_for(path, *, fallback: Callable[[Path],Path])`; fallback required, receives `path`, raises propagate. |
| 3 | MED | "normalized" undefined (lexical vs `resolve()`) | AC2: pinned lexical `os.path.normpath`/`PurePosixPath`, no FS access. |
| 4 | MED | symlink escape + `docs_root`==`project_dir` unaddressed | AC3: symlink stated as explicit known-limit; `"foo/.."`→`.` accepted. |
| 5 | LOW | drive-letter absolute is a POSIX no-op | DoD: dropped; `os.path.isabs` is the absolute check. |
| 6 | LOW | empty-string vs malformed boundary | AC4: one explicit rule (absent/`""`→default; wrong-type/bad-JSON→raise). |

## Slice 084-02 — verdict: needs-changes → resolved (highest-value)

Discovery inventory verified complete; **construction inventory had real gaps.**

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | HIGH | `memory-sync/memory.py` (5 artifact paths) missing | Added to inventory + DoD coverage. |
| 2 | HIGH | `_common/team_signal.py` `people_md_path` missing | Added. |
| 3 | HIGH | `scaffold-init/stocktake.py` (specs/refinement-todo) missing | Added (post-sentinel reader). |
| 4 | MED | AC6 guard module-scope unspecified (false-pos vs silent-gap) | AC6: pinned explicit module set + inline allowlist + AST detection. |
| 5 | MED | how `status-board`/`new` receive `docs_root` unspecified | DoR: threading model pinned (per-call `project_layout` read; detached-worktree site = push → refused). |

## Slice 084-03 — verdict: needs-changes → resolved

Render sites / contract-guard grounding verified.

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | HIGH | AC5 `git_toplevel` helper does not exist; net-new scope mis-presented as reuse | AC5 + DoR: declared net-new; home pinned (`workflow.py`); comparison spelled out (`git_toplevel` repo_root vs sentinel `project_root_for`). |
| 2 | MED | `project_dir` double-duty → guard could never fire | AC5: two inputs named distinctly; refusal must branch on `subproject_root`. |
| 3 | LOW | local-mode caveat wording/trigger/insertion unspecified | New AC6: pinned phrase `"whole-repo dirty check"`, trigger (non-default layout only), `_render_brief` branch. |
| 4 | LOW | AC3 primer-rewrite under-specified; plugin-only path `None` | AC3: exact rule (`docs/<x>`→`<docs_root>/<x>`, collapse under `"."`), both render paths. |
| — | note | AC1 had no named golden test | AC1: cites `test_scaffold.py`, `test_scaffold_mode.py`, `test_scaffold_contract.py`. |
