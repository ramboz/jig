---
status: DONE
dependencies: [049-01, 051-01]
last_verified: 2026-07-11
arch_review: true
---

## Slice 051-04 — start-time claim-collision guard (→ IN_PROGRESS)

> Originates from [issue 81](https://github.com/ramboz/jig/issues/81)
> ("check branch freshness + duplicate claims at slice *start*"). Observed
> twice: a parallel worktree built an entire slice already `DONE` on
> `origin/main`, colliding only at `git merge` time. Extends spec 051's
> reserve-on-`origin/main` mechanism from *number reservation* onto the
> `transition … → IN_PROGRESS` *claim* path (see spec Amendments +
> References/Enables, which already anticipated spec 049's claim adopting
> this mechanism).

**Goal:** `workflow.py transition <spec> <slice> IN_PROGRESS` consults the
authoritative `origin/main` copy of the slice *before* an agent starts
building — hard-blocking when that copy is already `DONE` (about to duplicate
landed work) or `IN_PROGRESS` under a foreign `claimed_by` — so a
parallel-worktree collision surfaces at *start*, not at merge.

**Context (root cause, from issue 81 + code):**
- `_branch_freshness_warning()` (the `git fetch origin main` +
  `HEAD..origin/main` count) is gated on `new_status in {"REVIEWED",
  "RECONCILED"}` (`workflow.py:1209`) — i.e. only at *finish*. Default
  `→ IN_PROGRESS` does **zero** network work.
- The on-disk claim guard (`workflow.py:1220`) refuses a foreign claim only
  when the **local** frontmatter already reads `IN_PROGRESS`. A stale local
  `DRAFT` file trips nothing.
- `_reserve_claim_on_main()` (`workflow.py:3576`) *does* read the
  `origin/main` copy under `--push`/`--pr`, but refuses only on a foreign
  **IN_PROGRESS** claim — it has **no `DONE` branch**, so the primary
  scenario is unguarded even in push mode (and push-by-default would
  *regress* a `DONE` slice to `IN_PROGRESS` on `origin/main`).

**DoR:**
- ✅ Root cause confirmed against code (refs above); reproduced conceptually
  from issue 81's two occurrences.
- ✅ House style for remote-dependent checks is established — block only when
  the remote is actually read; degrade to a warning when it is unreachable
  (`_branch_freshness_warning` no-origin/fetch-fail soft path; slice 051-03
  AC4).
- ✅ The remote-read primitive already exists (`git show origin/main:<path>`
  + `parse_frontmatter`, inside `_reserve_claim_on_main`) — this slice reuses
  its shape, it does not invent a new fetch mechanism.
- ✅ Both open questions resolved at authorship (see Resolved decisions):
  hard-block on `DONE`; bypass named `JIG_START_COLLISION_GATE=0`.

**Acceptance Criteria:**

1. **Remote read at start.** On `transition … → IN_PROGRESS` for a
   frontmatter-bearing slice, the command fetches `origin/main` and reads the
   slice's `origin/main` copy (`git show origin/main:<rel_path>` + frontmatter
   parse) — reusing `_reserve_claim_on_main`'s remote-read shape, not the
   generic `_branch_freshness_warning`.
2. **Hard-block on landed work.** If the `origin/main` copy's `status:` is
   `DONE`, the transition is refused, naming the slice and stating the local
   file is stale — i.e. "about to duplicate a slice already landed on
   `origin/main`; integrate `origin/main` before starting."
3. **Hard-block on foreign active claim.** If the `origin/main` copy is
   `IN_PROGRESS` under a `claimed_by` different from this session's
   identifier, the transition is refused — mirroring the on-disk foreign-claim
   refusal against the authoritative remote copy, naming the holder and the
   `--release` remedy.
4. **No false block on normal cases.** Proceeds (exit 0, stamps the claim)
   when: the slice is **absent** on `origin/main` (brand-new local slice); the
   origin copy is `DRAFT` / `READY_*` / `DEFERRED`; or the origin copy is
   `IN_PROGRESS` under **this same** identifier (idempotent re-claim).
