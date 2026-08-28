---
status: DONE
dependencies: [112-01, adr-0058]
last_verified: 2026-08-27
frame_review: true
---

## Slice 112-02 — classa-create-advance

**Goal:** Extend the Class-A hard gate to the earliest boundary — `workflow.py
transition` into a working state (and, where meaningful, `workflow.py new`) —
reusing the slice 112-01 primitive, so a session on a stale branch cannot
advance an identifier that is already `DONE`/`Accepted` on `origin/main`.

**DoR:**
- ✅ 112-01 DONE (primitive + gate posture established).

**Acceptance Criteria:**

1. **`transition … <working-state>` consults the primitive.** When the target
   identifier is already `DONE`/`Accepted` on `origin/main`, the transition is
   refused with a Class-A message naming the integrated state — before the status
   flip. Applies to advancing an existing slice/ADR, the stale-branch re-advance
   case.
2. **Scope guard:** the gate targets *advancing/re-opening* an already-integrated
   identifier, not ordinary forward progress on un-integrated work. A slice that
   is absent-or-earlier on `origin/main` transitions normally.
3. **Sanctioned re-open path.** A deliberate re-open of integrated work
   (supersession, or a revert-then-redo where the marker wasn't reverted) is
   passable via a bypass **distinct from the blanket** `JIG_CROSSREF_GATE=0`
   error-case escape (e.g. an explicit `--reopen`/`--supersede` flag) — resolves
   ADR-0058 Open-question 4. Exact surface decided in implementation.
4. **Best-effort + bypass** inherit slice 112-01's contract (unreachable base →
   warn-not-fail; `JIG_CROSSREF_GATE=0` skips).
5. **Host-package parity** regenerated.

**DoD:**
- [x] All ACs pass; full suite green.
- [x] Tests: integrated-DONE advance → refuse; un-integrated advance → pass;
      sanctioned re-open flag → pass; bypass → pass; unreachable base → warn.
- [x] Each new test shown to fail when its feature is removed.
- [x] Reviewed by `reviewer` subagent (compliance + craft).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, `workflow.py transition` on
a stale branch refuses to advance work that is already integrated on main —
observable at the command, closing the Class-A catch at the *earliest* boundary.

### Deviation log (after reconciliation)

1. **Scope split with the existing 051-04 start-collision guard.** `transition`
   already had `_refuse_start_collision` (slice 051-04) which Class-A-blocks
   `→ IN_PROGRESS` when the slice is `DONE` on `origin/main` (verified by the
   compliance review at `workflow.py:4806`). Rather than duplicate/replace that
   mature path (which also does Class-B foreign-claim work), the new
   `_refuse_integrated_advance` covers the *other* three working states
   (`READY_FOR_REVIEW` / `REVIEWED` / `RECONCILED`), reusing the 112-01
   `identifier_state_on_ref` primitive. Together they cover AC1 across all four
   working states.
2. **`--reopen` flag (AC3)** added to `transition` — a first-class, audited
   bypass for sanctioned re-open / supersession, distinct from the blanket
   `JIG_CROSSREF_GATE=0`; short-circuits before the git read.
3. **`workflow.py new` guard deliberately omitted (leanness).** `new` reserves
   `max+1`, so a freshly-reserved identifier structurally cannot target an
   already-integrated `DONE`; a guard there would be a no-op on the hot path.
4. **ADR arm not added to `transition`.** `transition` only advances slice labels
   (`NNN-MM`); ADR lifecycle advancement is `adr.py accept`, and land.py's 112-01
   backstop already blocks a branch introducing a duplicate-numbered ADR. Adding
   a per-transition ADR diff would be cost for no added coverage.
5. **Incidental test fix.** `Bug014WidenedClaimTests.test_push_at_working_state_
   is_silent_about_our_own_in_progress_trunk_claim` needed `identifier_state_on_ref`
   mocked (a non-git tmpdir) now that the new guard runs on push-path working-state
   transitions. Behavior unchanged; a fixture-only adjustment.
6. **Rule-of-three drift + `--reopen` asymmetry → refinement-todo.** There are now
   three cross-ref-DONE sites (`_refuse_start_collision`, `_refuse_integrated_advance`,
   `land.py check_cross_ref_state`) with divergent helpers/bypass surfaces, and
   `--reopen` covers only the advance guard (the `→ IN_PROGRESS` path still uses
   `JIG_START_COLLISION_GATE=0`). Unification deferred with a stated trigger in
   `docs/refinement-todo.md` (craft-review nit; deferral justified — avoids double
   origin read + risking 051-04's Class-B logic).
7. **Pre-existing scout flake** (`test_codex_semantic_index_internal_overlay_fixture_
   activates_scout`) — unrelated to this slice; logged, not a regression.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door untouched. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/product-vision.md` | `no-op` | No behavior/scope/principle drift. |
| `docs/architecture.md` | `no-op` | No module-boundary/public-contract change (guard is internal to `transition`, reuses the 112-01 primitive already rostered). |
| `skills/spec-workflow/SKILL.md` | `updated` | Documented the Class-A cross-ref advance guard + `--reopen` bypass in the transition section (live-prose drift fix). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / templates | `no-op` | Spec in flight; no primer compression yet. |
| `docs/inbox.md` | `no-op` | Nothing resolved. |
| `docs/refinement-todo.md` | `updated` | Added the two-guard unification deferred item (rule-of-three + `--reopen` asymmetry). |
| `docs/memory/**` | `no-op` | No new term/learning beyond the deviation log + refinement-todo. |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR added/changed. |
| `hosts/**` (vendored copies) | `updated` | `workflow.py` + `SKILL.md` regenerated via `build_host_packages.py`; `--check` in sync. |
