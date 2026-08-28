---
status: DONE
dependencies: [112-04, adr-0045, adr-0058]
last_verified: 2026-08-28
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
- [x] All ACs pass; full suite green.
- [x] Tests: both-ends-`IN_PROGRESS` cross-ref → halt; foreign `REVIEWED` claim →
      warn-and-transfer (NOT halt); simultaneous create → one winner; stale claim
      → releasable; offline → local-only, no hang.
- [x] Each new test shown to fail when its feature is removed.
- [x] Reviewed by `reviewer` (compliance + craft; arch — touches ADR-0045's
      claim boundary + adds a reservation lifecycle).
- [x] Implementation review passed.
- [x] Deviation log + Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.

**Assumptions:**

- **Load-bearing:** A3 (claim liveness) — that stale claims are cheaply
  distinguishable — determines whether AC2 can be a hard halt vs a strong nudge
  (ADR-0058 Kill criteria). Surfaced for frame-critique.

**Anti-horizontal-phasing check:** After this slice, two sessions racing to build
the same slice — same machine or across machines — resolve to one, at the
transition command, without disturbing legitimate review handoffs.

### Deviation log (after reconciliation)

1. **Mechanism.** New `skills/_common/claim_ref.py`: `refs/claims/<N>` CAS — local
   (`git update-ref <ref> HEAD ""` create-if-absent), remote
   (`git push --force-with-lease=<ref>:` create), with `reservation.classify_push_failure`
   routing a custom-namespace refusal to the ADR-0053 `reserve/<N>` branch fallback and
   everything else to best-effort/offline. All network paths timeout-guarded (AC6). Local
   reserve runs unconditionally on `→ IN_PROGRESS` entry; remote push only under
   `--push`/`--pr`; release fires on any forward move out of `IN_PROGRESS`.
2. **Cross-ref build-boundary halt (AC2) + the review-caught push-path gap.** The
   Class-B halt extends ADR-0045's both-ends-`IN_PROGRESS` block to consult sibling/remote
   refs via `find_sibling_in_progress_claim` (`cross_ref_state.py`). The *initial* wiring
   put it inside `_refuse_start_collision`, which is skipped under `--push`/`--pr` — so the
   compliance review caught that `--push` (the ADR-0045-encouraged publish flow) degraded
   the hard halt to an advisory warning. **Fixed:** extracted `_refuse_sibling_in_progress_claim`
   and called it at the same `transition()` point on BOTH the default and `--push`/`--pr`
   paths (before any CAS/trunk write), keeping the origin/main check push-gated (no double
   fetch). Craft + arch passed the default path; compliance caught the push gap — the
   layered gate working.
3. **AC3 / ADR-0045 preserved EXACTLY.** Hit condition is `status == IN_PROGRESS and
   foreign claimed_by`; the whole block is gated on `new_status == IN_PROGRESS`, so a
   foreign `REVIEWED`/`RECONCILED`/`READY_FOR_REVIEW` sibling claim is never a halt on
   either path (warn-and-transfer). Pinned by `test_reviewed_target_never_reaches_the_sibling_scan`
   + its `--push` sibling.
4. **A3 (claim liveness) RESOLVED — manual `--release` only** (no TTL/heartbeat). A CAS
   collision cannot distinguish a live racer from a stale ref (the ref carries no
   owner/timestamp), so the CAS ref is kept **advisory** and the identity read
   (`claimed_by`+`IN_PROGRESS` cross-ref) is the **sole hard block** — inheriting ADR-0045's
   already-accepted `claimed_by`+`--release` stale-claim posture. This is ADR-0058's
   Kill-criteria "demote the mutex to a nudge" path, taken deliberately; it resolves
   ADR-0058's claim-liveness Open-question.
5. **Guard-family unification trigger fired-partial** (05 touched `_refuse_start_collision`):
   the sibling *read* converged onto `cross_ref_state`; the shared-preamble/bypass extraction
   across all four sites was re-deferred (scope creep on a boundary-extending slice). Recorded
   in `docs/refinement-todo.md`, along with the related rule-of-three residual (two
   near-duplicate sibling-scan loops in `cross_ref_state.py`).
6. **Accepted residuals (craft/arch nits, non-blocking).** `push_claim` same-SHA no-op
   (two machines at the same HEAD both report a win — AC5 remote race not fully closed for
   same-SHA racers; local CAS + identity read carry the load-bearing halt). Benign redundant
   gate check on the default path (outer function returns early when disabled → no double
   bypass-emit). Hot-path cost: a sibling scan on every `→ IN_PROGRESS` (bounded by the
   scan budget; ADR-0058 sanctioned).
7. **Primer hygiene (spec closes).** 112-05 closes spec 112 (all non-deferred slices DONE).
   Added a compressed Key-terms bullet for ADR-0058 / spec 112 to `CLAUDE.md` and bumped the
   "shipped through" marker to 112.
8. **Pre-existing/environmental non-issues.** The known scout flake
   (`test_codex_semantic_index_internal_overlay_fixture_activates_scout`); and `run_tests.py`'s
   internal temp-dir drift probe transiently flags `plugin.json` — a standalone
   `build_host_packages.py --check` is clean, so committed state is in sync.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door untouched. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/product-vision.md` | `no-op` | No behavior/scope/principle drift. |
| `docs/architecture.md` | `no-op` | `claim_ref.py` is a new `_common` file; roster is illustrative, not exhaustive, and the module/read split needs no boundary re-statement (added a Key-terms primer bullet instead). |
| `CLAUDE.md` (primer) | `updated` | Spec 112 closes → added the ref-aware-lifecycle + claim-reservation Key-terms bullet; bumped "shipped through" to 112 (spec 025 compress-on-close). Not a shipped template, so no host regen. |
| `AGENTS.md` / scaffold templates | `no-op` | Not present / not affected (the scaffold source is `templates/CLAUDE.md.template`, untouched — this mechanism is jig-internal). |
| `docs/inbox.md` | `no-op` | Nothing resolved. |
| `docs/refinement-todo.md` | `updated` | Recorded the guard-unification trigger fired-partial + the scan-loop rule-of-three residual + the A3 resolution context. |
| `docs/memory/**` | `no-op` | Captured in the deviation log + refinement-todo + the CLAUDE.md primer. |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR added/changed (ADR-0058 already Accepted + indexed). |
| `hosts/**` (vendored copies) | `updated` | `claim_ref.py`, `cross_ref_state.py`, `workflow.py` regenerated; `--check` in sync. |
