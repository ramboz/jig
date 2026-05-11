---
name: memory-sync
description: >
  Persist new context, terms, learnings, and project knowledge to the memory layer
  (CLAUDE.md hot cache, docs/memory/, docs/inbox.md). Use when the user says remember
  this, save this for later, add to glossary, note this down, or at the end of a
  session to consolidate what was learned. Also auto-fires at session end to surface
  capture-worthy items. Do not use for updating specs, ADRs, or code comments —
  those have their own workflows.
user-invocable: true
---

> **Status: DRAFT — spec at [docs/specs/002-memory-layer/spec.md](../../docs/specs/002-memory-layer/spec.md)**
>
> Slice 002-01 (explicit-sync) is the next slice to implement.

## What this skill does (when implemented)

Follows the three-layer lookup/persist pattern:
```
hot cache (CLAUDE.md)
  ↓ miss
docs/memory/ search
  ↓ miss
ask the user
  ↓ answered
persist to the appropriate file
```

Persistence rules:
- High-frequency terms (≥3 references in a session) → `CLAUDE.md` Hot Cache section
- Niche/domain-specific terms → `docs/memory/glossary.md`
- Dead ends, failed approaches, "we tried X" → `docs/memory/learnings.md`
- Tool choices and reasoning → `docs/memory/tooling.md`
- Unresolved / not yet decided → `docs/inbox.md`

The `people.md` file (collaborators and context) is only present in team projects.

## Self-healing

If `docs/memory/` or `docs/inbox.md` don't exist (pre-scaffold-init project),
this skill creates them before writing. It does not require scaffold-init to have run.

## Gotchas

- The reviewer subagent explicitly cannot write to memory — defining the glossary
  is not the reviewer's job.
- `docs/inbox.md` is a parking lot, not a task list. Items there should be triaged
  during reconciliation: become a spec, become an ADR, or get dropped.
- The `jig-memory-scan` hook (UserPromptSubmit) and `jig-task-capture` hook (Stop)
  surface unknowns automatically. This skill handles the deliberate bulk-sync operation.