5. **Offline-degrade to warning.** If `git fetch origin main` fails, or there
   is no `origin` remote, or the `origin/main` copy cannot be parsed for a
   reason other than "absent", the command emits a loud warning
   ("start-collision check skipped: <reason>") and **proceeds** — it must not
   block a transition merely because the remote is unreachable (parity with
   slice 051-03 AC4 and `_branch_freshness_warning`).
6. **`_reserve_claim_on_main` `DONE` gap closed.** The push-mode reservation
   path (`--push`/`--pr`) additionally refuses when the `origin/main` copy is
   `DONE`, so no claim push can regress a landed slice's status from `DONE`
   back to `IN_PROGRESS` on `origin/main`. (Standalone defect found reviewing
   issue 81.)
7. **Prose-only slices unaffected.** Legacy no-frontmatter slices — where the
   claim machinery is already a no-op — take no new remote read and transition
   exactly as before.
8. **Bypass is explicit + audited.** The block is bypassable only via an
   explicit `JIG_START_COLLISION_GATE=0` (also `false`/`off`/`no`, mirroring
   `JIG_REVIEW_EVIDENCE_GATE`), never silently. When bypassed, a
   content-free bypass line is emitted (parity with the review-evidence gate's
   `emit_gate_bypass` audit trail).

**Edge cases to cover explicitly:**
- Remote copy is `DONE` **and** still carries a stale `claimed_by`: the `DONE`
  block wins (clearer message than the foreign-claim message).
- No `origin` remote at all (local-only repo): no fetch attempted; proceed
  (parity with `_branch_freshness_warning`'s no-origin short-circuit).
- Slice present on `origin/main` but with no frontmatter / unparseable
  `status:`: treat as "cannot read" → warn-and-proceed (AC5), do **not** block.
- `--release` force-clear/takeover path: unaffected — a deliberate release is
  not a collision and must still work.
- `transition` to any status **other than** `IN_PROGRESS`: no new remote read
  is added (scope is start-time only; REVIEWED/RECONCILED freshness unchanged).

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). 3273 tests OK (skipped=9).
- [x] Implementer test coverage exercises each AC with at least one fixture,
      including offline-degrade, the `DONE` block, the foreign-claim block, the
      same-identifier idempotent re-claim, absent-on-`origin`, and the
      `_reserve_claim_on_main` `DONE`-gap (AC6). Remote behavior tested against
      a `file://` bare repo (parity with 051-01's real-git E2E).
- [x] Reviewed by `reviewer` subagent (no implementation context). Reviewer
      prompt built by `review.py` (compliance/craft/arch/reconciliation).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated (deferred push-by-default +
      `session-plan` claim-check follow-ups).

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] `CLAUDE.md` hygiene per spec 025-01: this slice closes spec 051, but the
      Active-specs list is already "none" and no primer surface references 051 —
      nothing to compress. The load-bearing invariant is migrated to the
      status-board Notes column (051-04 row).
- [x] The spec 051 `## Amendments` entry records the shipped behavior
      (supersedes the original "No change to `transition`" non-goal for this
      narrow start-time-collision case); the network-default reversal is
      recorded on spec 049 `## Amendments`.
- [x] `transition` docstring updated with a 051-04 paragraph (there is no
      separate spec-workflow Skills-table row to edit).

**Non-goals (this slice):**
- **Push-by-default `IN_PROGRESS` claim** — the issue's secondary suggestion.
  Separable, and unsafe to ship *before* AC6 (it would otherwise regress
  `DONE` → `IN_PROGRESS` on `origin/main`). Tracked as a follow-up.
- **A standalone `workflow.py claim-check` / `session-plan` collision report**
  — a separate advisory surface. Follow-up.
- **Any change to REVIEWED/RECONCILED freshness behavior** — unchanged.

**Resolved decisions** (authorship, 2026-07-11):
- **Block vs loud-warn for `DONE` → hard-block (exit non-zero).** Full-slice
  duplication is the costliest outcome, and 051-03 already leans "refuse the
  expensive clash." A genuine post-DONE re-open that hasn't reached
  `origin/main` is covered by AC8's explicit bypass, so the block has a
  documented escape rather than a false wall.
