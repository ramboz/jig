---
status: DONE
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 051: worktree-aware number reservation

> **Implementation status (2026-06-02).** Slices **051-01** (spec reservation,
> `workflow.py new`) and **051-02** (ADR reservation, `adr.py new`) are
> **DONE** on branch `rescue/reservation-from-worktree` (commits `fbb5d6f`
> rescue + `b759cab` B1-fix). The reservation mechanism is recorded in
> [ADR-0015](../../decisions/adr-0015-worktree-aware-reservation.md) (Accepted).
> Slice **051-03** (land-time collision guardrail) is **DEFERRED** — it was not
> built in this change. **Retro provenance:** the implementation was first
> written by a mis-configured session directly on `main` and left uncommitted;
> it was rescued onto this branch, then independently reviewed and hardened
> (one blocker, B1 = relative-origin push failure, found and fixed). This spec
> is updated after the fact to record what shipped.

## Overview

Spec 028 / spec 003-03 built reserve-on-`origin/main` for spec
numbers (`workflow.py new`) and ADR numbers (`adr.py new`) to close
the parallel-session numbering-collision class. The mechanism works —
but only from the **primary** checkout. Its preflight
(`_preflight_branch_and_worktree`, `workflow.py:1092`; the twin in
`adr.py`) hard-refuses unless `git symbolic-ref --short HEAD` is
literally `main`:

```
refusing: current branch is 'claude/<...>', must be 'main'
(reservation lands on main; switch with `git checkout main`)
```

The remediation it suggests — `git checkout main` — is **impossible
inside a linked git worktree**: git forbids two worktrees from holding
the same branch (`fatal: 'main' is already used by worktree at ...`).
Since every parallel Claude session runs in a `.claude/worktrees/*`
worktree on a `claude/*` branch, `new` can never run there. The
safety mechanism is dead code in the exact workflow it was built for.

The fallback humans/agents reach for is hand-picking the next number
off a stale local view of `docs/specs/` — which is precisely the
collision spec 028 set out to prevent.

## Why now

This is not theoretical; it is the live failure mode, with evidence:

- **Reservation commits stop at 042.** `git log origin/main | grep
  reserve` shows clean `reserve NNN-slug` commits from 023→042, then
  nothing. Specs 043–048 were all introduced by hand "draft" commits
  (including `c7ad0b0 docs(specs): draft specs 045-047` — three
  numbers in one commit, the opposite of one-at-a-time reservation).
  The cutover coincides with parallel-worktree work becoming the norm.
- **ADRs were never reserved at all.** Zero `reserve adr` commits
  exist on `origin/main`; every ADR arrived in a content commit.
- **Two collisions hit in a single session (2026-05-29).** ADR-0010
  was independently claimed by two worktrees (tier-gating vs
  amendment-scope); ADR-0011 by a third; specs 045/046 were
  hand-numbered in the `silly-kilby` worktree against numbers already
  taken on main, forcing a renumber to 049/050 at rescue time.
- **"main is protected" is a red herring.** A direct push to `main`
  succeeded this session, so the push-refusal failure mode recorded in
  `docs/memory/learnings.md` (the ADR-0008 working-tree-only incident)
  is a *different*, secondary issue — not what's biting now. The
  primary cause is the unsatisfiable `HEAD==main` precondition.

Diagnosis captured via `debug-workflow` (diagnose mode), 2026-05-29.

## Goals

1. **Reservation runs from any branch / worktree.** `workflow.py new`
   and `adr.py new` reserve a number on `origin/main` without
   requiring the local `HEAD` to be `main` and without requiring the
   worktree to be the primary checkout.
2. **Zero disturbance to the caller's working state.** Reserving does
   not switch the worktree's branch, move `HEAD`, or stage/modify the
   caller's unrelated uncommitted work. (This also retires the
   clean-worktree precondition, which is hostile to in-flight worktree
   sessions.)
3. **Number computed from a fresh `origin/main`.** The next-free
   number is derived from `git fetch origin main` + the `origin/main`
   tree, not the local `docs/specs/` view — closing the stale-view gap
   that produces collisions.
4. **Push-failure classification preserved.** The existing
   non-fast-forward ("lost the race" → drop stranded state, re-run)
   vs protection/permission ("can't push" → PR-fallback) split
   (spec 003-03 / 028-03) carries over unchanged. Race-on-push still
   drops the stranded reservation cleanly.
5. **Reserved file lands in the caller's working tree.** After a
   successful reservation, the new `spec.md` / `adr-NNNN-*.md` is
   present in the worktree so the session can immediately edit it.
6. **A defense-in-depth guardrail catches collisions that slip
   through.** A pre-land check (`land.py prepare`) greps the branch's
   spec/ADR numbers against `origin/main` and refuses (or warns) on a
   clash — covering hand-edits, `--no-push` local reservations, and
   offline work that never reserved.

## Non-goals

