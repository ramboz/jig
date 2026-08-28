---
status: DRAFT
dependencies: [112-04, adr-0045, adr-0058]
last_verified:
arch_review: true
frame_review: true
---

## Slice 112-05 — classb-claim-reservation

**Goal:** ADR-0058 Class B (wiring item 3): reserve an identifier via a CAS claim
on entering a working state, and extend ADR-0045's both-ends-`IN_PROGRESS` block
so it consults foreign claims on **sibling/remote refs**, not just the local
checkout — closing the *concurrent-race* duplication class without re-blocking
ADR-0045's sanctioned implementer→reviewer handoff.

**DoR:**
- ✅ 112-04 spike closed — **A1 + A2 + local CAS all hold** (spike findings): the
  primary claim surface is a `refs/claims/<N>` ref used as a compare-and-swap lock
  (local `git update-ref … ""` create-if-absent; cross-machine `git push
  --force-with-lease=refs/claims/<N>:`), with the ADR-0053 `reserve/<N>` branch as
  the fallback for hosts that restrict custom ref namespaces (untested EMU/org
  policy). Treat the remote CAS as best-effort.
- ✅ ADR-0045's boundary semantics re-read (block both-ends-`IN_PROGRESS`;
  warn-and-transfer for other foreign-claim states).

**Acceptance Criteria:**

1. **Reserve:** entering `IN_PROGRESS` on N publishes a claim on the surface the
   spike selected (`refs/claims/<N>` CAS ref, local; pushed for cross-machine — or
   the ADR-0053 reservation-branch fallback). `claimed_by:` remains the
   human-readable owner.
2. **Cross-ref build-boundary halt:** entering `IN_PROGRESS` on an N already
   `IN_PROGRESS`-claimed on a sibling/remote ref **halts-and-reconciles**. This
   *extends the read scope* of ADR-0045's existing block — it does not change
   *when* the block fires.
3. **Preserve ADR-0045 exactly:** a foreign claim on N in any *non-build* working
   state (`REVIEWED`/`RECONCILED`/`READY_FOR_REVIEW`) stays **warn-and-transfer**,
   now cross-ref aware — never a new halt.
4. **Stale-claim release:** a claim from a crashed session is releasable
   (`--release`, spec 049) and — per the liveness policy chosen at spec time
   (TTL / heartbeat / manual) — not a chronic false-halt.
5. **Simultaneous-create race** closed by the CAS: two sessions creating the claim
   concurrently → exactly one wins; the loser is told, and reconciles.
6. **Best-effort offline:** when the remote is unreachable, the local mutex still
   applies and the cross-machine reservation degrades gracefully (no hang).
7. **Host-package parity** regenerated.

**DoD:**
- [ ] All ACs pass; full suite green.
- [ ] Tests: both-ends-`IN_PROGRESS` cross-ref → halt; foreign `REVIEWED` claim →
      warn-and-transfer (NOT halt); simultaneous create → one winner; stale claim
      → releasable; offline → local-only, no hang.
- [ ] Each new test shown to fail when its feature is removed.
- [ ] Reviewed by `reviewer` (compliance + craft; arch — touches ADR-0045's
      claim boundary + adds a reservation lifecycle).
- [ ] Implementation review passed.
- [ ] Deviation log + Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Assumptions:**

- **Load-bearing:** A3 (claim liveness) — that stale claims are cheaply
  distinguishable — determines whether AC2 can be a hard halt vs a strong nudge
  (ADR-0058 Kill criteria). Surfaced for frame-critique.

**Anti-horizontal-phasing check:** After this slice, two sessions racing to build
the same slice — same machine or across machines — resolve to one, at the
transition command, without disturbing legitimate review handoffs.

### Deviation log (after reconciliation)

_TBD at implementation._

### Reconciliation sweep

_TBD at reconciliation._