- **Escape-hatch name → `JIG_START_COLLISION_GATE=0`.** New, dedicated env
  var (not folded into `JIG_REVIEW_EVIDENCE_GATE`) so the two gates stay
  independently controllable; same falsey-token set and content-free audit
  line as the review-evidence gate.

**Anti-horizontal-phasing check:** After this slice, an agent that picks up a
slice already landed (or actively claimed) by a parallel worktree is stopped
*before* building — the end-to-end value (no silent full-slice duplication) is
delivered at the moment work starts, independent of the deferred
push-by-default and `session-plan` surfaces.

### Deviation log (after reconciliation)

The original spec/ACs are preserved above; implementation notes and
clarifications append here.

1. **What shipped.** `skills/spec-workflow/workflow.py`: two new helpers —
   `_origin_slice_state(project_dir, rel_path)` (never-raising tagged-tuple
   remote read: `no-origin` / `fetch-failed` / `absent` / `unreadable` /
   `present(status, claimed_by)`) and `_refuse_start_collision(...)` (the
   decision layer). The guard is wired into `transition()` on the → IN_PROGRESS
   path **only on the DEFAULT (local) path** (`not (push or pr_mode)`), because
   `_reserve_claim_on_main` already fetches + reads origin/main on the push
   path — the split avoids a double fetch. AC6 added a `DONE` refusal to
   `_reserve_claim_on_main`. Bypass: `JIG_START_COLLISION_GATE` via the shared
   `env_gate_enabled` + `emit_gate_bypass`. The `transition` docstring was
   updated with a 051-04 paragraph. Tests: `StartCollisionGuardTests` +
   `StartCollisionGuardE2E` (recorder + real-git `file://` bare origin).

2. **AC5 wording clarified (compliance + craft nit).** AC5's opening sentence
   lists "no `origin` remote" among the *warn* cases, but it is implemented as
   a **silent** proceed (grouped with `absent`), matching AC5's own edge-case
   bullet and the cited `_branch_freshness_warning` no-origin precedent (which
   returns `""` silently). The loud `start-collision check skipped: <reason>`
   warning is reserved for a genuine fetch failure or an unparseable present
   copy. Read AC5's opening sentence as superseded by its edge-case rows;
   `test_silent_proceed_on_no_origin` pins the silent behavior.

3. **REVIEWED / RECONCILED origin window (craft nit).** The hard block covers
   only `DONE` and foreign `IN_PROGRESS`, per AC2/AC4 scope. An origin copy at
   `REVIEWED`/`RECONCILED` falls through to *proceed* by design — those states
   clear `claimed_by` (spec 049 `_CLAIM_CLEARING_STATUSES`) and are rare on
   origin/main (claims are local by default), so there is no foreign owner to
   collide with; only a landed `DONE` is a definite duplication. Recorded here
   rather than widening the block.
   **[Rationale falsified 2026-07-24 — see `## Amendments`.]**

4. **`relative_to` fallback now warns (craft nit).** The (practically
   unreachable) case where the slice path can't be resolved under the project
   root now emits a loud `start-collision check skipped: …` warning instead of
   a silent skip, for AC5 parity.

5. **`_origin_slice_state` classifier tests added (compliance + craft nit).**
   Added direct recorder tests for the `fetch-failed` and `unreadable` kinds
   (previously covered only transitively).

6. **Reachability asymmetry is intentional (arch note).** The transition-level
   guard is *soft* (fetch-fail / absent / unreadable → proceed); the push-path
   `_reserve_claim_on_main` is *hard* (unreachable origin / absent-on-origin →
   refuse). A start-check legitimately does not require a reachable origin; a
   reservation does. Do not "harmonize" them.

7. **AC6 DONE refusal is NOT bypassable (arch/craft strength).** The
   `_reserve_claim_on_main` DONE refusal is a trunk-integrity guard, deliberately
   excluded from `JIG_START_COLLISION_GATE`: you may force a local start, but
   never regress a landed `DONE` → `IN_PROGRESS` on the shared trunk.