- **No change to the reservation *semantics* beyond reachability.**
  The artifact shapes (`docs(specs): reserve NNN-slug`, the ADR
  scaffold) and the PR-fallback flow stay as designed; this spec
  changes *where you can invoke from*, not what gets written.
- **No protection for non-helper writes.** Same scope rule as spec
  028: a human/agent that hand-creates a spec dir with the `Write`
  tool bypasses reservation. Goal #6's guardrail is the backstop, not
  a hard lock.
- **No retroactive renumbering of the existing collisions.** ADR-0010
  (this session's amendment-scope ADR) and any in-flight worktree
  collisions are resolved case-by-case by their owners, not by this
  spec.
- **No offline reservation guarantee.** If `git fetch origin main`
  fails (no network), reservation refuses by default; `--no-push`
  remains the explicit opt-in for local-only number assignment, with
  the Goal #6 guardrail catching the eventual collision.
- **No change to `transition` / `status-board` / `stale`.** Scoped to
  the `new` reservation path + the land guardrail. (But see
  References: spec 049's reserve-on-`IN_PROGRESS` inherits the same
  flaw and should adopt this mechanism.)

## Open questions

- **Reservation mechanism (load-bearing — ADR in 051-01). RESOLVED →
  option (B), recorded in
  [ADR-0015](../../decisions/adr-0015-worktree-aware-reservation.md).**
  Three candidates were weighed:
  - **(A) Plumbing commit, no checkout.** Build the reservation commit
    against `origin/main`'s tree with `git commit-tree` (+ a temp
    index for the added file), then `git push origin <sha>:main`.
    Touches neither `HEAD` nor the index nor the working tree. Cleanest
    on Goal #2, but uses lower-level git plumbing.
  - **(B) Ephemeral detached reservation — CHOSEN.** Build the
    reservation commit in an ephemeral **detached** worktree checked out
    at `origin/main` (`git worktree add --detach <tmp> origin/main`),
    push it BY SHA from `project_dir`, then tear the worktree down. Same
    end state as (A); reuses the familiar worktree + commit + push shape
    instead of lower-level plumbing. The spec originally leaned (A); the
    implementation chose (B) — recorded as a deviation in ADR-0015 and the
    051-01 deviation log.
  - **(C) Relax the preflight only.** Allow any branch, commit the
    reservation onto the *current* branch, push `HEAD:main`. Simplest
    diff, but pollutes the feature branch with the reservation commit
    and risks pushing unrelated commits — rejected for push mode, but
    adopted (scoped) for the `--no-push` provisional path only.
- **Guardrail strictness (051-03).** Refuse (exit non-zero) vs warn on
  a detected number collision at land time. Lean refuse for spec/ADR
  *number* clashes (cheap to fix, expensive if merged), warn for
  softer drift. Revisit if it produces false positives on legitimate
  renumbers.
- **`--no-push` from a worktree.** Should local-only reservation still
  fetch `origin/main` first to at least pick a number unlikely to
  collide? Lean yes — fetch-then-pick-locally is strictly better than
  the current stale-local-view pick even when not pushing.

## Decomposition

Three slices. SPIDR Interface-axis split — the same mechanism lands on
three distinct surfaces (spec-number CLI, ADR-number CLI, land
guardrail). 051-01 establishes the mechanism (and its ADR); 051-02
mirrors it into `adr.py`; 051-03 is the independent backstop.

### Slices

- [051-01 — worktree-aware spec reservation](slice-01-worktree-aware-spec-reservation.md) — DONE
- [051-02 — worktree-aware ADR reservation](slice-02-worktree-aware-adr-reservation.md) — DONE
- [051-03 — land-time collision guardrail](slice-03-land-time-collision-guardrail.md) — DEFERRED

## References

- **Originating diagnosis:** 2026-05-29 `debug-workflow` (diagnose
  mode) session. Leading cause ~90%: unsatisfiable `HEAD==main`
  precondition in a worktree-based workflow. Evidence in "Why now".
- **Pattern precedent:** spec 003-03 (reserve-on-main + PR fallback +
  race-on-push), spec 028-01 (same for ADR numbering), spec 028-03
  (status-board race classifier).
- **Code under change:** `skills/spec-workflow/workflow.py`
  (`_preflight_branch_and_worktree`, `cmd_new`, `_classify_push_*`),
  `skills/adr-workflow/adr.py` (twin preflight + `cmd_new`),
  `skills/slice-land/land.py` (`prepare`).
- **Enables:** spec 049 Goal #2 (reserve-on-`IN_PROGRESS`) shares the
  reservation path and inherits the same worktree blocker; it should
  depend on / adopt 051-01's mechanism rather than re-deriving it.
- **Secondary, out of scope:** the push-refused → working-tree-only
  silent-failure mode (`docs/memory/learnings.md`, ADR-0008 / slice
  036-01 incident). Real, but distinct from the `HEAD==main` blocker.
- **Dogfood note:** this spec was itself hand-numbered (051) because
  `workflow.py new` refused to run in the authoring worktree — the
  exact defect it fixes.
