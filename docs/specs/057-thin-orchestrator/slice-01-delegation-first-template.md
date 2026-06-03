---
status: DRAFT
dependencies: [055-01, 056-03]
last_verified:
arch_review: true  # adds a workflow.py CLI surface + a new orchestration pattern
---

## Slice 057-01 — Delegation-first session template

**Goal:** When picking up a spec, the orchestrator gets a **deterministic
dispatch plan** — each non-DEFERRED slice mapped to its phase sequence
(implement → reviews → reconcile → land) with the subagent type + skill for
each phase — so it *dispatches and integrates* rather than doing turn-heavy
work itself. Cuts orchestrator **turn count**, the data-confirmed cost driver
(cost ∝ turns, r = 0.92).

**DoR:**
- ✅ 055 mechanisms landed (this builds on the delegate-reads philosophy).
- ✅ 056 token tracking + `.jig/spec-ref` marker landed (to verify the
  turn-count / cost effect on disciplined vs undisciplined slices).
- ✅ Deep-dive findings recorded in `spec.md` Overview (the rationale).
- ✅ Open question #1 (helper vs template vs skill) resolved at clarify.

**Acceptance Criteria:**

1. **A dispatch plan is emitted from the spec deterministically.** Given a spec
   path, `workflow.py session-plan <spec>` prints **to stdout** (clarify Q1/Q2)
   each non-DEFERRED slice and, per slice, the
   standard phase sequence — implement → compliance → craft →
   *arch (iff the slice's `arch_review: true`)* → reconcile → land — naming the
   subagent type and skill for each phase. Output is a function of the spec's
   slices + their frontmatter (no hidden state).
2. **It is delegation-first.** The plan explicitly marks the delegated
   (subagent) phases vs the orchestrator's dispatch loop, and recommends pushing
   multi-turn sub-work into bounded subagents that return summaries — naming the
   turn-count rationale (the orchestrator re-reads its full context every turn).
3. **"Run thin" guidance exists.** `docs/workflow.md` gains a delegation-first /
   dispatch-and-integrate section, reachable from the Hot-Cache/template pointer
   (parity with 055-01's doc pattern). A doc-presence test asserts it.
4. **Soft / non-blocking.** The plan is advisory output; nothing is enforced or
   gated on it. Producing it has no side effects on spec/slice state.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Coverage: a multi-slice spec yields the correct per-slice phase plan; an
      `arch_review: true` slice includes the arch phase and a normal slice omits
      it; a DEFERRED slice is excluded; the doc section is present.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Arch (arch-review) pass run (slice declares `arch_review: true`); blockers addressed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice a developer runs one
command (or follows one template) and gets the full delegation checklist for a
spec, then executes by dispatching — usable end-to-end, not intermediate state.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the dispatch-plan
      shape + the turn-count rationale.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (if this slice + 057-02 close the spec,
      compress the Active-specs entry). If a new skill is introduced, add its row.
