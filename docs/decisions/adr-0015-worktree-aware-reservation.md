---
dependencies: []
last_verified: 2026-06-02
---

# ADR-0015: Worktree-aware number reservation — branch-routed reserve, detached worktree off main

## Status

Accepted (2026-06-02)

Drafted under [spec 051-01](../specs/051-worktree-aware-reservation/slice-01-worktree-aware-spec-reservation.md)
(the slice's DoR calls for the reservation mechanism to be recorded as an
ADR before implementation, since it sets the pattern slice 051-02 mirrors).

This ADR **supersedes the deferred decision** in
[`docs/refinement-todo.md`](../refinement-todo.md) titled *"`workflow.py
new` / `adr.py new` refuse on non-main branches, defeating reserve-on-main
when work originates on a feature branch"* — that entry is now marked
RESOLVED and linked here.

## Context

[Spec 003-03](../specs/003-spec-workflow-promotion/spec.md)
(spec numbers, `workflow.py new`) and
[spec 028-01](../specs/028-parallel-session-locks/slice-01-adr-numbering-on-main.md)
(ADR numbers, `adr.py new`) built reserve-on-`origin/main`: claim a
sequential number by committing a stub and pushing it to `origin/main`, so
parallel sessions cannot both grab the same `NNN`/`NNNN`. The mechanism
works — but both helpers' preflight **hard-refused unless the current branch
was literally `main`** (the reservation commit lands on local `main`, so the
helper insisted on being there), and on refusal advised `git checkout main`.

That guard is **structurally unsatisfiable from a linked git worktree**. Git
permits a branch to be checked out in exactly one worktree at a time, so a
linked worktree can *never* be on `main` — the primary worktree holds it.
The suggested remedy is impossible there too: `git checkout main` in a
linked worktree fails with `fatal: 'main' is already used by worktree at
...`. Because jig's own workflow is worktree-per-task (every parallel
session runs in a `.claude/worktrees/*` worktree on a `claude/*` branch),
**the reservation tool was incompatible with the exact workflow jig
prescribes** — dead code in the place it was built to serve.

The fallback humans and agents reached for — hand-picking the next number
off a stale local `docs/specs/` view — is precisely the collision the
reservation flow was built to prevent. It bit repeatedly:

- **Spec 021 → 022 renumber (2026-05-15).** A feature-branch session was
  refused reservation up front ("must switch to main first"), continued
  without reserving, parallel work landed `021-migrate-copy-machinery` on
  `origin/main` in the meantime, and the feature branch had to rename
  `021-contracts/` → `022-contracts/` at merge time (propagating the
  renumber across slice files, deviation logs, CLAUDE.md, ADR-0005, and
  test labels).
- **ADR-0010 → 0012 renumber (2026-05-29).** A tier-gating ADR was created
  *locally* in a worktree (reserve-on-main being unusable off-main);
  meanwhile two other worktrees independently claimed `ADR-0010`
  (amendment-scope) and `ADR-0011` (spec-gate) on `main`. At land time the
  tier-gating ADR had to be renumbered to **0012** across 13 files, then
  rebased onto the advanced main.

The deferred refinement-todo entry recorded this as a known gap and named
three candidate fixes; this ADR settles the choice.

## Decision Options Considered

The shape of the fix is "how do we land a reservation commit on
`origin/main` without being on `main` and without disturbing the caller's
worktree." Four options:

### Option (a): Temporary worktree at main — **CHOSEN** (refined to `--detach`)

Build the reservation commit in a throwaway worktree of `main`, push, then
remove the worktree. The caller's checkout, branch, and working tree are
never touched. A *plain* `git worktree add <path> main` hits the same
one-checkout-per-branch wall (`main` is already held by the primary
worktree), so the refinement is to add the worktree **detached at
`origin/main`** — `git worktree add --detach <tmp> origin/main` — which
checks out no branch and therefore sidesteps the rule entirely.

- **Pros:** Cleanest on the "zero disturbance" goal — cwd never leaves the
  feature branch's working tree. Reuses the proven push / race / PR-fallback
  classifiers. Detached HEAD makes the one-checkout-per-branch rule
  irrelevant.
- **Cons:** Adds a temp-worktree dependency to the helper, and a teardown
  obligation (must always remove the worktree, even on failure).

### Option (b): Auto-fast-forward the feature branch first — REJECTED

Fast-forward the current branch's pointer to `origin/main`, commit the
reservation on it, push, merge back.

- **Cons:** *Impossible from a linked worktree* for the same reason — you
  cannot fast-forward onto `main` while another worktree holds it — and it
  moves the user's branch tip silently, surprising a caller who was not
  ready to FF. Fails the zero-disturbance goal.

### Option (c): Push to a side-ref, fast-forward main later — REJECTED

`git push origin HEAD:refs/heads/reserve-<NNN-slug>` and ask `origin` to FF
`main` when ready.

- **Cons:** Opens a **collision window** between the side-ref push and the
  eventual FF: a second reservation can claim the same number unless the
  number-scan *also* reads the outstanding reservation refs — extra
  machinery, and the window is exactly what reservation exists to close.

### Option (d): Unify everything onto the worktree path — DEFERRED

Drop the on-`main` in-place path and always reserve via the worktree
mechanism, even from the primary checkout.

- **Pros:** Simpler long-term (one code path instead of two).
- **Cons:** Changes the proven on-`main` behavior and churns the
  battle-tested [spec 037-02](../specs/037-git-origin-safety/slice-02-reserve-against-origin.md)
  code for no functional gain today. Deferred — revisit only if maintaining
  two paths becomes a real burden.

## Recommended Decision

**Reservation routes on the current branch (keep-the-split), with the
off-main path using an ephemeral detached worktree at `origin/main`.**

`reserve_spec` / `reserve_adr` read `git symbolic-ref --short HEAD` and
dispatch:

- **On `main`** (primary worktree, clean tree): the proven in-place flow
  from spec 003-03 + spec 037-02 runs **unchanged** — commit on local
  `main`, fetch + divergence preflight, push `origin main`, race / protection
  classification, PR-fallback.
- **Off `main`** (feature branch / linked worktree), push mode: reserve
  inside an ephemeral **detached** worktree checked out at `origin/main`
  (`git worktree add --detach <tmp> origin/main`), build the stub commit
  there, push it to `origin/main`, then tear the worktree down. The caller's
  cwd, branch, and working tree are never touched. Race on push → discard the
  temp worktree + emit a re-run message (the stranded commit lives only in
  the worktree, so no `reset --hard` is needed); protected branch → push the
  commit to a `reserve/<...>` branch and `gh pr create`.
- **Off `main` with `--no-push`**: a *provisional* reservation committed on
  the current branch. The number is computed from the local working tree, so
  it may collide at merge time — the commit is **pathspec-scoped** so it
  cannot sweep in unrelated staged work (worktree sessions are usually
  mid-edit; the old clean-tree refusal is gone for this path).

This keeps the well-understood on-`main` path intact while making the
*off-main* case — the one jig's workflow actually puts you in — a first-class
flow. The mechanism is **inline-mirrored** between `workflow.py` and `adr.py`
rather than extracted to a shared helper — there are two callers, and
[ADR-0002](./adr-0002-contracts-stays-deferred.md)'s extraction trigger is
*three* callers needing the same helper (a bar
[ADR-0003](./adr-0003-extract-find-slice-section.md) reaffirmed). The
original reservation helpers (spec 028-01) already inline-mirror spec 003-03
under this same precedent, so the worktree-aware additions follow suit. (This
is a deliberate deviation from spec 051-02 AC #2, which assumed a shared
extracted primitive — noted in that slice's deviation log.)

### The relative-origin lesson (push by SHA from project_dir)

An independent review of the rescued implementation found one blocker (B1):
the off-main push originally ran from inside the temp worktree (`cwd=wt`),
which **fails for any repo with a RELATIVE `origin` URL** (e.g.
`../origin.git`) — git resolves the relative remote against cwd, and the
temp worktree sits outside the repo tree, so the remote name does not
resolve. GitHub https/ssh remotes are absolute, so the common case worked
and masked the bug. The fix: resolve the reservation commit's SHA in the
worktree, then **push it by SHA from `project_dir`** (where `origin`
resolves correctly) — the commit's objects already live in the shared
object store, so the SHA is reachable from the primary tree. This is
recorded here because it is the kind of mistake the next person to touch the
worktree path will otherwise repeat.

## Consequences

**Becomes easier:**

- Reservation works **identically from `main`, a feature branch, or a linked
  worktree** — the helper is finally usable from where jig's worktree-based
  workflow actually puts the developer, closing the 021→022 / ADR-0010→0012
  class of land-time renumbers.
- The caller's working tree is **never disturbed** — no branch switch, no
  `HEAD` move, no stash dance, no sweeping of unrelated staged work.

**Becomes harder / the costs:**

- The off-main push must go **by SHA from `project_dir`**, not from the temp
  worktree, or relative-`origin` repos break (the B1 lesson above). This is a
  non-obvious invariant the worktree path now carries.
- The ephemeral worktree is a teardown obligation: it is always removed in a
  `finally` (`git worktree remove --force` + `shutil.rmtree` + `git worktree
  prune`) so a stale `.git/worktrees/` admin entry cannot accumulate even if
  `remove` fails.
- Two reservation code paths (on-main in-place vs off-main detached) now
  coexist; option (d) (unify) is deferred against the day that split becomes
  a maintenance burden.

**Honest caveat (defense-in-depth, not a hard lock).** This is *best-effort*
serialization. True collision-avoidance still relies on `origin/main` being
the single push target every reservation races against; a human or agent who
hand-creates a spec dir / ADR file with the `Write` tool (or reserves
`--no-push` locally) bypasses it. That is the same scope boundary
[ADR-0011](./adr-0011-spec-gate-model.md) (spec-gate) and
[ADR-0013](./adr-0013-security-floor-policy.md) (security floor) draw: the
in-process mechanism is a deliberateness/convenience floor, and the durable
backstop is out-of-band (the land-time collision guardrail named as spec
051-03, plus CI / branch protection).

## Open questions

- **Should the on-main and off-main paths eventually unify (option d)?**
  Deferred — revisit only if maintaining the two paths proves a real burden.
- **`--no-push` collision exposure.** A `--no-push` off-main reservation
  picks its number from the local tree and can still collide at merge time.
  The intended backstop is the land-time collision guardrail (spec 051-03,
  not built on this branch); until then `--no-push` numbers are explicitly
  provisional.
