---
status: DRAFT
dependencies: [adr-0058]
last_verified:
arch_review: true
frame_review: true
---

## Slice 112-01 — classa-land-backstop

**Goal:** Introduce the shared cross-ref lifecycle-state primitive and wire its
first consumer — a Class-A blocker in `land.py prepare` that refuses GO when the
slice/ADR being landed is already `DONE`/`Accepted` on `origin/main` (or a merged
ancestor). Delivers, end-to-end, a false-positive-free stop against re-landing
already-integrated work.

**DoR:**
- ✅ ADR-0058 Accepted (done).
- ✅ Access to `origin/main` for the read (best-effort; the gate degrades to a
  non-blocking warning when the base ref is unreachable).

**Acceptance Criteria:**

1. **New primitive `identifier_state_on_ref(identifier, ref)`** (home:
   `skills/_common/`) returns the lifecycle marker (`DONE`/`Accepted`/… or
   `absent`) for a slice (`NNN-MM`) or ADR (`NNNN`) on a given git ref, matching
   on the **number**, not the filename (survives a renamed slug). Reads via
   `git show <ref>:<path>`; returns `absent` when the file is not on that ref.
2. **`land.py prepare` gains a fifth blocker.** When the slice under land (or its
   linked ADR) is already `DONE`/`Accepted` on `origin/main`, `prepare` reports a
   Class-A blocker and exits non-zero (GO refused), naming the ref and the
   integrated state. Folded into the existing `has_blocker` computation.
3. **False-positive guard:** the gate does **not** fire on the normal case where
   the identifier is absent from `origin/main` or is at an equal/earlier state.
   The one legitimate `DONE`-on-main case (sanctioned re-open / supersession) is
   passable via the deliberateness bypass (AC5).
4. **Best-effort:** when `origin/main` cannot be resolved/read (offline, no
   remote), the check emits a non-blocking warning and does not fail `prepare`
   — consistent with `_branch_freshness_warning`'s posture.
5. **Bypass:** `JIG_CROSSREF_GATE=0` (also `false`/`off`/`no`) skips the Class-A
   blocker, logged like jig's other gate bypasses (ADR-0011). Exact env name may
   be reconciled with existing `JIG_*` naming during implementation.
6. **Host-package parity:** `land.py` and any new `_common` helper are vendored
   into `hosts/`; the slice regenerates host copies so CI drift stays green.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Tests exercise: integrated-DONE → refuse; absent → pass; equal/earlier →
      pass; unreachable-base → warn-not-fail; bypass set → pass. Number-match
      across a renamed slug covered.
- [ ] Each new test shown to fail when its feature is removed.
- [ ] Reviewed by `reviewer` subagent (compliance + craft; arch pass — this
      slice introduces a shared primitive and extends the land-gate contract).
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, a developer running
`land.py prepare` on a branch that duplicates already-integrated work gets an
explicit refusal instead of a GO — an observable, end-to-end behavior change at a
real command, not internal scaffolding.

### Deviation log (after reconciliation)

_TBD at implementation._

### Reconciliation sweep

_TBD at reconciliation._
