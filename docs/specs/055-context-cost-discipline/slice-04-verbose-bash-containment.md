---
status: DONE
dependencies: [055-01]
last_verified: 2026-06-01
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
- [x] All ACs pass; full test suite green. 1857 tests, OK (3 skipped).
- [x] Coverage asserts `agents/implementer.md` carries the
      surface-only-results instruction, and that the tdd-loop contract is
      unchanged.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed (2 nits → both fixed; none blocking).
- [x] Deviation log produced.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if decisions were deferred (n/a — no deferrals).

**Anti-horizontal-phasing check:** After this slice the workflow keeps verbose
command output — a ≈ 19% context slice — out of the expensive orchestrator
context by default.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the
      implementer surface-only-results contract.
- [x] CLAUDE.md hygiene per spec 025-01 rule (n/a — spec 055 has no entry in
      the repo CLAUDE.md's Active specs to compress; it lists none).

### Deviation log (after reconciliation)

The spec above is preserved. Implementation notes:

1. **What shipped.** Implemented via the `jig:implementer` subagent (strict
   TDD). `agents/implementer.md` gains a "Surface results, not logs" section
   (the implementer runs its own test/build commands and surfaces only the
   result — pass/fail + key failing lines — not full logs) plus an
   Output-format clause. `docs/workflow.md`'s Context-cost discipline section
   gains a "Keep verbose command output out of the orchestrator" rule (citing
   the ≈19% Bash-output share) with two concrete idioms (run the suite via the
   implementer; for one-off orchestrator commands prefer summarizing/quiet
   flags + bounded VCS views, or pipe to a count). `scripts/test_context_cost_discipline.py`
   gains 3 classes asserting the implementer instruction, the verbose-Bash
   rule, and (source-level) that the tdd-loop contract is intact.
   `skills/tdd-loop/tdd.py` untouched. Suite: 1857 tests, OK (3 skipped).

2. **Dogfooding note.** Implementation + all three review passes ran in
   isolated subagents; the orchestrator kept only summaries — the very
   discipline this slice documents.

3. **Review findings folded in** (compliance + craft both `pass`; evidence in
   `reviews/slice-04-{compliance,craft}.md`):
   - *Fixed (craft nit)* — tightened the summarize-idiom assertion from the
     bare substring `"pipe"` (would match `pipeline`) to the concrete `"wc -l"`
     token.
   - *Fixed (both passes' nit)* — broadened the test module docstring, which
     read "055-01" only, to note the 055-04 additions (implementer instruction,
     verbose-Bash rule, tdd-loop guard).

4. **Plan adherence / impact.** Followed the planned shape (implementer-prompt
   + workflow guidance + docs-lint tests). AC #4 (no tdd-loop regression)
   satisfied by leaving `tdd.py` untouched + a source-level guard; runtime
   coverage stays in the untouched `test_tdd.py`. No conventions or
   architecture impact; no ADR. Inbox: nothing to park.

5. **Spec close-out.** Final slice — 055-01/02/03 are DONE; transitioning
   055-04 to DONE closes spec 055 (the context-cost discipline workstream:
   delegate-reads, in-session growth nudge, read-once/read-lean, verbose-Bash
   containment).
