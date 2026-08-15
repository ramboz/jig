---
status: DONE
skill: spec-workflow
use_cases: []
---

# Spec 111: First-class blockers

> Reserved 2026-08-07 (as spec 108; renumbered to 111 on 2026-08-15 after 108 was
> taken by research-notes-convention). Shaped 2026-08-15 onto
> [ADR-0057](../../decisions/adr-0057-first-class-blockers-are-annotations.md).

## Overview

jig tracks lifecycle state (`DRAFT → … → DONE`, plus `DEFERRED`/`ABANDONED`) and
dependencies, but it has **no first-class notion of "this work is actionable but
stuck, and on what."** Consumers that want to answer *"how many blockers does
this project have right now?"* — the motivating case is the Gauge portfolio
dashboard's "blocked" count — must approximate from a grab-bag of proxies that
mostly mean **parked** or **ordered**, not **actively blocking**:

- `DEFERRED` slices carrying a `**Resolution trigger:**` line,
- deferred decisions in `docs/refinement-todo.md`,
- unmet slice `dependencies:`,
- the legacy Compass narrative `blockers` array (only present for
  legacy-Compass sources).

These conflate *"parked by choice, will resurface on a trigger"* (`DEFERRED`) and
*"not-yet-started ordering"* (`dependencies:`) with *"a live work item is stuck
waiting on X."* This spec builds the small, explicit convention ADR-0057 decides,
so the signal becomes honest and derivable.

## The decision (ADR-0057)

A **first-class blocker** is an **annotation on an actionable slice**, not a new
lifecycle state:

- **`blocked_by:`** — an optional frontmatter field naming what the slice is
  blocked on (free text in v1). Valid on an **actionable** slice:
  `READY_FOR_IMPLEMENTATION` (ready to start) or a working state
  (`READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED`). It is the
  machine-readable signal.
- **`**Blocked:**`** — a body line (same shape as `**Resolution trigger:**`)
  carrying the human explanation and the condition that would clear it.
- **Blocked count** = actionable-state slices with a non-empty `blocked_by:`.
- **Clearing** = remove the annotation (no separate trigger machinery).

A blocker is distinct from `DEFERRED` (parked *by choice*, not prevented) and from
`dependencies:` (not-yet-started slice-id ordering). See ADR-0057 for the
annotation-vs-state rationale and the "actionable, not started" boundary.

## Assumptions

- **A1 — jig has no existing `Blocked` / `blocked_by` convention (grounded by
  enumeration, 2026-08-15).** `grep -rIn 'blocked_by'` and `grep -rIn '\*\*Blocked'`
  across `docs/specs/**`, `skills/**`, `scripts/**` return empty (excluding this
  spec + ADR-0057); and the frontmatter keys the lifecycle code reads are closed
  by syntax to `status` / `frame_review` / `arch_review` / `code_health_review` /
  `design_review` / `dependencies` / `kind` / `claimed_by` (every one a literal
  `fm_fields.get("…")` in `workflow.py`) — `blocked_by` is genuinely new. Full
  detail in ADR-0057 A1.
- **A2 — the consumer's blocked count includes ready-but-stuck work (assumption,
  not grounded).** Gauge's exact count semantics were not probed (separate repo);
  the "actionable" boundary is chosen for the face-value reading. ADR-0057 A2
  carries the kill condition.

## Decomposition (SPIDR)

Two vertical slices, both delivering end-to-end value:

- **111-01 (Data + Interface):** the convention itself — `blocked_by:` frontmatter
  + `**Blocked:**` body line read by `collect_slices`, surfaced as a
  `## Blocked slices` section on the status board (mirroring `## Deferred
  slices`). End-to-end value: an author marks an actionable slice blocked and the
  board renders a clean, countable Blocked section. This is the consumer-visible
  value Gauge reads.
- **111-02 (Rules):** `spec_lint` validation — a soft warning when `blocked_by:`
  appears on a **non-actionable** slice (`DRAFT` / `DONE` / `DEFERRED` /
  `ABANDONED`), where it is almost certainly a misfiled dependency/deferral.
  Additive; depends on 111-01 (the convention must exist to validate it).

Rules/Data/Interface cover it — no Spike (the mechanism is a direct mirror of the
DEFERRED/ABANDONED rendering, already probed) and no Path split (a single happy
path: annotate → render/validate).

## Slices

- [111-01 — blocked-annotation-and-board](slice-01-blocked-annotation-and-board.md)
- [111-02 — spec-lint-validation](slice-02-spec-lint-validation.md)
