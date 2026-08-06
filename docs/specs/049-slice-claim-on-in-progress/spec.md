---
status: DONE
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 049: slice claim on IN_PROGRESS

## Overview

Spec 028 closed the parallel-worktree collision class for five shared
mutable artifacts (spec numbers, ADR numbers, status-board regen,
inbox / refinement-todo appends). It deliberately stopped at
helper-driven writes; **slice ownership itself** — i.e., which
worktree picked up which `READY_FOR_IMPLEMENTATION` slice — was not
in scope.

Today the status board renders a slice as `IN_PROGRESS` once
`workflow.py transition` flips its frontmatter, but the row does not
record **who/which worktree** owns it. Two parallel sessions reading
the board can both pick up the same slice and only discover the
collision at land/merge time — the same failure mode shape as the
spec-number collision spec 028-01 closed, one level up.

This spec extends the spec 028 reserve-on-main pattern to slice
ownership: transitioning a slice to `IN_PROGRESS` stamps a `claimed_by:`
identifier (worktree branch name) in the slice frontmatter and reserves
the transition on `origin/main` the same way `workflow.py new` reserves
spec numbers — with the same race-on-push classifier and PR fallback.

## Why now

- **Pattern is validated.** Spec 028-01 / 028-03 shipped the
  reserve-on-main + checksum-race-detection patterns. Extending to
  one more artifact is incremental work, not a new invention.
- **Empirical risk is present.** `git worktree list` regularly shows
  30+ active branches; the user reports running parallel sessions
  against the same project. The collision is not theoretical.
- **The cost compounds at land time.** Two contributors discovering
  they implemented the same slice differently surfaces at PR review
  or merge, after both have invested implementation effort. A
  refusal at `transition IN_PROGRESS` is much cheaper.
- **The status board already has a Notes column** that survives
  regen (spec 028-03 + 030-02). `claimed_by:` rendering has a
  natural home; no new column required.

## Goals

1. **`claimed_by:` field in slice frontmatter.** New optional field,
   set by `workflow.py transition <slice> IN_PROGRESS` to an identifier
   the helper can derive (lean: current git branch name). Cleared on
   `IN_PROGRESS → REVIEWED` and on any back-transition to
   `READY_FOR_IMPLEMENTATION` / `DRAFT`.
2. **Reserve-on-main on IN_PROGRESS transition.** Same shape as
   spec 003-03 / 028-01: commit the frontmatter change to
   `origin/main` with race-on-push classifier and PR fallback. If
   another worktree already claimed the slice, the helper refuses
   with a structured error naming the existing `claimed_by:`.
3. **Status board renders the claim.** `workflow.py status-board`
   surfaces `claimed_by:` for `IN_PROGRESS` rows — either as a
   suffix to the status cell (`IN_PROGRESS (wt-foo)`) or as a column.
   Pick one in the slice based on table-width impact.
4. **Refusal on stale claim.** `transition <slice> IN_PROGRESS`
   refuses if `claimed_by:` is already set to a different identifier
   AND the slice's `status:` is already `IN_PROGRESS`. Surface a
   "currently claimed by X; force-release with --release" instruction.
5. **`--release` escape hatch.** Allows an operator to manually
   release a stale claim (e.g., the original worktree was abandoned).
   Clears `claimed_by:` and resets `status:` to
   `READY_FOR_IMPLEMENTATION`.
6. **Race-on-push detection.** Same shape as spec 003-03's
   non-fast-forward handling: "I lost the race" (re-run) vs "I don't
   have permission" (PR-fallback). Don't conflate.
7. **Dogfood.** At least one slice in this spec is implemented from
   a session that exercises the new claim mechanism against a
   parallel session attempting to claim the same slice. Don't ship
   without proving the lock holds.

## Non-goals

- **No claim on `READY_FOR_IMPLEMENTATION` slices.** Claiming
  requires committing to start the work. Browsing the board doesn't
  reserve anything.
- **No multi-claim / assignment / queueing.** A slice has at most
  one `claimed_by:` at a time. No "assign to user X" semantics —
  the field is a runtime claim, not a planning artifact.
- **No human identity inference.** The identifier is the worktree
  branch name (or a `JIG_CLAIM_ID` env override), not the git
  author email or any cross-session human identity. Keeping this
  scoped to per-worktree avoids dragging in `people.md` semantics —
  that's spec 050's domain.
