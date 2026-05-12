---
name: spec-workflow
description: >
  Drive the spec-driven lifecycle for any non-trivial work item: SPIDR-split a
  new spec into vertical slices, transition state markers (DRAFT → READY_FOR_REVIEW
  → READY_FOR_IMPLEMENTATION → IN_PROGRESS → REVIEWED → RECONCILED → DONE), and
  enforce the reconciliation checklist before commit. Use when starting non-trivial
  new work, creating a spec, transitioning a slice's state, or reconciling a slice
  that's been reviewed. Do not use for quick one-off fixes that don't need a spec,
  or for bug-shaped work where `debug-workflow` is the better fit.
user-invocable: true
---

> Spec 003 promoted this skill from stub to active. The deterministic state
> mutations live in `workflow.py`; this SKILL.md drives the judgment layer.

## What this skill does

- Guides SPIDR-splitting a new spec into vertical slices (Spike last, not first —
  try Rules / Data / Interface / Path first).
- Flags slices that look like horizontal phasing (no user-facing layer touched).
- Drives the spec lifecycle state transitions via `workflow.py`.
- Coordinates implementer + reviewer subagent invocations at the right points.
- Enforces the reconciliation checklist before a slice goes DONE.
- Consults `docs/memory/glossary.md` when drafting ACs to surface unknown domain terms.

## How to use

### Creating a new spec

1. Confirm the work needs a spec. Trivial fixes don't.
2. Pick a number (next free `NNN-` slug under `docs/specs/`).
3. Create `docs/specs/NNN-<slug>/{spec.md,plan.md,tasks.md}` with the conventional
   structure: status frontmatter, overview, SPIDR analysis, ordered slices.
4. SPIDR-split: for each slice, the goal is **one vertical piece** that delivers
   end-to-end value. Spike is the last resort, not the first reach.
5. Set each slice's `**STATUS: DRAFT**` initially.
6. Add rows to `docs/specs/README.md` (or regenerate via `workflow.py status-board`).

### Picking up a slice

1. Check `docs/specs/README.md` for the next slice in `READY_FOR_IMPLEMENTATION`
   (or `DRAFT` for a slice you intend to plan now).
2. Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/spec-workflow/workflow.py" transition \
     "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>" IN_PROGRESS
   ```
3. Fill in / refresh `plan.md` and `tasks.md` for the slice.
4. Spawn the `implementer` subagent with the spec path. Implementer writes the
   deliverable to disk (TDD — failing tests first).

### After implementation

1. Spawn the `reviewer` subagent against the deliverable. Reviewer is read-only;
   it returns `pass | fail | needs-changes`.
2. Address reviewer findings, adding regression tests for any real bugs found.
3. Transition: `transition <spec.md> <slice> REVIEWED`.

### Reconciliation (REVIEWED → RECONCILED)

Walk the **Reconciliation checklist** below. Every item is a gate.

### Closing the slice

1. After reconciliation review passes:
   `transition <spec.md> <slice> RECONCILED`
2. Commit the work.
3. After commit: `transition <spec.md> <slice> DONE`
4. Regenerate the board: `workflow.py status-board <project-dir>`.
5. Run `/jig:memory-sync` (or `memory.py`) to consolidate any new learnings.

## Spec lifecycle states

```
DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION → IN_PROGRESS
  → REVIEWED → RECONCILED → DONE
```

Status transitions are mutations on `spec.md`'s `**STATUS: ...**` line and the
matching row in `docs/specs/README.md`. Use `workflow.py transition` for the
former and `workflow.py status-board` to re-sync the latter.

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

- **Spike is the LAST SPIDR technique** to reach for, not the first. AI agents
  default to spiking too eagerly; try Rules / Data / Interface / Path first.
- **Every slice must be vertical** (crosses all layers, delivers end-to-end value).
  A slice that touches only the DB or only the parser is horizontal phasing — flag it.
- **The reviewer subagent must NOT be invoked with prior implementation context.**
  Write the deliverable to disk first; reviewer reads only the spec + deliverable
  + acceptance criteria.
- **The reviewer is read-only on `docs/memory/`** — memory-sync runs as a separate
  step during reconciliation, never as part of review.
- **`workflow.py transition` uses substring matching on slice names** — `001-01`
  matches `## Slice 001-01 — greenfield-scaffold`. If you have multiple slices
  whose names share a fragment, the helper refuses with an `ambiguous` error;
  use a more specific fragment.
- **`workflow.py status-board` preserves the preamble** before the `| Spec` table
  header. Custom intro text survives regen. Idempotent: no churn if the board is
  already current. **Notes column** also survives regen (the helper parses existing
  Notes and re-emits them).
- **`workflow.py` ignores `## Spike` headers.** Spikes are research artifacts, not
  lifecycle-managed work items. They don't have a STATUS marker the helper can
  transition. If you need a spike to be tracked in the status board, model it as a
  `## Slice Nnna — <name>` instead, or update the board's Notes column manually.
- **Avoid raw `|` characters in the Notes column** of `docs/specs/README.md`.
  Markdown tables use pipes as cell separators; raw pipes in a Note value would
  truncate the cell during regen's preservation step. Use HTML-entity `&#124;`
  or rephrase if you really need a pipe.
