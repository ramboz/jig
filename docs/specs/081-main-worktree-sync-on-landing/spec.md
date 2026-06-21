---
status: IN_PROGRESS
skill: slice-land
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 081: Main worktree sync on landing

> Reserved on 2026-06-20 via `workflow.py new`. Body to be drafted in a feature branch.

## Overview

Spec 051 and ADR-0015 made spec and ADR number reservation work from
linked worktrees by treating `origin/main` as the coordination authority.
That solved the "I cannot check out `main` here" problem, but it left a
nearby operational gap: after a slice lands to `origin/main`, the canonical
local `main` worktree can still sit behind the remote tip.

That stale local `main` is not the authority for correctness, but it still
matters. Humans inspect it, older host adapters may fork worktrees from it,
and agents use it as a mental cue for "what has landed." When it lags after
landing, a later session can start from a half-true world: the remote has the
reservation or reconciled slice, while the visible local checkout does not.

The desired landing invariant is:

> A landing is complete only after the change has reached `origin/main` and
> the canonical local `main` worktree has been fast-forwarded to that same
> commit, or the tool has explicitly reported why that final sync could not
> be performed.

This spec does not change the reservation authority. `origin/main` remains
the source of truth. The new behavior is local housekeeping after the
authoritative push succeeds.

## Goals

1. **Post-land sync is automatic.** The direct landing path attempts to
   fast-forward the local worktree that has `refs/heads/main` checked out
   after it successfully pushes to `origin/main`.
2. **The caller's worktree is untouched.** A landing invoked from a linked,
   detached, or feature worktree never tries to switch that worktree to
   `main`.
3. **Fast-forward only.** The sync path fetches `origin/main` and updates the
   canonical `main` worktree only with a fast-forward operation. It never
   creates a merge commit, rebases unrelated local work, or discards local
   changes.
4. **Local sync failure is visible.** If the canonical `main` worktree is
   missing, dirty, locked, diverged, or otherwise unavailable, the landing
   result says exactly that while preserving the fact that `origin/main`
   already received the authoritative push.
5. **Workflow docs name the invariant.** `docs/workflow.md` and the
   slice-landing guidance explain the post-land sync step and distinguish it
   from reservation correctness.

## Non-goals

- **No new reservation protocol.** Spec 051 / ADR-0015 remain the mechanism
  for spec and ADR number reservation from worktrees.
- **No guarantee that every worktree updates.** Only the canonical local
  `main` worktree is synced. Existing feature worktrees keep their current
  heads.
- **No destructive cleanup.** Dirty or diverged `main` worktrees are reported,
  not reset.
- **No dependency on local `main` for landing correctness.** The successful
  push to `origin/main` is still the authoritative landing event.

## Assumptions

- `git worktree list --porcelain` can identify the local worktree whose
  branch is `refs/heads/main`.
- The landing helper already has one or more chokepoints that run after the
  authoritative `origin/main` push succeeds.
- Protected-main / PR-shaped landings may not be able to sync local `main`
  until the PR is actually merged. That case should be reported rather than
  pretending the sync happened.

## Decomposition

SPIDR split: **Path**. The value is a single landing-path behavior change:
after the remote landing transaction completes, the tool performs the local
main-worktree sync or reports why it cannot.

## Slices

- [081-01 — post-land main worktree sync](slice-01-post-land-main-worktree-sync.md)

## References

- [Spec 051: worktree-aware number reservation](../051-worktree-aware-reservation/spec.md)
- [ADR-0015: Worktree-aware number reservation](../../decisions/adr-0015-worktree-aware-reservation.md)
- [Workflow: worktree baseline](../../workflow.md)
