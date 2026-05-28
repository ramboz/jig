---
status: IN_PROGRESS
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 037: Compare against origin, not local refs (land.py + workflow.py)

## Overview

Two helpers compare against *local* git refs when they should compare
against `origin/<ref>`. Both are recoverable today (push fails, user
retries), but the recovery is non-obvious and the documented design
intent is "team-wide reservation / safe FF merge" — which requires
origin awareness. `land.py execute --mode direct` is a destructive
path users actually run.

A third related gap: `reserve_spec`'s preflight refuses dirty
worktrees but not diverged-from-origin local main. A user with
unpushed commits *and* a fetched `origin/main` ahead of them gets a
push failure later, not an upfront refusal.

## Why now

- **Highest-blast-radius live bug in the repo.** `_execute_direct`
  has no rollback path on push failure; the user is left on a
  half-merged local main with no recovery hint.
- **All four failures verified live on 2026-05-26.** See Current
  state below for line refs.
- **The classifier and the race-recovery in `reserve_spec` already
  exist** (workflow.py:1190 / 1356) — the fix is upstream of them:
  prevent the failure in the first place by reading from origin.

## Goals

1. **`_check_ff_viable` reads `origin/main`.** Fetches first, then
   verifies the FF condition against `origin/main`, not local `main`.
   Refuses with a clear message when local is behind origin. Network
   failure during fetch degrades to a warning + local check (matches
   `reserve_spec` precedent).
2. **`_execute_direct` adds a rollback path** on push failure.
   Either prints the recovery command and refuses to proceed, or
   performs `git reset --hard origin/main` after explicit
   acknowledgement. Lean: print + refuse (destructive helpers
   should not silently reset).
3. **`reserve_spec` scans `origin/main` for next-number computation**
   when push mode is on. Uses `git ls-tree --name-only origin/main
   docs/specs/` instead of `os.listdir(specs_dir)`. For `--no-push`,
   scans the working tree (no remote contract to honor).
4. **`reserve_spec` preflight refuses diverged main.** When local
   main is behind `origin/main` (after fetch), refuse with "pull or
   rebase before reserving" rather than letting the push fail.

## Non-goals

- **No new tooling.** All fixes are inside existing helpers.
- **No change to the "must be on main" rule.** The reserve-from-feature-
  branch gap (see `refinement-todo.md` "`workflow.py new --from-branch`")
  is a separate cluster. Out of scope here.
- **No re-opening of slice 007-02's deferred safety items.**
  Slice 007-02 (direct-mode-execute) is DONE, not DEFERRED — but its
  deviation log explicitly punted on hardening the destructive git
  path ("filed for slice 007-02 to tighten when actually executing"
  was a worktree-detection note; the broader safety-surface concerns
  were never formally captured). This spec absorbs those concerns
  without re-opening 007-02. No status change to 007-02.
- **No rewrite of `_classify_push_failure`.** Classifier handles
  post-failure routing fine; the issue is preventing the failure.

## Current state (verified 2026-05-26)

| Bug | Code location | Current behavior | Required behavior |
|---|---|---|---|
| 1. FF check | `skills/slice-land/land.py:562` (`_check_ff_viable`) | `git merge-base --is-ancestor main <branch>` — local main | Read `origin/main` after fetch |
| 2. No rollback | `skills/slice-land/land.py:729–748` (`_execute_direct`) | Pushes; on failure appends "Error" and breaks; no rollback hint | Print recovery command, refuse to leave half-merged state |
| 3. Reservation scan | `skills/spec-workflow/workflow.py:977` (`_next_spec_number`) | `specs_dir.iterdir()` — working tree | `git ls-tree origin/main` when in push mode |
| 4. Preflight | `skills/spec-workflow/workflow.py:1109` (`_preflight_branch_and_worktree`) | Refuses off-main + dirty; doesn't check ahead/behind | Add diverged-from-origin check |