8. **049-01 network-default reversal (arch note).** The default → IN_PROGRESS
   path is no longer network-free — it now runs `git fetch origin main` for the
   collision guard (the local *claim stamp* stays local; only the *check*
   fetches). This reverses spec 049-01's "local by default, no network" claim
   UX for the transition; recorded durably via a `## Amendments` entry on spec
   049 (closed-spec-drift, ADR-0010).

9. **No new ADR (arch confirmed).** This extends Accepted ADR-0015's mechanism
   rather than introducing a new one; the spec 051 `## Amendments` + the
   Resolved-decisions record above are sufficient per ADR-0010.

10. **Read-shape duplication within budget (craft nit).** The
    `git show origin/main:<rel>` + `parse_frontmatter` shape now appears in both
    `_origin_slice_state` and inline in `_reserve_claim_on_main` (2nd caller —
    within ADR-0003's inline-mirror-until-third-caller budget; extraction
    candidate at a third caller).

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `skills/spec-workflow/workflow.py` docstring | `updated` | `transition` docstring gained a 051-04 paragraph. |
| `docs/specs/049-slice-claim-on-in-progress/spec.md` | `updated` | `## Amendments` entry records the → IN_PROGRESS network-default reversal (ADR-0010). |
| `docs/specs/051-worktree-aware-reservation/spec.md` | `updated` | Slices list + `## Amendments` (transition-scope extension) added at authorship; spec rollup rolled to IN_PROGRESS. |
| `docs/decisions/` (ADR) | `no-op` | Arch pass confirmed no new ADR — extension of Accepted ADR-0015. |
| `docs/architecture.md` | `no-op` | No module boundary / public artifact surface changed; no "transition is network-free" invariant asserted there. |
| `CLAUDE.md` primer | `no-op` | Active-specs list is already "none" — nothing to compress. The load-bearing invariant migrates to the status-board Notes column at close-out (see the deferred status-board row below), not to CLAUDE.md. |
| `docs/specs/README.md` status board | `deferred` | Regenerated at close-out (post-DONE). |
| `docs/refinement-todo.md` | `updated` | Added a durable deferred-decision entry for the two scoped-out follow-ups (push-by-default claim; `session-plan` claim-check report) with a resolution trigger — more robust than the slice Non-goals alone (DoD line 116). |
| `docs/memory/` | `deferred` | `/jig:memory-sync` at close-out for the start-collision-guard learning. |

## Amendments

> Post-DONE corrections per [ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md).
> The original record above is preserved; dated entries below record reality.

### 2026-07-24 — dev-log note 3's premise no longer holds (ADR-0043)

Note 3 justified letting a `REVIEWED`/`RECONCILED` origin copy fall through on
the grounds that *"those states clear `claimed_by` … so there is no foreign owner
to collide with"*. Both halves of that premise are now false:

- [ADR-0043](../../decisions/adr-0043-slice-claim-covers-active-lifecycle.md)
  (from [bug 013](../../bugs/013-slice-claim-covers-only-in-progress.md)) makes
  `REVIEWED` and `RECONCILED` **claim-bearing** working states — clearing on
  `→ REVIEWED` is precisely the edge it reverses, because it left reconciliation
  unmarked.
- The constant named here no longer exists: `_CLAIM_CLEARING_STATUSES` was
  renamed `_CLAIM_RELEASE_STATUSES` and now holds the pickup-queue states
  (`DRAFT` / `READY_FOR_IMPLEMENTATION`) plus the terminal three.

The behaviour also changed, in the direction this note declined: a foreign claim
on an `origin/main` copy at a non-`IN_PROGRESS` working state now emits a
**non-blocking warning** from `_refuse_start_collision`. The *hard block* remains
scoped exactly as 051-04 shipped it — `DONE` and both-ends-`IN_PROGRESS` — so
this record's AC2/AC4 scope decision stands; only the "nothing to collide with"
reasoning is withdrawn.

Swept rather than line-corrected, per the bug-011 learning: the withdrawn
phrasing was grepped across `docs/` and this was its only surviving site.
