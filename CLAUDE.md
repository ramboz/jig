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
- 002-memory-layer: **complete** (all 4 slices DONE)
- 003-spec-workflow-promotion: slice 003-01 (lifecycle-helper) **DONE**; spec-workflow promoted from stub to active. Slices 003-02 (anti-horizontal-phasing-check) and 003-03 (new-spec-scaffolding) explicitly deferred.
- 002-memory-layer: STATUS DRAFT — slice 002-01 (explicit-sync) queued

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

Building Tier 0 skills. Starting with scaffold-init (spec 001) and memory-layer (spec 002).

## Skills in this repo

| Skill | Status | Invocable |
|---|---|---|
| `/jig:scaffold-init` | Spec 001 fully implemented (slices 001-01..001-05 all DONE) | Yes (explicit) |
| `/jig:memory-sync` | Spec 002 fully implemented (all 4 slices DONE) | Yes (explicit) |
| `/jig:spec-workflow` | Slice 003-01 DONE — active, auto-triggering; `workflow.py` helper for state transitions + status-board sync | Yes (auto + explicit) |
| `/jig:independent-review` | DRAFT — stub only | Yes (stub — shows DRAFT warning) |
| `/jig:contracts` | DRAFT — stub only | Yes (stub — shows DRAFT warning) |

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
