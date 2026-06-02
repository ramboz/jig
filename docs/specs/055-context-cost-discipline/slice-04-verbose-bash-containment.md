---
status: READY_FOR_REVIEW
dependencies: [055-01]
last_verified:
---

## Slice 055-04 — Keep verbose command output out of the orchestrator

**Goal:** Route verbose command output (test suites, builds, long `git
log`/`diff`) into the implementer subagent — or a summarized form — so it
never lands in the orchestrator's re-read loop. Bash output is ≈ 19% of
orchestrator context.

**DoR:**
- ✅ 055-01 landed (principle + discipline section).

**Acceptance Criteria:**

1. `agents/implementer.md` is updated to make explicit that the implementer
   runs its own test/build commands and surfaces only the **result**
   (pass/fail + the key failing lines) to the orchestrator, not full logs.
2. The `docs/workflow.md` "Context-cost discipline" section gains the rule:
   verbose commands (full test runs, builds, `git log`) belong in a subagent,
   or should be reduced to a summary before entering orchestrator context.
3. The guidance gives concrete idioms (run the suite via the implementer; for
   one-off orchestrator commands prefer summarizing flags / piping to a count
   over dumping full output).
4. No regression to the existing implementer TDD behavior or the `tdd-loop`
   helper contract (`tdd.py` normalized exit codes unchanged).

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Coverage asserts `agents/implementer.md` carries the
      surface-only-results instruction, and that the tdd-loop contract is
      unchanged.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if decisions were deferred.

**Anti-horizontal-phasing check:** After this slice the workflow keeps verbose
command output — a ≈ 19% context slice — out of the expensive orchestrator
context by default.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the
      implementer surface-only-results contract.
- [ ] CLAUDE.md hygiene per spec 025-01 rule (this is the last planned slice —
      if it closes the spec, compress the Active-specs entry).
