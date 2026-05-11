---
name: spec-workflow
description: >
  Manage the spec lifecycle for a work item: SPIDR splitting, vertical slice enforcement,
  state transitions, and Definition of Done checks. Use when starting non-trivial new
  work, creating a spec, reviewing spec readiness, or transitioning a spec from one
  lifecycle state to another (DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION →
  IN_PROGRESS → REVIEWED → RECONCILED → DONE).
  Do not use for quick one-off fixes that don't need a spec, or for bug fixes
  that fit the debug-workflow instead.
disable-model-invocation: true
user-invocable: true
---

> **Status: DRAFT — not yet implemented.**
> This skill is planned in the jig roadmap but not ready for use.
> See [docs/specs/001-scaffold-init/spec.md](../../docs/specs/001-scaffold-init/spec.md)
> for the first active spec.

## What this skill does (when implemented)

- Enforces SPIDR splitting (Spike last, not first — try Rules/Data/Interface/Path first)
- Anti-horizontal-phasing guardrail: flags slices that don't touch the user-facing layer
- Manages spec lifecycle state transitions with hook-enforced gates
- Includes a memory-sync step during the reconciliation phase
- Consults `docs/memory/glossary.md` when drafting ACs to surface unknown domain terms

## Spec lifecycle states

```
DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION → IN_PROGRESS
  → REVIEWED → RECONCILED → DONE
```

## Gotchas

- Spike is the LAST SPIDR technique to reach for, not the first.
- Every slice must be vertical (crosses all layers, delivers end-to-end value).
  A slice that touches only the DB is horizontal phasing — flag it.
- The reviewer subagent must NOT be invoked with prior implementation context.
  Write deliverable to disk first; reviewer reads only spec + deliverable + ACs.
