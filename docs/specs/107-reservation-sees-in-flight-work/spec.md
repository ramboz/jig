---
status: IN_PROGRESS
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 107: Reservation sees work in flight

> From [issue #147](https://github.com/ramboz/jig/issues/147). Decision recorded
> in [ADR-0053](../../decisions/adr-0053-reservation-numbering-sees-in-flight-branches.md).

## Overview

Number reservation is supposed to stop two sessions claiming the same `NNN`.
Today it cannot, for two independent reasons, and both reduce to the same blind
spot: **the mechanism only sees work that has already reached `origin/main`.**

1. **The claim cannot be published by a contributor.** Reservation ends in a
   direct push to `main`. Under branch protection that push is refused, and the
   refusal is meant to fall back to a pull request. It never does —
   `_classify_push_failure` tests generic race markers before specific
   protection markers, and GitHub's protected-branch refusal always contains the
   word `rejected`. Every protection refusal is therefore reported as a race,
   and the caller is told to re-run, which fails identically every time.
   Maintainers bypass branch protection, so the push succeeds and the classifier
   is never reached — the defect is invisible to exactly the people who could
   fix it.

2. **A published claim is invisible to the next caller.** The next number is
   derived from the files present in one tree — the working copy, or
   `origin/main`. A reservation sitting on a branch or in an open pull request
   is in neither, so the next session computes the same number and no conflict
   ever surfaces, because the two records have different paths.

Fixing (1) without (2) hands a contributor a reservation pull request that
reserves nothing. Both are in scope.

**Observed three times in 24 hours** (full evidence in ADR-0053 § Context): two
sequential `adr.py new --pr` calls both allocated `adr-0047`
([#161](https://github.com/ramboz/jig/pull/161) /
[#162](https://github.com/ramboz/jig/pull/162)); this spec's own ADR reservation
allocated `adr-0047` a third time and was renumbered by hand; and bugs 015/016
were hand-resolved across [#143](https://github.com/ramboz/jig/pull/143) /
[#144](https://github.com/ramboz/jig/pull/144) /
[#145](https://github.com/ramboz/jig/pull/145).

**Out of scope**, at the maintainer's direction in
[#147](https://github.com/ramboz/jig/issues/147#issuecomment-5137532236):
contributions from forks (invisible to `origin`, accepted gap), and the
number-keyed atomic claim ref (ADR-0053 Option D — deferred behind a trigger in
`docs/refinement-todo.md`). Also out of scope: the status-board merge conflicts
from #143/#144/#145. Those are a rendering problem in a shared file, not a
numbering problem, and they survive this spec untouched.

## Assumptions

- **A1 — `git ls-tree` reads a remote-tracking ref without checking it out.**
  Probed 2026-07-31: `git ls-tree -r --name-only origin/<branch> -- docs/bugs/`
  returned listings for all 12 branches on `origin` from a linked worktree.
- **A2 — reservation branch names are not a usable index.** Probed 2026-07-31:
  2 of 12 `origin` branches match `refs/heads/reserve/*`; the numbers actually
  in flight sit on `claude/*` branches whose names carry no number. This is why
  slice 107-02 reads trees rather than ref names.
- **A3 — the protected-branch refusal text used in tests is captured, not
  recalled.** The existing fixtures were written from memory, omit the
  ` ! [remote rejected]` line real git always prints, and consequently pass
  against the bug. Replacing them is the regression test, not a tidy-up.

## Decomposition

SPIDR — split on **Rules** (how a push failure is classified) and **Data**
(where the next number is read from). The two are independent: each ships and is
verifiable alone, and 107-01 is the smaller, so it goes first.

- **Paths** — rejected as a split axis. The three helpers (`bug.py`, `adr.py`,
  `workflow.py`) carry the same logic and must not diverge; splitting per helper
  would land a repo in which two of three families behave differently.
- **Interfaces** — no user-facing surface changes. Same commands, same flags.

## Slices

- [107-01 — protection refusals reach the pull-request fallback](slice-01-protection-refusals-reach-the-fallback.md)
- [107-02 — numbering counts every in-flight branch](slice-02-numbering-counts-in-flight-branches.md)
