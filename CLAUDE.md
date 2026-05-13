# jig — AI-Native Dev Scaffold

> The Claude Code skill pack that scaffolds AI-native development practices.
> We dogfood the workflow we build.

## Hot Cache

Frequently-referenced terms and project state. Loaded every session.
Update via `/jig:memory-sync` or when `jig-memory-scan` surfaces an unknown reference.

### Project codenames / active work
- **jig** = this skill pack repo (the plugin itself)

### Key terms
- **SPIDR** = Mike Cohn's five story-splitting techniques (Spike, Path, Interface, Data, Rules)
- **Tier 0/1/2** = installation tiers for jig skills (see docs/memory/glossary.md)
- **Hot Cache** = the structured CLAUDE.md section for high-frequency terms
- **Dumb zone** = >40% context fill; above this, model recall degrades (Horthy)
- **Vertical slice** = a spec slice that crosses all layers and delivers end-to-end value
- **Reconciliation** = post-implementation phase: deviation log, doc updates, second review pass

### Active specs
- 001-scaffold-init: **complete** (Spike 001a + slices 001-01..001-05 all DONE)
- ADR-0001 (scaffold-stable) **accepted** — closes the stocktake-flagged signal
- ADR-0002 (contracts stays deferred) **accepted** — `contracts` skill stays a deliberate stub; resolution triggers documented
- 002-memory-layer: **complete** (all 4 slices DONE)
- 003-spec-workflow-promotion: slice 003-01 (lifecycle-helper) **DONE**; spec-workflow promoted from stub to active. Slices 003-02 (anti-horizontal-phasing-check) and 003-03 (new-spec-scaffolding) explicitly deferred.
- 004-independent-review-promotion: slice 004-01 (review-helper) **DONE**; independent-review promoted from stub to active. The skill was dogfooded by reviewing its own implementation with the helper it introduces.
- 005-adr-workflow: **first Tier 1 spec**; slice 005-01 (adr-helper) **DONE** — `adr.py` helper (new / accept / index / resolve-todo) + active SKILL.md + template landed; 46 tests green; reviewed + reconciled. Slices 005-02 (supersede) and 005-03 (boundary-change-detection) explicitly deferred.
- 006-tdd-loop: **second Tier 1 spec**; slice 006-01 (tdd-helper) **DONE** — `tdd.py` helper (detect + run, with exit-code normalization 0/1/2) + active SKILL.md landed; 25 tests (23 pass + 2 skipped where pytest is absent locally); pytest > vitest > jest priority; detection-only for vitest/jest; reviewed + reconciled. Slices 006-02 (ac-coverage) and 006-03 (pre-commit-gate) explicitly deferred.
- 007-slice-land: **third Tier 1 spec**; slice 007-01 (land-prepare) **DONE** — `land.py prepare` produces a readiness report (status / tests / deviation log / DoD checks) + mode-aware next-steps (direct or pr). 31 tests (30 pass + 1 pytest-skipped); reviewed + reconciled. No destructive git ops in this slice; addresses unmerged-worktree gap. Slices 007-02 (direct-mode-execute), 007-03 (pr-mode-execute), and 007-04 (scaffold-json-integration-flag) explicitly deferred.
- ADR-0004 (decisions-folder-naming) **accepted** — jig's default ADR layout will rename `docs/adrs/` → `docs/decisions/` with `adr-NNNN-` filename prefix. **Helper for the rename now exists** (slice 008-02); jig's own rename is reserved for slice 008-03 (jig-self-migration). One follow-up open question parked in refinement-todo (backwards-compat window for `adr.py`).
- 008-migrate-existing-project: **first Tier 0 sibling spec to scaffold-init**; slice 008-01 (migrate-report) **DONE** — `migrate.py report <dir>` produces a read-only 5-section migration report. Slice 008-02 (rename-decisions) **DONE** — `migrate.py rename-decisions <dir> [--dry-run]` applies ADR-0004's rename: `docs/adrs/` → `docs/decisions/` + filename pad/prefix + cross-reference rewriting bounded to `docs/`, `CLAUDE.md`, `.claude/`. Atomic, idempotent, refuses on conflict/collision. 65 tests in `skills/migrate/` (34 from 008-01 + 31 new); 354 total across 9 skills; zero regressions. Reviewer caught one real correctness bug (greedy-substring corruption of canonical refs when legacy+canonical mix in the same file) — fixed inline with a `(?<!adr-)` negative-lookbehind regex + regression test. Validator dry-run is clean (62 lines: 22 file renames + 38 cross-ref updates); jig-self dry-run is 17 lines (1 dir + 4 files + 12 cross-refs). Slices 008-03 (jig-self-migration), 008-04 (slice-to-spec-mapping), 008-05 (scaffold-init --migrate suggestion) deferred.
- 009-dod-close-out-separation: slice 009-01 (close-out-section-recognition) **DONE** — `slice-land`'s `check_dod` now recognizes a `### Close-out (post-DONE)` subsection inside a slice and excludes its checkboxes from the count, resolving the chicken-and-egg where post-DONE items (status-board regen, CLAUDE.md updates) blocked landing. 2 new tests (33 total in slice-land); slice 008-01 was the first slice to close cleanly under the new convention. Reviewer caught me pre-ticking the Reconciliation-review-pass box (the exact anti-pattern this spec was created to discourage) — logged in deviation log §8.

