---
status: Proposed
dependencies: [adr-0015]
last_verified: 2026-07-31
frame_review: true
---

# ADR-0053: Reservation numbering reads every in-flight branch, not just origin/main

## Status

Proposed (2026-07-31)

Drafted under [spec 107](../specs/107-reservation-sees-in-flight-work/spec.md),
from [issue #147](https://github.com/ramboz/jig/issues/147). The mechanism is
shared by three helpers, so it is recorded before implementation the way
[ADR-0015](adr-0015-worktree-aware-reservation.md) was.

This ADR **narrows [ADR-0015](adr-0015-worktree-aware-reservation.md)** rather
than superseding it. ADR-0015 decided *where the reservation commit is built*
(an ephemeral detached worktree at `origin/main`, so reservation works from a
linked worktree) and that decision stands. This ADR changes *what the number is
computed from* and *where the claim is published* — the two things ADR-0015 left
pointed at `origin/main` alone.

## Context

Reservation exists to stop two sessions claiming the same `NNN`. It has two
halves, and both are broken in the same direction: they can only see work that
has already reached `origin/main`.

**Half one — the claim can't be published.** ADR-0015's flow ends in `git push
origin <sha>:refs/heads/main`. Under branch protection that push is refused, and
the refusal is meant to route to a PR fallback. It doesn't:
`_classify_push_failure` checks generic race markers before specific protection
markers, and GitHub's protected-branch refusal always contains the substring
`rejected`:

```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: error: Changes must be made through a pull request.
 ! [remote rejected] abc1234 -> main (protected branch hook declined)
```

So every protection refusal is reported as a race, and the caller is told to
re-run — which fails identically, forever. Maintainer accounts bypass branch
protection, so the direct push succeeds and the classifier is never consulted;
contributors without bypass hit it on every reservation. Same code, opposite
experience. `GH013` (repository rulesets, GitHub's current mechanism) is not
recognised at all.

**Half two — the claim, once published, is invisible anyway.** `_next_number`
(bugs), `_next_spec_number` (specs) and `_adr_files` (ADRs) derive the next id
from the files present in one tree: the local working copy, or `origin/main`.
An in-flight reservation — a pushed branch, an open PR — is in neither. So the
next session computes the same number. Following the mechanism as designed means
merging a reservation PR *before* starting work, which nobody does.

Half two is the load-bearing one: fixing half one alone gets a contributor a
reservation PR that reserves nothing.

**Observed, three times, in twenty-four hours:**

- **2026-07-31, PRs [#161](https://github.com/ramboz/jig/pull/161) /
  [#162](https://github.com/ramboz/jig/pull/162).** Two sequential `adr.py new
  … --pr` calls — same session, same machine, no concurrency — both allocated
  `adr-0047`. The first reservation was sitting on
  `reserve/adr-0047-frontmatter-summary-over-prose`, which the second call's
  `origin/main` view cannot see. Two ADRs, one number, two open PRs, and no
  merge conflict at any point: the files have different paths, so git has
  nothing to complain about.
- **2026-07-31, this ADR.** Reserving a number for this very decision,
  `adr.py new … --no-push` allocated `adr-0047` a third time. Renumbered to
  0053 by hand after scanning the branches — the workaround this ADR exists to
  remove.
- **2026-07-30, bugs 015/016** ([#143](https://github.com/ramboz/jig/pull/143) /
  [#144](https://github.com/ramboz/jig/pull/144) /
  [#145](https://github.com/ramboz/jig/pull/145)) — three bug records appended
  within one afternoon, numbers hand-resolved at merge time.

The failure is silent by construction. Nothing conflicts, nothing fails, and the
duplicate is only visible once both records are on `main`.

## Decision Options Considered

### Option A: Fix the push classification only (issue #147 directions 1 + 2)

Check protection markers before race markers; add `GH013` / `repository rule
violations`; replace the hand-typed test fixtures with captured git stderr.

- **Pros:** Small and self-contained — three helpers plus their host mirrors.
  Makes the PR fallback reachable for contributors for the first time.
- **Cons:** Fixes half one only. The contributor now gets a reservation PR that
  reserves nothing, because the next session's numbering still can't see it.
  Necessary, not sufficient.

### Option B: List reservation branch names (`git ls-remote origin 'refs/heads/reserve/*'`)

Reservation branch names are deterministic (`reserve/bug-NNN-<slug>`,
`reserve/adr-NNNN-<slug>`, `reserve/NNN-<slug>`), so the names alone carry the
numbers. One network call, no fetch, no tree reads.

- **Pros:** Cheapest possible read. Works under branch protection.
- **Cons:** Only sees numbers claimed through the `--pr` path. A number claimed
  on an ordinary working branch — which is how nearly all of jig's own numbers
  are claimed — is invisible, because those branches are named
  `claude/github-issue-140-63ae37`, not `reserve/…`. Probed on 2026-07-31: of
  the 12 branches on `origin`, exactly 2 matched `refs/heads/reserve/*`, and
  both were the accidental duplicates above. This was the reporter's own first
  suggestion in #147 and it does not survive contact with the branch list.

### Option C: Read the docs tree of every in-flight ref (chosen)

At numbering time, enumerate local branches and remote-tracking branches, read
each one's `docs/<bugs|specs|decisions>/` listing with `git ls-tree`, and take
the maximum across all of them plus the working tree.

- **Pros:** Sees every claim regardless of how the branch is named or whether a
  PR was opened. Needs no merge, no branch-naming convention, and no push to a
  protected branch. Uses refs already present after a `git fetch`, so the cost
  is one network round-trip plus cheap local reads.
- **Cons:** Needs a fetch to be current, so numbering acquires a network
  dependency it did not have. Scans O(branches) trees. Stale branches hold their
  numbers indefinitely, so the sequence develops gaps.

### Option D: Number-keyed atomic claim ref

As C, but the claim is pushed to a ref named for the number alone
(`refs/heads/reserve/bug-024`, slug excluded). A second claimant's push is
refused as non-fast-forward, reads that as "taken", and retries at the next
number.

- **Pros:** Restores the one property the push-to-`main` flow had that C does
  not — a single winner. Works under branch protection, since it is a side
  branch.
- **Cons:** Adds a push to the numbering path, which is what made reservation
  unreachable in the first place. Only closes a window that C narrows from days
  to seconds.

## Recommended Decision

**Option C, with Option A folded in.**

1. **Numbering input becomes every in-flight ref.** The next number is
   `max(number seen in the working tree, on any local branch, on any
   remote-tracking branch) + 1`. Implemented once in
   `skills/_common/reservation.py` and consumed by all three helpers — the third
   caller, so per [ADR-0023](adr-0023-lifecycle-family-spine.md) this is an
   extraction rather than a coincidence.
2. **A best-effort fetch precedes the scan**, and every git failure in the scan
   degrades to the local view with a warning on stderr. Numbering never fails
   because the network is down; it gets narrower and says so.
3. **Publication is the branch push that already happens.** Pushing the working
   branch is what makes a claim visible to everyone else, and it is permitted
   under branch protection. No push to `main` is required for a number to count
   as taken.
4. **The push classifier is corrected** (Option A) rather than deleted. Specific
   markers beat generic ones, `GH013` and `repository rule violations` join the
   protection set, and the bare `rejected` race marker is dropped — with
   protection checked first it matches every remaining failed push and routes
   genuine unknown failures into "re-run this", which is advice that cannot
   work. Fixtures become captured multi-line git stderr.

**Explicitly out of scope**, both at the maintainer's direction in
[#147](https://github.com/ramboz/jig/issues/147#issuecomment-5137532236):

- **Fork branches.** A contributor without write access pushes to their fork,
  which `origin` never sees, so they keep today's behaviour. Accepted gap —
  "let's see if and when it hits".
- **Option D's atomic ref.** Deferred pending evidence that the narrowed window
  actually fires — "let's wait and see how frequently this fires in the end".
  Recorded in [`docs/refinement-todo.md`](../refinement-todo.md) with a
  resolution trigger, not dropped.

## Consequences

**Becomes easier:**

- A contributor without branch-protection bypass can reserve a number that
  actually holds, which has never worked.
- A number claimed on any branch — reservation branch, working branch, local
  branch not yet pushed — counts as taken. This is the failure from
  #161/#162 and it stops being reachable.
- Reservation no longer depends on writing to `main`, so the protected-branch
  path stops being the mechanism's single point of failure.

**Becomes harder:**

- Numbering reads the network. It is best-effort and degrades loudly, but "the
  next number" is no longer a pure function of the working tree, which makes it
  harder to reason about offline and in tests. Tests pin the degraded path
  explicitly.
- Numbers develop gaps. An abandoned branch holds its number until the branch is
  deleted. Anything assuming a dense sequence breaks; nothing in the repo does
  today (probed: the boards render whatever ids exist).
- The scan is O(branches) `git ls-tree` calls. At 12 branches this is
  milliseconds; at several hundred it would want a cap.

## Assumptions

- **`git ls-tree` reads a remote-tracking ref without checkout.** Verified
  2026-07-31: `git ls-tree -r --name-only origin/<branch> -- docs/bugs/` returned
  listings for all 12 branches on `origin` from this worktree.
- **`git fetch` is the only network step and is read-only.** It updates
  `refs/remotes/*` and writes nothing to the remote.
- **Reservation branch names are not a reliable index.** Verified 2026-07-31:
  2 of 12 `origin` branches match `refs/heads/reserve/*`; the numbers actually
  in flight live on `claude/*` branches. This is what rules out Option B.
- **GitHub's protected-branch refusal contains `rejected`.** Taken from a
  captured refusal, not from memory — the captured text becomes the test
  fixture, which is the point of direction 2.

## Kill criteria

- **A fetch-dependent numbering step proves too slow or too flaky in practice.**
  If the fetch materially delays reservation or fails often enough that the
  degraded local path becomes the normal path, the scan should move behind an
  explicit `--scan` flag or to a cached ref list.
- **Duplicate numbers keep appearing after this ships.** That would mean the
  narrowed window in Option C is the live failure mode, not the blind input —
  which promotes Option D from deferred to required.
- **Branch count grows past the point where an O(branches) scan is sensible.**
  A repo with hundreds of live branches wants a different index.