The misleading comment at `workflow.py:1269` ("Fetch origin/main first
so the next-number scan reflects the freshest state") needs updating
once bug 3 is fixed — today the fetch updates the ref but the scan
ignores it.

## Decomposition

**Suggested SPIDR axis: P (Path)** primary — the two helpers
(`land.py` / `workflow.py`) are independent code paths.

### Slices

1. **[`037-01 land-ff-against-origin`](slice-01-land-ff-against-origin.md)**
   — `_check_ff_viable` fetches and verifies against `origin/main`;
   `_execute_direct` prints a recovery hint on push failure (no
   auto-rollback). Regression tests against a simulated stale-
   local-main repo.
2. **[`037-02 reserve-against-origin`](slice-02-reserve-against-origin.md)**
   — `_next_spec_number` reads `origin/main` via `git ls-tree` in
   push mode; preflight refuses on diverged local main. Race
   classifier remains as the last-resort catch.
3. *(maybe)* **`037-03 shared-origin-helper`** — only if slices 1
   and 2 converge on identical "fetch + verify + handle four failure
   modes" shape. ADR-0002's "three callers" rule applies; with only
   two callers, lean: leave duplicated.

Slices 1 and 2 are independent. Slice 1 has higher user-impact
(destructive path) — queue it first.

## Open questions for `/jig:clarify`

- **Q1.** Should `_execute_direct` perform the rollback automatically,
  or print the recovery command and refuse? Lean: print + refuse.
  Destructive helpers should not silently reset.
- **Q2.** What if `git fetch` itself fails? `reserve_spec` warns +
  proceeds on local view (line 1280). `_check_ff_viable` should do
  the same — warn, proceed on local refs, document the degraded path.
- **Q3.** Does slice 007-02 (direct-mode-execute) need any status
  change to reflect that 037 absorbs its deferred safety concerns?
  Spec body originally claimed 007-02 was DEFERRED, but it's DONE —
  the safety concerns lived in its deviation log, not in a parked
  slice. Lean: no status change; 037 absorbs the concerns without
  touching 007-02.

## Dependencies / coordination

- **None upstream from other external-review clusters.** Can run
  in parallel with 035, 036, 038, 039.
- **Light coupling with `refinement-todo.md`'s "race-on-disk" entry**
  — resolving slice 2 may close it.
- **Light coupling with DONE slice 007-02's deviation log** — see Q3.

## References

- External review brief: [`brief-03-git-origin-safety.md`](../../external-review/brief-03-git-origin-safety.md)
- Verification 2026-05-26: all four bugs confirmed live.

## Clarifications

### Q1: When `_execute_direct` finishes the local FF merge but the subsequent `git push` to origin fails, what should it do?
_(category: Edge Cases & Failure Modes)_

Print recovery + refuse. Append a clear recovery command (e.g. `git reset --hard origin/main` or `git push` retry hint) to the report and exit non-zero. No automatic state change. Matches "destructive helpers should not silently reset".

### Q2: When `git fetch origin main` itself fails (network down, auth issue, etc.) inside `_check_ff_viable`, what should the helper do?
_(category: Edge Cases & Failure Modes)_

Warn + proceed on local. Emit a warning explaining the degraded check, then run the existing `--is-ancestor` against local `main`. Mirrors `reserve_spec`'s precedent at workflow.py:1280. Lets offline land happen but flags the risk.

### Q3: Slice 007-02 (direct-mode-execute) — does it need any status change to reflect that 037 absorbs its deferred safety concerns?
_(category: Dependencies & Blockers)_

**Note:** Q3 was originally framed against a false premise — spec body claimed 007-02 was DEFERRED, but on verification it is DONE. The safety concerns lived in 007-02's deviation log, not in a parked slice. Corrected resolution: no status change to 007-02. Spec 037 absorbs the concerns without re-opening or superseding the slice. Spec body's non-goal and dependency-coordination notes were rewritten to match.

### Q4: What if the repo has no `origin` remote at all, or `origin/main` doesn't exist locally (fresh clone with no fetch yet, local-only repo)? This affects both `_check_ff_viable` and the new `_next_spec_number` push-mode scan.
_(category: Edge Cases & Failure Modes)_

Treat as `--no-push` / local-only. If `origin` is absent, fall through to existing local-tree behavior (working-tree scan for spec numbers; local main ancestor check for FF). Land helper still proceeds with the local merge; no push attempted. Matches reserve_spec's existing `--no-push` pathway.

### Q5: Goal 4 (preflight refuses diverged main) and Goal 1 (FF check refuses behind-origin) both add new refusal paths. Should they use a distinct exit code from existing dirty/off-main refusals, or share?
_(category: Acceptance Criteria Testability)_

Share existing refusal exit code. Same non-zero exit code as today's dirty-tree and off-main refusals. Differentiation lives in the stderr message (e.g. "local main is N commits behind origin/main — pull or rebase first"). Simpler contract; tests assert on message content, not code.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Clear |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Resolved |
| Non-functional Requirements | Partial |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |
