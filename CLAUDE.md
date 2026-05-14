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
- 003-spec-workflow-promotion: slice 003-01 (lifecycle-helper) **DONE**; slice 003-04 (auto-tick-review-passed-on-transition) **DONE** — `workflow.py transition` now auto-ticks "Implementation review passed" on IN_PROGRESS → REVIEWED and "Reconciliation review passed" on REVIEWED → RECONCILED, structurally fixing the pre-tick anti-pattern that hit slices 007-01, 008-03, 011-02. 9 new tests (371 total). Dogfooded on its own DoD: both auto-ticks fired correctly when the slice itself transitioned. Slices 003-02 (anti-horizontal-phasing-check) and 003-03 (new-spec-scaffolding) explicitly deferred.
- 004-independent-review-promotion: slice 004-01 (review-helper) **DONE**; independent-review promoted from stub to active. The skill was dogfooded by reviewing its own implementation with the helper it introduces.
- 005-adr-workflow: **first Tier 1 spec**; slice 005-01 (adr-helper) **DONE** — `adr.py` helper (new / accept / index / resolve-todo) + active SKILL.md + template landed; 46 tests green; reviewed + reconciled. Slices 005-02 (supersede) and 005-03 (boundary-change-detection) explicitly deferred.
- 006-tdd-loop: **second Tier 1 spec**; slice 006-01 (tdd-helper) **DONE** — `tdd.py` helper (detect + run, with exit-code normalization 0/1/2) + active SKILL.md landed; 25 tests (23 pass + 2 skipped where pytest is absent locally); pytest > vitest > jest priority; detection-only for vitest/jest; reviewed + reconciled. Slices 006-02 (ac-coverage) and 006-03 (pre-commit-gate) explicitly deferred.
- 007-slice-land: **third Tier 1 spec**; slice 007-01 (land-prepare) **DONE** — `land.py prepare` produces a readiness report (status / tests / deviation log / DoD checks) + mode-aware next-steps (direct or pr). 31 tests (30 pass + 1 pytest-skipped); reviewed + reconciled. No destructive git ops in this slice; addresses unmerged-worktree gap. Slices 007-02 (direct-mode-execute), 007-03 (pr-mode-execute), and 007-04 (scaffold-json-integration-flag) explicitly deferred.
- ADR-0004 (decisions-folder-naming) **accepted** and **implemented** by slice 008-03 — jig's ADR layout is now `docs/decisions/adr-NNNN-<slug>.md`. Both open questions closed: implementation scope folded into spec 008 via the rename-decisions helper; backwards-compat window for `adr.py` answered by flipping defaults wholly (no transitional dual-read).
- 008-migrate-existing-project: **first Tier 0 sibling spec to scaffold-init**; slices 008-01 (migrate-report) + 008-02 (rename-decisions) + 008-03 (jig-self-migration) + 008-05 (scaffold-init --migrate suggestion) all **DONE**. 008-01 added `migrate.py report`. 008-02 added `migrate.py rename-decisions [--dry-run]` (atomic, idempotent, refuses on conflict/collision; 65 tests; bidirectional substring corruption fixed via `(?<!adr-)` regex). 008-03 applied the helper to jig itself: `docs/adrs/` gone, 4 ADRs at `docs/decisions/adr-NNNN-*.md`, templates moved + `adr-0000-template.md`, `adr.py` defaults updated end-to-end. Took 4 reconciliation-review passes due to bidirectional-arrow narrative collapses; lesson recorded in slice 008-03 deviation log §7. 008-05 closes the adoption arc — `scaffold-init` now refuses on spec-driven layouts without `scaffold.json` and routes to `/jig:migrate` (new `LooksAlreadySpecDrivenError`, exit 3, names every detected trigger; 7 new tests). Spec 008 effectively complete; only 008-04 (slice-to-spec-mapping) remains, deferred on sub-slice topology decision.
- 009-dod-close-out-separation: slice 009-01 (close-out-section-recognition) **DONE** — `slice-land`'s `check_dod` now recognizes a `### Close-out (post-DONE)` subsection inside a slice and excludes its checkboxes from the count, resolving the chicken-and-egg where post-DONE items (status-board regen, CLAUDE.md updates) blocked landing. 2 new tests (33 total in slice-land); slice 008-01 was the first slice to close cleanly under the new convention. Reviewer caught me pre-ticking the Reconciliation-review-pass box (the exact anti-pattern this spec was created to discourage) — logged in deviation log §8.
- 011-plugin-self-install: **first dev-infrastructure spec** (no new skill, no Tier; `skill: (none — dev infrastructure)`); slices 011-01 (local-plugin-install) + 011-02 (subagent-type-fallback-upgrade) both **DONE**. 011-01 landed `.claude-plugin/marketplace.json` (`jig-dev` marketplace), `scripts/verify_install.py` (headless 4-check + `probe` subcommand), `CONTRIBUTING.md` (install + rollback + live-verify runbook + session-restart requirement), and 20 new tests. First-real-reviewer dogfood ran clean (2026-05-13): all three subagent types resolved; `reviewer`/`architect` refused capability-probe writes; `implementer` wrote. 011-02 added `review.py subagent-type {implementation|reconciliation}` subcommand (detects `${CLAUDE_PLUGIN_ROOT}` + `agents/reviewer.md`, gracefully falls back to `general-purpose`), updated SKILL.md's bash recipe to call it deterministically, and noted reachability in `docs/architecture.md` under "Three subagents, no more." 11 new tests in `test_review.py` (362 total, no regressions). **First `jig:reviewer` substantive review ran clean on routing** (subagent_type accepted; 14 read-only tool calls; no Write/Edit/Bash attempts; output in documented VERDICT format) but reviewed a stale install snapshot — three findings filed to inbox (2026-05-13): install-snapshot lag, `migrate` test direct-invocation breakage, DoD pre-tick anti-pattern recurring across slices (007-01 → 008-03 → 011-02). Slices 011-03 (scaffold.json self-install marker) and 011-04 (SubagentStart reachability) explicitly deferred. Spec 011 effectively complete.

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

