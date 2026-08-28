---
status: DRAFT
dependencies: [112-01, adr-0058]
last_verified:
arch_review: true
frame_review: true
---

## Slice 112-03 — classc-sibling-done-read

**Goal:** Close the **reported incident** (ADR-0058 Class C, wiring item 2): at
create / advance-into-working, read local+remote sibling refs for the same
identifier at an *evidence-complete* `DONE`, and **halt-and-reconcile** ("build on
that branch / integrate it — don't duplicate") with a bypass. This is the case
neither the Class-A gate (not on `origin/main`) nor the Class-B claim mutex (claim
cleared at `DONE`) catches.

**DoR:**
- ✅ 112-01 DONE (the `identifier_state_on_ref` primitive + per-ref read exist).

**Acceptance Criteria:**

1. **Sibling scan** reuses `reservation.py`'s local+remote ref enumeration and the
   112-01 per-ref read to find any ref (other than the current branch / its own
   remote) where identifier N is at `DONE`/`Accepted`, matching on number.
2. **Evidence gating (per ADR-0058 Open-question / bridge caveat):** the halt
   fires on a sibling `DONE` whose recorded review-evidence files
   (`reviews/…`) are present *on that ref* (the stronger, ADR-0014-keyed read).
   The ref-vs-working-tree distinction is handled explicitly: the check reads
   committed ref state via `git show <ref>:<path>`.
3. **Halt-and-reconcile:** on a hit, create/advance is refused with a message
   naming the sibling ref + its `DONE` state, and the reconcile guidance (build on
   / integrate that branch). Exit non-zero.
4. **Bypass:** a deliberate re-do (`JIG_CROSSREF_GATE=0`, or a `--reopen`-style
   flag) proceeds — covering the abandoned-but-evidence-complete branch and the
   sanctioned parallel-completion case.
5. **Best-effort:** unreachable remote refs → the scan degrades to a non-blocking
   warning; never hangs (timeout-guarded).
6. **Host-package parity** regenerated.

**DoD:**
- [ ] All ACs pass; full suite green.
- [ ] Tests: sibling evidence-complete `DONE` → refuse; sibling `DONE` marker but
      evidence absent on ref → (per chosen posture) warn-not-refuse; no sibling →
      pass; own branch/remote excluded; bypass → pass; unreachable remote → warn.
- [ ] Each new test shown to fail when its feature is removed.
- [ ] Reviewed by `reviewer` (compliance + craft; arch — new cross-ref read path).
- [ ] Implementation review passed.
- [ ] Deviation log + Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Assumptions:**

- **Load-bearing:** the evidence-vs-working-tree bridge (AC2) — jig's `DONE`
  requires recorded verdicts, but ADR-0014 validates the *working tree* at
  transition while this reads *committed ref state*; the incident case (a landed
  sibling) has both, but the general strength of the signal depends on evidence
  files being committed on the ref. Surfaced for frame-critique.

**Anti-horizontal-phasing check:** After this slice, a session that would rebuild
a slice already finished on a sibling branch is stopped at the door with the
sibling named — the reported incident, closed at a real command.

### Deviation log (after reconciliation)

_TBD at implementation._

### Reconciliation sweep

_TBD at reconciliation._