- **No protection for non-helper Edit-tool writes to slice
  frontmatter.** A human or agent that hand-edits a slice's `status:`
  with the `Edit` tool bypasses the claim. Same scope rule as spec
  028: this spec protects helper-driven transitions.
- **No claim on `DEFERRED` slices.** DEFERRED is parked-without-
  owner. Re-opening via `DEFERRED → DRAFT → READY_FOR_IMPLEMENTATION
  → IN_PROGRESS` re-runs the claim logic from scratch.

## Open questions

- **Identifier source.** Lean: `git rev-parse --abbrev-ref HEAD`
  (current branch name). Alternative: hostname + worktree dir basename
  (survives branch rename mid-work). Decide in the slice; lean toward
  branch name for parity with `workflow.py new`'s shape.
- **Status-board rendering.** Suffix-in-status-cell (`IN_PROGRESS
  (claude/foo)`) vs new column. Suffix is cheaper, less table churn;
  column is more scannable for projects with many in-flight slices.
  Lean suffix; revisit if it bloats the cell.
- **`--release` authorization.** Today the helper would accept any
  invocation with `--release`. Worth requiring an explicit
  `--reason "..."` string for the audit trail? Lean yes — cheap,
  logs into the deviation log naturally.
- **Atomicity vs. degraded mode.** If `origin/main` is unreachable
  (offline), should `transition IN_PROGRESS` refuse, or stamp
  `claimed_by:` locally with a warning? Lean: parity with `workflow.py
  new`'s `--no-push` flag — local-only claim is opt-in, default is
  refuse. Avoids surprise collisions when the network comes back.

## Decomposition

Two slices, sequenced. SPIDR Rules-axis split.

### Slices

- [049-01 — claim-and-release-on-transition](slice-01-claim-and-release-on-transition.md) — DRAFT
- [049-02 — status-board-claim-rendering](slice-02-status-board-claim-rendering.md) — DRAFT

## References

- **Originating conversation:** 2026-05-28 — review of jig's multi-
  contributor story. Slice-claim identified as the most natural
  one-level-up extension of spec 028.
- **Pattern precedent:** Spec 003-03 (reserve-on-main + PR fallback +
  race-on-push), spec 028-01 (same pattern for ADR numbering).
- **Adjacent spec:** Spec 050 (solo→team re-detection) — different
  mechanism, related theme. Kept separate because the code paths
  and reviewers don't overlap.
- **Doctrine:** Spec 028's "add locks narrowly where the failure
  mode was empirically observed." Slice-claim qualifies because the
  user empirically runs parallel worktrees against the same project.

## Amendments

> Post-DONE corrections/extensions per [ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md).
> The original spec above is preserved; dated entries below record reality.

### 2026-07-11 — `→ IN_PROGRESS` is no longer network-free (spec 051-04 start-collision guard)

