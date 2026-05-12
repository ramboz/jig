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
- Drives the reconciliation phase via an explicit checklist (see below)
- Consults `docs/memory/glossary.md` when drafting ACs to surface unknown domain terms

## Spec lifecycle states

```
DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION → IN_PROGRESS
  → REVIEWED → RECONCILED → DONE
```

## Reconciliation checklist

When a slice transitions `REVIEWED → RECONCILED`, walk this checklist before the
status flip is allowed. Each item is a gate.

- [ ] **Deviation log** — write what changed during implementation and why,
      under a "Deviation log (after reconciliation)" subsection of the slice
      in `spec.md`. Original ACs preserved above; deviations append, not overwrite.
- [ ] **Architecture impact** — did module boundaries or public contracts change?
      If yes, update `docs/architecture.md` AND write an ADR.
- [ ] **Conventions impact** — did this slice introduce or change a rule worth
      recording? If yes, edit `docs/conventions.md` (requires
      `JIG_CONVENTIONS_APPROVED=1`).
- [ ] **Inbox triage** — sweep `docs/inbox.md` for items resolved by this slice;
      move them to the relevant memory file or strike them through.
- [ ] **Memory-sync** — run `/jig:memory-sync` (or invoke `memory.py` directly)
      to persist any new domain terms, dead-end learnings, or tool decisions
      that emerged during implementation. **This is where slice 002-04's
      integration lives**: the reconciliation phase explicitly surfaces
      memory-worthy items for persistence. The reviewer subagent reads from
      memory but never writes to it (see `agents/reviewer.md`).
- [ ] **Reconciliation review** — spawn a second reviewer subagent with a
      reconciliation-review prompt: are the doc changes faithful? Is the
      deviation log honest? Is scope appropriate (no scope creep in docs)?
- [ ] **Commit** — only after all gates pass.

## Gotchas

- Spike is the LAST SPIDR technique to reach for, not the first.
- Every slice must be vertical (crosses all layers, delivers end-to-end value).
  A slice that touches only the DB is horizontal phasing — flag it.
- The reviewer subagent must NOT be invoked with prior implementation context.
  Write deliverable to disk first; reviewer reads only spec + deliverable + ACs.
- The reviewer is **read-only on `docs/memory/`** — memory-sync runs as a
  separate step during reconciliation, never as part of review.