### Deferred decisions
→ See [docs/refinement-todo.md](docs/refinement-todo.md)

## Key documents

| Document | Purpose | When to read |
|---|---|---|
| [docs/workflow.md](docs/workflow.md) | How we build — spec lifecycle, session workflow | Start of every session |
| [docs/architecture.md](docs/architecture.md) | Tech stack, module boundaries, decisions | Before touching plugin internals |
| [docs/conventions.md](docs/conventions.md) | Skill/hook/agent authoring standards | Before writing any skill or hook |
| [docs/specs/README.md](docs/specs/README.md) | Spec status board | To pick up next work |
| [docs/refinement-todo.md](docs/refinement-todo.md) | Deferred decisions | When hitting an undefined case |
| [docs/memory/glossary.md](docs/memory/glossary.md) | Domain terms | When encountering unknown terms |
| [docs/memory/learnings.md](docs/memory/learnings.md) | Dead ends and gotchas | Before repeating a mistake |
| [docs/inbox.md](docs/inbox.md) | Parked ideas | During reconciliation |

## Current sprint focus

Tier 0 is complete (4 active skills + 1 deliberate stub + 1 sibling: `migrate`). Tier 1: `adr-workflow` (005) DONE, `tdd-loop` (006) DONE, `slice-land` (007 + 009 close-out fix) DONE. Spec 008 (migrate): slices 008-01 (report) + 008-02 (rename-decisions) DONE; slices 008-03 (jig-self-migration — apply 008-02 to jig itself + update `adr.py` defaults), 008-04 (slice-to-spec-mapping), 008-05 (scaffold-init --migrate suggestion) explicitly deferred. ADR-0004's helper is built; jig's own rename pending 008-03. Remaining Tier 1 candidate: `pr-review` (still unblocked — slice-land creates the PR-shaped artifact). `local-dev-parity` still has no signal.

## Skills in this repo

| Skill | Status | Invocable |
|---|---|---|
| `/jig:scaffold-init` | Spec 001 fully implemented (slices 001-01..001-05 all DONE) | Yes (explicit) |
| `/jig:memory-sync` | Spec 002 fully implemented (all 4 slices DONE) | Yes (explicit) |
| `/jig:spec-workflow` | Slice 003-01 DONE — active, auto-triggering; `workflow.py` helper for state transitions + status-board sync | Yes (auto + explicit) |
| `/jig:independent-review` | Slice 004-01 DONE — active, auto-triggering; `review.py` helper builds standardized prompts for implementation + reconciliation review | Yes (auto + explicit) |
| `/jig:contracts` | **Deliberate stub** (ADR-0002) — kept stubbed until a third caller needs the duplicated lookup, OR a real user reports cross-module-coupling pain | Yes (explicit only — auto-invocation disabled) |
| `/jig:adr-workflow` | Slice 005-01 DONE — active, auto-triggering; `adr.py` helper for new / accept / index / resolve-todo across `docs/decisions/` + `docs/refinement-todo.md` | Yes (auto + explicit) |
| `/jig:tdd-loop` | Slice 006-01 DONE — active, auto-triggering; `tdd.py` helper for detect + run with normalized exit codes (0 green / 1 red / 2 env error), pytest/vitest/jest support, priority pytest > vitest > jest. | Yes (auto + explicit) |
| `/jig:slice-land` | Slice 007-01 DONE + slice 009-01 close-out fix DONE — active, auto-triggering; `land.py prepare` emits readiness report (status / tests / deviation log / DoD-with-close-out-exclusion) + mode-aware next-steps (direct or pr). Recognizes `### Close-out (post-DONE)` to skip post-DONE items in DoD count. No destructive git ops yet; 007-02/03 add those. | Yes (auto + explicit) |
| `/jig:migrate` | Slices 008-01 + 008-02 DONE — active, auto-triggering; `migrate.py report <dir>` (read-only 5-section migration report) + `migrate.py rename-decisions <dir> [--dry-run]` (applies ADR-0004's rename: dir + filename pad/prefix + bounded cross-reference rewriting, atomic, idempotent, refuses on conflict). Sibling to scaffold-init (Tier 0). Future subcommands `slice-to-spec` (008-04) deferred. | Yes (auto + explicit) |

## Session workflow

1. Check `docs/specs/README.md` for current status.
2. Pick up next `READY_FOR_IMPLEMENTATION` slice.
3. Spawn `implementer` subagent with the spec path.
4. After deliverable is on disk, spawn `reviewer` subagent.
5. Reconcile: update docs, write deviation log, run reconciliation review.
6. Run `/jig:memory-sync` to consolidate learnings.
7. Update spec status and status board.

## Constraints for agents working on this repo

- Do not modify `docs/conventions.md` without explicit human approval.
- Reviewer subagent has read-only tools (Read, Glob, Grep). It cannot write to memory.
- `templates/CLAUDE.md.template` is the source template for scaffold-init. Do not confuse it with this file.
- Hook commands use `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...` — never bare names.
- All hook scripts use Python 3 for JSON parsing — never jq.
