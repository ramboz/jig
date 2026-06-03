---
status: DONE
dependencies: [055-01, 056-03]
last_verified: 2026-06-03
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
- [x] All ACs pass; full test suite green (no regressions).
- [x] Coverage: a multi-slice spec yields the correct per-slice phase plan; an
      `arch_review: true` slice includes the arch phase and a normal slice omits
      it; a DEFERRED slice is excluded; the doc section is present.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Arch (arch-review) pass run (slice declares `arch_review: true`); blockers addressed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (None deferred — the spec-level edge-case gap was resolved in-implementation.)

**Anti-horizontal-phasing check:** After this slice a developer runs one
command (or follows one template) and gets the full delegation checklist for a
spec, then executes by dispatching — usable end-to-end, not intermediate state.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the dispatch-plan
      shape + the turn-count rationale.
- [x] `CLAUDE.md` hygiene per spec 025-01 (Active-specs was already "(none)"; added
      a "Thin-orchestrator discipline" Key-terms entry for spec 057 and noted
      `session-plan` on the `/jig:spec-workflow` skill row — no new skill introduced).

### Deviation log

The spec above is preserved. Implementation notes:

1. **What shipped.** `workflow.py session-plan <spec.md>` (clarify Q1/Q2: helper
   form, stdout-only) — enumerates the spec's non-DEFERRED slices via the shared
   `_common.parsing.iter_slices` and prints, per slice, the standard phase
   sequence: implement → compliance → craft → [arch iff the slice's frontmatter
   declares `arch_review: true`] → reconcile → land, naming the subagent type and
   skill for each phase (`[subagent]` / `{skill}` markup). Arch-phase truthiness
   reuses the shared `frontmatter_flag_truthy` / `FRONTMATTER_TRUTHY` predicate
   (no hand-rolled truthiness — same source the gate reads, per slice 045-03).
   Output is a pure function of the slices + their frontmatter; no side effects on
   spec/slice state. `docs/workflow.md` gained a `### Run thin — dispatch and
   integrate` subsection under Context-cost discipline (parity with 055-01's doc
   pattern), reachable from the existing Hot-Cache/template context-cost pointer.

2. **Empty / non-standard-slice edge case (coverage-summary deferred item).**
   Decision: a spec with **zero non-DEFERRED slices** prints a clear
   `No slices to plan (<reason>).` line — exit 0, no crash, no empty plan. The
   message distinguishes the two empty cases: `this spec has no slices` (no
   slice files / sections at all) vs `every slice is DEFERRED`. Rationale: the
   command is advisory/soft (AC #4); a missing or fully-parked spec is a valid
   query, not an error, and the reason aids the reader. Covered by
   `test_no_slices_to_plan_message` + `test_no_slices_at_all_message`.

3. **Subagent/skill mapping** is sourced from CLAUDE.md "Session workflow" +
   `docs/workflow.md` Post-implementation review. Held as a module-level table
   (`_SESSION_PLAN_PHASES`) so the sequence is a single source of truth. The
   output distinguishes two kinds of phase: **DELEGATE to a [subagent]** (runs
   in an isolated context) vs an **ORCHESTRATOR step** (the orchestrator's own
   dispatch loop), and only names a real jig `{skill}` when the phase runs one:
   implement → DELEGATE `[implementer]` (the implementer *agent*, no skill);
   compliance → DELEGATE `[reviewer]` runs `{jig:independent-review}`; craft →
   DELEGATE `[reviewer]` runs `{pr-review}`; arch → DELEGATE `[reviewer]` runs
   `{arch-review}`; reconcile → ORCHESTRATOR step runs `{jig:independent-review}`;
   land → ORCHESTRATOR step runs `{jig:slice-land}`.

4. **Deviation-log location.** Slice instruction suggested
   `docs/specs/057-thin-orchestrator/deviations.md`, but the repo's established
   convention (056, 055, and prior specs) is a `### Deviation log` subsection
   **inside the slice file**. Followed the repo convention, as the instruction
   directed when one exists.

5. **Test environment.** Full `test_workflow.py` run: 225 tests, 10 new
   (SessionPlan + doc-presence) all pass. 4 pre-existing errors in
   `NewSpecScaffoldsFilePerSliceTests` (`ModuleNotFoundError: No module named
   'skills'`) reproduce on the pristine baseline and are unrelated — they need
   pytest-from-repo-root package resolution, not the plain `python3` invocation
   available in this environment.

6. **Post-review reconciliation fix (craft + arch nit).** The first cut rendered
   every phase as `DELEGATED to [actor] via {skill}`, which mislabeled the
   `implement` phase (`{jig:implementer}` — an *agent*, not a skill) and
   `reconcile` (`{reconciliation review}` — a *phase*, not a skill), and tagged
   orchestrator-driven steps (reconcile/land) as if they were isolated-subagent
   work. Both independent reviewers (craft, arch) flagged this as a non-blocking
   honesty nit. Addressed inline before recording verdicts: the `{skill}` slot now
   names only real skills, `implement` carries no skill, and reconcile/land render
   as `ORCHESTRATOR step` rather than `DELEGATED`. Tests re-run green (17/17 in the
   SessionPlan + doc + arch-flag suites); the substring assertions were format-
   agnostic so no test changes were needed.
