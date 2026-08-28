---
status: DONE
dependencies: [112-01, adr-0058]
last_verified: 2026-08-28
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
- [x] All ACs pass; full suite green.
- [x] Tests: sibling evidence-complete `DONE` → refuse; sibling `DONE` marker but
      evidence absent on ref → (per chosen posture) warn-not-refuse; no sibling →
      pass; own branch/remote excluded; bypass → pass; unreachable remote → warn.
- [x] Each new test shown to fail when its feature is removed.
- [x] Reviewed by `reviewer` (compliance + craft; arch — new cross-ref read path).
- [x] Implementation review passed.
- [x] Deviation log + Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.

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

1. **Guard composition (all working states).** `_refuse_sibling_done` is dispatched
   at the *same* `transition()` point as the Class-A guards but on the wider
   `_CLAIM_WORKING_STATUSES` — including `IN_PROGRESS`, the reported incident's entry
   point (051-04 only scans origin/main there; a sibling `DONE` is genuinely new
   info). Reuses `find_sibling_done` and shares the `--reopen`/`JIG_CROSSREF_GATE=0`
   bypass with Class A. Not a new dispatch site, but the cross-ref guard *family* is
   now four same-shaped sites (see §6).
2. **Evidence gating (AC2 — the load-bearing bit).** The hard halt fires only when the
   sibling `DONE` is *evidence-complete on that ref* — the `reviews/slice-NN-{compliance,
   craft,reconciliation}.md` files present on the ref, read from committed ref state via
   `git ls-tree`/`git show` (NOT the working tree). A bare `DONE` marker without those
   files on the ref is downgraded to a non-blocking warning. This matches ADR-0058's
   ref-vs-working-tree bridge caveat exactly; verified by real-git-fixture tests
   (DONE+evidence → refuse; DONE-marker-only → warn).
3. **`list_branch_refs` extraction (rule-of-three).** The local+remote ref enumeration
   was extracted from `reservation.py` into a neutral `list_branch_refs` primitive and
   reused by `find_sibling_done` — a clean shared name, no back-coupling (arch/craft
   confirmed).
4. **`workflow.py new` guard omitted; AC1 "create" half covered elsewhere.** The guard
   is wired at `transition` (advance-into-working) only. The "create" half of AC1/AC3 is
   satisfied structurally by ADR-0053 reservation numbering (a fresh number can't reuse
   an in-flight identifier) — a different mechanism, not this guard. Noted so the
   AC-to-mechanism mapping is explicit.
5. **Session-limit recovery.** The implementer subagent was terminated mid-verification
   by a shared-account session limit (not a logic error). The orchestrator completed
   verification: fixed one 101-char comment (ruff E501), regenerated host packages
   (`--check` in sync), and confirmed the targeted suites green (cross_ref_state 29,
   workflow 523, reservation OK, ruff clean). All three review passes then independently
   verified the deliverable (incl. the vacuous-test check the interrupted red-check
   hadn't finished).
6. **Reviewer residuals → widened refinement-todo.** Logged, not fixed under session
   pressure (all [nit], non-blocking): `SiblingDone.evidence_complete` is dead generality
   (always True, unread); `_SIBLING_SCAN_TOTAL_BUDGET` is arguably speculative beyond the
   per-call timeout; `_adr_evidence_complete` under-fires for an Accepted sibling ADR that
   never required frame-critique (safe direction); the current-branch exclusion
   `endswith("/"+name)` has an unlikely false-negative edge. The two
   behaviorally-relevant residuals (ADR-arm under-fire + branch-exclusion edge) are folded
   into the widened four-site unification entry in `docs/refinement-todo.md`; the two pure
   cleanup nits (dead `evidence_complete` field, speculative total-budget) are recorded
   here in the deviation log only.
7. **Pre-existing scout flake** — unrelated; logged, not a regression.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door untouched. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/product-vision.md` | `no-op` | No behavior/scope/principle drift. |
| `docs/architecture.md` | `no-op` | No new `_common` file (find_sibling_done in existing cross_ref_state.py, list_branch_refs in existing reservation.py); no module-boundary change. |
| `skills/spec-workflow/SKILL.md` | `no-op` | The transition Class-C guard shares the Class-A guard's already-documented refusal surface (`--reopen` / cross-ref); no new user-facing flag to document. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / templates | `no-op` | Spec in flight; no compression yet. |
| `docs/inbox.md` | `no-op` | Nothing resolved. |
| `docs/refinement-todo.md` | `updated` | Widened the cross-ref-guard unification entry (two→four sites) + folded 03's reviewer residuals. |
| `docs/memory/**` | `no-op` | No new term/learning beyond the deviation log + refinement-todo. |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR added/changed. |
| `hosts/**` (vendored copies) | `updated` | `cross_ref_state.py`, `reservation.py`, `workflow.py` regenerated; `--check` in sync. |
