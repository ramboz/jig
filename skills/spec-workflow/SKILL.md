---
name: spec-workflow
description: >
  Drive the spec-driven lifecycle for any non-trivial work item: SPIDR-split a
  new spec into vertical slices, transition state markers (DRAFT → READY_FOR_REVIEW
  → READY_FOR_IMPLEMENTATION → IN_PROGRESS → REVIEWED → RECONCILED → DONE; also
  DEFERRED for parked slices with a stated resolution trigger), enforce the
  reconciliation checklist before commit, and surface stale specs/ADRs whose
  `last_verified` date has aged past dependency changes. Use when starting
  non-trivial new work, creating a spec, transitioning a slice's state,
  parking a slice as DEFERRED, reconciling a reviewed slice, or auditing
  doc freshness. Do not use for quick one-off fixes that don't need a spec,
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
2. **Reserve the next free number on origin/main:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/spec-workflow/workflow.py" new <slug>
   ```

   The helper computes `max(NNN) + 1` across `docs/specs/`, writes a
   minimum stub `docs/specs/NNN-<slug>/spec.md` (frontmatter + Overview
   + SPIDR-analysis headers), commits it as
   `docs(specs): reserve NNN-<slug>`, and pushes to `origin/main`. If
   the push is refused by branch protection / permissions, the helper
   automatically falls back to a `reserve/NNN-<slug>` branch + `gh pr
   create`. This locks the number **team-wide** before any drafting
   begins, killing the parallel-worktree spec-number-collision failure
   mode logged across specs 014/015/016/017. Run it from a clean main.

   Flags: `--no-push` for solo machines without a remote (commit
   locally only, never touch fetch/push); `--pr` to skip the
   direct-push attempt on protection-locked main.

   For projects without remote access — or when you'd rather pick the
   number by hand — you can still `mkdir docs/specs/NNN-<slug>/` and
   write `spec.md` directly; `workflow.py new` is the convenience path,
   not a gate.
3. Create `docs/specs/NNN-<slug>/{spec.md,plan.md,tasks.md}` with the conventional
   structure: status frontmatter, overview, SPIDR analysis, ordered slices.
4. SPIDR-split: for each slice, the goal is **one vertical piece** that delivers
   end-to-end value. Spike is the last resort, not the first reach.
5. For each new slice, use the template at
   `templates/docs/specs/slice-template.md` — it ships the canonical
   frontmatter shape (`status`, `dependencies`, `last_verified`) plus
   DoR / AC / DoD / Close-out sections. Set `status: DRAFT` in the
   frontmatter. Legacy slices that use prose `**STATUS: DRAFT**` markers
   still work (lazy migration); no need to rewrite them.
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

         DEFERRED ⇄ DRAFT  (parked slices with a stated resolution trigger)
```

Status transitions are mutations on either `spec.md`'s frontmatter `status:`
field (new convention, slice 015-01) or the prose `**STATUS: ...**` line
(legacy — still supported via lazy migration), AND the matching row in
`docs/specs/README.md`. Use `workflow.py transition` for the spec mutation
and `workflow.py status-board` to re-sync the board.

### DEFERRED state

A slice is `DEFERRED` when scoped but parked — the work is identified but
not the current priority. Different from `DRAFT` which means "not yet
fleshed out." Transitions:

- Any state → `DEFERRED` is allowed.
- `DEFERRED` → `DRAFT` (re-open) is allowed.
- `DEFERRED` → any other state is **refused** — re-open via DRAFT first
  so review gates aren't silently skipped. This is the first
  FROM-state-restricted transition in jig's lifecycle.

When transitioning a slice to `DEFERRED`, add a `**Resolution trigger:**`
line in the slice body (same convention `docs/refinement-todo.md` uses).
The status-board renders deferred slices in a separate `## Deferred slices`
section with that trigger as the per-row context.

### Slice frontmatter (slice 015-01 convention)

New slices written from `templates/docs/specs/slice-template.md` use a
typed frontmatter block right after the `## Slice ...` heading:

```yaml
---
status: DRAFT
dependencies: [007-02, adr-0004]
last_verified:
---
```

- `status` — current lifecycle state. `workflow.py transition` updates
  this when present.
- `dependencies` — flow-style list of slice fragments (e.g. `007-02`)
  and ADR IDs (e.g. `adr-0004`). `transition <slice> DONE` refuses if
  any listed dependency is not DONE / accepted.
- `last_verified` — date the slice was last reconciled. `transition`
  stamps this automatically on `→ RECONCILED`. Used by `stale`.

Legacy slices using prose `**STATUS:**` markers still work — the
transition helper writes to whichever shape is present. No retroactive
mass migration; new slices use the template, old slices stay as-is.

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

### Auditing staleness (`workflow.py stale`)

Slice 015-03 added a read-only freshness audit:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/spec-workflow/workflow.py" stale \
  [--project-dir DIR] [--days N]
```

Walks `docs/specs/*/spec.md` and `docs/decisions/adr-*.md`, extracts
`last_verified` + `dependencies` from frontmatter, and lists items
meeting the **conjunctive criterion**:

> An item is stale iff (a) `today - last_verified > --days` (default 90)
> AND (b) at least one file referenced by `dependencies` was modified
> since `last_verified`.

Pure age isn't enough — a verified-2-years-ago ADR for an unchanged
decision shouldn't fire. Pure recency-of-dep isn't either — a doc
verified yesterday with old deps is fine. Both conditions must hold.

The check uses `git log -1 --format=%cs <path>` for committed-state
authority and falls back to filesystem mtime when git is unavailable
or the file isn't tracked. Read-only: it lists, doesn't transition.
Bumping `last_verified` is a deliberate human/agent action — edit the
file, or re-run `transition <slice> RECONCILED` after re-verifying.

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
  Notes and re-emits them). **Deferred slices** appear in a separate `## Deferred
  slices` table below the active table; only the active table preserves Notes.
- **`workflow.py` ignores `## Spike` headers.** Spikes are research artifacts, not
  lifecycle-managed work items. They don't have a STATUS marker the helper can
  transition. If you need a spike to be tracked in the status board, model it as a
  `## Slice Nnna — <name>` instead, or update the board's Notes column manually.
- **Avoid raw `|` characters in the Notes column** of `docs/specs/README.md`.
  Markdown tables use pipes as cell separators; raw pipes in a Note value would
  truncate the cell during regen's preservation step. Use HTML-entity `&#124;`
  or rephrase if you really need a pipe.
- **`DEFERRED → DONE` (or any non-DRAFT state) is refused.** Re-open the
  slice with `DEFERRED → DRAFT` first, then advance through the normal
  lifecycle. This prevents silently skipping review gates when a parked
  slice is picked back up.
- **`transition <slice> DONE` validates `dependencies:`.** If any
  listed dep slice isn't DONE or any listed ADR isn't Accepted, the
  helper refuses with a structured error naming each unsatisfied dep.
  Empty / missing `dependencies:` skips the check.