049-01 established that the claim is **local by default (no network)** —
"preserves the everyday 'start a slice' UX." [Spec 051-04](../051-worktree-aware-reservation/slice-04-start-time-collision-guard.md)
(originating from [issue 81](https://github.com/ramboz/jig/issues/81)) **narrows
that default**: `transition … → IN_PROGRESS` now runs `git fetch origin main`
+ `git show origin/main:<slice>` to consult the authoritative origin/main copy
and hard-block a start-time collision (slice already `DONE`, or `IN_PROGRESS`
under a foreign `claimed_by`). The **claim stamp itself stays local** — only
the collision *check* fetches, and it degrades softly offline (silent for a
local-only repo / a fresh slice, a warning on a genuine fetch failure), so
starting a slice still works without a network. The reversal is deliberate:
issue 81 showed the "trust the local file" default let a parallel worktree
duplicate an entire landed slice, colliding only at merge. Bypass the new
fetch with `JIG_START_COLLISION_GATE=0`.

### 2026-07-24 — the claim spans the WORKING states, not `IN_PROGRESS` only (ADR-0045)

This spec's AC1 stamped `claimed_by:` only on `→ IN_PROGRESS`; its **AC4**
cleared it on `IN_PROGRESS → REVIEWED` and on the back-edges to
`READY_FOR_IMPLEMENTATION` / `DRAFT`. Its Non-goals scoped that deliberately:
*"No claim on `READY_FOR_IMPLEMENTATION` slices. Claiming requires committing to
start the work. Browsing the board doesn't reserve anything."*

[ADR-0045](../../decisions/adr-0045-slice-claim-covers-active-lifecycle.md)
**widens AC1's stamp, partially reverses AC4's clearing, and preserves that
Non-goal.**
[Bug 014](../../bugs/014-slice-claim-covers-only-in-progress.md) (from
[issue 130](https://github.com/ramboz/jig/issues/130)) showed the cost of the
`REVIEWED` clearing edge: jig routes agent sessions to work by reading slice
state, so a slice under spec review, frame-critique, or — worst —
`REVIEWED → RECONCILED` reconciliation carried no owner, and every pickup
surface read that silence as "free". A real incident had one session twice
recommend a `READY_FOR_REVIEW` slice as *"unblocked, unclaimed"* while another
session was working it. The phase that rewrites the most had the least ownership
signal, precisely because AC4 cleared the claim on the way into it.

**What changed.** The lifecycle now splits two ways for ownership:

- **Working states** — `READY_FOR_REVIEW`, `IN_PROGRESS`, `REVIEWED`,
  `RECONCILED` — **stamp** the claim. This is the reversal: `REVIEWED` no longer
  clears, and `READY_FOR_REVIEW` newly stamps.
- **Release points** — `DRAFT`, `READY_FOR_IMPLEMENTATION` (the pickup queue),
  plus the terminal `DONE` / `DEFERRED` / `ABANDONED` — **clear** it.
  `--release --reason` still force-clears anywhere.

**What did NOT change, and why it matters.** Two of AC4's three clearing edges
(`READY_FOR_IMPLEMENTATION`, `DRAFT`) survive untouched, and the Non-goal above
stands. A first cut of ADR-0045 widened the stamp to all six non-terminal states
and was **wrong**: `spec-workflow/SKILL.md` tells a reader to pick the next slice
from `READY_FOR_IMPLEMENTATION` (or `DRAFT`), so stamping those leaves the spec
author's branch name on a slice that is now free — the board labels every ready
slice with a departed owner, and the implementer's first `→ IN_PROGRESS` warns on
the routine path. That inverts bug 014 rather than fixing it. Caught by the
frame-critique pass and reproduced before narrowing.

**Refusal semantics unchanged.** AC3 still hard-refuses only when *both* ends
are `IN_PROGRESS` — two sessions building one slice. Every other foreign claim,
on your own copy or on `origin/main`, is a loud **non-blocking warning** naming
the holder (new); two sessions working one spec can be legitimate, and blocking
would manufacture false refusals.

**AC2 reserve-on-main, narrowed.** `--push` / `--pr` now reserves at any working
state, but its payload changed: `_reserve_claim_on_main` takes the transition's
target state and publishes trunk `status:` **only** for `IN_PROGRESS`. That one
write is load-bearing — spec 051-04's `_refuse_start_collision` reads exactly
`status: IN_PROGRESS` + a foreign `claimed_by` off `origin/main` — while
publishing any other state would regress the trunk's lifecycle view, which the
landing flow owns. Three invariants now live in `_reserve_claim_on_main`, not one: (a) the payload
rule above; (b) it warns before replacing a foreign trunk claim; and (c) it
**declines to write at all** when the trunk copy is at `status: IN_PROGRESS`
under a *different* identifier or none — that state is enforced by
`_refuse_start_collision`, so stamping a claim over it would move a live lock and
refuse the previous owner in the reserving session's name, or (unclaimed)
manufacture the enforced pair from the other direction. An own trunk claim falls
through to the benign idempotent no-op. `--push` at a working state other than
`IN_PROGRESS` is therefore **best-effort**: it can warn, push nothing, exit 0. Symmetrically, `_refuse_start_collision` warns (never
blocks) on a foreign trunk claim at a non-`IN_PROGRESS` working state, so a
pushed claim has a consumer instead of being written and ignored.

Still out of scope (unchanged): a local claim remains invisible to a worktree on
an unpushed branch — the separately parked push-by-default item in
[refinement-todo](../../refinement-todo.md), from issue 81. The reported incident
was two worktrees on separate branches, so **coverage alone does not close it**;
see ADR-0045 Context.
