---
status: IN_PROGRESS
dependencies: [112-01, adr-0058]
last_verified:
frame_review: true
claimed_by: claude/jig-conflict-cleanup-3c1218
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
- [ ] All ACs pass; full suite green.
- [ ] Tests: integrated-DONE advance → refuse; un-integrated advance → pass;
      sanctioned re-open flag → pass; bypass → pass; unreachable base → warn.
- [ ] Each new test shown to fail when its feature is removed.
- [ ] Reviewed by `reviewer` subagent (compliance + craft).
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, `workflow.py transition` on
a stale branch refuses to advance work that is already integrated on main —
observable at the command, closing the Class-A catch at the *earliest* boundary.

### Deviation log (after reconciliation)

_TBD at implementation._

### Reconciliation sweep

_TBD at reconciliation._
