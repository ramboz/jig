---
slice: 051-01 — worktree-aware spec reservation
pass: craft
verdict: pass
reviewer: general-purpose (independent, no implementation context)
reviewed_at: 2026-06-02T17:23:00Z
prompt_source: independent review of the rescued detached-worktree reservation (commits fbb5d6f + b759cab); workflow.py + adr.py reservation paths
---

VERDICT: pass

REASONING:
The branch-routed reservation design is sound. The on-`main` in-place flow
(spec 003-03 + 037-02) is left byte-for-byte unchanged — the only new entry
point is a `_current_branch(project_dir) != "main"` dispatch at the top of
`reserve_spec` / `reserve_adr`, so the proven happy path cannot regress. The
off-main path builds the reservation commit in an ephemeral DETACHED worktree
checked out at `origin/main` (`git worktree add --detach <tmp> origin/main`),
which correctly sidesteps the one-checkout-per-branch rule that made the old
`HEAD==main` guard unsatisfiable from a linked worktree. The caller's cwd,
branch, and working tree are never touched, and the `--no-push` off-main path
commits provisionally on the current branch with a pathspec-scoped `git
commit -- <files>` so unrelated staged work is not swept in. The ephemeral
worktree is always torn down (`git worktree remove --force` + `shutil.rmtree`
+ `git worktree prune`) in a `finally`. The push-failure classifier (race vs
protection vs other) and PR-fallback are reused, not reimplemented; race
recovery on the off-main path is trivial because the stranded commit lives
only in the worktree the `finally` removes. Real-git E2E coverage is present
(relative-origin reservation; `--no-push` dirty-safety) in addition to the
stubbed-subprocess unit tests.

SPECIFIC ISSUES:
- [blocker] (FIXED — B1) The off-main push originally ran from inside the
  temp worktree (`cwd=wt`). That FAILS for any repo with a RELATIVE `origin`
  URL (e.g. `../origin.git`): git resolves the relative remote against cwd,
  and the temp worktree sits outside the repo tree, so the remote name does
  not resolve. GitHub https/ssh remotes are absolute, so the common case
  worked and masked the bug. Fix applied in commit b759cab: resolve the
  reservation commit's SHA in the worktree, then push it BY SHA from
  `project_dir` (where `origin` resolves; the objects are in the shared
  store). Applied to both `_reserve_via_detached_worktree` and
  `_pr_fallback_from_worktree` in `workflow.py` and `adr.py`, with a
  real-git relative-origin E2E test that fails before the fix
  ("'../origin.git' does not appear to be a git repository") and passes
  after.
- [nit] (FIXED) Three stale `_preflight_branch_and_worktree` references
  (the old combined preflight name) were left in comments/messages after the
  branch check moved to the `_current_branch` dispatch; corrected in b759cab.
- [nit] (FIXED) Added `git worktree prune` to the `finally` so a stale
  `.git/worktrees/` admin entry cannot accumulate if `worktree remove` ever
  fails.

RECONCILIATION NOTES:
- The mechanism is inline-mirrored between `workflow.py` and `adr.py` rather
  than extracted to a shared helper. This is a deliberate deviation from
  spec 051-02 AC #2 (which assumed a shared primitive): there are only two
  callers, and ADR-0002's extraction trigger is three. Recorded in ADR-0015
  and the 051-01 / 051-02 deviation logs.
- The implementation chose spec 051 Open-question option (B) "Ephemeral
  detached reservation", not the leaned-toward (A) plumbing-commit
  (`git commit-tree`). Both reach the same end state; (B) reuses the
  familiar worktree + commit + push shape. Recorded in ADR-0015.
- The land-time collision guardrail (spec 051-03) is NOT part of this
  change; slice 051-03 stays DEFERRED.

Provenance: independent review of the rescued reservation work
(commits fbb5d6f rescue + b759cab B1-fix); full suite green at 1935 tests, OK.