Tier 0 is complete (4 active skills + 1 deliberate stub + 1 sibling: `migrate`). Tier 1: `adr-workflow` (005) DONE, `tdd-loop` (006) DONE, `slice-land` (007 + 009 close-out fix) DONE. Spec 008 (migrate) **effectively complete**: slices 008-01 (report) + 008-02 (rename-decisions) + 008-03 (jig-self-migration) + 008-05 (scaffold-init --migrate suggestion) all DONE; only 008-04 (slice-to-spec-mapping) remains, gated on sub-slice topology decision. ADR-0004 is fully implemented. Adoption arc is closed — scaffold-init now routes existing-spec-driven projects to `/jig:migrate`. Remaining Tier 1 candidate: `pr-review` (still unblocked — slice-land creates the PR-shaped artifact). `local-dev-parity` still has no signal.

## Skills in this repo

| Skill | Status | Invocable |
|---|---|---|
| `/jig:scaffold-init` | Spec 001 fully implemented (slices 001-01..001-05 all DONE) + slice 008-05 — refuses on spec-driven layouts without `scaffold.json` and routes to `/jig:migrate`. | Yes (explicit) |
| `/jig:memory-sync` | Spec 002 fully implemented (all 4 slices DONE) | Yes (explicit) |
| `/jig:spec-workflow` | Slice 003-01 DONE + slice 003-04 DONE — active, auto-triggering; `workflow.py` helper for state transitions + status-board sync. As of 003-04, `transition` auto-ticks "Implementation review passed" on IN_PROGRESS → REVIEWED and "Reconciliation review passed" on REVIEWED → RECONCILED, structurally preventing the pre-tick anti-pattern. | Yes (auto + explicit) |
| `/jig:independent-review` | Slice 004-01 DONE + slice 011-02 DONE — active, auto-triggering; `review.py` helper builds standardized prompts for implementation + reconciliation review, plus a `subagent-type` subcommand that picks `reviewer` (when jig is installed as a plugin) or `general-purpose` (fallback) so SKILL.md's bash recipe resolves the Task argument deterministically. | Yes (auto + explicit) |
| `/jig:contracts` | **Deliberate stub** (ADR-0002) — kept stubbed until a third caller needs the duplicated lookup, OR a real user reports cross-module-coupling pain | Yes (explicit only — auto-invocation disabled) |
| `/jig:adr-workflow` | Slice 005-01 DONE + slice 008-03 ADR-0004 implementation DONE — active, auto-triggering; `adr.py` helper for new / accept / index / resolve-todo, writing to `docs/decisions/adr-NNNN-<slug>.md` per ADR-0004. | Yes (auto + explicit) |
| `/jig:tdd-loop` | Slice 006-01 DONE — active, auto-triggering; `tdd.py` helper for detect + run with normalized exit codes (0 green / 1 red / 2 env error), pytest/vitest/jest support, priority pytest > vitest > jest. | Yes (auto + explicit) |
| `/jig:slice-land` | Slice 007-01 DONE + slice 009-01 close-out fix DONE — active, auto-triggering; `land.py prepare` emits readiness report (status / tests / deviation log / DoD-with-close-out-exclusion) + mode-aware next-steps (direct or pr). Recognizes `### Close-out (post-DONE)` to skip post-DONE items in DoD count. No destructive git ops yet; 007-02/03 add those. | Yes (auto + explicit) |
| `/jig:migrate` | Slices 008-01 + 008-02 + 008-03 DONE — active, auto-triggering; `migrate.py report <dir>` (read-only 5-section migration report) + `migrate.py rename-decisions <dir> [--dry-run]` (applies ADR-0004's rename: dir + filename pad/prefix + bounded cross-reference rewriting, atomic, idempotent, refuses on conflict). Dogfooded by 008-03 (jig migrated itself). Sibling to scaffold-init (Tier 0). Future subcommand `slice-to-spec` (008-04) deferred. | Yes (auto + explicit) |

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
